"""Multi-day VaR / ES (Step 08 §3.2, "10-day horizon").

    filtered HS paths: bootstrap the GARCH standardised residuals through the variance recursion
                       for h days; the h-day loss is -(prod(1 + r) - 1)
    historical:        overlapping h-day compounded returns of the window
    sqrt(h) scaling:   VaR_1d x sqrt(h), shown only as a labelled comparison (it assumes i.i.d.
                       returns, which the Ljung-Box and ARCH tests reject)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from quantedge.portfolio.returns import horizon_returns
from quantedge.risk import es as esf
from quantedge.risk.garch import GarchFHSModel


def fhs_paths(model: GarchFHSModel, h: int, n_paths: int, rng: np.random.Generator) -> np.ndarray:
    """Simulated h-day losses from a fitted GarchFHSModel (parameters fixed, residuals resampled)."""
    p = model.params
    mu, omega, a, b = float(p["mu"]), float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"])
    z = -model.neg_z                                   # standardised residuals (return sign)
    s2 = np.full(n_paths, (100.0 * model.sigma_next) ** 2)
    growth = np.ones(n_paths)
    for _ in range(h):
        draw = z[rng.integers(0, len(z), n_paths)]
        r = mu + np.sqrt(s2) * draw                    # in percent
        growth *= 1.0 + r / 100.0
        s2 = omega + a * (r - mu) ** 2 + b * s2
    return -(growth - 1.0)


def horizon_table(model: GarchFHSModel, window_returns: pd.Series, h: int, rng: np.random.Generator,
                  alphas=(0.95, 0.99), n_paths: int = 50_000) -> pd.DataFrame:
    sims = fhs_paths(model, h, n_paths, rng)
    hist = -horizon_returns(window_returns, h).to_numpy()
    rows = []
    for a in alphas:
        rows.append({"alpha": a, "horizon": h, "method": "GARCH-FHS paths",
                     "var": esf.sample_var(sims, a), "es": esf.sample_es(sims, a)})
        rows.append({"alpha": a, "horizon": h, "method": "historical overlapping",
                     "var": esf.sample_var(hist, a), "es": esf.sample_es(hist, a)})
        rows.append({"alpha": a, "horizon": h, "method": "sqrt(h) scaling (comparison only)",
                     "var": model.var(a) * math.sqrt(h), "es": model.es(a) * math.sqrt(h)})
    return pd.DataFrame(rows)
