import numpy as np
import pandas as pd
import pytest

from quantedge.ml.quantile_models import (
    LGBMQuantile,
    LinearQR,
    monotonicity_violations,
    ratio_es,
    rearrange,
    walk_forward_ml,
)


@pytest.fixture(scope="module")
def hetero():
    """Losses whose scale is a known feature: y_{t+1} = sigma_t * eps."""
    rng = np.random.default_rng(0)
    n = 2200
    idx = pd.bdate_range("2010-01-01", periods=n)
    sigma = np.exp(rng.normal(-4.6, 0.4, n))          # around 1% with variation
    X = pd.DataFrame({"sigma": sigma, "noise": rng.normal(size=n)}, index=idx)
    y = pd.Series(sigma * rng.standard_normal(n), index=idx)
    return X, y


def test_rearrange_fixes_crossing_rows():
    q = np.array([[1.0, 2.0, 3.0], [1.0, 3.0, 2.0]])
    out, fixed = rearrange(q)
    assert fixed == 1 and np.all(np.diff(out, axis=1) >= 0)


def test_ratio_es_guards():
    var_ml = np.array([0.02, 0.02, 0.02])
    var_evt = np.array([0.01, 0.0, 0.01])
    es_evt = np.array([0.013, 0.01, 0.05])          # ratio 1.3, guarded (zero VaR), 5.0 -> clipped
    es, hits = ratio_es(var_ml, var_evt, es_evt)
    np.testing.assert_allclose(es, [0.026, 0.02, 0.05])
    assert hits == 2 and np.all(es >= var_ml)


class _Spy:
    calls = []

    def __init__(self, levels):
        self.levels = levels

    def fit(self, X, y):
        _Spy.calls.append(X.index.max())
        return self

    def predict(self, X):
        _Spy.calls.append(("predict", X.index[0]))
        return np.tile(np.arange(1, len(self.levels) + 1, dtype=float), (len(X), 1))


def test_training_never_sees_the_forecast_origin_or_later(hetero):
    X, y = hetero
    _Spy.calls = []
    out = walk_forward_ml(_Spy, X, y, levels=(0.99,), retrain_every=50, min_train=500)
    last_train = None
    for c in _Spy.calls:
        if isinstance(c, tuple):
            assert last_train < c[1]       # trained only on origins before this origin
        else:
            last_train = c
    assert out.index[0] > X.index[500 - 1]


def test_linear_qr_coverage_on_heteroskedastic_data(hetero):
    X, y = hetero
    out = walk_forward_ml(lambda lv: LinearQR(lv), X, y, levels=(0.90, 0.95), retrain_every=100,
                          min_train=1000)
    for a in (0.90, 0.95):
        assert abs(out[f"hit_{a}"].mean() - (1 - a)) < 0.03


@pytest.mark.slow
def test_lgbm_coverage_monotone_and_es(hetero):
    X, y = hetero
    make = lambda lv: LGBMQuantile(lv, params={"n_estimators": 200})  # noqa: E731
    out = walk_forward_ml(make, X, y, levels=(0.95,), retrain_every=200, min_train=1000,
                          es_levels={0.95: (0.95, 0.97, 0.99)})
    assert abs(out["hit_0.95"].mean() - 0.05) < 0.03
    assert (out["es_0.95"] >= out["var_0.95"]).all()
    model = LGBMQuantile((0.95,), params={"n_estimators": 200}).fit(X.iloc[:1500], y.iloc[:1500])
    low, high = model.predict(pd.DataFrame({"sigma": [0.005, 0.03], "noise": [0.0, 0.0]}))[:, 0]
    assert high > low                                # higher volatility -> higher VaR
    assert 0.0 <= monotonicity_violations(model, X.iloc[1500:1530], "sigma", 0.95) <= 1.0
    shap = model.contributions(X.iloc[1500:1510], 0.95)
    np.testing.assert_allclose(shap.sum(axis=1), model.predict(X.iloc[1500:1510])[:, 0], rtol=1e-6)


def test_ice_curves_and_monotonicity_on_known_models():
    from quantedge.ml.quantile_models import ice_curves

    class Fake:
        levels = (0.99,)

        def __init__(self, f):
            self.f = f

        def predict(self, Z):
            return np.column_stack([self.f(Z)])

    X = pd.DataFrame({"vol": np.linspace(0.1, 0.5, 40), "other": np.linspace(-1, 1, 40)})
    up = Fake(lambda Z: 2 * Z["vol"].to_numpy() + Z["other"].to_numpy())
    curves = ice_curves(up, X, "vol", 0.99, n_grid=5)
    assert curves.shape == (40, 5) and np.allclose(curves[:, -1] - curves[:, 0], curves[0, -1] - curves[0, 0])
    assert monotonicity_violations(up, X, "vol", 0.99, n_grid=5) == 0.0
    assert monotonicity_violations(Fake(lambda Z: -Z["vol"].to_numpy()), X, "vol", 0.99) == 1.0
    dip = Fake(lambda Z: Z["vol"].to_numpy() - 0.5 * ((Z["vol"].to_numpy() > 0.3) & (Z["other"].to_numpy() > 0)))
    assert monotonicity_violations(dip, X, "vol", 0.99, n_grid=9) == pytest.approx(0.5)
