"""Step 22–23: hyperparameter grids for the ML challengers, chosen on validation only.

    .venv\\Scripts\\python scripts\\run_ml_grid.py [--skip-lstm]

For each model the configuration with the lowest 99% pinball loss among those passing the coverage
tests (Kupiec, CC, no red window) on 2019–2022 is kept; if none passes, the lowest-pinball one is
kept and flagged. Every configuration's result is appended to data/artifacts/ml_grid_val.parquet
as it finishes, then the arena is rescored against the champion. Research-only (LSTM needs torch).
"""

from __future__ import annotations

import argparse
import itertools
import json
import time

import pandas as pd

from quantedge import pipeline as p
from quantedge.backtest.report import selection_table
from quantedge.config import load_config
from quantedge.data.partition import Partition
from quantedge.ml.quantile_models import LGBMQuantile, LinearQR, ratio_es, walk_forward_ml
from quantedge.paths import ARTIFACTS

BACKTESTS = {"historical": "Historical", "normal": "Normal", "student_t": "Student-t",
             "cornish_fisher": "Cornish-Fisher", "evt": "EVT", "monte_carlo": "Monte Carlo",
             "garch_fhs": "GARCH-FHS", "conditional_evt": "Conditional EVT"}
GRID_FILE = ARTIFACTS / "ml_grid_val.parquet"


def log_result(rows: list, model: str, config: dict, df: pd.DataFrame, val) -> None:
    t = selection_table({model: df.loc[val]}, 0.99).iloc[0]
    rows.append({"model": model, "config": json.dumps(config), "pinball": t.pinball, "fz0": t.fz0,
                 "exceptions": int(t.exceptions), "kupiec_p": t.kupiec_p, "cc_p": t.cc_p,
                 "rolling_red": t.rolling_red, "passes": bool(t.passes)})
    pd.DataFrame(rows).to_parquet(GRID_FILE)
    print(f"  {model} {config}: pinball {t.pinball:.7f}, exceptions {int(t.exceptions)}, "
          f"passes {bool(t.passes)}", flush=True)


def pick(rows: list, model: str) -> dict:
    g = pd.DataFrame([r for r in rows if r["model"] == model])
    ok = g[g.passes]
    best = (ok if len(ok) else g).sort_values("pinball").iloc[0]
    return {"config": json.loads(best.config), "passes": bool(best.passes)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-lstm", action="store_true")
    args = ap.parse_args()
    t0 = time.perf_counter()
    cfg = load_config()
    part = Partition.from_config(cfg)
    val = slice(*part.bounds("val"))
    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    sel = p.run_portfolio_selection(cfg, macro)
    focus = str(sel["scorecard"].index[0])
    champion = json.loads((ARTIFACTS / "champion.json").read_text(encoding="utf-8"))["champion"]
    print(f"portfolio {focus}, champion {champion}", flush=True)
    X, y = p.ml_inputs(cfg, sel["results"][focus], macro)
    bt = {v: pd.read_parquet(ARTIFACTS / f"backtest_{k}_500.parquet") for k, v in BACKTESTS.items()}
    levels = (0.95, 0.975, 0.99)
    es_levels = {0.975: tuple(cfg.ml["es_integral_levels"]), 0.99: (0.99, 0.9925, 0.995, 0.9975)}
    lg = cfg.ml["lgbm"]
    kw = dict(retrain_every=lg["retrain_every"], start=part.val[0], end=part.val[1],
              es_levels=es_levels, min_train=750)
    rows: list = []
    forecasts: dict[str, pd.DataFrame] = {}

    forecasts["Linear QR"] = walk_forward_ml(lambda lv: LinearQR(lv), X, y, levels, **kw)
    log_result(rows, "Linear QR", {}, forecasts["Linear QR"], val)

    lgbm_runs = {}
    for nl, md in itertools.product(lg["grid"]["num_leaves"], lg["grid"]["min_data_in_leaf"]):
        conf = {"num_leaves": nl, "min_data_in_leaf": md, "learning_rate": lg["learning_rate"],
                "n_estimators": lg["n_estimators"], "feature_fraction": lg["feature_fraction"]}
        df = walk_forward_ml(lambda lv, c=conf: LGBMQuantile(lv, c, seed=cfg.seed), X, y, levels, **kw)
        lgbm_runs[json.dumps(conf)] = df
        log_result(rows, "LightGBM", conf, df, val)
    best_lgbm = pick(rows, "LightGBM")
    forecasts["LightGBM"] = lgbm_runs[json.dumps(best_lgbm["config"])]

    if not args.skip_lstm:
        from quantedge.ml.lstm_quantile import LSTMConfig, walk_forward_lstm

        lc = cfg.ml["lstm"]
        lstm_runs = {}
        for L, H, wd in itertools.product(lc["grid"]["seq_len"], lc["grid"]["hidden"], lc["grid"]["weight_decay"]):
            conf = {"seq_len": L, "hidden": H, "weight_decay": wd}
            lcfg = LSTMConfig(seq_len=L, hidden=H, dropout=lc["dropout"], weight_decay=wd, fz0_weight=lc["fz0_weight"])
            df = walk_forward_lstm(X, y, lcfg, seeds=tuple(lc["seeds"]), retrain_every=lc["retrain_every"],
                                   start=part.val[0], end=part.val[1])
            lstm_runs[json.dumps(conf)] = df
            log_result(rows, "LSTM", conf, df, val)
        forecasts["LSTM"] = lstm_runs[json.dumps(pick(rows, "LSTM")["config"])]

    cevt = bt["Conditional EVT"]
    for name in [n for n in ("Linear QR", "LightGBM") if n in forecasts]:
        df = forecasts[name].join(cevt[["var_0.99", "es_0.99"]].add_suffix("_cevt"), how="inner")
        es, _ = ratio_es(df["var_0.99"].to_numpy(), df["var_0.99_cevt"].to_numpy(), df["es_0.99_cevt"].to_numpy(),
                         cfg.ml["es_ratio"]["eps"], tuple(cfg.ml["es_ratio"]["clip"]))
        forecasts[f"{name} (ratio ES)"] = df.drop(columns=["var_0.99_cevt", "es_0.99_cevt"]).assign(**{"es_0.99": es})
    for name, df in forecasts.items():
        df.to_parquet(ARTIFACTS / f"ml_{name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.parquet")
    for name in ("Conditional EVT", "GARCH-FHS"):
        forecasts.setdefault(name, bt[name])
    table = p.score_arena(cfg, forecasts, bt, champion)
    chosen = {"LightGBM": best_lgbm, **({"LSTM": pick(rows, "LSTM")} if not args.skip_lstm else {})}
    (ARTIFACTS / "ml_selected_configs.json").write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    pd.set_option("display.width", 250)
    cols = ["exceptions", "kupiec_p", "cc_p", "rolling_red", "pinball", "fz0", "fz0_vs_champion",
            "dm_vs_champion", "dm_p_holm", "mcs_pvalue", "in_mcs", "passes"]
    print(table[cols].sort_values("pinball").to_string(float_format=lambda x: f"{x:.6g}"))
    print(f"chosen configs: {chosen}")
    print(f"done in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
