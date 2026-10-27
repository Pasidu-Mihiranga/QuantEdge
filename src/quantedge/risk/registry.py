"""Model registry: the sidebar method selector maps here (Step 08 §4)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from quantedge.risk.garch import GarchFHSModel
from quantedge.risk.montecarlo import MonteCarloModel
from quantedge.risk.var import CornishFisherModel, HistoricalModel, NormalModel, StudentTModel


def make_models(rng: np.random.Generator, mc_sims: int = 100_000) -> dict[str, Callable[[], object]]:
    """Factories for the conventional models (fresh, unfitted instances)."""
    return {
        "Historical": HistoricalModel,
        "Normal": NormalModel,
        "Student-t": StudentTModel,
        "Cornish-Fisher": CornishFisherModel,
        "Monte Carlo": lambda: MonteCarloModel(n_sims=mc_sims, rng=rng),
        "GARCH-FHS": GarchFHSModel,
    }


# ML challengers (Steps 22–23) register here once built; they are not in the default line-up.
CHALLENGERS: dict[str, Callable[[], object]] = {}
