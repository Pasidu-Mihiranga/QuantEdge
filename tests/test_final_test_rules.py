"""Spec §5 step 7 as applied by the one-shot final test (pre-committed before the freeze)."""

import pandas as pd

from quantedge.backtest.final_test import limits_model

SCORES = pd.DataFrame({"passes": [True, True, True, False]}, index=["Champ", "A", "B", "Linear QR"])
ES = {"Champ": 0.020, "A": 0.022, "B": 0.025}


def test_champion_that_passes_sets_the_limits():
    assert limits_model(SCORES, "Champ", ES)["limits_model"] == "Champ"


def test_failing_champion_falls_back_to_the_passing_model_with_the_higher_current_es():
    s = SCORES.assign(passes=[False, True, True, True])
    out = limits_model(s, "Champ", ES)            # Linear QR passes but is not a risk model in ES
    assert out["limits_model"] == "B" and "higher current ES" in out["rule"]


def test_no_passing_risk_model_means_reject():
    s = SCORES.assign(passes=[False, False, False, True])
    out = limits_model(s, "Champ", ES)
    assert out["limits_model"] is None and "REJECT" in out["rule"]
