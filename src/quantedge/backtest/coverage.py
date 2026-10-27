"""VaR coverage tests and the Basel traffic light (Step 11 §3.2–3.4, Step 22 §3.4–3.5).

I_t = 1{l_t > VaR_t}; p = 1 - alpha is the expected exception rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

CANONICAL_PLUS = {5: 0.40, 6: 0.50, 7: 0.65, 8: 0.75, 9: 0.85}


def _xlogy(x: float, y: float) -> float:
    return 0.0 if x == 0 else x * math.log(y)


def kupiec_lr(x: int, T: int, p: float) -> float:
    """LR_POF = -2 ln[(1-p)^(T-x) p^x] + 2 ln[(1-p_hat)^(T-x) p_hat^x], chi2(1) under H0."""
    p_hat = x / T
    ll0 = _xlogy(T - x, 1 - p) + _xlogy(x, p)
    ll1 = _xlogy(T - x, 1 - p_hat) + _xlogy(x, p_hat)
    return float(max(-2.0 * (ll0 - ll1), 0.0))


@dataclass(frozen=True)
class CoverageResult:
    T: int
    x: int
    expected: float
    rate: float
    lr: float
    pvalue: float


def kupiec(hits: np.ndarray, alpha: float) -> CoverageResult:
    hits = np.asarray(hits, dtype=int)
    T, x, p = len(hits), int(hits.sum()), 1 - alpha
    lr = kupiec_lr(x, T, p)
    return CoverageResult(T, x, p * T, x / T, lr, float(stats.chi2.sf(lr, 1)))


@dataclass(frozen=True)
class ChristoffersenResult:
    lr_ind: float
    p_ind: float
    lr_cc: float
    p_cc: float
    pi01: float
    pi11: float


def christoffersen(hits: np.ndarray, alpha: float) -> ChristoffersenResult:
    """Independence (Markov) and conditional-coverage tests. LR_cc = LR_POF + LR_ind ~ chi2(2),
    with LR_POF on the same T-1 transitions so the decomposition is consistent."""
    hits = np.asarray(hits, dtype=int)
    prev, cur = hits[:-1], hits[1:]
    n00 = int(np.sum((prev == 0) & (cur == 0)))
    n01 = int(np.sum((prev == 0) & (cur == 1)))
    n10 = int(np.sum((prev == 1) & (cur == 0)))
    n11 = int(np.sum((prev == 1) & (cur == 1)))
    if n10 + n11 == 0:
        nan = float("nan")
        return ChristoffersenResult(nan, nan, nan, nan, n01 / max(n00 + n01, 1), nan)
    pi01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    pi11 = n11 / (n10 + n11)
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)
    ll_null = _xlogy(n00 + n10, 1 - pi) + _xlogy(n01 + n11, pi)
    ll_alt = _xlogy(n00, 1 - pi01) + _xlogy(n01, pi01) + _xlogy(n10, 1 - pi11) + _xlogy(n11, pi11)
    lr_ind = max(-2.0 * (ll_null - ll_alt), 0.0)
    lr_pof = kupiec_lr(int(cur.sum()), len(cur), 1 - alpha)
    lr_cc = lr_pof + lr_ind
    return ChristoffersenResult(lr_ind, float(stats.chi2.sf(lr_ind, 1)), lr_cc,
                                float(stats.chi2.sf(lr_cc, 2)), pi01, pi11)


def basel_cutoffs(T: int, alpha: float = 0.99) -> tuple[int, int]:
    """(max green count, min red count) from the binomial CDF of exceptions:
    green if P(X <= x) < 0.95, red if P(X <= x) >= 0.9999 (reproduces 4 / 10 at T = 250)."""
    p = 1 - alpha
    x = np.arange(T + 1)
    cdf = stats.binom.cdf(x, T, p)
    green_max = int(x[cdf < 0.95].max()) if np.any(cdf < 0.95) else -1
    red_min = int(x[cdf >= 0.9999].min())
    return green_max, red_min


def basel_zone(x: int, T: int, alpha: float = 0.99) -> str:
    green_max, red_min = basel_cutoffs(T, alpha)
    if x <= green_max:
        return "green"
    return "red" if x >= red_min else "yellow"


def basel_plus_factor(x: int) -> float:
    """Canonical 250-day plus factor (multiplier = 3 + plus)."""
    return 0.0 if x <= 4 else CANONICAL_PLUS.get(x, 1.0)


def rolling_basel(hits: pd.Series, window: int = 250, alpha: float = 0.99) -> pd.DataFrame:
    """Exceptions and zone over every trailing 250-day window (the only valid canonical use)."""
    counts = hits.astype(int).rolling(window).sum().dropna().astype(int)
    zones = counts.map(lambda x: basel_zone(int(x), window, alpha))
    return pd.DataFrame({"exceptions": counts, "zone": zones})


def zone_shares(rolling: pd.DataFrame) -> dict[str, float]:
    shares = rolling["zone"].value_counts(normalize=True)
    return {z: float(shares.get(z, 0.0)) for z in ("green", "yellow", "red")}


def clopper_pearson(x: int, T: int, level: float = 0.95) -> tuple[float, float]:
    """Exact binomial interval for the exception rate."""
    a = 1 - level
    lo = 0.0 if x == 0 else float(stats.beta.ppf(a / 2, x, T - x + 1))
    hi = 1.0 if x == T else float(stats.beta.ppf(1 - a / 2, x + 1, T - x))
    return lo, hi


def power_kupiec(T: int, p0: float, p1: float, level: float = 0.05) -> float:
    """P(Kupiec rejects at `level`) when the true exception rate is p1 and H0 says p0."""
    crit = stats.chi2.ppf(1 - level, 1)
    xs = np.arange(T + 1)
    reject = np.array([kupiec_lr(int(x), T, p0) > crit for x in xs])
    return float(stats.binom.pmf(xs[reject], T, p1).sum())
