import numpy as np
import pandas as pd
import pytest

from quantedge.config import load_config
from quantedge.decision.ips import IPSLimits, OptimizerConstraints, constraints_for_optimizer
from quantedge.portfolio import optimize as opt
from quantedge.portfolio.walkforward import (
    bootstrap_weights,
    candidate_strategies,
    rebalance_dates,
    scorecard,
    walk_forward,
)
from quantedge.portfolio.weights_path import (
    pit_loss_target,
    pit_risk_returns,
    point_in_time_weights,
)

CFG = load_config()
LIMITS = IPSLimits.from_config(CFG.ips)
TICKERS = list(CFG.universe)


def _free(n):
    names = tuple(f"A{i}" for i in range(n))
    return OptimizerConstraints(names, np.zeros(n), np.ones(n), np.zeros((0, n)), np.zeros(0),
                                np.ones(n) / n)


def _sigma2():
    s = np.array([[0.04, 0.006], [0.006, 0.01]])
    return pd.DataFrame(s, index=["A0", "A1"], columns=["A0", "A1"])


@pytest.fixture(scope="module")
def market():
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2004-11-18", "2012-12-31")
    vols = np.array([0.012, 0.013, 0.017, 0.003, 0.011, 0.016, 0.014])
    corr = np.full((7, 7), 0.5)
    np.fill_diagonal(corr, 1.0)
    corr[3, :] = corr[:, 3] = 0.0
    corr[3, 3] = 1.0
    cov = corr * np.outer(vols, vols)
    r = rng.multivariate_normal(np.full(7, 0.0003), cov, len(idx))
    returns = pd.DataFrame(r, index=idx, columns=TICKERS)
    rf = pd.Series(0.0001, index=idx)
    return returns, rf


def test_gmv_matches_closed_form_without_bounds():
    s = _sigma2()
    w = opt.gmv(s, _free(2)).weights.to_numpy()
    inv = np.linalg.inv(s.to_numpy())
    expected = inv @ np.ones(2) / (np.ones(2) @ inv @ np.ones(2))
    np.testing.assert_allclose(w, expected, atol=1e-6)


def test_max_sharpe_matches_closed_form_without_bounds():
    s = _sigma2()
    mu = pd.Series([0.08, 0.05], index=s.index)
    w = opt.max_sharpe(mu, s, 0.02, _free(2)).weights.to_numpy()
    raw = np.linalg.inv(s.to_numpy()) @ (mu.to_numpy() - 0.02)
    np.testing.assert_allclose(w, raw / raw.sum(), atol=1e-5)


def test_erc_equalises_risk_contributions():
    s = pd.DataFrame(np.diag([0.04, 0.01, 0.0225]) + 0.002, index=["A0", "A1", "A2"],
                     columns=["A0", "A1", "A2"])
    res = opt.erc(s, _free(3))
    w = res.diagnostics["unconstrained"].to_numpy()
    rc = w * (s.to_numpy() @ w)
    assert rc.max() - rc.min() < 1e-6
    np.testing.assert_allclose(res.weights.to_numpy(), w, atol=1e-6)  # no binding bounds


def test_min_cvar_beats_gmv_and_equal_weight_in_sample(market):
    returns, _ = market
    est = returns.iloc[:756]
    cons = constraints_for_optimizer(LIMITS, TICKERS)
    mu, sigma = opt.estimate_inputs(est, 0.02)

    def cvar(w):
        loss = -(est.to_numpy() @ w.to_numpy())
        q = np.quantile(loss, 0.99)
        return loss[loss >= q].mean()

    w_cvar = opt.min_cvar(est, cons).weights
    assert cvar(w_cvar) <= cvar(opt.gmv(sigma, cons).weights) + 1e-4
    assert cvar(w_cvar) <= cvar(opt.equal_weight(TICKERS).weights) + 1e-4


def test_every_optimiser_respects_ips(market):
    returns, _ = market
    est = returns.iloc[:756]
    strategies, _ = candidate_strategies(CFG, LIMITS, TICKERS)
    for name, strat in strategies.items():
        if name in ("Equal weight", "60/40 benchmark"):
            continue  # fixed reference portfolios, not optimised under the IPS
        w = strat(est, 0.02).weights
        assert w.sum() == pytest.approx(1.0, abs=1e-8)
        bad = [c.name for c in LIMITS.check({"weights": w}, tol=1e-6) if not c.passed]
        assert not bad, f"{name} breaches {bad}"


