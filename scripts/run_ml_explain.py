"""Step 22 explainability for the LightGBM challenger: SHAP importance, a crisis-day breakdown and
the monotonicity diagnostic, on validation (2019-2022).

    .venv\\Scripts\\python scripts\\run_ml_explain.py

One model with the selected configuration (`ml_selected_configs.json`) is fitted on development
data only (forecast origins whose next-day target is <= 2018-12-31) and explains its validation
forecasts. The walk-forward arena retrains every 21 days on an expanding window, so this is one
representative fit, not the exact model behind each validation day.

- SHAP: LightGBM's built-in pred_contrib at the 99% level; importance = mean |SHAP| per feature.
- Crisis day: the validation day with the highest predicted 99% VaR, broken down by feature.
- Monotonicity: share of validation days whose predicted 99% VaR falls anywhere as one volatility
  feature rises across its 5-95% range (`monotonicity_violations`; 0 = monotone everywhere).
  LightGBM's quantile objective cannot impose monotone constraints, so this is measured instead.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from quantedge import pipeline as p
from quantedge.config import load_config
from quantedge.data.partition import Partition
from quantedge.ml.quantile_models import LGBMQuantile, ice_curves, monotonicity_violations
from quantedge.paths import ARTIFACTS

LEVEL = 0.99
VOL_FEATURES = ["rv_5", "rv_20", "rv_60", "ewma_vol", "downside_semivol_20", "garch_sigma", "vix"]
N_MONO_ROWS = 250


class _Weights:
    def __init__(self, history: pd.DataFrame):
        self.weights_history = history


def main() -> None:
    t0 = time.perf_counter()
    cfg = load_config()
    part = Partition.from_config(cfg)
    macro = pd.read_parquet(ARTIFACTS / "clean_macro.parquet")
    focus = json.loads((ARTIFACTS / "status.json").read_text(encoding="utf-8"))["focus_portfolio"]
    slug = focus.lower().replace(" ", "_").replace("/", "").replace("(", "").replace(")", "")
    X, y = p.ml_inputs(cfg, _Weights(pd.read_parquet(ARTIFACTS / f"wf_weights_{slug}.parquet")), macro)
    data = pd.concat([X, y.rename("__y")], axis=1).dropna()
    train = data.loc[: part.dev[1]].iloc[:-1]          # the last dev origin's target is the first val day
    val = data.loc[part.val[0]: part.val[1]].drop(columns="__y")
    params = json.loads((ARTIFACTS / "ml_selected_configs.json").read_text(encoding="utf-8"))["LightGBM"]["config"]
    model = LGBMQuantile((LEVEL,), params, seed=cfg.seed).fit(train.drop(columns="__y"), train["__y"])

    shap = model.contributions(val, LEVEL)
    feats = shap.drop(columns="expected_value")
    importance = (feats.abs().mean().sort_values(ascending=False).rename("mean_abs_shap").to_frame()
                  .assign(share=lambda d: d["mean_abs_shap"] / d["mean_abs_shap"].sum()))
    importance.to_parquet(ARTIFACTS / "ml_shap_importance.parquet")

    pred = pd.Series(model.predict(val)[:, 0], index=val.index)
    day = pred.idxmax()
    crisis = pd.DataFrame({"value": val.loc[day], "shap": feats.loc[day]}).sort_values("shap", key=np.abs, ascending=False)
    crisis.to_parquet(ARTIFACTS / "ml_shap_crisis_day.parquet")

    rows = val.iloc[np.linspace(0, len(val) - 1, N_MONO_ROWS).astype(int)]
    mono = []
    for f in VOL_FEATURES:
        curves = ice_curves(model, rows, f, LEVEL)
        drop = np.maximum.accumulate(curves, axis=1) - curves          # fall below the running maximum
        rise = curves[:, -1] - curves[:, 0]
        mono.append({"feature": f, "violation_share": monotonicity_violations(model, rows, f, LEVEL),
                     "median_largest_dip_bp": float(np.median(drop.max(axis=1)) * 1e4),
                     "median_total_rise_bp": float(np.median(rise) * 1e4),
                     "share_rising_overall": float((rise > 0).mean())})
    mono = pd.DataFrame(mono).set_index("feature")
    mono.to_parquet(ARTIFACTS / "ml_monotonicity.parquet")

    summary = {"model": "LightGBM", "config": params, "level": LEVEL, "portfolio": focus,
               "trained_on": [str(train.index.min().date()), str(train.index.max().date())],
               "explained": [str(val.index.min().date()), str(val.index.max().date())],
               "crisis_day_origin": str(day.date()), "crisis_day_var99": float(pred.loc[day]),
               "crisis_day_expected_value": float(shap.loc[day, "expected_value"]),
               "monotonicity_rows": N_MONO_ROWS, "seconds": round(time.perf_counter() - t0, 1)}
    (ARTIFACTS / "ml_explain.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(importance.round(5).head(8).to_string())
    print(crisis.head(6).round(5).to_string())
    print(mono.round(3).to_string())


if __name__ == "__main__":
    main()
