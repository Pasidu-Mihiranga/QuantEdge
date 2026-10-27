"""LSTM deep challenger: joint VaR/ES network trained on pinball + FZ0 (Step 23).

Head (loss units, positive = loss):  q90 = a,  q95 = q90 + softplus(b),  q99 = q95 + softplus(c),
ES99 = q99 + softplus(d)  ->  q90 <= q95 <= q99 <= ES99 on every row, by construction.
Loss: pinball_90 + pinball_95 + lambda * FZ0(VaR99, ES99), with FZ0 shared with backtest.scoring.
Research-only: torch is in requirements-research.txt and is never imported by the app.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from torch import nn

LEVELS = (0.90, 0.95, 0.99)


def set_determinism(seed: int) -> None:
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def make_sequences(X: pd.DataFrame, L: int, train_end: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Standardise with rows < train_end only, then build windows ending at each row t (rows t-L+1..t).
    Returns (sequences, row positions, scaler stats). Rows with incomplete windows are skipped."""
    values = X.to_numpy(dtype=np.float32)
    mu = np.nanmean(values[:train_end], axis=0)
    sd = np.nanstd(values[:train_end], axis=0)
    sd[sd == 0] = 1.0
    z = np.nan_to_num((values - mu) / sd, nan=0.0)
    pos = np.arange(L - 1, len(z))
    seqs = np.stack([z[p - L + 1: p + 1] for p in pos]).astype(np.float32)
    return seqs, pos, np.vstack([mu, sd])


class JointQuantileLSTM(nn.Module):
    def __init__(self, n_features: int, hidden: int = 32, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, num_layers=1, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.dense = nn.Sequential(nn.Linear(hidden, 16), nn.ReLU())
        self.head = nn.Linear(16, 4)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h, _ = self.lstm(x)
        o = self.head(self.dense(self.drop(h[:, -1, :])))
        sp = nn.functional.softplus
        q90 = o[:, 0]
        q95 = q90 + sp(o[:, 1])
        q99 = q95 + sp(o[:, 2])
        es99 = q99 + sp(o[:, 3])
        return torch.stack([q90, q95, q99, es99], dim=1)


def pinball_t(loss: torch.Tensor, q: torch.Tensor, a: float) -> torch.Tensor:
    return ((a - (loss < q).float()) * (loss - q)).mean()


def fz0_t(loss: torch.Tensor, var: torch.Tensor, es: torch.Tensor, a: float, floor: float = 1e-6) -> torch.Tensor:
    """FZ0 on returns y = -loss with v = -VaR, e = -ES (same formula as backtest.scoring.fz0)."""
    y, v = -loss, -var
    e = -torch.clamp(es, min=floor)
    p = 1.0 - a
    hit = (y <= v).float()
    return (-(1.0 / (p * e)) * hit * (v - y) + v / e + torch.log(-e) - 1.0).mean()


def joint_loss(out: torch.Tensor, loss: torch.Tensor, lam: float = 1.0) -> torch.Tensor:
    return (pinball_t(loss, out[:, 0], 0.90) + pinball_t(loss, out[:, 1], 0.95)
            + lam * fz0_t(loss, out[:, 2], out[:, 3], 0.99))


@dataclass
class LSTMConfig:
    seq_len: int = 60
    hidden: int = 32
    dropout: float = 0.2
    weight_decay: float = 1e-4
    lr: float = 1e-3
    batch: int = 64
    max_epochs: int = 300
    patience: int = 20
    fz0_weight: float = 1.0
    loss_scale: float = 100.0   # train on losses in percent for numerically friendly gradients


def train_window(seqs: np.ndarray, y: np.ndarray, cfg: LSTMConfig, seed: int,
                 init_state: dict | None = None) -> JointQuantileLSTM:
    """Train on time-ordered sequences; early stopping on the last 20% (never shuffled across the cut)."""
    set_determinism(seed)
    model = JointQuantileLSTM(seqs.shape[2], cfg.hidden, cfg.dropout)
    if init_state is not None:
        model.load_state_dict(init_state)
    cut = int(len(seqs) * 0.8)
    Xt, yt = torch.from_numpy(seqs[:cut]), torch.from_numpy((y[:cut] * cfg.loss_scale).astype(np.float32))
    Xv, yv = torch.from_numpy(seqs[cut:]), torch.from_numpy((y[cut:] * cfg.loss_scale).astype(np.float32))
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    gen = torch.Generator().manual_seed(seed)
    best, best_state, bad = float("inf"), None, 0
    for _ in range(cfg.max_epochs):
        model.train()
        for b in torch.randperm(len(Xt), generator=gen).split(cfg.batch):  # shuffling within the training part only
            opt.zero_grad()
            joint_loss(model(Xt[b]), yt[b], cfg.fz0_weight).backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.no_grad():
            v = float(joint_loss(model(Xv), yv, cfg.fz0_weight))
        if v < best - 1e-6:
            best, best_state, bad = v, {k: t.clone() for k, t in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= cfg.patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model


def walk_forward_lstm(X: pd.DataFrame, target: pd.Series, cfg: LSTMConfig, seeds=(11, 22, 33, 44, 55),
                      retrain_every: int = 63, min_train: int = 750, start=None, end=None) -> pd.DataFrame:
    """Expanding-window walk-forward with a seed ensemble (averaging preserves the ordering).

    For forecast origin t, the scaler and training sequences use rows strictly before t; the
    output is indexed by the forecast day (origin + 1) like the other backtests.
    """
    data = pd.concat([X, target.rename("__y")], axis=1).dropna()
    feats = data.drop(columns="__y")
    yv = data["__y"].to_numpy()
    next_day = pd.Series(target.index[1:], index=target.index[:-1])
    origins = data.index
    lo = max(min_train, int(origins.searchsorted(pd.Timestamp(start)))) if start is not None else min_train
    hi = int(origins.searchsorted(pd.Timestamp(end), side="right")) if end is not None else len(origins)
    rows, models, last, states = [], None, -10**9, {}
    for i in range(lo, hi):
        if models is None or i - last >= retrain_every:
            seqs, pos, _ = make_sequences(feats, cfg.seq_len, train_end=i)
            train_mask = pos < i
            models = [train_window(seqs[train_mask], yv[pos[train_mask]], cfg, s, states.get(s)) for s in seeds]
            states = {s: m.state_dict() for s, m in zip(seeds, models, strict=True)}
            forecast_seqs, forecast_pos = seqs, pos
            last = i
        k = int(np.searchsorted(forecast_pos, i))
        with torch.no_grad():
            preds = np.mean([m(torch.from_numpy(forecast_seqs[k:k + 1])).numpy()[0] for m in models], axis=0)
        preds = preds / cfg.loss_scale
        origin = origins[i]
        if origin not in next_day.index:
            continue
        loss = float(yv[i])
        rows.append({"date": next_day[origin], "loss": loss,
                     "var_0.9": preds[0], "var_0.95": preds[1], "var_0.99": preds[2], "es_0.99": preds[3],
                     "hit_0.9": int(loss > preds[0]), "hit_0.95": int(loss > preds[1]),
                     "hit_0.99": int(loss > preds[2])})
    return pd.DataFrame(rows).set_index("date")
