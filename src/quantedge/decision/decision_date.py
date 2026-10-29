"""The decision at the decision date (after the freeze): one source of truth for every headline number.

Production counterpart of notebook 06 Part B (spec §5). It scores the minimum-variance frontier with
data before `decision.date` (t − 1), applies the locked rule, and writes:

- `decision_numbers.json`: verdict, recommended weights, required and expected return, risk limits,
  losses in dollars, the margins that would flip the verdict, model validity, ten-year odds;
- `decision_frontier.parquet`: every frontier point on every criterion;
- `decision_robustness.parquet`: the verdict over the D4 assumption grid.

The app, the memo and the defence document read these files only, so a number has one value
everywhere. `tests/test_decision_date.py` checks them against notebook 06 Part B.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from quantedge.config import Config
from quantedge.data.partition import Partition, TestLockedError, load_returns
from quantedge.decision.ips import IPSLimits, constraints_for_optimizer
from quantedge.decision.objective import (
    crisis_loss,
    forward_asset_returns,
    forward_portfolio_return,
    through_the_cycle,
)
from quantedge.paths import ARTIFACTS
from quantedge.portfolio import optimize as opt
from quantedge.stress.factor import (
    estimate_factor_betas,
    regime_stress_weeks,
    scenario_loss,
    weekly_factors,
    weekly_log_returns,
)

EQUITY_NAME = "{:.0%} equity"


def es_shares(w: pd.Series, returns: pd.DataFrame, alpha: float = 0.99) -> pd.Series:
    """Euler 99% ES shares on the full history (notebook 06 A6): E[w_i L_i | L_p ≥ VaR] / E[L_p | L_p ≥ VaR]."""
    loss = -(returns @ w)
    tail = loss >= loss.quantile(alpha)
    return w * (-returns.loc[tail].mean()) / loss[tail].mean()


def resize_d8(w: pd.Series, returns: pd.DataFrame, cap: float, spy_cap: float, step: float = 0.005) -> tuple[pd.Series, float]:
    """D8 sizing: move weight from the ETF above the ES-share cap to SPY in 0.5 pp steps (SPY cap respected)."""
    w = w.copy()
    moved = 0.0
    for _ in range(200):
        sh = es_shares(w, returns)
        if sh.max() <= cap:
            break
        big = sh.idxmax()
        d = min(step, w[big], spy_cap - w["SPY"])
        if d <= 0 or big == "SPY":
            break
        w[big] -= d
        w["SPY"] += d
        moved += d
    return w, moved


def ten_year_odds(w: pd.Series, returns: pd.DataFrame, cpi: pd.Series, fwd: float, inflation: float,
                  spending: float, growth: float, paths: int, months: int, block: int, seed: int) -> dict[str, float]:
    """Notebook 06 B6: stationary bootstrap of monthly returns and US CPI (2005 → decision date), each
    re-centred to its forward value; P(10-year real return ≥ the objective) and P(real value after
    spending < 80%), spending = rate × average value of the last 36 months."""
    rng = np.random.default_rng(seed)
    monthly = (1 + returns.loc["2005-01-01":]).resample("ME").prod() - 1
    infl = cpi.pct_change().reindex(monthly.index, method="ffill").to_numpy()
    r = (monthly @ w).to_numpy()
    r = r - r.mean() + ((1 + fwd) ** (1 / 12) - 1)
    f = infl - np.nanmean(infl) + ((1 + inflation) ** (1 / 12) - 1)
    f = np.nan_to_num(f, nan=(1 + inflation) ** (1 / 12) - 1)
    n = len(r)
    idx = rng.integers(0, n, paths)
    gross, price, value, hist = np.ones(paths), np.ones(paths), np.ones(paths), [np.ones(paths)] * 36
    for _ in range(months):
        gross *= 1 + r[idx]
        price *= 1 + f[idx]
        value = value * (1 + r[idx])
        hist = hist[1:] + [value]
        value = value - spending / 12 * np.mean(hist, axis=0)
        jump = rng.random(paths) < 1 / block
        idx = np.where(jump, rng.integers(0, n, paths), (idx + 1) % n)
    real_ann = (gross / price) ** (12 / months) - 1
    target = (1 + spending) * (1 + growth) - 1
    return {"p_objective": float(np.mean(real_ann >= target)), "median_real_return": float(np.median(real_ann)),
            "p_real_value_below_80": float(np.mean(value / price < 0.8)), "paths": paths}


def _fred(raw, name: str, before: pd.Timestamp) -> pd.Series:
    s = raw.fred[name].dropna()
    return s.loc[s.index < before]


def run(cfg: Config, raw=None, write: bool = True) -> dict:
    """Score the frontier at the decision date and apply the locked rule (spec §5)."""
    from quantedge.data.load import load_raw

    part = Partition.from_config(cfg)
    if not part.frozen():
        raise TestLockedError("Decision-date numbers use 2023+ data: create the freeze tag first.")
    raw = raw if raw is not None else load_raw()
    D = pd.Timestamp(cfg.decision["date"])
    ips, dec, fwd_cfg = cfg.ips, cfg.decision, cfg.ips["forward"]
    returns = load_returns("all", cfg).loc[lambda r: r.index < D]
    tickers = list(returns.columns)
    nav = cfg.nav_usd

    # Inputs at t − 1 (G1): yields, breakeven inflation, betas, dividend yields, long-run covariance
    y10, pi, tips = (float(_fred(raw, n, D).iloc[-1]) / 100 for n in ("DGS10", "T10YIE", "DFII10"))
    spending, growth = ips["spending_rate"], ips["real_growth"]
    required = (1 + spending) * (1 + growth) * (1 + pi) - 1
    est = returns.iloc[-fwd_cfg["beta_window"]:]
    beta = est.cov()["SPY"] / est["SPY"].var()
    close = raw.close.loc[raw.close.index < D, tickers]
    divs = raw.dividends.loc[raw.dividends.index < D, tickers].fillna(0.0)
    div_yield = divs.loc[returns.index[-1] - pd.Timedelta(days=365):].sum() / close.iloc[-1]
    cov_long = pd.DataFrame(LedoitWolf().fit(returns.to_numpy()).covariance_ * 252, index=tickers, columns=tickers)

    def fwd_return(w: pd.Series, erp=fwd_cfg["erp"], spread=fwd_cfg["agg_spread"], agg_wht=0.0, dy=0.0) -> float:
        f = {**fwd_cfg, "erp": erp, "agg_spread": spread,
             "withholding": {**fwd_cfg["withholding"], "AGG": agg_wht}}
        net = forward_asset_returns(y10 + dy, pi, beta, div_yield, f)
        return forward_portfolio_return(w, net, cov_long)

    # Scenario betas at the decision date (D5: regime stress weeks, weekly log returns, liquidity day)
    macro = pd.DataFrame({k: _fred(raw, k, D) for k in ("DGS10", "DCOILWTICO", "VIXCLS", "DTWEXBGS", "BAA10Y")})
    mask = regime_stress_weeks(returns.index, _fred(raw, "DTB3", D))
    betas = estimate_factor_betas(weekly_log_returns(returns), weekly_factors(macro), sample="regime", mask=mask).betas
    hyp = cfg.stress["hypothetical"]

    # Frontier (G2, G3): minimum variance (Ledoit-Wolf, 756 days) at each equity share under the D3 caps
    limits = IPSLimits.from_config(ips)
    cons = constraints_for_optimizer(limits, tickers)
    sigma = pd.DataFrame(LedoitWolf().fit(est.to_numpy()).covariance_ * 252, index=tickers, columns=tickers)
    equity = list(ips["limits"]["equity_group"])
    levels = [float(x) for x in dec["frontier_levels"]]
    weights = {x: opt.min_var_at_equity(sigma, cons, equity, x).weights.clip(lower=0.0) for x in levels}
    weights = {x: w / w.sum() for x, w in weights.items()}
    dev = returns.loc[: part.dev[1]]
    net_income = div_yield * (1 - pd.Series({t: fwd_cfg["withholding"].get(t, 0.0) for t in tickers}))
    rows = {}
    for x, w in weights.items():
        ttc = through_the_cycle(w, dev)
        crises = crisis_loss(w, returns, cfg.stress["historical"])
        sh = es_shares(w, returns)
        rows[x] = {"forward_return": fwd_return(w), "vol_ttc": ttc["vol_ann"], "es99_ttc": ttc["es99_1d"],
                   "worst_crisis_loss": float(crises.max()), "worst_crisis": str(crises.idxmax()),
                   "hypothetical_loss": scenario_loss(betas, hyp["shock"], w, hyp.get("liquidity_day")),
                   "income_yield": float(w @ net_income), "largest_es_share": float(sh.max()), "largest_es_share_etf": str(sh.idxmax()),
                   "caps_binding": ", ".join(t for t in tickers if abs(w[t] - limits.cap(t)) < 1e-4)}
    fr = pd.DataFrame(rows).T
    fr.index.name = "equity_share"
    num = ["forward_return", "vol_ttc", "es99_ttc", "worst_crisis_loss", "hypothetical_loss", "income_yield", "largest_es_share"]
    fr[num] = fr[num].astype(float)
    fr["d2_loss"] = fr[["worst_crisis_loss", "hypothetical_loss"]].max(axis=1)

    # D2 limits recalibrated mechanically at this date (G4)
    xs = np.array(levels)
    x_at = float(np.interp(ips["crisis_budget"], fr["d2_loss"], xs))
    vol_lim, es_lim = float(np.interp(x_at, xs, fr["vol_ttc"])), float(np.interp(x_at, xs, fr["es99_ttc"]))
    budget = ips["crisis_budget"]
    fr["within_limits"] = (fr["d2_loss"] <= budget + 1e-9) & (fr["vol_ttc"] <= vol_lim + 1e-9) & (fr["es99_ttc"] <= es_lim + 1e-9)
    fr["meets_objective"] = fr["forward_return"] >= required

    # The locked rule (spec §5, D10 as amended 2026-10-28/29)
    def rule(f: dict[float, float]) -> tuple[str, float | None]:
        ok = [x for x in levels if f[x] >= required and fr.loc[x, "within_limits"]]
        if ok:
            return "ACCEPT", min(ok)
        near = [x for x in levels if f[x] >= required and fr.loc[x, "d2_loss"] <= budget + dec["max_budget_loosening"] + 1e-9]
        return ("ADJUST THE RISK LIMIT", min(near)) if near else ("REJECT", None)

    verdict, rec = rule(fr["forward_return"].to_dict())
    feasible = [x for x in levels if fr.loc[x, "within_limits"]]
    best = max(feasible, key=lambda x: fr.loc[x, "forward_return"])
    point = rec if rec is not None else best
    sustainable = (1 + fr.loc[best, "forward_return"]) / ((1 + pi) * (1 + growth)) - 1

    def accept_at(**kw) -> bool:
        return any(fwd_return(weights[x], **kw) >= required for x in feasible)

    if verdict == "ACCEPT":
        lose_dy = next((float(d) for d in np.arange(0, -0.03001, -0.0005) if not accept_at(dy=d)), float("nan"))
        yield_margin = {"direction": "ACCEPT is lost if the real yield falls by", "pp": -lose_dy, "tips_threshold": tips + lose_dy}
    else:
        gain_dy = next((float(d) for d in np.arange(0, 0.03001, 0.0005) if accept_at(dy=d)), float("nan"))
        yield_margin = {"direction": "ACCEPT needs the real yield to rise by", "pp": gain_dy, "tips_threshold": tips + gain_dy}
    erp_breakeven = next((float(e) for e in np.arange(0, 0.15001, 0.0005) if accept_at(erp=e)), float("nan"))

    rob = dec["robustness"]
    grid = []
    for e in rob["erp"]:
        for s in rob["agg_spread"]:
            for t in rob["agg_withholding"]:
                v, _ = rule({x: fwd_return(weights[x], erp=e, spread=s, agg_wht=t) for x in levels})
                grid.append({"erp": e, "agg_spread": s, "agg_withholding": t, "verdict": v.split()[0],
                             "best_margin": max(fwd_return(weights[x], erp=e, spread=s, agg_wht=t) for x in feasible) - required})
    grid = pd.DataFrame(grid)

    # D8 sizing on the recommended (or advised) point
    w0 = weights[point]
    w_final, moved = resize_d8(w0, returns, dec["es_share_cap"], limits.cap("SPY"))
    sh_final = es_shares(w_final, returns)

    def dollars(x: float) -> dict[str, float]:
        r = fr.loc[x]
        return {"equity_share": x, "expected_return_usd": r.forward_return * nav, "shortfall_usd": (required - r.forward_return) * nav,
                "worst_crisis_usd": r.worst_crisis_loss * nav, "hypothetical_usd": r.hypothetical_loss * nav,
                "es99_ttc_usd": r.es99_ttc * nav, "income_usd": r.income_yield * nav, "within_limits": bool(r.within_limits),
                "meets_objective": bool(r.meets_objective)}

    i = levels.index(point)
    alternatives = {"lower_risk": dollars(levels[max(i - 1, 0)]), "recommended": dollars(point),
                    "higher_return": dollars(levels[min(i + 1, len(levels) - 1)])}

    sim = dec["simulation"]
    odds = ten_year_odds(w_final, returns, raw.fred["CPIAUCSL"].loc[lambda s: s.index < D], fwd_return(w_final), pi,
                         spending, growth, sim["paths"], sim["months"], sim["block"], sim["seed"])

    final = json.loads((ARTIFACTS / "final_test_result.json").read_text(encoding="utf-8")) \
        if (ARTIFACTS / "final_test_result.json").exists() else {}
    scores = pd.read_parquet(ARTIFACTS / "final_test_scores.parquet") if (ARTIFACTS / "final_test_scores.parquet").exists() else None
    champ = final.get("champion")
    model = {}
    if scores is not None and champ in scores.index:
        c = scores.loc[champ]
        model = {"champion": champ, "test_start": final["test_start"], "test_end": final["test_end"], "days": final["days"],
                 "exceptions": int(c.exceptions), "expected": 0.01 * final["days"], "kupiec_p": float(c.kupiec_p),
                 "cc_p": float(c.cc_p), "passes": bool(c.passes), "limits_model": final.get("limits_model"),
                 "models_passing": [m for m in scores.index if bool(scores.loc[m, "passes"])],
                 "challenger_adopted": bool(final.get("condition_3", {}).get("Linear QR", False))}

    numbers = {
        "decision_date": str(D.date()), "data_end": str(returns.index[-1].date()), "nav_usd": nav,
        "verdict": verdict, "recommended_equity": rec, "advised_equity": point,
        "weights": {t: float(v) for t, v in w_final.items()}, "weights_before_d8": {t: float(v) for t, v in w0.items()},
        "d8_moved_to_spy": moved, "largest_es_share": float(sh_final.max()), "largest_es_share_etf": str(sh_final.idxmax()),
        "objective": {"spending": spending, "real_growth": growth, "inflation_breakeven": pi, "required_return": required,
                      "y10": y10, "tips": tips},
        "expected_return": fwd_return(w_final), "return_margin": fwd_return(w_final) - required,
        "return_margin_usd": (fwd_return(w_final) - required) * nav, "sustainable_spending": float(sustainable),
        "limits": {"crisis_budget": budget, "vol_max": vol_lim, "es99_max": es_lim, "equity_at_budget": x_at},
        "risk": {k: float(fr.loc[point, k]) for k in ("vol_ttc", "es99_ttc", "worst_crisis_loss", "hypothetical_loss", "d2_loss",
                                                    "income_yield")} | {"worst_crisis": str(fr.loc[point, "worst_crisis"])},
        "yield_margin": yield_margin, "erp_breakeven": erp_breakeven,
        "robustness": {k: int(v) for k, v in grid["verdict"].value_counts().items()},
        "alternatives": alternatives, "ten_year": odds, "model_validity": model,
        "scenario": {"name": hyp["name"], "loss": float(fr.loc[point, "hypothetical_loss"])},
    }
    if write:
        (ARTIFACTS / "decision_numbers.json").write_text(json.dumps(numbers, indent=2, default=float), encoding="utf-8")
        fr.to_parquet(ARTIFACTS / "decision_frontier.parquet")
        grid.to_parquet(ARTIFACTS / "decision_robustness.parquet")
        pd.DataFrame(weights).T.rename_axis("equity_share").to_parquet(ARTIFACTS / "decision_weights.parquet")
    return {"numbers": numbers, "frontier": fr, "grid": grid, "weights": weights}


if __name__ == "__main__":
    from quantedge.config import load_config

    out = run(load_config())
    n = out["numbers"]
    print(f"{n['decision_date']}: {n['verdict']} at {n['advised_equity']:.0%} equity; expected {n['expected_return']:.2%} "
          f"vs required {n['objective']['required_return']:.2%}; robustness {n['robustness']}")
