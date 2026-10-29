"""Precompute pipeline (Step 15 §3.1). Stages are added as each step is built.

    python -m quantedge.pipeline
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from quantedge.config import Config, load_config
from quantedge.data.cleaning import build_clean_dataset
from quantedge.data.partition import Partition, load_returns
from quantedge.decision.ips import IPSLimits, required_return
from quantedge.paths import ARTIFACTS
from quantedge.portfolio.returns import build_returns
from quantedge.portfolio.walkforward import candidate_strategies, scorecard, walk_forward


def run_portfolio_selection(cfg: Config, macro: pd.DataFrame, variant: str | None = None,
                            mrp: float = 0.05, allow_cash: bool = False, tag: str | None = None) -> dict:
    """Step 07 walk-forward selection on dev + validation only (Step 22: test locked).

    `variant` names an `ips.variants` case; `mrp` and `allow_cash` are sensitivity settings. Any
    non-base run writes only a suffixed scorecard and is never used for selection."""
    from quantedge.portfolio.returns import CASH, add_cash_asset

    part = Partition.from_config(cfg)
    end = part.val[1]
    returns = load_returns("dev+val", cfg)
    rf = pd.read_parquet(ARTIFACTS / "returns_rf.parquet")["rf"].reindex(returns.index)
    tickers = list(cfg.universe)
    if allow_cash:
        returns = add_cash_asset(returns, rf)
        tickers.append(CASH)
    limits = IPSLimits.from_config(cfg.ips, variant)
    req = required_return(macro["CPIAUCSL"], cfg.ips["spending_rate"], cfg.ips["real_growth"],
                          macro["T10YIE"], cfg.ips["cpi_years"], as_of=end)
    strategies, _ = candidate_strategies(cfg, limits, tickers, mrp=mrp)
    results = {name: walk_forward(returns, s, rf, window=cfg.portfolio.estimation_window_days,
                                  cost_bps=cfg.portfolio.cost_bps_per_side, name=name)
               for name, s in strategies.items()}
    card = scorecard(results, limits, req["required_return"], cfg.stress["historical"], end, rf)
    tag = tag or variant
    if tag is not None:
        card.to_parquet(ARTIFACTS / f"portfolio_scorecard_val_{tag}.parquet")
        return {"scorecard": card, "results": results, "required_return": req}
    card.to_parquet(ARTIFACTS / "portfolio_scorecard_val.parquet")
    pd.DataFrame({k: r.perf for k, r in results.items()}).to_parquet(ARTIFACTS / "wf_performance_val.parquet")
    for name, r in results.items():
        slug = name.lower().replace(" ", "_").replace("/", "").replace("(", "").replace(")", "")
        r.weights_history.to_parquet(ARTIFACTS / f"wf_weights_{slug}.parquet")
    (ARTIFACTS / "required_return.json").write_text(json.dumps(req, indent=2), encoding="utf-8")
    return {"scorecard": card, "results": results, "required_return": req}


def run_evt(cfg: Config, wf_result, label: str) -> dict:
    """Step 10 threshold analysis on the point-in-time risk series of one candidate (dev + val)."""
    from quantedge.portfolio.weights_path import pit_risk_returns, point_in_time_weights
    from quantedge.risk import evt

    returns = load_returns("dev+val", cfg)
    wpath = point_in_time_weights(wf_result.weights_history, returns.index, cfg.partition.warmup_weights)
    losses = -pit_risk_returns(returns, wpath).to_numpy()
    rng = cfg.rng(stream=10)
    ev = evt.threshold_evidence(losses, cfg.evt.threshold_quantiles, rng, B=200)
    choices = [evt.select_threshold_diagnostic(losses, ev, cfg.evt.min_exceedances),
               evt.select_threshold_forwardstop(losses, ev),
               evt.select_threshold_fixed(losses, 0.95, ev)]
    table = evt.sensitivity_table(losses, choices, ps=(0.99, 0.995, 0.999, evt.return_level_p(10)))
    table.insert(0, "portfolio", label)
    ev.to_parquet(ARTIFACTS / "evt_threshold_evidence.parquet")
    table.to_parquet(ARTIFACTS / "evt_sensitivity.parquet")
    return {"evidence": ev, "choices": choices, "table": table, "losses": losses}


def backtest_specs(cfg: Config, evt_threshold_q: float = 0.90) -> list:
    """The eight conventional models plus the two GJR variants, with their refit cadence (Step 11 §3.1)."""
    from quantedge.backtest.engine import ModelSpec
    from quantedge.risk.evt import ConditionalEVTModel, EVTModel
    from quantedge.risk.garch import GarchFHSModel
    from quantedge.risk.montecarlo import MonteCarloModel
    from quantedge.risk.var import CornishFisherModel, HistoricalModel, NormalModel, StudentTModel

    rng = cfg.rng(stream=11)
    return [
        ModelSpec("Historical", HistoricalModel, 1),
        ModelSpec("Normal", NormalModel, 1),
        ModelSpec("Student-t", StudentTModel, 1),
        ModelSpec("Cornish-Fisher", CornishFisherModel, 1),
        ModelSpec("EVT", lambda: EVTModel(evt_threshold_q), cfg.backtest.refit_every),
        ModelSpec("Monte Carlo", lambda: MonteCarloModel(n_sims=20_000, rng=rng), cfg.backtest.refit_every),
        ModelSpec("GARCH-FHS", GarchFHSModel, cfg.backtest.refit_every),
        ModelSpec("Conditional EVT", ConditionalEVTModel, cfg.backtest.refit_every),
        ModelSpec("GJR-FHS", lambda: GarchFHSModel(o=1), cfg.backtest.refit_every),
        ModelSpec("GJR conditional EVT", lambda: ConditionalEVTModel(o=1), cfg.backtest.refit_every),
    ]


def run_backtests(cfg: Config, wf_result, label: str, window: int | None = None) -> dict:
    """Step 11 walk-forward backtests on dev + val; champion chosen on validation only."""
    from quantedge.backtest.engine import run_models
    from quantedge.backtest.report import choose_champion, crisis_breakdown, selection_table
    from quantedge.portfolio.weights_path import point_in_time_weights

    window = window or cfg.risk.default_window
    part = Partition.from_config(cfg)
    returns = load_returns("dev+val", cfg)
    wpath = point_in_time_weights(wf_result.weights_history, returns.index, cfg.partition.warmup_weights)
    results = run_models(backtest_specs(cfg), returns, wpath, window,
                         alphas=(0.95, 0.975, 0.99), start=cfg.backtest.oos_start, end=part.val[1])
    for name, df in results.items():
        df.to_parquet(ARTIFACTS / f"backtest_{name.lower().replace(' ', '_').replace('-', '_')}_{window}.parquet")
    tables = {split: selection_table(results, 0.99, *part.bounds(split)) for split in ("dev", "val")}
    tables["val"].to_parquet(ARTIFACTS / f"backtest_selection_val_{window}.parquet")
    tables["dev"].to_parquet(ARTIFACTS / f"backtest_selection_dev_{window}.parquet")
    rule_choice, reason = choose_champion(tables["val"], cfg.backtest.champion_rule)
    champion = cfg.backtest.champion or rule_choice
    if champion != rule_choice:
        reason = f"locked in config (inputs_lock); the rule on this run picks {rule_choice}"
        print(f"[backtest] WARNING: the locked champion {champion} differs from the rule's choice {rule_choice}")
    crises = crisis_breakdown(results, cfg.stress["historical"])
    crises.to_parquet(ARTIFACTS / f"backtest_crises_{window}.parquet")
    if window == cfg.risk.default_window:   # other windows are sensitivity runs, never the official choice
        (ARTIFACTS / "champion.json").write_text(
            json.dumps({"portfolio": label, "window": window, "champion": champion, "rule_choice": rule_choice,
                        "reason": reason}, indent=2),
            encoding="utf-8")
    return {"results": results, "tables": tables, "champion": champion, "rule_choice": rule_choice, "reason": reason,
            "crises": crises}


def run_stress(cfg: Config, results: dict, macro: pd.DataFrame, focus: str) -> dict:
    """Step 12 on every candidate's latest target weights; data up to the end of validation."""
    from quantedge.stress.factor import estimate_factor_betas, weekly_factors, weekly_returns
    from quantedge.stress.historical import replay, stress_matrix
    from quantedge.stress.hypothetical import apply_shock, duration_check
    from quantedge.stress.reverse import most_likely_breach, parametric_var_es, stressed_sigma

    part = Partition.from_config(cfg)
    returns = load_returns("dev+val", cfg)
    windows = cfg.stress["historical"]
    weights = {name: r.weights_history.iloc[-1] for name, r in results.items()}
    matrix = stress_matrix(weights, returns, windows, cfg.nav_usd)

    etf_w = weekly_returns(returns)
    fac_w = weekly_factors(macro.loc[: part.val[1]])
    betas = {s: estimate_factor_betas(etf_w, fac_w, windows, sample=s) for s in ("full", "stress")}
    hyp = cfg.stress["hypothetical"]
    shocks = {s: {name: apply_shock(b, hyp["shock"], w, cfg.nav_usd, etf_w, fac_w)
                  for name, w in weights.items()} for s, b in betas.items()}
    matrix[hyp["name"]] = [shocks["full"][n].portfolio_return for n in matrix.index]
    matrix[hyp["name"] + " (stress betas)"] = [shocks["stress"][n].portfolio_return for n in matrix.index]

    calm, crisis = returns.cov(), stressed_sigma(returns, windows)
    w = weights[focus]
    rev = {k: most_likely_breach(s, w, cfg.stress["reverse"]["loss"], cfg.stress["reverse"]["horizon_days"])
           for k, s in (("calm", calm), ("stressed", crisis))}
    pvar = {k: parametric_var_es(s, w) for k, s in (("calm", calm), ("stressed", crisis))}
    focus_replays = {s: replay(returns, w, a, b, cfg.nav_usd, s) for s, (a, b) in windows.items()}

    matrix.to_parquet(ARTIFACTS / "stress_matrix.parquet")
    betas["full"].betas.to_parquet(ARTIFACTS / "stress_betas_full.parquet")
    betas["stress"].betas.to_parquet(ARTIFACTS / "stress_betas_stress.parquet")
    return {"matrix": matrix, "betas": betas, "shocks": shocks, "reverse": rev, "stressed_var": pvar,
            "replays": focus_replays, "agg_duration_check": duration_check(hyp["shock"]["d_yield10_bp"])}


