"""Step 20 MiroFish Value Score (MVS, 100 points), computed identically for variants A, B and N.

All points and sub-weights come from the frozen `scorecard` block in data/behavioral/scenarios.yaml.
Operational choices the pre-registration leaves open are stated here and in the report:
- novelty credit is 1 inside the Mahalanobis band [2, 4], rising linearly from 0 below it and
  falling linearly to 0 at twice the upper bound above it;
- variant N's shock is the average of the three historical crisis return vectors, scaled to the
  scenario horizon by sqrt(h / crisis length);
- the EVT h-day reference loss is the 1-day 1-in-10-year loss x sqrt(h) (labelled approximation);
- D4 actionability is scored automatically as "the scenario changes the candidates' loss ranking
  versus the historical-crisis ranking"; changes to a Step 13 check or a sizing recommendation are
  assessed by the team and reported alongside;
- human inputs (reviewer ratings, Cohen's kappa, cache rebuild) are read from files the team fills
  in; until they exist the dimension is reported as partial (missing parts score 0 and are flagged).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

ECON_DURATION = 6.0  # AGG duration used by the rates rule (-D x dy)


def chi2_credit(d2: float, dof: int, full_pct: float, zero_pct: float) -> float:
    """1 when the chi2 percentile of d2 is at most `full_pct`, 0 at `zero_pct`, linear between."""
    pct = 100 * stats.chi2.cdf(d2, dof)
    if pct <= full_pct:
        return 1.0
    if pct >= zero_pct:
        return 0.0
    return float((zero_pct - pct) / (zero_pct - full_pct))


def novelty_credit(d: float, band: tuple[float, float]) -> float:
    lo, hi = band
    if lo <= d <= hi:
        return 1.0
    if d < lo:
        return float(max(0.0, d / lo))
    return float(max(0.0, 1 - (d - hi) / hi))


def mahalanobis(x: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(x @ np.linalg.solve(cov, x)))


def naive_shock(crisis_vectors: pd.DataFrame, crisis_days: pd.Series, h: int) -> pd.Series:
    """Variant N: average historical crisis return vector, scaled to horizon h by sqrt(h / length)."""
    scaled = crisis_vectors.mul(np.sqrt(h / crisis_days), axis=0)
    return scaled.mean()


def economic_rules(shock: pd.Series, coding: dict, factor_shocks: pd.Series, consistency: float) -> float:
    """Share of applicable economic-consistency rules the scenario passes (D3 b)."""
    passed, n = 0, 0
    dy = float(factor_shocks.get("d_yield10_bp", 0.0))
    if dy > 0:
        n += 1
        expected = -ECON_DURATION * dy / 10_000
        passed += abs(shock["AGG"] - expected) <= 0.5 * abs(expected)
    if coding["behaviour"]["panic_selling"] >= 2:
        n += 1
        passed += shock["EEM"] <= shock["SPY"]
    if float(factor_shocks.get("dln_oil", 0.0)) > 0:
        n += 1
        passed += shock["XLE"] >= shock["SPY"]
    havens = [a for a in coding["behaviour"]["flight_to_safety"] if a in shock.index]
    if havens:
        n += 1
        passed += all(shock[a] >= 0 for a in havens)
    n += 1
    passed += consistency >= 0.5
    return passed / n


@dataclass
class ScenarioResult:
    """Everything the MVS needs about one variant on one scenario (one replicate)."""

    scenario: str
    kind: str                       # forward | replay
    horizon: int
    etf_shock: pd.Series
    factor_shocks: pd.Series
    coding: dict
    consistency: float
    candidate_losses: pd.Series     # loss by candidate (positive = loss)
    focus_loss: float
    realised: pd.Series | None = None    # realised ETF returns over the replay window
    realised_focus_loss: float | None = None


@dataclass
class Context:
    stressed_cov_daily: pd.DataFrame
    crisis_vectors: pd.DataFrame          # historical crisis cumulative returns (rows: crises)
    crisis_ranking: list[str]             # candidate ranking (best first) by worst historical loss
    worst_hist_loss: float
    evt_1d_10y: float
    weights_cfg: dict
    human: dict = field(default_factory=dict)   # reviewer_rating (0-1), kappa, cache_rebuild (0/1)


def dimension_scores(results: list[ScenarioResult], ctx: Context, compliance: dict, replicate_cv: float | None) -> dict:
    w = ctx.weights_cfg
    cols = list(ctx.stressed_cov_daily.columns)
    out, flags = {}, []

    reps = [r for r in results if r.kind == "replay" and r.realised is not None]
    vals = []
    for r in reps:
        pred, real = r.etf_shock.reindex(cols), r.realised.reindex(cols)
        h = float((np.sign(pred) == np.sign(real)).mean())
        rho = float(pred.rank().corr(real.rank()))
        e = abs(r.focus_loss - r.realised_focus_loss) / max(abs(r.realised_focus_loss), 1e-6)
        d = w["D1_historical_fidelity"]["weights"]
        vals.append(d["sign_hit"] * h + d["spearman"] * max(rho, 0) + d["loss_error"] * max(0.0, 1 - e))
    out["D1"] = w["D1_historical_fidelity"]["points"] * (float(np.mean(vals)) if vals else 0.0)
    if not vals:
        flags.append("D1: no replay results")

    fwd = [r for r in results if r.kind == "forward"] or results
    d2v, d3v, d4v = [], [], []
    for r in fwd:
        cov_h = ctx.stressed_cov_daily.to_numpy() * r.horizon
        x = r.etf_shock.reindex(cols).fillna(0).to_numpy()
        ref = max(ctx.worst_hist_loss, ctx.evt_1d_10y * np.sqrt(r.horizon))
        sev = min(1.0, max(r.focus_loss, 0.0) / ref)
        dist = min(mahalanobis(x - v.reindex(cols).to_numpy(), cov_h) for _, v in ctx.crisis_vectors.iterrows())
        nov = novelty_credit(dist, tuple(w["D2_tail_informativeness"]["novelty_band_mahalanobis"]))
        d = w["D2_tail_informativeness"]["weights"]
        d2v.append(d["severity"] * sev + d["novelty"] * nov)
        c = w["D3_plausibility"]
        plaus = chi2_credit(mahalanobis(x, cov_h) ** 2, len(cols), c["chi2_full_credit_pct"], c["chi2_zero_credit_pct"])
        econ = economic_rules(r.etf_shock, r.coding, r.factor_shocks, r.consistency)
        d3v.append(c["weights"]["mahalanobis_plausibility"] * plaus + c["weights"]["economic_rules"] * econ)
        losses = r.candidate_losses
        disc = min(1.0, (losses.max() - losses.min()) / max(abs(losses.mean()), 1e-9))
        ranking = list(losses.sort_values().index)
        action = float(ranking[: len(ctx.crisis_ranking)] != ctx.crisis_ranking[: len(ranking)])
        d4 = w["D4_decision_usefulness"]["weights"]
        human = ctx.human.get("reviewer_rating")
        d4v.append(d4["discrimination"] * disc + d4["actionability"] * action + d4["human_rating"] * (human or 0.0))
    out["D2"] = w["D2_tail_informativeness"]["points"] * float(np.mean(d2v))
    out["D3"] = w["D3_plausibility"]["points"] * float(np.mean(d3v))
    out["D4"] = w["D4_decision_usefulness"]["points"] * float(np.mean(d4v))
    if ctx.human.get("reviewer_rating") is None:
        flags.append("D4: reviewer ratings missing (scored 0)")

    d5 = w["D5_reproducibility"]
    cv_part = 1.0 if replicate_cv is None else max(0.0, 1 - replicate_cv / d5["cv_zero_credit"])
    k = ctx.human.get("kappa")
    lo, hi = d5["kappa_map"]
    kappa_part = 0.0 if k is None else float(np.clip((k - lo) / (hi - lo), 0, 1))
    rebuild = ctx.human.get("cache_rebuild")
    out["D5"] = d5["points"] * (d5["weights"]["replicate_cv"] * cv_part + d5["weights"]["kappa"] * kappa_part
                                + d5["weights"]["cache_rebuild"] * float(rebuild or 0))
    if k is None:
        flags.append("D5: Cohen's kappa missing (scored 0)")
    if rebuild is None:
        flags.append("D5: cache rebuild not yet checked (scored 0)")

    items = w["D6_cost_compliance"]["items"]
    out["D6"] = float(sum(pts for name, pts in items.items() if compliance.get(name, False)))
    out["total"] = float(sum(out[d] for d in ("D1", "D2", "D3", "D4", "D5", "D6")))
    out["flags"] = flags
    return out


def bootstrap_mean_ci(values: list[float], rng: np.random.Generator, n: int = 10_000, level: float = 0.95) -> tuple[float, float, float]:
    v = np.asarray(values, float)
    boots = rng.choice(v, size=(n, len(v)), replace=True).mean(axis=1)
    a = (1 - level) / 2
    return float(v.mean()), float(np.quantile(boots, a)), float(np.quantile(boots, 1 - a))


def adoption(mvs_a: float, mvs_b: list[float], brs_a: float | None, brs_b: float | None, mvs_n: float,
             compliance_b: dict, rng: np.random.Generator) -> dict:
    """Pre-registered adoption rule (scenarios.yaml -> scorecard.adoption_rule)."""
    if not compliance_b.get("compliant_toolkit") or not compliance_b.get("approved_data_only"):
        return {"outcome": "REJECTED", "reason": "B fails a compliance item"}
    diff = [b - mvs_a for b in mvs_b]
    mean, lo, hi = bootstrap_mean_ci(diff, rng)
    brs_ok = brs_a is not None and brs_b is not None and brs_b >= brs_a
    if mean >= 5 and lo > 0 and brs_ok:
        outcome = "ADOPTED"
    elif float(np.mean(mvs_b)) < mvs_a:
        outcome = "APPENDIX"
    else:
        outcome = "HYBRID"
    return {"outcome": outcome, "diff_mean": mean, "diff_ci": (lo, hi), "brs_available": brs_a is not None and brs_b is not None,
            "beats_naive": {"A": mvs_a > mvs_n, "B": float(np.mean(mvs_b)) > mvs_n}}
