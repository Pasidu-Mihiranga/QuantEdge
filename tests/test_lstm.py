"""Step 23 acceptance tests for the LSTM challenger."""

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from quantedge.backtest.scoring import fz0  # noqa: E402
from quantedge.ml.lstm_quantile import (  # noqa: E402
    JointQuantileLSTM,
    LSTMConfig,
    fz0_t,
    make_sequences,
    train_window,
    walk_forward_lstm,
)


def test_outputs_are_ordered_by_construction():
    torch.manual_seed(0)
    model = JointQuantileLSTM(5, hidden=8)
    out = model(torch.randn(256, 20, 5)).detach().numpy()
    assert np.all(np.diff(out, axis=1) >= 0)   # q90 <= q95 <= q99 <= ES99


def test_training_fz0_matches_scoring_fz0():
    rng = np.random.default_rng(1)
    loss = rng.normal(0, 0.01, 500)
    var = np.abs(rng.normal(0.02, 0.003, 500))
    es = var + np.abs(rng.normal(0.005, 0.001, 500))
    ours = float(fz0_t(torch.tensor(loss), torch.tensor(var), torch.tensor(es), 0.99))
    assert ours == pytest.approx(float(fz0(loss, var, es, 0.99).mean()), abs=1e-8)


def test_sequences_and_scaler_ignore_the_future():
    rng = np.random.default_rng(2)
    X = pd.DataFrame(rng.normal(size=(300, 3)), columns=list("abc"))
    seqs, pos, stats = make_sequences(X, 20, train_end=200)
    X2 = X.copy()
    X2.iloc[200:] = rng.normal(50, 10, size=(100, 3))
    seqs2, _, stats2 = make_sequences(X2, 20, train_end=200)
    np.testing.assert_allclose(stats, stats2)
    keep = pos < 200
    np.testing.assert_allclose(seqs[keep], seqs2[keep])


def test_training_is_deterministic_on_cpu():
    rng = np.random.default_rng(3)
    seqs = rng.normal(size=(200, 10, 3)).astype(np.float32)
    y = np.abs(rng.normal(0, 0.01, 200))
    cfg = LSTMConfig(seq_len=10, hidden=8, max_epochs=5, patience=5)
    a = train_window(seqs, y, cfg, seed=7)
    b = train_window(seqs, y, cfg, seed=7)
    x = torch.from_numpy(seqs[:5])
    with torch.no_grad():
        np.testing.assert_allclose(a(x).numpy(), b(x).numpy())


@pytest.mark.slow
def test_walk_forward_lstm_learns_heteroskedastic_scale():
    rng = np.random.default_rng(4)
    n = 1400
    idx = pd.bdate_range("2012-01-02", periods=n)
    sigma = np.exp(rng.normal(-4.6, 0.4, n))
    X = pd.DataFrame({"sigma": sigma, "noise": rng.normal(size=n)}, index=idx)
    y = pd.Series(sigma * rng.standard_normal(n), index=idx)
    cfg = LSTMConfig(seq_len=10, hidden=8, max_epochs=40, patience=8)
    out = walk_forward_lstm(X, y, cfg, seeds=(1, 2), retrain_every=200, min_train=800)
    assert (out["es_0.99"] >= out["var_0.99"]).all()
    assert out["hit_0.95"].mean() < 0.12            # sensible coverage on a short, noisy sample
    origin_sigma = X["sigma"].shift(1).reindex(out.index)   # the volatility known at the forecast origin
    assert np.corrcoef(out["var_0.95"], origin_sigma)[0, 1] > 0.3
