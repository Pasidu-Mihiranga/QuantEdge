import numpy as np
import pandas as pd
import pytest
from arch import arch_model
from scipy import stats

from quantedge.backtest.engine import ModelSpec, run_models, walk_forward_var
from quantedge.backtest.es_backtest import acerbi_szekely_z2
from quantedge.backtest.report import choose_champion, crisis_breakdown, selection_table
from quantedge.risk.garch import GarchFHSModel
from quantedge.risk.var import HistoricalModel, NormalModel


@pytest.fixture(scope="module")
def iid():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2010-01-01", periods=2500)
    r = pd.DataFrame(rng.normal(0, 0.01, (2500, 2)), index=idx, columns=["A", "B"])
    w = pd.DataFrame({"A": 0.5, "B": 0.5}, index=idx)
    return r, w


class _Recorder:
    """Mock model that records the last date of every fit window."""

    seen: list = []

    def fit(self, series):
        _Recorder.seen.append(series.index.max())
        self.q = float(np.quantile(-series, 0.99))
        return self

    def var(self, a):
        return self.q

    def es(self, a):
        return self.q * 1.2


def test_every_fit_window_ends_before_the_forecast_day(iid):
    r, w = iid
    _Recorder.seen = []
    out = walk_forward_var(ModelSpec("rec", _Recorder, 1), r, w, window=250, alphas=(0.99,))
    assert len(_Recorder.seen) == len(out)
    assert all(last < day for last, day in zip(_Recorder.seen, out.index, strict=True))


def test_weights_held_are_the_previous_days_weights(iid):
    r, w = iid
    w2 = w.copy()
    switch = r.index[1500]
    w2.loc[w2.index >= switch] = [1.0, 0.0]
    out = walk_forward_var(ModelSpec("HS", HistoricalModel, 1), r, w2, window=250, alphas=(0.99,))
    nxt = r.index[1501]
    assert out.loc[switch, "loss"] == pytest.approx(-(r.loc[switch] @ np.array([0.5, 0.5])))
    assert out.loc[nxt, "loss"] == pytest.approx(-r.loc[nxt, "A"])


def test_correct_model_is_calibrated_on_iid_normal(iid):
    r, w = iid
    out = walk_forward_var(ModelSpec("Normal", NormalModel, 1), r, w, window=500)
    rate = out["hit_0.99"].mean()
    assert 0.003 < rate < 0.02
    table = selection_table({"Normal": out})
    assert table.loc["Normal", "kupiec_p"] > 0.01


def test_garch_update_matches_fixed_parameter_filter():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.standard_t(6, 1500) * 0.01)
    m = GarchFHSModel().fit(r.iloc[:1400])
    for k in range(1400, 1410):
        m.update(float(r.iloc[k]))
    fixed = arch_model(100 * r.iloc[:1410], mean="Constant", vol="GARCH", p=1, q=1, dist="t",
                       rescale=False).fix(m.params.to_numpy())
    expected = float(np.sqrt(fixed.forecast(horizon=1, reindex=False).variance.iloc[-1, 0])) / 100
    assert m.sigma_next == pytest.approx(expected, rel=1e-6)


def test_z2_zero_under_correct_es_and_negative_when_es_too_low():
    rng = np.random.default_rng(2)
    loss = rng.standard_normal(200_000)
    a = 0.975
    v = stats.norm.ppf(a)
    e = stats.norm.pdf(v) / (1 - a)
    assert acerbi_szekely_z2(loss, np.full_like(loss, v), np.full_like(loss, e), a).z2 == pytest.approx(0, abs=0.03)
    low = acerbi_szekely_z2(loss, np.full_like(loss, v), np.full_like(loss, e * 0.5), a)
    assert low.z2 < -0.7 and low.zone != "green"


def test_champion_and_crisis_breakdown(iid):
    r, w = iid
    res = run_models([ModelSpec("Normal", NormalModel, 1), ModelSpec("Historical", HistoricalModel, 1)],
                     r, w, window=500)
    table = selection_table(res)
    name, reason = choose_champion(table)
    assert name in ("Historical", "Normal")
    if table["passes"].any():
        assert name == table[table.passes].sort_values("pinball").index[0]   # default: lowest_pinball_passing
    cb = crisis_breakdown(res, {"window": (str(r.index[800].date()), str(r.index[900].date()))})
    assert set(cb.model) == {"Normal", "Historical"} and (cb.days == 101).all()


def test_champion_rules():
    table = pd.DataFrame({"passes": [True, True, False], "pinball": [0.30, 0.20, 0.10],
                          "complexity": [0, 7, 3]}, index=["Historical", "Conditional EVT", "Normal"])
    assert choose_champion(table, "lowest_pinball_passing")[0] == "Conditional EVT"
    assert choose_champion(table, "simplest_passing")[0] == "Historical"
    none = table.assign(passes=False)
    assert choose_champion(none)[0] == "Normal"
