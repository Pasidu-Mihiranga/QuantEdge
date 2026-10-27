"""GARCH(1,1)-t filtered historical simulation (Step 08 §3.2).

    100 r_t = mu + e_t,  e_t = sigma_t z_t,  sigma_t^2 = omega + alpha e_{t-1}^2 + beta sigma_{t-1}^2
    VaR_{t+1} = -(mu + sigma_{t+1|t} q_{1-a}(z)),  ES from the empirical tail of -z.

Volatility clustering is captured; parameters carry estimation error. Only the filtered
(one-step-ahead) variance is used, never smoothed estimates.
"""

from __future__ import annotations

import warnings

import numpy as np
from arch import arch_model

from quantedge.risk import es as esf
from quantedge.risk.base import portfolio_returns


class GarchFHSModel:
    name = "GARCH-FHS"

    def __init__(self, dist: str = "t"):
        self.dist = dist
        self._last_params = None

    def fit(self, returns, weights=None):
        r = portfolio_returns(returns, weights)
        am = arch_model(100.0 * r, mean="Constant", vol="GARCH", p=1, q=1, dist=self.dist, rescale=False)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = am.fit(disp="off", starting_values=self._last_params, show_warning=False)
        self._last_params = res.params.to_numpy()
        self.result = res
        self.params = res.params
        self.mu = float(res.params["mu"]) / 100.0
        self.sigma_next = float(np.sqrt(res.forecast(horizon=1, reindex=False).variance.iloc[-1, 0])) / 100.0
        z = (res.resid / res.conditional_volatility).dropna().to_numpy()
        self.neg_z = -z                       # standardised losses
        self.persistence = float(res.params["alpha[1]"] + res.params["beta[1]"])
        return self

    def update(self, r_new: float) -> None:
        """Roll the filter forward one day with the parameters held fixed (no refit):
        sigma^2_{t+1} = omega + alpha (100 r_t - mu)^2 + beta sigma^2_t."""
        p = self.params
        e = 100.0 * r_new - p["mu"]
        s2 = (100.0 * self.sigma_next) ** 2
        self.sigma_next = float(np.sqrt(p["omega"] + p["alpha[1]"] * e**2 + p["beta[1]"] * s2)) / 100.0

    def var(self, alpha):
        return float(-self.mu + self.sigma_next * esf.sample_var(self.neg_z, alpha))

    def es(self, alpha):
        return float(-self.mu + self.sigma_next * esf.sample_es(self.neg_z, alpha))

    def loss_sample(self):
        return -self.mu + self.sigma_next * self.neg_z
