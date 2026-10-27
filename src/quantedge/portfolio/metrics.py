"""Performance KPIs (Step 06 §3.1). Daily data, annualisation factor A = 252.

All functions take simple returns. Excess return e_t = R_t - rf_t.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

A = 252


def _excess(r: pd.Series, rf: pd.Series | float) -> pd.Series:
    if isinstance(rf, pd.Series):
        rf = rf.reindex(r.index)
    return (r - rf).dropna()


def cagr(r: pd.Series) -> float:
    """(V_T / V_0)^(A/T) - 1."""
    r = r.dropna()
    return float((1 + r).prod() ** (A / len(r)) - 1)


def volatility(r: pd.Series) -> float:
    """std(R) sqrt(A)."""
    return float(r.std() * np.sqrt(A))


def sharpe(r: pd.Series, rf: pd.Series | float = 0.0) -> float:
    """mean(e) A / (std(e) sqrt(A)). Returns NaN (with a warning) for zero-volatility series."""
    e = _excess(r, rf)
    sd = e.std()
    if not np.isfinite(sd) or sd < 1e-14:
        warnings.warn("Sharpe undefined for a zero-volatility series", stacklevel=2)
        return float("nan")
    return float(e.mean() / sd * np.sqrt(A))


def sharpe_se_lo(r: pd.Series, rf: pd.Series | float = 0.0) -> float:
    """Lo (2002) i.i.d. standard error of the annualised Sharpe ratio.

    SE(SR_daily) = sqrt((1 + SR_daily^2 / 2) / T);  SE(SR_annual) = SE(SR_daily) sqrt(A).
    """
    e = _excess(r, rf)
    sr_d = e.mean() / e.std()
    return float(np.sqrt((1 + 0.5 * sr_d**2) / len(e)) * np.sqrt(A))


def downside_deviation(r: pd.Series, rf: pd.Series | float = 0.0) -> float:
    """sqrt(mean(min(e, 0)^2)) sqrt(A), with MAR = rf."""
    e = _excess(r, rf)
    return float(np.sqrt((np.minimum(e, 0) ** 2).mean()) * np.sqrt(A))


def sortino(r: pd.Series, rf: pd.Series | float = 0.0) -> float:
    """mean(e) A / downside deviation."""
    dd = downside_deviation(r, rf)
    return float("nan") if dd == 0 else float(_excess(r, rf).mean() * A / dd)


def treynor(r: pd.Series, rf: pd.Series | float, beta: float, min_beta: float = 0.1) -> float:
    """mean(e) A / beta; NaN ("not meaningful") when |beta| < min_beta."""
    if abs(beta) < min_beta:
        return float("nan")
    return float(_excess(r, rf).mean() * A / beta)


def tracking_error(r: pd.Series, bench: pd.Series) -> float:
    """std(R_p - R_b) sqrt(A)."""
    return float((r - bench.reindex(r.index)).dropna().std() * np.sqrt(A))


def information_ratio(r: pd.Series, bench: pd.Series) -> float:
    """mean(R_p - R_b) A / (std(R_p - R_b) sqrt(A))."""
    active = (r - bench.reindex(r.index)).dropna()
    sd = active.std()
    return float("nan") if sd == 0 else float(active.mean() / sd * np.sqrt(A))


def wealth(r: pd.Series) -> pd.Series:
    """Cumulative value of $1 invested, V_t = prod(1 + R)."""
    return (1 + r.fillna(0)).cumprod()


def drawdown_series(values: pd.Series) -> pd.DataFrame:
    """Underwater curve: dd_t = V_t / max_{s<=t} V_s - 1 (zero or negative)."""
    peak = values.cummax()
    return pd.DataFrame({"value": values, "peak": peak, "drawdown": values / peak - 1})


def max_drawdown_info(values: pd.Series) -> dict:
    """Depth, peak, trough and recovery dates and durations (trading days) of the deepest drawdown."""
    dd = drawdown_series(values)["drawdown"]
    depth = float(dd.min())
    if depth == 0:
        return {"max_drawdown": 0.0, "peak": None, "trough": None, "recovery": None,
                "days_to_trough": 0, "days_to_recover": 0}
    trough = dd.idxmin()
    peak = values.loc[:trough].idxmax()
    after = values.loc[trough:]
    recovered = after[after >= values.loc[peak]]
    recovery = recovered.index[0] if len(recovered) else None
    idx = values.index
    return {
        "max_drawdown": depth,
        "peak": peak,
        "trough": trough,
        "recovery": recovery,
        "days_to_trough": int(idx.get_loc(trough) - idx.get_loc(peak)),
        "days_to_recover": None if recovery is None else int(idx.get_loc(recovery) - idx.get_loc(trough)),
    }


def max_drawdown(r: pd.Series) -> float:
    return max_drawdown_info(wealth(r))["max_drawdown"]


def calmar(r: pd.Series) -> float:
    """CAGR / |MDD|."""
    mdd = max_drawdown(r)
    return float("nan") if mdd == 0 else cagr(r) / abs(mdd)


def omega(r: pd.Series, threshold: float = 0.0) -> float:
    """Omega(threshold) = sum max(R - L, 0) / sum max(L - R, 0)."""
    gains = np.maximum(r - threshold, 0).sum()
    losses = np.maximum(threshold - r, 0).sum()
    return float("nan") if losses == 0 else float(gains / losses)


def ulcer_index(r: pd.Series) -> float:
    """sqrt(mean(dd_t^2)): captures both the depth and the duration of drawdowns."""
    dd = drawdown_series(wealth(r))["drawdown"]
    return float(np.sqrt((dd**2).mean()))


def kpi_table(series: dict[str, pd.Series], rf: pd.Series | float, bench: pd.Series,
              betas: dict[str, float] | None = None, alphas: dict[str, tuple[float, float]] | None = None
              ) -> pd.DataFrame:
    """One row per return series. `betas` and `alphas` (alpha_ann, t-stat) come from capm.py."""
    rows = []
    for name, r in series.items():
        r = r.dropna()
        beta = (betas or {}).get(name, np.nan)
        alpha, alpha_t = (alphas or {}).get(name, (np.nan, np.nan))
        sr = sharpe(r, rf)
        se = sharpe_se_lo(r, rf)
        rows.append({
            "series": name, "cagr": cagr(r), "volatility": volatility(r),
            "sharpe": sr, "sharpe_ci_low": sr - 1.96 * se, "sharpe_ci_high": sr + 1.96 * se,
            "sortino": sortino(r, rf), "treynor": treynor(r, rf, beta) if np.isfinite(beta) else np.nan,
            "jensen_alpha": alpha, "jensen_alpha_t": alpha_t, "beta": beta,
            "information_ratio": information_ratio(r, bench), "tracking_error": tracking_error(r, bench),
            "max_drawdown": max_drawdown(r), "calmar": calmar(r), "omega": omega(r),
            "ulcer": ulcer_index(r), "skew": float(r.skew()), "excess_kurtosis": float(r.kurt()),
            "hit_rate": float((r > 0).mean()),
        })
    return pd.DataFrame(rows).set_index("series")


_TEMPLATES = {
    "sharpe": "Sharpe {v:.2f}: each unit of total volatility earned {v:.2f} units of excess return a year.",
    "sortino": "Sortino {v:.2f}: each unit of downside volatility earned {v:.2f} units of excess return.",
    "treynor": "Treynor {v:.2%}: excess return per unit of market (beta) risk.",
    "jensen_alpha": "Jensen's alpha {v:.2%} a year: return beyond what CAPM predicts for this beta.",
    "information_ratio": "Information ratio {v:.2f}: active return per unit of tracking error versus 60/40.",
    "max_drawdown": "Max drawdown {v:.1%}: the worst peak-to-trough fall an investor would have lived through.",
    "calmar": "Calmar {v:.2f}: annual growth per unit of worst drawdown.",
    "omega": "Omega {v:.2f}: total gains are {v:.2f} times total losses.",
    "ulcer": "Ulcer index {v:.3f}: combines how deep and how long drawdowns lasted.",
    "volatility": "Volatility {v:.1%} a year: typical size of annual swings.",
    "cagr": "Growth {v:.2%} a year, compounded.",
}


def interpret(kpi: str, value: float) -> str:
    """Plain-English sentence for one KPI value (shown under the KPI cards in the app)."""
    if value is None or not np.isfinite(value):
        return f"{kpi}: not meaningful for this series."
    template = _TEMPLATES.get(kpi)
    return template.format(v=value) if template else f"{kpi}: {value:.4g}"
