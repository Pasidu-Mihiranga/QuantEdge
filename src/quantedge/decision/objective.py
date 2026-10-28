"""Return objective and risk-limit evidence measured as the team agreed (D1, D2, D4, D10).

Ported from notebooks 03 §4 and 06 A2 so the pipeline, the app and the memo give the verdict the
notebooks give. Every input is dated at `as_of` (the end of validation until the freeze; the
decision date after it).

- Required return (D1): `quantedge.decision.ips.required_return`.
- Forward expected return (D4, spec §3.1): AGG = y10 + spread; equities = y10 + β × ERP;
  GLD = breakeven inflation; minus expense ratios, withholding tax on dividends and trading costs;
  minus the volatility drag ½ wᵀΣw (a geometric, compound return).
- Risk evidence (D2): volatility and 99% ES through the cycle (development data, which includes
  the GFC) and the worst crisis loss, all with today's weights held fixed.
- Limit calibration (D2): the frontier point whose worst crisis loss equals the crisis budget sets
  the volatility and ES limits.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from quantedge.risk.es import sample_es


def forward_asset_returns(y10: float, inflation: float, beta: pd.Series, div_yield: pd.Series,
                          fwd: dict) -> pd.Series:
    """Net arithmetic forward return per ETF (spec §3.1), before the portfolio volatility drag.

    μ_AGG = y10 + spread, μ_GLD = π, μ_i = y10 + β_i × ERP otherwise; net = μ − expense −
    dividend yield × withholding − trading cost.
    """
    tickers = list(beta.index)
    mu = pd.Series({t: (y10 + fwd["agg_spread"] if t == "AGG" else inflation if t == "GLD"
                        else y10 + float(beta[t]) * fwd["erp"]) for t in tickers})
    expense = pd.Series(fwd["expense_ratios"], dtype=float).reindex(tickers).fillna(0.0)
    wht = pd.Series({t: fwd["withholding"].get(t, 0.0) for t in tickers}, dtype=float)
    return mu - expense - div_yield.reindex(tickers).fillna(0.0) * wht - fwd["trading_cost"]


def forward_portfolio_return(w: pd.Series, net: pd.Series, cov_annual: pd.DataFrame) -> float:
    """Geometric forward return: wᵀ net − ½ wᵀΣw."""
    w = w.reindex(net.index, fill_value=0.0)
    s = cov_annual.loc[net.index, net.index].to_numpy()
    return float(w @ net - 0.5 * w.to_numpy() @ s @ w.to_numpy())


def forward_inputs(returns: pd.DataFrame, close: pd.DataFrame, dividends: pd.DataFrame,
                   macro: pd.DataFrame, as_of: pd.Timestamp, beta_window: int = 756) -> dict:
    """Market inputs at `as_of`: 10-year yield, breakeven inflation, betas to SPY (last
    `beta_window` days), trailing 12-month dividend yield, long-run Ledoit-Wolf covariance (annual)."""
    r = returns.loc[:as_of]
    est = r.iloc[-beta_window:]
    beta = est.cov()["SPY"] / est["SPY"].var()
    c, d = close.loc[:as_of, r.columns], dividends.loc[:as_of, r.columns].fillna(0.0)
    div_yield = d.loc[r.index[-1] - pd.Timedelta(days=365):].sum() / c.iloc[-1]
    cov = pd.DataFrame(LedoitWolf().fit(r.to_numpy()).covariance_ * 252, index=r.columns, columns=r.columns)
    return {"y10": float(macro["DGS10"].loc[:as_of].dropna().iloc[-1]) / 100,
            "inflation": float(macro["T10YIE"].loc[:as_of].dropna().iloc[-1]) / 100,
            "beta": beta, "div_yield": div_yield, "cov_long": cov}


def path_loss(r: pd.Series) -> float:
    """Peak-to-trough loss of a daily return path (positive), starting from a value of 1."""
    v = (1 + r).cumprod()
    return float(-(v / np.maximum(v.cummax(), 1.0) - 1).min())


def crisis_loss(w: pd.Series, returns: pd.DataFrame, windows: dict[str, tuple[str, str]]) -> pd.Series:
    """Loss in each historical crisis window with today's weights held fixed (constant mix).

    The window runs from the peak close to the trough close, so the path starts the day after `start`."""
    p = returns @ w.reindex(returns.columns, fill_value=0.0)
    return pd.Series({name: path_loss(p.loc[(p.index > pd.Timestamp(a)) & (p.index <= pd.Timestamp(b))])
                      for name, (a, b) in windows.items()})


def through_the_cycle(w: pd.Series, dev_returns: pd.DataFrame, alpha: float = 0.99) -> dict[str, float]:
    """Annualised volatility and Acerbi-Tasche 99% 1-day ES of today's weights on development data."""
    loss = -(dev_returns @ w.reindex(dev_returns.columns, fill_value=0.0))
    return {"vol_ann": float(loss.std() * np.sqrt(252)), "es99_1d": sample_es(loss.to_numpy(), alpha)}


def calibrate_limits(frontier: dict[float, pd.Series], dev_returns: pd.DataFrame, returns: pd.DataFrame,
                     windows: dict[str, tuple[str, str]], budget: float) -> tuple[pd.DataFrame, dict[str, float]]:
    """Notebook 03 §4: the equity share whose worst crisis loss equals the budget, and the
    through-the-cycle volatility and ES at that share (linear interpolation along the frontier)."""
    rows = {}
    for x, w in sorted(frontier.items()):
        rows[x] = {**through_the_cycle(w, dev_returns), "worst_crisis_loss": float(crisis_loss(w, returns, windows).max())}
    table = pd.DataFrame(rows).T.rename_axis("equity_share")
    xs, loss = table.index.to_numpy(float), table["worst_crisis_loss"].to_numpy()
    x_at = float(np.interp(budget, loss, xs))
    return table, {"crisis_budget": budget, "equity_share": x_at,
                   "vol_ann_max": float(np.interp(x_at, xs, table["vol_ann"])),
                   "es99_1d_max": float(np.interp(x_at, xs, table["es99_1d"]))}
