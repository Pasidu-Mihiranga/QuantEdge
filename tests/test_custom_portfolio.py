import numpy as np
import pandas as pd
import pytest

from quantedge.decision.ips import IPSLimits
from quantedge.portfolio.custom import custom_check, normalise

IDX = pd.bdate_range("2015-01-01", periods=900)
WINDOWS = {"stress": ("2016-01-04", "2016-06-30")}
LIMITS = IPSLimits(vol_ann_max=0.08, stress_drawdown_max=0.20, es99_1d_max=0.015, es99_10d_max=0.05,
                   single_asset_max=0.6, asset_floors={"B": 0.2})


def returns() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    return pd.DataFrame(rng.normal(0.0002, [0.012, 0.004, 0.009], size=(len(IDX), 3)), index=IDX, columns=list("ABC"))


def test_normalise_rescales_and_rejects_invalid_weights():
    assert normalise({"A": 2, "B": 2}, list("ABC")).tolist() == [0.5, 0.5, 0.0]
    with pytest.raises(ValueError):
        normalise({"A": -0.1, "B": 1.1}, list("ABC"))
    with pytest.raises(ValueError):
        normalise({}, list("ABC"))


def test_custom_check_flags_ips_breaches_and_matches_hand_calculations():
    r = returns()
    out = custom_check({"A": 70, "B": 10, "C": 20}, r, LIMITS, WINDOWS, window=250)
    failed = set(out["weight_checks"].loc[~out["weight_checks"]["passed"], "name"])
    assert failed == {"weight A", "weight B floor"} and not out["weights_ok"]
    port = r.iloc[-250:] @ out["weights"]
    hs = out["risk"].set_index(["model", "alpha"]).loc[("Historical", 0.99)]
    assert hs["var"] == pytest.approx(np.quantile(-port, 0.99), rel=0.02)
    assert hs["es"] >= hs["var"] > 0
    assert set(out["risk"]["model"]) == {"Historical", "Normal", "Student-t", "Cornish-Fisher"}
    assert out["full_sample"]["volatility"] == pytest.approx((r @ out["weights"]).std() * np.sqrt(252), rel=1e-6)
    assert set(out["risk_checks"]["name"]) == {"vol_ann", "es99_1d", "stress_drawdown"}


def test_heavy_check_adds_garch_and_evt():
    out = custom_check({"A": 0.3, "B": 0.5, "C": 0.2}, returns(), LIMITS, WINDOWS, window=500, heavy=True)
    assert {"GARCH-FHS", "EVT"} <= set(out["risk"]["model"]) and out["weights_ok"]
