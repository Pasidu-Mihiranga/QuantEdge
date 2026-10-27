"""Feature set for the ML challengers (Step 22 §3.6). Every feature in row t uses data dated <= t.

Target (built elsewhere): l_{t+1} = -w_tau(t)' R_{t+1} at point-in-time weights.
Return features are pro-forma: today's weights applied to past asset returns, which is valid because
the weights are known at t. FRED series are lagged one extra day (publication delay).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from arch import arch_model

FRED_LAG = 1


def pro_forma_returns(returns: pd.DataFrame, wpath: pd.DataFrame, lags: int = 5) -> pd.DataFrame:
    """r_{t-k} computed with the weights known at t (k = 0 .. lags-1)."""
    cols = list(wpath.columns)
    r = returns[cols].to_numpy()
    w = wpath.reindex(returns.index).to_numpy()
    out = {}
    for k in range(lags):
        shifted = np.vstack([np.full((k, len(cols)), np.nan), r[: len(r) - k]]) if k else r
        out[f"ret_lag{k}"] = np.einsum("ij,ij->i", shifted, w)
    return pd.DataFrame(out, index=returns.index)


def garch_sigma_path(r: pd.Series, refit_every: int = 21, min_obs: int = 500) -> pd.Series:
    """One-step-ahead GARCH(1,1)-t volatility sigma_{t+1|t}, without look-ahead.

    Parameters are re-estimated every `refit_every` days on data <= t and then held fixed while the
    variance recursion is filtered forward: s2_{t+1} = omega + alpha e_t^2 + beta s2_t.
    """
    x = 100.0 * r.to_numpy()
    n = len(x)
    out = np.full(n, np.nan)
    params, s2_next = None, None
    for t in range(min_obs - 1, n):
        if params is None or (t - (min_obs - 1)) % refit_every == 0:
            res = arch_model(x[: t + 1], mean="Constant", vol="GARCH", p=1, q=1, dist="t",
                             rescale=False).fit(disp="off", show_warning=False)
            params = res.params
            s2_t = float(res.conditional_volatility[-1] ** 2)   # sigma^2_t | t-1 from the new fit
        else:
            s2_t = s2_next                                     # carried from the previous day
        e_t = x[t] - params["mu"]
        s2_next = params["omega"] + params["alpha[1]"] * e_t**2 + params["beta[1]"] * s2_t
        out[t] = math.sqrt(s2_next) / 100.0
    return pd.Series(out, index=r.index, name="garch_sigma")


def build_features(returns: pd.DataFrame, macro: pd.DataFrame, wpath: pd.DataFrame,
                   garch_sigma: pd.Series | None = None) -> pd.DataFrame:
    """Feature matrix indexed by the forecast origin t."""
    f = pro_forma_returns(returns, wpath)
    r0 = f["ret_lag0"]
    for w in (5, 20, 60):
        f[f"rv_{w}"] = r0.rolling(w).std() * math.sqrt(252)
    f["ewma_vol"] = np.sqrt((r0**2).ewm(alpha=1 - 0.94, adjust=False).mean() * 252)
    f["downside_semivol_20"] = np.sqrt((np.minimum(r0, 0) ** 2).rolling(20).mean() * 252)
    if garch_sigma is not None:
        f["garch_sigma"] = garch_sigma.reindex(f.index)

    m = macro.reindex(f.index).shift(FRED_LAG)
    f["vix"] = m["VIXCLS"]
    f["vix_chg5"] = m["VIXCLS"].diff(5)
    f["dgs10_chg5"] = m["DGS10"].diff(5)
    f["credit_chg5"] = m["BAA10Y"].diff(5)

    rets = returns[list(wpath.columns)]
    corr = rets.rolling(60).corr()
    k = rets.shape[1]
    avg = corr.groupby(level=0).apply(lambda c: (c.to_numpy().sum() - k) / (k * (k - 1)))
    f["avg_corr_60"] = avg.reindex(f.index)
    f["spy_agg_corr_60"] = rets["SPY"].rolling(60).corr(rets["AGG"])

    wealth = (1 + r0.fillna(0)).cumprod()
    f["dist_252d_high"] = wealth / wealth.rolling(252, min_periods=1).max() - 1
    return f


VOL_FEATURES = ("rv_5", "rv_20", "rv_60", "ewma_vol", "downside_semivol_20", "garch_sigma", "vix")