FRONTIER_LEVELS = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def decision_measures(cfg: Config, weights: dict[str, pd.Series], hypothetical: dict[str, float],
                      macro: pd.DataFrame, as_of: pd.Timestamp, raw=None) -> pd.DataFrame:
    """D2 risk evidence and the D4 forward return for each portfolio, today's weights held fixed
    (notebooks 03 §4 and 06 A2): one row per portfolio, columns named as `rules.MEASURE_LIMIT`."""
    from quantedge.data.load import load_raw
    from quantedge.decision.objective import (
        crisis_loss,
        forward_asset_returns,
        forward_inputs,
        forward_portfolio_return,
        through_the_cycle,
    )

    raw = raw if raw is not None else load_raw()
    part = Partition.from_config(cfg)
    returns = load_returns("dev+val", cfg).loc[:as_of]
    fwd = cfg.ips["forward"]
    mkt = forward_inputs(returns, raw.close, raw.dividends, macro, as_of, fwd["beta_window"])
    net = forward_asset_returns(mkt["y10"], mkt["inflation"], mkt["beta"], mkt["div_yield"], fwd)
    rows = {}
    for name, w in weights.items():
        w = w.reindex(returns.columns, fill_value=0.0)
        ttc = through_the_cycle(w, returns.loc[: part.dev[1]])
        crises = crisis_loss(w, returns, cfg.stress["historical"])
        rows[name] = {"vol_ann": ttc["vol_ann"], "worst_hist_drawdown": float(crises.max()),
                      "worst_hist_name": str(crises.idxmax()), "hypothetical_loss": hypothetical.get(name, float("nan")),
                      "es99_1d": ttc["es99_1d"], "forward_return": forward_portfolio_return(w, net, mkt["cov_long"]),
                      "equity_share": float(w.reindex(cfg.ips["limits"]["equity_group"]).sum())}
    return pd.DataFrame(rows).T.astype({k: float for k in ("vol_ann", "worst_hist_drawdown", "hypothetical_loss",
                                                           "es99_1d", "forward_return", "equity_share")})


