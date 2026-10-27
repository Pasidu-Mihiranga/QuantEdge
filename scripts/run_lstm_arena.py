"""Step 23: train the LSTM challenger on the validation period and rescore the arena.

    .venv\\Scripts\\python scripts\\run_lstm_arena.py [--seq-len 60 --hidden 32 --weight-decay 1e-4]

Research-only (needs requirements-research.txt). Writes data/artifacts/ml_lstm.parquet and
refreshes ml_arena_val.parquet with the LSTM included.
"""

from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from quantedge import pipeline as p
from quantedge.config import load_config
from quantedge.data.partition import Partition
from quantedge.ml.lstm_quantile import LSTMConfig, walk_forward_lstm
from quantedge.paths import ARTIFACTS

BACKTESTS = {"historical": "Historical", "normal": "Normal", "student_t": "Student-t",
             "cornish_fisher": "Cornish-Fisher", "evt": "EVT", "monte_carlo": "Monte Carlo",
             "garch_fhs": "GARCH-FHS", "conditional_evt": "Conditional EVT"}
ML = {"Linear QR": "ml_linear_qr", "LightGBM": "ml_lightgbm",
      "Linear QR (ratio ES)": "ml_linear_qr_ratio_es", "LightGBM (ratio ES)": "ml_lightgbm_ratio_es"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq-len", type=int, default=60)
    ap.add_argument("--hidden", type=int, default=32)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    args = ap.parse_args()

    t0 = time.perf_counter()
    cfg = load_config()
    part = Partition.from_config(cfg)
    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    sel = p.run_portfolio_selection(cfg, macro)
    focus = str(sel["scorecard"].index[0])
    X, y = p.ml_inputs(cfg, sel["results"][focus], macro)
    lc = cfg.ml["lstm"]
    lcfg = LSTMConfig(seq_len=args.seq_len, hidden=args.hidden, dropout=lc["dropout"],
                      weight_decay=args.weight_decay, fz0_weight=lc["fz0_weight"])
    print(f"training LSTM {lcfg} on {focus}", flush=True)
    lstm = walk_forward_lstm(X, y, lcfg, seeds=tuple(lc["seeds"]), retrain_every=lc["retrain_every"],
                             start=part.val[0], end=part.val[1])
    lstm.to_parquet(ARTIFACTS / "ml_lstm.parquet")
    print(f"LSTM forecasts: {len(lstm)} days in {time.perf_counter() - t0:.0f}s", flush=True)

    bt = {v: pd.read_parquet(ARTIFACTS / f"backtest_{k}_500.parquet") for k, v in BACKTESTS.items()}
    forecasts = {k: pd.read_parquet(ARTIFACTS / f"{v}.parquet") for k, v in ML.items()}
    forecasts["LSTM"] = lstm
    for name in ("Conditional EVT", "GARCH-FHS"):
        forecasts.setdefault(name, bt[name])
    champion = json.loads((ARTIFACTS / "champion.json").read_text(encoding="utf-8"))["champion"]
    table = p.score_arena(cfg, forecasts, bt, champion)
    pd.set_option("display.width", 250)
    cols = ["T", "exceptions", "kupiec_p", "cc_p", "rolling_red", "pinball", "fz0", "fz0_vs_champion",
            "dm_vs_champion", "dm_p_holm", "mcs_pvalue", "in_mcs", "passes"]
    print(table[cols].sort_values("pinball").to_string(float_format=lambda x: f"{x:.6g}"))
    print(f"done in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
