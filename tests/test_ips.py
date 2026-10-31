from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from quantedge.config import load_config
from quantedge.decision.ips import IPSLimits, constraints_for_optimizer, required_return

CFG = load_config()
LIMITS = IPSLimits.from_config(CFG.ips)


def test_required_return_compounds_spending_growth_and_breakeven_inflation():
    idx = pd.date_range("2000-01-31", "2022-12-31", freq="ME")
    cpi = pd.Series(100 * 1.025 ** (np.arange(len(idx)) / 12), index=idx)
    be = pd.Series(2.30, index=pd.date_range("2022-01-03", "2022-12-30", freq="B"))
    be.loc["2022-07-01":] = 2.10
    out = required_return(cpi, 0.03, 0.005, be, years=10)
    assert out["inflation"] == pytest.approx(0.021)
    assert out["required_return"] == pytest.approx(1.03 * 1.005 * 1.021 - 1)
    assert out["cpi_avg_10y"] == pytest.approx(0.025, abs=1e-9)
    as_of = required_return(cpi, 0.03, 0.005, be, years=10, as_of=pd.Timestamp("2022-03-31"))
    assert as_of["inflation"] == pytest.approx(0.023) and as_of["cpi_window_end"] <= "2022-03-31"


def test_config_holds_the_agreed_d1_d2_values():
    assert CFG.ips["spending_rate"] == 0.03 and CFG.ips["real_growth"] == 0.005      # D1
    assert CFG.ips["crisis_budget"] == 0.25 and LIMITS.stress_drawdown_max == 0.25   # D2
    assert (LIMITS.vol_ann_max, LIMITS.es99_1d_max) == (0.084, 0.0223)              # D2-derived


def test_limit_exactly_at_boundary_passes_and_just_above_fails():
    at = {c.name: c for c in LIMITS.check({"vol_ann": LIMITS.vol_ann_max, "es99_1d": LIMITS.es99_1d_max})}
    assert at["vol_ann"].passed and at["es99_1d"].passed
    above = {c.name: c for c in LIMITS.check({"vol_ann": LIMITS.vol_ann_max + 0.0001})}
    assert not above["vol_ann"].passed
    assert above["vol_ann"].margin == pytest.approx(-0.0001)


def test_weight_limits_cover_caps_floors_and_equity_group():
    w = pd.Series({"SPY": 0.30, "EFA": 0.10, "EEM": 0.12, "AGG": 0.24, "GLD": 0.14,
                   "XLE": 0.05, "XLK": 0.05})
    assert LIMITS.asset_floors == {}                  # D3: no AGG floor
    lim = replace(LIMITS, asset_floors={"AGG": 0.25})  # the floor mechanism is kept for sensitivity cases
    checks = {c.name: c for c in lim.check({"weights": w})}
    assert not checks["weight EEM"].passed            # cap 10%
    assert not checks["weight AGG floor"].passed      # floor 25%
    assert not checks["equity total"].passed          # 62% > 50%
    assert checks["weight GLD"].passed                # cap 15% (D3)


def test_optimizer_constraints_are_feasible_and_respected():
    tickers = list(CFG.universe)
    cons = constraints_for_optimizer(LIMITS, tickers)
    x = cons.feasible_point
    assert x.sum() == pytest.approx(1.0)
    assert np.all(x >= cons.lower - 1e-9) and np.all(x <= cons.upper + 1e-9)
    assert np.all(cons.A_ub @ x <= cons.b_ub + 1e-9)
    checks = LIMITS.check({"weights": pd.Series(x, index=tickers)})
    assert all(c.passed for c in checks)


def test_infeasible_limits_raise():
    tight = IPSLimits(vol_ann_max=0.08, stress_drawdown_max=0.2, es99_1d_max=0.015,
                      es99_10d_max=0.05, single_asset_max=0.10)
    with pytest.raises(ValueError, match="infeasible"):
        constraints_for_optimizer(tight, list(CFG.universe))  # 7 x 10% < 100%


def test_agg_cap_is_65_percent_and_original_case_is_kept_as_variant():
    w = pd.Series({"SPY": 0.15, "EFA": 0.05, "EEM": 0.0, "AGG": 0.60, "GLD": 0.20, "XLE": 0.0, "XLK": 0.0})
    checks = {c.name: c for c in LIMITS.check({"weights": w})}
    assert checks["weight AGG"].passed and checks["weight AGG"].limit == pytest.approx(0.65)
    assert checks["weight XLE"].limit == pytest.approx(0.10)       # tighter caps unchanged
    assert checks["weight SPY"].limit == pytest.approx(0.40)       # general cap unchanged
    original = IPSLimits.from_config(CFG.ips, variant="original_agg40")
    assert not {c.name: c for c in original.check({"weights": w})}["weight AGG"].passed
    assert original.asset_caps["XLE"] == pytest.approx(0.10)       # variant only overrides AGG