def run_decision_evidence(cfg: Config, results: dict, stress_out: dict, macro: pd.DataFrame) -> dict:
    """Write the D1/D2 decision evidence (`decision_measures.parquet`) and the D2 limit calibration
    along the 20-50% equity frontier (`limit_calibration.parquet`, `.json`)."""
    from sklearn.covariance import LedoitWolf

    from quantedge.data.load import load_raw
    from quantedge.decision.ips import constraints_for_optimizer
    from quantedge.decision.objective import calibrate_limits
    from quantedge.portfolio import optimize as opt

    part = Partition.from_config(cfg)
    as_of = part.val[1]
    raw = load_raw()
    hyp_name = cfg.stress["hypothetical"]["name"]
    hyp = {n: -float(stress_out["matrix"].loc[n, hyp_name]) for n in stress_out["matrix"].index}
    weights = {n: r.weights_history.iloc[-1] for n, r in results.items()}
    measures = decision_measures(cfg, weights, hyp, macro, as_of, raw)
    measures.to_parquet(ARTIFACTS / "decision_measures.parquet")

    returns = load_returns("dev+val", cfg).loc[:as_of]
    limits = IPSLimits.from_config(cfg.ips)
    tickers = list(cfg.universe)
    est = returns.iloc[-cfg.ips["forward"]["beta_window"]:]
    sigma = pd.DataFrame(LedoitWolf().fit(est.to_numpy()).covariance_ * 252, index=tickers, columns=tickers)
    cons = constraints_for_optimizer(limits, tickers)
    equity = list(cfg.ips["limits"]["equity_group"])
    frontier = {x: opt.min_var_at_equity(sigma, cons, equity, x).weights for x in FRONTIER_LEVELS}
    table, derived = calibrate_limits(frontier, returns.loc[: part.dev[1]], returns, cfg.stress["historical"],
                                      cfg.ips["crisis_budget"])
    betas = pd.read_parquet(ARTIFACTS / "stress_betas_full.parquet")
    shock = pd.Series(cfg.stress["hypothetical"]["shock"], dtype=float)
    r_star = betas[shock.index] @ shock
    fm = decision_measures(cfg, {f"{x:.0%}": w for x, w in frontier.items()},
                           {f"{x:.0%}": -float(w.reindex(r_star.index, fill_value=0.0) @ r_star)
                            for x, w in frontier.items()}, macro, as_of, raw)
    table["forward_return"] = fm["forward_return"].to_numpy()
    table["hypothetical_loss"] = fm["hypothetical_loss"].to_numpy()
    table.to_parquet(ARTIFACTS / "limit_calibration.parquet")
    derived |= {"as_of": str(as_of.date()), "config_vol_ann_max": limits.vol_ann_max,
                "config_es99_1d_max": limits.es99_1d_max}
    (ARTIFACTS / "limit_calibration.json").write_text(json.dumps(derived, indent=2), encoding="utf-8")
    return {"measures": measures, "calibration": table, "derived": derived}


