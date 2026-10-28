"""Rule-based verdict: ACCEPT / ADJUST RISK LIMIT / REJECT (Step 13 §3.3).

The engine computes evidence and a rule outcome; the team owns the final recommendation and its
wording (brief §8.7). Every threshold comes from `config.yaml -> decision:` and is displayed.

Decision record doc/decisions/decision_engine.md: when risk limits fail, a minimum-relaxation
calculation finds the smallest loosening of the named limits under which some candidate portfolio
passes (minimax over candidates of the largest relative loosening). ADJUST RISK LIMIT if that
loosening is at most `max_limit_relaxation`, and any amendment requires explicit client
(investment-committee) approval before implementation. REJECT if no risk model is valid or the
minimum loosening exceeds the bound.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from quantedge.decision.ips import IPSLimits

# measure -> the IPS limit it is checked against (C2 and C3 share the stress drawdown limit)
MEASURE_LIMIT = {"vol_ann": "vol_ann_max", "worst_hist_drawdown": "stress_drawdown_max",
                 "hypothetical_loss": "stress_drawdown_max", "es99_1d": "es99_1d_max"}


@dataclass(frozen=True)
class Relaxation:
    candidate: str
    required: dict[str, float]      # limit -> minimum value under which the candidate passes
    relative: dict[str, float]      # limit -> relative loosening (0.25 = 25% looser)
    max_relative: float
    table: pd.DataFrame


def minimum_relaxation(candidates: pd.DataFrame, lim: IPSLimits) -> Relaxation:
    """Smallest loosening of the named limits that makes some candidate comply.

    `candidates` has one row per portfolio and any of the columns in MEASURE_LIMIT. For each
    candidate the required value of a limit is max(current limit, the candidate's measure); the
    chosen candidate minimises its largest relative loosening (ties: the smaller total loosening)."""
    rows = {}
    for name, m in candidates.iterrows():
        req = {}
        for measure, key in MEASURE_LIMIT.items():
            if measure in m and pd.notna(m[measure]):
                req[key] = max(req.get(key, getattr(lim, key)), float(m[measure]))
        rel = {k: v / getattr(lim, k) - 1.0 for k, v in req.items()}
        rows[name] = {**{f"required_{k}": v for k, v in req.items()},
                      **{f"loosen_{k}": v for k, v in rel.items()},
                      "max_relative": max(rel.values(), default=0.0), "total_relative": sum(rel.values())}
    table = pd.DataFrame(rows).T.sort_values(["max_relative", "total_relative"])
    best = str(table.index[0])
    keys = [c.removeprefix("required_") for c in table.columns if c.startswith("required_")]
    required = {k: float(table.loc[best, f"required_{k}"]) for k in keys
                if table.loc[best, f"loosen_{k}"] > 1e-12}
    relative = {k: float(table.loc[best, f"loosen_{k}"]) for k in required}
    return Relaxation(best, required, relative, float(table.loc[best, "max_relative"]), table)


@dataclass(frozen=True)
class Evidence:
    vol_ann: float                  # C1 annualised volatility through the cycle (dev data, today's weights; D2)
    worst_hist_drawdown: float      # C2 worst historical crisis loss, today's weights (positive; D2)
    hypothetical_loss: float        # C3 hypothetical scenario loss (positive)
    es99_1d: float                  # C4 99% 1-day ES through the cycle (dev data incl. the GFC; D2)
    evt_es99: float                 # C5 EVT 99% ES
    return_level_10y: float         # C5 once-in-10-years daily loss
    champion_valid: bool            # C6 selected model passes Kupiec, CC and Basel
    any_model_valid: bool           # C6 for REJECT: at least one model is valid
    max_risk_to_capital: float      # reported for sizing, not a verdict check (C7 removed, audit G15)
    expected_return: float          # C8 forward expected return, net of costs (D4)
    required_return: float          # C8 CPI + spending + real growth (D1)
    resized_passes: bool = False    # a re-sized portfolio exists that passes C1–C5
    resized_weights: dict | None = None
    relaxation: Relaxation | None = None   # minimum relaxation across candidates (preferred when given)
    es99_conditional: float = float("nan")  # champion's current conditional ES: a D9 monitoring alert, not a check


@dataclass(frozen=True)
class Check:
    code: str
    name: str
    value: float | bool
    limit: float | bool
    passed: bool
    margin: float | None = None


@dataclass(frozen=True)
class Verdict:
    status: str
    checks: list[Check]
    reasons: list[str] = field(default_factory=list)
    adjustments: dict = field(default_factory=dict)


def _max_check(code, name, value, limit, tol=1e-12) -> Check:
    return Check(code, name, value, limit, value <= limit + tol, limit - value)


def run_checks(ev: Evidence, lim: IPSLimits, dcfg: dict) -> list[Check]:
    tol = dcfg["evt_tolerance"]
    return [
        _max_check("C1", "Volatility (through the cycle)", ev.vol_ann, lim.vol_ann_max),
        _max_check("C2", "Worst historical crisis loss", ev.worst_hist_drawdown, lim.stress_drawdown_max),
        _max_check("C3", "Hypothetical scenario loss", ev.hypothetical_loss, lim.stress_drawdown_max),
        _max_check("C4", "99% 1-day ES (through the cycle)", ev.es99_1d, lim.es99_1d_max),
        _max_check("C5a", "EVT 99% ES", ev.evt_es99, lim.es99_1d_max * tol),
        _max_check("C5b", "Once-in-10-years daily loss (EVT)", ev.return_level_10y, dcfg["return_level_limit"]),
        Check("C6", "Backtest validity of the selected model", ev.champion_valid, True, ev.champion_valid),
        Check("C8", "Expected return vs required", ev.expected_return, ev.required_return,
              ev.expected_return >= ev.required_return, ev.expected_return - ev.required_return),
    ]


LIMIT_OF = {"C1": "vol_ann_max", "C2": "stress_drawdown_max", "C3": "stress_drawdown_max", "C4": "es99_1d_max"}


def evaluate(ev: Evidence, lim: IPSLimits, dcfg: dict) -> Verdict:
    checks = run_checks(ev, lim, dcfg)
    by = {c.code: c for c in checks}
    if not ev.any_model_valid:
        return Verdict("REJECT", checks, ["No risk model passes the backtests: risk cannot be measured reliably."])

    risk_fail = [c for c in checks if c.code in ("C1", "C2", "C3", "C4", "C5a", "C5b") and not c.passed]
    gap = ev.required_return - ev.expected_return
    reasons, adjustments = [], {}

    if not risk_fail and by["C6"].passed and (by["C8"].passed or gap < dcfg["return_gap_tolerance"]):
        note = [] if by["C8"].passed else [f"Return gap of {gap:.2%} disclosed (below the {dcfg['return_gap_tolerance']:.0%} tolerance)."]
        return Verdict("ACCEPT", checks, ["All risk checks pass.", *note])

    if risk_fail:
        if ev.resized_passes:
            reasons.append("Risk checks fail as proposed, but a re-sized portfolio passes them.")
            adjustments["resized_weights"] = ev.resized_weights
        else:
            relax = ev.relaxation or minimum_relaxation(pd.DataFrame([{
                "vol_ann": ev.vol_ann, "worst_hist_drawdown": ev.worst_hist_drawdown,
                "hypothetical_loss": ev.hypothetical_loss, "es99_1d": ev.es99_1d}], index=["evaluated"]), lim)
            if relax.max_relative > dcfg["max_limit_relaxation"]:
                worst = max(relax.relative, key=relax.relative.get)
                return Verdict("REJECT", checks,
                               [f"Even the least-amended candidate ({relax.candidate}) needs {worst} loosened by "
                                f"{relax.relative[worst]:.0%}, more than the {dcfg['max_limit_relaxation']:.0%} "
                                "maximum: no acceptable portfolio exists."], {"minimum_relaxation": relax})
            if relax.required:
                reasons.append(f"No portfolio meets the current risk limits. Minimum relaxation: {relax.candidate} "
                               "complies if " + ", ".join(f"{k} is loosened to {v:.2%} (+{relax.relative[k]:.0%})"
                                                          for k, v in relax.required.items()) + ".")
                reasons.append("Amended limits require explicit approval by the investment committee (client) "
                               "before implementation.")
                adjustments["loosen_limits_to"] = relax.required
                adjustments["minimum_relaxation"] = relax
                adjustments["client_approval_required"] = True
            other = [c.name for c in risk_fail if c.code not in LIMIT_OF]
            if other:
                reasons.append("Re-sizing needed for: " + ", ".join(other) + ".")
    if not by["C6"].passed:
        reasons.append("The selected model fails its backtest: use the most conservative valid model for limits.")
    if gap >= dcfg["return_gap_tolerance"]:
        reasons.append(f"Expected return is {gap:.2%} below the required return: lower the return objective, "
                       "review the spending rate, or loosen a named risk limit.")
        adjustments["return_gap"] = gap
    return Verdict("ADJUST RISK LIMIT", checks, reasons, adjustments)
