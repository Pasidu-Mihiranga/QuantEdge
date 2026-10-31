"""Option C: before the freeze, the pipeline must reproduce notebook 04's independently
written backtest on validation 2019-22 for the pre-registered 35%-equity frontier portfolio.

The reference numbers below are copied from notebooks/04_backtesting.ipynb §2 (run 2026-10-28). Notebook 04
re-checks the same agreement from its side (§7), so a change on either side fails one of the two checks.
"""

import json

import pandas as pd
import pytest

from quantedge.config import load_config
from quantedge.paths import ARTIFACTS

pytestmark = pytest.mark.skipif(not (ARTIFACTS / "champion.json").exists(), reason="run the pipeline first")

CFG = load_config()
NOTEBOOK_04 = {  # model: (99% VaR exceptions in 1008 days, mean 99% pinball loss x 10^4)
    "Historical": (13, 3.556),
    "Normal": (25, 3.252),
    "GARCH-FHS": (12, 2.132),
    "GJR-FHS": (13, 2.020),
    "Conditional EVT": (14, 2.040),
    "GJR conditional EVT": (14, 1.995),
}


@pytest.fixture(scope="module")
def val_table():
    return pd.read_parquet(ARTIFACTS / f"backtest_selection_val_{CFG.risk.default_window}.parquet")


@pytest.mark.parametrize("model", list(NOTEBOOK_04))
def test_pipeline_reproduces_notebook_04_on_validation(val_table, model):
    exceptions, pinball = NOTEBOOK_04[model]
    row = val_table.loc[model]
    assert int(row["T"]) == 1008
    assert int(row["exceptions"]) == exceptions
    assert row["pinball"] * 1e4 == pytest.approx(pinball, abs=6e-4)   # the notebook reports 3 decimals


def test_locked_champion_is_what_the_rule_picks_and_runs_on_the_focus_portfolio():
    champ = json.loads((ARTIFACTS / "champion.json").read_text(encoding="utf-8"))
    status = json.loads((ARTIFACTS / "status.json").read_text(encoding="utf-8"))
    assert champ["champion"] == champ["rule_choice"] == CFG.backtest.champion == "GJR conditional EVT"
    assert champ["window"] == CFG.risk.default_window
    assert status["focus_portfolio"] == CFG.portfolio.focus