def ml_inputs(cfg: Config, wf_result, macro: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Feature matrix and next-day loss target at point-in-time weights (dev + val only)."""
    from quantedge.ml.features import build_features, garch_sigma_path
    from quantedge.portfolio.weights_path import (
        pit_loss_target,
        pit_risk_returns,
        point_in_time_weights,
    )

    part = Partition.from_config(cfg)
    returns = load_returns("dev+val", cfg)
    wpath = point_in_time_weights(wf_result.weights_history, returns.index, cfg.partition.warmup_weights)
    sigma = garch_sigma_path(pit_risk_returns(returns, wpath), refit_every=cfg.ml["retrain_every"])
    X = build_features(returns, macro.loc[: part.val[1]], wpath, sigma)
    return X, pit_loss_target(returns, wpath)


def run_ml_arena(cfg: Config, wf_result, backtests: dict, champion: str, macro: pd.DataFrame) -> dict:
    """Step 22 M3–M4: the linear QR challenger vs the champion, scored on validation.

    LightGBM and the LSTM were evaluated and rejected (both failed coverage in every configuration;
    doc/decisions/ml_selection.md) and are archived at the git tag archive/mirofish-ml."""
    from quantedge.ml.quantile_models import LinearQR, ratio_es, walk_forward_ml

    part = Partition.from_config(cfg)
    X, y = ml_inputs(cfg, wf_result, macro)
    levels = (0.95, 0.975, 0.99)
    es_levels = {0.975: tuple(cfg.ml["es_integral_levels"]), 0.99: (0.99, 0.9925, 0.995, 0.9975)}
    kw = dict(retrain_every=cfg.ml["retrain_every"], start=cfg.backtest.oos_start, end=part.val[1],
              es_levels=es_levels, min_train=750)
    out = {"Linear QR": walk_forward_ml(lambda lv: LinearQR(lv), X, y, levels, **kw)}
    # ES variant (a): ratio hybrid with the conditional-EVT ES/VaR ratio of the same day.
    cevt = backtests["Conditional EVT"]
    for name in list(out):
        df = out[name].join(cevt[["var_0.99", "es_0.99"]].add_suffix("_cevt"), how="inner")
        es_ratio, hits = ratio_es(df["var_0.99"].to_numpy(), df["var_0.99_cevt"].to_numpy(),
                                  df["es_0.99_cevt"].to_numpy(), cfg.ml["es_ratio"]["eps"],
                                  tuple(cfg.ml["es_ratio"]["clip"]))
        ratio_df = df.drop(columns=["var_0.99_cevt", "es_0.99_cevt"]).assign(**{"es_0.99": es_ratio})
        ratio_df.attrs["ratio_guard_hits"] = hits
        out[f"{name} (ratio ES)"] = ratio_df
    for name, df in out.items():
        df.to_parquet(ARTIFACTS / f"ml_{name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.parquet")
    table = score_arena(cfg, out, backtests, champion)
    return {"forecasts": out, "arena": table, "features": X, "target": y}


def score_arena(cfg: Config, forecasts: dict, backtests: dict, champion: str) -> pd.DataFrame:
    """Score challengers against the champion on validation: pinball (primary), FZ0 relative to the
    champion, DM with Holm correction, and 90% MCS membership (Step 22 §3.8)."""
    from quantedge.backtest import scoring as sc
    from quantedge.backtest.report import selection_table

    part = Partition.from_config(cfg)
    val = slice(*part.bounds("val"))
    arena = {champion: backtests[champion].loc[val], **{k: v.loc[val] for k, v in forecasts.items()}}
    common = sorted(set.intersection(*(set(d.index) for d in arena.values())))
    arena = {k: v.loc[common] for k, v in arena.items()}
    table = selection_table(arena, 0.99)
    pin = pd.DataFrame({k: sc.pinball(v.loss, v["var_0.99"], 0.99) for k, v in arena.items()}, index=common)
    fz = pd.DataFrame({k: sc.fz0(v.loss, v["var_0.99"], v["es_0.99"], 0.99) for k, v in arena.items()}, index=common)
    dm = {k: sc.dm_test(pin[k], pin[champion]) for k in arena if k != champion}
    table["dm_vs_champion"] = pd.Series({k: r.stat for k, r in dm.items()})
    table["dm_p_holm"] = pd.Series(sc.holm({k: r.pvalue for k, r in dm.items()}))
    mcs = sc.model_confidence_set(pin, size=0.10, reps=1000, seed=cfg.seed)
    table = table.join(mcs)
    # FZ0 is often negative (log term), so compare relative to |champion|: +0.02 means 2% worse.
    table["fz0_vs_champion"] = (fz.mean() - fz[champion].mean()) / abs(fz[champion].mean())
    table.to_parquet(ARTIFACTS / "ml_arena_val.parquet")
    return table


def run_risk_snapshot(cfg: Config, wf_result, label: str, evt_threshold_q: float) -> dict:
    """Steps 08–10 and 13 at the latest target weights, fitted on the last W days up to validation end."""
    from quantedge.risk.contributions import euler_parametric, euler_simulation_es
    from quantedge.risk.diagnostics import disagreement_table, es_var_ratio_table, tail_statistics
    from quantedge.risk.evt import ConditionalEVTModel, EVTModel, return_level_p
    from quantedge.risk.garch import GarchFHSModel
    from quantedge.risk.montecarlo import MonteCarloModel
    from quantedge.risk.var import CornishFisherModel, HistoricalModel, NormalModel, StudentTModel

    returns = load_returns("dev+val", cfg)
    w = wf_result.weights_history.iloc[-1]
    window = returns.iloc[-cfg.risk.default_window:]
    port = pd.Series(window.to_numpy() @ w.reindex(window.columns).to_numpy(), index=window.index)
    models = {
        "Historical": HistoricalModel(), "Normal": NormalModel(), "Student-t": StudentTModel(),
        "Cornish-Fisher": CornishFisherModel(), "EVT": EVTModel(evt_threshold_q),
        "Monte Carlo": MonteCarloModel(n_sims=cfg.risk.mc_sims, rng=cfg.rng(stream=12)),
        "GARCH-FHS": GarchFHSModel(), "Conditional EVT": ConditionalEVTModel(),
        "GJR conditional EVT": ConditionalEVTModel(o=1),
    }
    for m in models.values():
        m.fit(port)
    alphas = (*cfg.risk.confidence_levels, 0.975)
    rows = [{"model": n, "alpha": a, "var": m.var(a), "es": m.es(a),
             "var_usd": m.var(a) * cfg.nav_usd, "es_usd": m.es(a) * cfg.nav_usd}
            for n, m in models.items() for a in sorted(alphas)]
    snapshot = pd.DataFrame(rows)
    p10 = return_level_p(10)
    extra = {"return_level_10y_evt": models["EVT"].var(p10), "return_level_10y_cevt": models["Conditional EVT"].var(p10),
             "cornish_fisher_monotone": bool(models["Cornish-Fisher"].monotone),
             "student_t_nu": models["Student-t"].nu, "garch_persistence": models["GARCH-FHS"].persistence}
    from quantedge.risk.horizon import horizon_table

    h10 = horizon_table(models["GARCH-FHS"], port, 10, cfg.rng(stream=13))
    h10.to_parquet(ARTIFACTS / "risk_horizon_10d.parquet")
    fhs99 = h10[(h10.method == "GARCH-FHS paths") & (h10.alpha == 0.99)].iloc[0]
    extra |= {"var99_10d": float(fhs99["var"]), "es99_10d": float(fhs99["es"]),
              "es99_10d_limit": float(cfg.ips["limits"]["es99_10d_max"])}
    contrib = euler_simulation_es(w, window, 0.99).assign(method="historical ES 99%")
    contrib_p = euler_parametric(w, window.cov(), 0.99, "es").assign(method="parametric ES 99%")
    snapshot.to_parquet(ARTIFACTS / "risk_snapshot.parquet")
    pd.concat([contrib, contrib_p]).to_parquet(ARTIFACTS / "risk_contributions.parquet")
    disagreement_table(models).to_parquet(ARTIFACTS / "risk_disagreement.parquet")
    es_var_ratio_table(models).to_parquet(ARTIFACTS / "risk_es_var_ratios.parquet")
    facts = tail_statistics(-port)
    (ARTIFACTS / "risk_extras.json").write_text(json.dumps({**extra, **facts, "portfolio": label,
                                                            "window_start": str(window.index[0].date()),
                                                            "window_end": str(window.index[-1].date())},
                                                           indent=2), encoding="utf-8")
    return {"snapshot": snapshot, "extras": extra, "contributions": contrib}


GOVERNANCE = [
    "Rebalance quarterly to the target weights (5 bps per side assumed).",
    "Re-convene the committee if the 250-day Basel traffic light turns yellow or red.",
    "Re-convene if the portfolio drawdown exceeds 10% from its peak.",
    "Review the IPS limits and the spending rate annually, and after any limit amendment.",
    "Any amended limit takes effect only after explicit investment-committee approval.",
]


def write_memo(cfg: Config) -> Path | None:
    """Step 13 committee memo draft: numbers filled in, judgement left to the team."""
    from quantedge.decision.evidence import build
    from quantedge.decision.memo import render_memo
    from quantedge.paths import ROOT

    b = build(cfg)
    if b is None:
        return None
    extras = json.loads((ARTIFACTS / "risk_extras.json").read_text(encoding="utf-8"))
    numbers = {"portfolio": b.focus, "weights": b.weights, "expected_return": b.evidence.expected_return,
               "required_return": b.evidence.required_return, "var99": b.var99, "es99": b.evidence.es99_conditional,
               "return_level_10y": b.evidence.return_level_10y, "worst_hist_loss": b.worst_hist_loss,
               "worst_hist_name": b.worst_hist_name, "worst_drawdown_held": float(pd.read_parquet(
                   ARTIFACTS / "portfolio_scorecard_val.parquet").loc[b.focus, "worst_crisis_drawdown"]),
               "hypothetical_loss": b.evidence.hypothetical_loss,
               "champion": b.champion, "champion_reason": b.champion_reason, "governance": GOVERNANCE,
               **{k: extras.get(k, float("nan")) for k in ("es99_10d", "es99_10d_limit")}}
    out = ROOT / "reports" / "committee_memo_draft.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render_memo(b.verdict, numbers, cfg.nav_usd), encoding="utf-8")
    return out


def run_innovation(cfg: Config, wf_result, macro: pd.DataFrame) -> dict:
    """Step 14 on the focus portfolio's point-in-time book, data up to the end of validation."""
    from quantedge.macro.analysis import (
        cpi_yoy,
        inflation_beta,
        lkr_context,
        rates_impact,
        rolling_stock_bond_corr,
    )
    from quantedge.ml.features import garch_sigma_path
    from quantedge.paths import RAW
    from quantedge.portfolio.overlay import compare, vol_target_backtest
    from quantedge.portfolio.returns import CASH, add_cash_asset
    from quantedge.portfolio.walkforward import simulate
    from quantedge.portfolio.weights_path import pit_risk_returns, point_in_time_weights
    from quantedge.risk.copula import CopulaMCModel, tail_dependence
    from quantedge.risk.regime import filtered_high_prob, fit_markov, regime_risk, vix_agreement

    part = Partition.from_config(cfg)
    returns = load_returns("dev+val", cfg)
    rf = pd.read_parquet(ARTIFACTS / "returns_rf.parquet")["rf"].reindex(returns.index)
    wh = wf_result.weights_history
    wpath = point_in_time_weights(wh, returns.index, cfg.partition.warmup_weights)
    port = pit_risk_returns(returns, wpath)
    out: dict = {}

    # A. regimes: parameters on development data, filter run forward with them held fixed
    fit = fit_markov(port.loc[: part.dev[1]], seed=cfg.seed)
    p_high = filtered_high_prob(port, fit)
    rr = regime_risk(port, p_high)
    p_high.to_frame().to_parquet(ARTIFACTS / "regime_p_high.parquet")
    rr.to_parquet(ARTIFACTS / "regime_risk.parquet")
    vix_agreement(p_high, macro["VIXCLS"]).to_parquet(ARTIFACTS / "regime_vix.parquet")
    es99 = rr[rr.alpha == 0.99].set_index("regime")["es"]
    out["regime"] = {"sigma_calm": fit.sigma[0], "sigma_high": fit.sigma[1],
                     "duration_calm_days": fit.expected_duration[0], "duration_high_days": fit.expected_duration[1],
                     "p_high_latest": float(p_high.iloc[-1]), "es99_high_over_calm": float(es99["high-vol"] / es99["calm"]),
                     "fit_window_end": str(part.dev[1].date())}

    # B. volatility-target overlay vs static, into AGG and into T-bills
    sigma = garch_sigma_path(port, refit_every=21)
    target = float(cfg.ips["limits"]["vol_ann_max"])
    static, static_to = simulate(returns, wh, cfg.portfolio.cost_bps_per_side)
    agg = vol_target_backtest(returns, wh, sigma, target, safe="AGG", cost_bps=cfg.portfolio.cost_bps_per_side)
    cash_returns = add_cash_asset(returns, rf)
    wh_cash = wh.assign(**{CASH: 0.0})
    cash = vol_target_backtest(cash_returns, wh_cash, sigma, target, safe=CASH, cost_bps=cfg.portfolio.cost_bps_per_side)
    table = compare({"Static": static, "Overlay to AGG": agg.perf, "Overlay to T-bills": cash.perf},
                    cfg.stress["historical"], {"Static": static_to, "Overlay to AGG": agg.turnover,
                                               "Overlay to T-bills": cash.turnover})
    table.to_parquet(ARTIFACTS / "overlay_compare.parquet")
    pd.DataFrame({"Static": static, "Overlay to AGG": agg.perf, "Overlay to T-bills": cash.perf}).to_parquet(
        ARTIFACTS / "overlay_performance.parquet")
    out["overlay"] = table

    # C. t-copula vs Gaussian copula at the latest weights, last W days
    w = wh.iloc[-1]
    window = returns.iloc[-cfg.risk.default_window:]
    t_cop = CopulaMCModel(n_sims=cfg.risk.mc_sims, rng=cfg.rng(stream=14)).fit(window, w)
    g_cop = CopulaMCModel(n_sims=cfg.risk.mc_sims, rng=cfg.rng(stream=14), gaussian=True).fit(window, w)
    eq = ["SPY", "EFA", "EEM"]
    rho_spy_efa = float(t_cop.R[list(window.columns).index("SPY"), list(window.columns).index("EFA")])
    cop = {"nu": t_cop.nu, "rho_spy_efa": rho_spy_efa, "lambda_L_spy_efa": tail_dependence(rho_spy_efa, t_cop.nu),
           "var99_t": t_cop.var(0.99), "es99_t": t_cop.es(0.99), "var99_gauss": g_cop.var(0.99), "es99_gauss": g_cop.es(0.99),
           "joint_crash_t": t_cop.joint_crash_probability(eq, history=window),
           "joint_crash_gauss": g_cop.joint_crash_probability(eq, history=window),
           "joint_crash_history": float((window[eq] < window[eq].quantile(0.05)).all(axis=1).mean())}
    cop["es_uplift_t_vs_gauss"] = cop["es99_t"] / cop["es99_gauss"] - 1
    out["copula"] = cop

    # D. macro and FX
    corr = rolling_stock_bond_corr(returns)
    pd.concat([corr, cpi_yoy(macro["CPIAUCSL"]).reindex(corr.index, method="ffill")], axis=1).to_parquet(
        ARTIFACTS / "macro_stock_bond.parquet")
    fx_file = RAW / "fx_LKR_X.parquet"
    usd_lkr = pd.read_parquet(fx_file).iloc[:, 0].loc[: part.val[1]] if fx_file.exists() else None
    betas = pd.read_parquet(ARTIFACTS / "stress_betas_full.parquet")
    out["macro"] = {"inflation": inflation_beta(port, macro["CPIAUCSL"].loc[: part.val[1]]),
                    "rates_plus_100bp": rates_impact(w, betas),
                    "stock_bond_corr_2021_end": float(corr.loc[:"2021-12-31"].iloc[-1]),
                    "stock_bond_corr_2022_end": float(corr.iloc[-1]),
                    "lkr": lkr_context(usd_lkr, port) if usd_lkr is not None else None}
    summary = {k: v for k, v in out.items() if k != "overlay"}
    (ARTIFACTS / "innovation_summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    return out


SENSITIVITY_CASES = {
    "base": {},
    "ips_v1_limits": {"variant": "v1_limits"},
    "mrp_4pct": {"mrp": 0.04},
    "mrp_6pct": {"mrp": 0.06},
    "cash_allowed": {"allow_cash": True},
    "original_agg40": {"variant": "original_agg40"},
}


def run_verdict_sensitivity(cfg: Config, macro: pd.DataFrame) -> pd.DataFrame:
    """Step 13 §3.4: does the outcome change under other assumptions?

    Every case reruns the walk-forward selection and evaluates the focus portfolio with the same
    D1/D2 evidence as the verdict (`decision_measures`): risk limits by minimum relaxation across
    IPS-compliant candidates, the return objective against the forward expected return."""
    from quantedge.data.load import load_raw
    from quantedge.decision.evidence import _objective_loss
    from quantedge.decision.rules import MEASURE_LIMIT, minimum_relaxation

    betas = pd.read_parquet(ARTIFACTS / "stress_betas_full.parquet")
    shock = pd.Series(cfg.stress["hypothetical"]["shock"], dtype=float)
    r_star = betas[shock.index] @ shock
    as_of = Partition.from_config(cfg).val[1]
    raw = load_raw()
    rows = []
    for name, kw in SENSITIVITY_CASES.items():
        sel = run_portfolio_selection(cfg, macro, tag=f"sens_{name}", **kw)
        card = sel["scorecard"]
        limits = IPSLimits.from_config(cfg.ips, kw.get("variant"))
        weights = {c: sel["results"][c].weights_history.iloc[-1] for c in card.index}
        hyp = {c: -float(w.reindex(r_star.index, fill_value=0.0) @ r_star) for c, w in weights.items()}
        meas = decision_measures(cfg, {c: w.drop("CASH", errors="ignore") for c, w in weights.items()},
                                 hyp, macro, as_of, raw)
        cands = meas.loc[card.index[card["weights_within_ips"]], list(MEASURE_LIMIT)]
        top = cfg.portfolio.focus if cfg.portfolio.focus in card.index else str(card.index[0])
        relax = minimum_relaxation(cands, limits) if len(cands) else None
        gap = sel["required_return"]["required_return"] - float(meas.loc[top, "forward_return"])
        obj = _objective_loss(ARTIFACTS, sel["required_return"]["required_return"])   # base-case frontier (spec §5)
        if relax is None or relax.max_relative > cfg.decision["max_limit_relaxation"]:
            outcome = "REJECT"
        elif relax.max_relative == 0 and gap <= cfg.decision["return_gap_tolerance"]:
            outcome = "ACCEPT"
        elif gap > cfg.decision["return_gap_tolerance"] and obj is not None and not (
                obj <= limits.stress_drawdown_max + cfg.decision["max_budget_loosening"] + 1e-12):
            outcome = "REJECT"
        else:
            outcome = "ADJUST RISK LIMIT"
        rows.append({"case": name, "top_candidate": top, "forward_return": float(meas.loc[top, "forward_return"]),
                     "volatility": float(meas.loc[top, "vol_ann"]), "es99_ttc": float(meas.loc[top, "es99_1d"]),
                     "worst_crisis_loss": float(meas.loc[top, "worst_hist_drawdown"]),
                     "least_amended": relax.candidate if relax else None,
                     "max_loosening": relax.max_relative if relax else float("nan"),
                     "return_gap": gap, "outcome": outcome})
    out = pd.DataFrame(rows).set_index("case")
    out.to_parquet(ARTIFACTS / "verdict_sensitivity.parquet")
    return out


def write_artifacts_manifest(cfg: Config) -> Path:
    """SHA-256 of every artifact plus the config hash and git commit (reproducibility protocol)."""
    import subprocess

    from quantedge.data.manifest import sha256_file
    from quantedge.paths import ROOT

    try:
        sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        sha = "unknown"
    files = {f.name: sha256_file(f) for f in sorted(ARTIFACTS.glob("*")) if f.is_file()
             and f.name != "artifacts_manifest.json"}
    out = ARTIFACTS / "artifacts_manifest.json"
    out.write_text(json.dumps({"config_sha256": cfg.sha256, "git_commit": sha, "files": files}, indent=2),
                   encoding="utf-8")
    return out


def _cached(name: str) -> bool:
    return (ARTIFACTS / name).exists()


def run(cfg: Config, force_backtests: bool = False, with_ml: bool = False) -> dict:
    out = {}
    t0 = time.perf_counter()
    clean = build_clean_dataset(cfg)
    out["clean"] = clean
    print(f"[clean]    {len(clean.prices)} dates x {clean.prices.shape[1]} ETFs, "
          f"{len(clean.flags)} flags, stats window ends {clean.analysis_end.date()}")
    out["returns"] = build_returns(clean.prices, clean.macro)
    print(f"[returns]  {len(out['returns']['simple'])} daily returns")
    sel = run_portfolio_selection(cfg, clean.macro)
    out["selection"] = sel
    for variant in cfg.ips.get("variants", {}):
        alt = run_portfolio_selection(cfg, clean.macro, variant)
        print(f"[select]   sensitivity '{variant}': top candidate {alt['scorecard'].index[0]}, "
              f"IPS passes: {int(alt['scorecard']['ips_pass'].sum())}")
    focus = cfg.portfolio.focus or str(sel["scorecard"].index[0])
    wf = sel["results"][focus]
    print(f"[select]   required return {sel['required_return']['required_return']:.2%}; focus: {focus} (provisional)")

    evt_out = run_evt(cfg, wf, f"{focus} (provisional)")
    rule_a = evt_out["choices"][0]
    print(f"[evt]      Rule A threshold q = {rule_a.quantile}, xi = {rule_a.fit.xi:.3f}")
    out["risk"] = run_risk_snapshot(cfg, wf, focus, rule_a.quantile)
    print("[risk]     snapshot, contributions, disagreement written")
    out["stress"] = run_stress(cfg, sel["results"], clean.macro, focus)
    print("[stress]   matrix, betas written")
    out["decision"] = run_decision_evidence(cfg, sel["results"], out["stress"], clean.macro)
    d = out["decision"]["derived"]
    print(f"[decision] D2 calibration: {d['crisis_budget']:.0%} budget -> {d['equity_share']:.1%} equity, "
          f"vol <= {d['vol_ann_max']:.2%}, ES <= {d['es99_1d_max']:.2%} (config {d['config_vol_ann_max']:.2%} / "
          f"{d['config_es99_1d_max']:.2%})")
    out["innovation"] = run_innovation(cfg, wf, clean.macro)
    print(f"[innov]    regimes, overlay, copula, macro written (ES t vs Gaussian copula: "
          f"{out['innovation']['copula']['es_uplift_t_vs_gauss']:+.1%})")
    if force_backtests or not _cached("champion.json"):
        out["backtests"] = run_backtests(cfg, wf, f"{focus} (provisional)")
        print(f"[backtest] champion: {out['backtests']['champion']}")
    else:
        print("[backtest] cached artifacts reused (pass --force-backtests to recompute)")
    if with_ml:
        champion = json.loads((ARTIFACTS / "champion.json").read_text(encoding="utf-8"))["champion"]
        backtests = (out.get("backtests") or {}).get("results") or {
            name: pd.read_parquet(ARTIFACTS / f"backtest_{name.lower().replace(' ', '_').replace('-', '_')}_"
                                              f"{cfg.risk.default_window}.parquet")
            for name in {champion, "Conditional EVT"}}
        out["ml"] = run_ml_arena(cfg, wf, backtests, champion, clean.macro)
        print("[ml]       linear QR arena written (ml_arena_val.parquet)")

    m = out["decision"]["measures"].loc[focus]
    passes = all(c.passed for c in IPSLimits.from_config(cfg.ips).check(
        {"vol_ann": m.vol_ann, "stress_drawdown": max(m.worst_hist_drawdown, m.hypothetical_loss),
         "es99_1d": m.es99_1d, "weights": wf.weights_history.iloc[-1]}))
    status = {"focus_portfolio": focus, "provisional": not Partition.from_config(cfg).frozen(),
              "provisional_reason": ("methodology not yet frozen; the champion and the ML adoption are "
                                     "confirmed only after the final test" if passes else
                                     "the focus portfolio does not meet every IPS limit"),
              "weights": {k: float(v) for k, v in wf.weights_history.iloc[-1].items()},
              "weights_as_of": str(wf.weights_history.index[-1].date()),
              "data_end": str(clean.prices.index.max().date()),
              "analysis_end": str(clean.analysis_end.date()), "config_sha256": cfg.sha256,
              "frozen": Partition.from_config(cfg).frozen()}
    (ARTIFACTS / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    memo = write_memo(cfg)
    print(f"[memo]     draft written to {memo}")
    from quantedge.decision.evidence import build
    from quantedge.reports.tearsheet import render

    bundle = build(cfg)
    if bundle is not None:
        sheet = memo.parent / "tearsheet.html"
        sheet.write_text(render(cfg, bundle), encoding="utf-8")
        print(f"[report]   tear sheet written to {sheet}")
        from quantedge.reports import report

        (memo.parent / "report.html").write_text(report.render(cfg), encoding="utf-8")
        print(f"[report]   report draft written to {memo.parent / 'report.html'} (narrative in reports/narrative/)")
    if Partition.from_config(cfg).frozen():
        from quantedge.decision import decision_date

        d = decision_date.run(cfg)["numbers"]
        print(f"[decide]   {d['decision_date']}: {d['verdict']} at {d['advised_equity']:.0%} equity "
              f"(expected {d['expected_return']:.2%} vs required {d['objective']['required_return']:.2%})")
    sens = run_verdict_sensitivity(cfg, clean.macro)
    print(f"[sensitiv] outcomes: {sens['outcome'].to_dict()}")
    print(f"[manifest] {write_artifacts_manifest(cfg)}")
    print(f"done in {time.perf_counter() - t0:.1f}s")
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="QuantEdge precompute pipeline")
    ap.add_argument("--force-backtests", action="store_true")
    ap.add_argument("--with-ml", action="store_true", help="rerun the linear QR challenger arena (slow)")
    args = ap.parse_args()
    run(load_config(), force_backtests=args.force_backtests, with_ml=args.with_ml)