def test_benchmark_6040_itself_breaches_the_ips():
    """Documented finding: the 60/40 policy benchmark violates the client's IPS
    (SPY 60% > 40% single-asset cap; 60% equity > 50% equity cap)."""
    w = opt.fixed(CFG.benchmark, TICKERS).weights
    failed = {c.name for c in LIMITS.check({"weights": w}) if not c.passed}
    assert failed == {"weight SPY", "equity total"}


def test_walk_forward_has_no_look_ahead(market):
    returns, rf = market
    seen = []

    def spy_strategy(est, rf_annual):
        seen.append(est.index.max())
        return opt.fixed(CFG.benchmark, TICKERS)

    res = walk_forward(returns, spy_strategy, rf, window=756)
    for tau, last in zip(res.weights_history.index, seen, strict=True):
        assert last <= tau
    assert res.perf.index.min() > res.weights_history.index[0]
    assert all(d.month in (3, 6, 9, 12) for d in rebalance_dates(returns.index, 756))


def test_scorecard_ranks_and_flags_ips(market):
    returns, rf = market
    strategies, _ = candidate_strategies(CFG, LIMITS, TICKERS)
    picked = {k: strategies[k] for k in ("Equal weight", "60/40 benchmark", "Global min variance")}
    results = {k: walk_forward(returns, s, rf, name=k) for k, s in picked.items()}
    card = scorecard(results, LIMITS, 0.065, CFG.stress["historical"], pd.Timestamp("2012-12-31"))
    assert not card.loc["Equal weight", "weights_within_ips"]  # EEM/XLE/XLK above 10%
    assert list(card["rank"]) == [1, 2, 3]


def test_weight_path_ignores_the_future_and_uses_warmup(market):
    returns, rf = market
    strategies, _ = candidate_strategies(CFG, LIMITS, TICKERS)
    gmv = strategies["Global min variance"]
    base = walk_forward(returns, gmv, rf)
    tau = base.weights_history.index[2]
    shocked = returns.copy()
    shocked.loc[shocked.index > tau] *= -3.0  # perturb everything after tau
    again = walk_forward(shocked, gmv, rf)
    pd.testing.assert_series_equal(base.weights_history.loc[tau], again.weights_history.loc[tau])

    path = point_in_time_weights(base.weights_history, returns.index, CFG.partition.warmup_weights)
    first = base.weights_history.index[0]
    assert path.loc[path.index < first, "SPY"].eq(0.60).all()
    pd.testing.assert_series_equal(path.loc[first], base.weights_history.loc[first], check_names=False)
    assert np.allclose(path.sum(axis=1), 1.0)


def test_pit_returns_use_previous_day_weights():
    idx = pd.bdate_range("2020-01-01", periods=4)
    r = pd.DataFrame({"A": [0.01, 0.02, 0.03, 0.04], "B": [0.0, 0.0, 0.0, 0.0]}, index=idx)
    wh = pd.DataFrame({"A": [1.0], "B": [0.0]}, index=[idx[1]])
    path = point_in_time_weights(wh, idx, {"A": 0.0, "B": 1.0})
    rp = pit_risk_returns(r, path)
    np.testing.assert_allclose(rp.to_numpy(), [0.0, 0.03, 0.04])   # day 2 still held B
    target = pit_loss_target(r, path)
    assert target.loc[idx[1]] == pytest.approx(-0.03)                # l_{t+1} at weights of t


def test_bootstrap_weights_shape(market):
    returns, _ = market
    rng = np.random.default_rng(1)
    strategies, _ = candidate_strategies(CFG, LIMITS, TICKERS)
    boot = bootstrap_weights(returns.iloc[:300], strategies["Global min variance"], 0.02, rng, n=5)
    assert boot.shape == (5, 7)
    np.testing.assert_allclose(boot.sum(axis=1), 1.0, atol=1e-8)
