"""Model-selection table, champion choice and crisis breakdown (Step 11 §3.6–3.7).

Selection rule (declared in advance, validation period only; decision record
doc/decisions/champion_rule.md): a model is adequately validated when Kupiec and Christoffersen CC
are not rejected at 5%, no rolling-250 window is red and Z2 is not rejected at 97.5%. Among those,
the model with the lowest mean 99% pinball loss is the champion ("lowest_pinball_passing"). The
earlier parsimony rule ("simplest_passing") is kept for comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantedge.backtest import coverage as cv
from quantedge.backtest import scoring as sc
from quantedge.backtest.es_backtest import acerbi_szekely_z2

COMPLEXITY = ["Historical", "Normal", "Student-t", "Cornish-Fisher", "EVT", "Monte Carlo",
              "GARCH-FHS", "Conditional EVT"]


def selection_table(results: dict[str, pd.DataFrame], alpha: float = 0.99,
                    start=None, end=None, test_level: float = 0.05) -> pd.DataFrame:
    rows = []
    for name, df in results.items():
        d = df.loc[start:end]
        hits = d[f"hit_{alpha}"].to_numpy()
        T, x = len(hits), int(hits.sum())
        k = cv.kupiec(hits, alpha)
        c = cv.christoffersen(hits, alpha)
        roll = cv.rolling_basel(d[f"hit_{alpha}"], 250, alpha) if alpha == 0.99 else None
        shares = cv.zone_shares(roll) if roll is not None and len(roll) else {}
        lo, hi = cv.clopper_pearson(x, T)
        z2 = acerbi_szekely_z2(d.loss, d["var_0.975"], d["es_0.975"], 0.975) if "es_0.975" in d else None
        row = {
            "model": name, "T": T, "exceptions": x, "expected": (1 - alpha) * T,
            "rate": x / T, "rate_ci_low": lo, "rate_ci_high": hi,
            "kupiec_p": k.pvalue, "ind_p": c.p_ind, "cc_p": c.p_cc,
            "full_period_zone": cv.basel_zone(x, T, alpha),
            "rolling_green": shares.get("green", np.nan), "rolling_yellow": shares.get("yellow", np.nan),
            "rolling_red": shares.get("red", np.nan),
            "worst_250d_exceptions": int(roll["exceptions"].max()) if roll is not None and len(roll) else np.nan,
            "z2_975": z2.z2 if z2 else np.nan, "z2_zone": z2.zone if z2 else "n/a",
            "pinball": float(sc.pinball(d.loss, d[f"var_{alpha}"], alpha).mean()),
            "fz0": float(sc.fz0(d.loss, d[f"var_{alpha}"], d[f"es_{alpha}"], alpha).mean()),
        }
        cc_ok = np.isnan(row["cc_p"]) or row["cc_p"] >= test_level
        row["passes"] = bool(row["kupiec_p"] >= test_level and cc_ok
                             and (row["rolling_red"] == 0 or np.isnan(row["rolling_red"]))
                             and row["z2_zone"] in ("green", "n/a"))
        rows.append(row)
    table = pd.DataFrame(rows).set_index("model")
    table["complexity"] = [COMPLEXITY.index(m) if m in COMPLEXITY else len(COMPLEXITY) for m in table.index]
    return table


def choose_champion(table: pd.DataFrame, rule: str = "lowest_pinball_passing") -> tuple[str, str]:
    """Champion among adequately validated models; if none pass, the lowest-pinball model, flagged."""
    passing = table[table["passes"]]
    if not len(passing):
        best = str(table.sort_values("pinball").index[0])
        return best, "no model passes all tests: carried into the decision engine as model risk"
    if rule == "simplest_passing":
        return str(passing.sort_values("complexity").index[0]), "simplest adequately validated model"
    if rule == "lowest_pinball_passing":
        return (str(passing.sort_values("pinball").index[0]),
                "lowest 99% pinball loss among adequately validated models (provisional until the final test)")
    raise ValueError(f"unknown champion rule {rule!r}")


def crisis_breakdown(results: dict[str, pd.DataFrame], windows: dict[str, tuple[str, str]],
                     alpha: float = 0.99) -> pd.DataFrame:
    rows = []
    for name, df in results.items():
        for crisis, (s, e) in windows.items():
            d = df.loc[s:e]
            if d.empty:
                continue
            hit = d[f"hit_{alpha}"].astype(bool)
            exceed = (d.loss - d[f"var_{alpha}"])[hit]
            rows.append({"model": name, "crisis": crisis, "days": len(d), "exceptions": int(hit.sum()),
                         "expected": (1 - alpha) * len(d),
                         "mean_exceedance": float(exceed.mean()) if len(exceed) else 0.0,
                         "max_exceedance": float(exceed.max()) if len(exceed) else 0.0})
    return pd.DataFrame(rows)
