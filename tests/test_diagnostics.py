import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quantedge.risk.diagnostics import (
    disagreement_table,
    es_var_ratio_table,
    gap_sentence,
    tail_statistics,
    window_sensitivity,
)
from quantedge.risk.examples import subadditivity_demo
from quantedge.risk.var import HistoricalModel, NormalModel, StudentTModel


@pytest.fixture(scope="module")
def fat_tailed():
    rng = np.random.default_rng(2)
    return pd.Series(stats.t.rvs(3.5, size=4000, random_state=rng) * 0.006)


def test_fat_tails_show_up_in_the_disagreement_table(fat_tailed):
    models = {m.name: m.fit(fat_tailed) for m in (HistoricalModel(), NormalModel(), StudentTModel())}
    table = disagreement_table(models)
    assert table.loc[0.99, "Normal"] < table.loc[0.99, "Historical"]  # Normal understates at 99%
    facts = tail_statistics(-fat_tailed)
    assert facts["excess_kurtosis"] > 2
    assert "Normal VaR is" in gap_sentence(table, facts)


def test_es_var_ratio_exceeds_normal_reference_for_fat_tails(fat_tailed):
    models = {"Historical": HistoricalModel().fit(fat_tailed), "Normal": NormalModel().fit(fat_tailed)}
    t = es_var_ratio_table(models).set_index(["model", "alpha"])
    assert t.loc[("Normal", 0.99), "es_var_ratio"] == pytest.approx(1.146, abs=0.02)
    assert t.loc[("Historical", 0.99), "es_var_ratio"] > t.loc[("Historical", 0.99), "normal_reference"]


def test_window_sensitivity_shape(fat_tailed):
    w = window_sensitivity(fat_tailed)
    assert list(w.index) == [250, 500, 1000]


def test_var_is_not_subadditive_but_es_is():
    d = subadditivity_demo()
    assert d["var_single"] == pytest.approx(-5.0)
    assert d["var_portfolio"] == pytest.approx(95.0)
    assert d["var_portfolio"] > d["var_sum_of_singles"]
    assert d["es_single"] == pytest.approx((0.04 * 100 - 0.01 * 5) / 0.05)
    assert d["es_portfolio"] <= d["es_sum_of_singles"]
