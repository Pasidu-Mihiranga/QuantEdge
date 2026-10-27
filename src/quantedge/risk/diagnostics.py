"""Why the VaR models disagree (Step 08 §3.3) and the ES/VaR tail signal (Step 09 §3.4).

The table supplies the statistics; the team writes the final interpretation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch

from quantedge.risk.es import NORMAL_ES_VAR_RATIO
from quantedge.risk.var import HistoricalModel


def tail_statistics(losses: pd.Series, lags: int = 10) -> dict[str, float]:
    x = losses.dropna()
    return {
        "skew_loss": float(stats.skew(x)),
        "excess_kurtosis": float(stats.kurtosis(x)),
        "jarque_bera_p": float(stats.jarque_bera(x).pvalue),
        "ljungbox_sq_p": float(acorr_ljungbox(x**2, lags=[lags], return_df=True)["lb_pvalue"].iloc[0]),
        "arch_lm_p": float(het_arch(x, nlags=lags)[1]),
    }


def disagreement_table(models: dict[str, object], alphas=(0.90, 0.95, 0.99)) -> pd.DataFrame:
    """VaR of every fitted model at each alpha, plus each model's gap to historical simulation."""
    rows = []
    for a in alphas:
        row = {"alpha": a}
        for name, m in models.items():
            row[name] = m.var(a)
        rows.append(row)
    table = pd.DataFrame(rows).set_index("alpha")
    if "Historical" in table and "Normal" in table:
        table["HS / Normal"] = table["Historical"] / table["Normal"]
    return table


def window_sensitivity(returns: pd.Series, windows=(250, 500, 1000), alphas=(0.95, 0.99)) -> pd.DataFrame:
    """Historical VaR on the most recent W days: how much 'history choice' moves the number."""
    rows = []
    for w in windows:
        m = HistoricalModel().fit(returns.iloc[-w:])
        rows.append({"window": w, **{f"var_{int(a * 100)}": m.var(a) for a in alphas}})
    return pd.DataFrame(rows).set_index("window")


def es_var_ratio_table(models: dict[str, object], alphas=(0.95, 0.975, 0.99)) -> pd.DataFrame:
    """ES/VaR per model next to the Normal reference (1.254 at 95%, 1.146 at 99%).

    A historical ratio above the reference is direct evidence of a fatter-than-Normal tail.
    """
    rows = []
    for name, m in models.items():
        for a in alphas:
            v = m.var(a)
            rows.append({"model": name, "alpha": a, "var": v, "es": m.es(a),
                         "es_var_ratio": m.es(a) / v if v > 0 else np.nan,
                         "normal_reference": NORMAL_ES_VAR_RATIO[a]})
    return pd.DataFrame(rows)


def gap_sentence(table: pd.DataFrame, facts: dict[str, float], alpha: float = 0.99) -> str:
    """Draft sentence linking the observed Normal-vs-HS gap to the kurtosis evidence."""
    hs, nm = table.loc[alpha, "Historical"], table.loc[alpha, "Normal"]
    gap = (nm - hs) / hs
    direction = "below" if gap < 0 else "above"
    return (f"At {alpha:.0%}, Normal VaR is {abs(gap):.0%} {direction} historical VaR; portfolio excess "
            f"kurtosis is {facts['excess_kurtosis']:.1f} (Jarque-Bera p = {facts['jarque_bera_p']:.3g}).")
