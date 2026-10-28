"""Quantile challengers: linear quantile regression (baseline) and LightGBM (Step 22 §3.6–3.7).

Both predict the conditional quantiles of next-day loss l_{t+1} from features known at t.
Quantile predictions are rearranged row-wise (Chernozhukov, Fernandez-Val & Galichon, 2010) because
separately fitted quantile models can cross; monotone feature constraints do not prevent this.
Features are standardised with statistics of the training window only.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd


def rearrange(q: np.ndarray) -> tuple[np.ndarray, int]:
    """Sort each row of quantile predictions (columns in increasing level); return fixes made."""
    sorted_q = np.sort(q, axis=1)
    return sorted_q, int(np.sum(np.any(sorted_q != q, axis=1)))


class _Scaler:
    def fit(self, X: pd.DataFrame):
        self.mu, self.sd = X.mean(), X.std().replace(0, 1.0)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return (X - self.mu) / self.sd


class LinearQR:
    """statsmodels QuantReg, one fit per quantile level."""

    name = "Linear QR"

    def __init__(self, levels):
        self.levels = tuple(levels)

    def fit(self, X: pd.DataFrame, y: pd.Series):
        import statsmodels.api as sm

        self.scaler = _Scaler().fit(X)
        Xs = sm.add_constant(self.scaler.transform(X), has_constant="add")
        self.cols = Xs.columns
        self.params = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for a in self.levels:
                self.params[a] = sm.QuantReg(y.to_numpy(), Xs.to_numpy()).fit(q=a, max_iter=5000).params
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        import statsmodels.api as sm

        Xs = sm.add_constant(self.scaler.transform(X), has_constant="add")[self.cols].to_numpy()
        return np.column_stack([Xs @ self.params[a] for a in self.levels])


class LGBMQuantile:
    """One LightGBM quantile model per level; early stopping on the last 20% of the training
    window (time-ordered, never shuffled).

    LightGBM (4.x) rejects monotone_constraints with the quantile objective, because its quantile
    leaf renewal would break them. Monotonicity in volatility is therefore measured with
    `monotonicity_violations` and reported, not imposed (documented deviation from Step 22 §3.6)."""

    name = "LightGBM"

    def __init__(self, levels, params: dict | None = None, seed: int = 0):
        self.levels = tuple(levels)
        self.params = {"num_leaves": 7, "min_data_in_leaf": 50, "learning_rate": 0.03,
                       "n_estimators": 500, "feature_fraction": 0.8, **(params or {})}
        self.seed = seed

    def fit(self, X: pd.DataFrame, y: pd.Series):
        import lightgbm as lgb

        self.cols = list(X.columns)
        cut = int(len(X) * 0.8)
        self.models = {}
        for a in self.levels:
            m = lgb.LGBMRegressor(objective="quantile", alpha=a, random_state=self.seed,
                                  deterministic=True, verbose=-1, bagging_seed=self.seed,
                                  feature_fraction_seed=self.seed, **self.params)
            m.fit(X.iloc[:cut], y.iloc[:cut], eval_X=(X.iloc[cut:],), eval_y=(y.iloc[cut:],),
                  eval_metric="quantile", callbacks=[lgb.early_stopping(50, verbose=False)])
            self.models[a] = m
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.column_stack([self.models[a].predict(X[self.cols]) for a in self.levels])

    def contributions(self, X: pd.DataFrame, level: float) -> pd.DataFrame:
        """SHAP values from LightGBM's built-in pred_contrib (last column is the expected value)."""
        raw = self.models[level].predict(X[self.cols], pred_contrib=True)
        return pd.DataFrame(raw, index=X.index, columns=[*self.cols, "expected_value"])


def ice_curves(model, X: pd.DataFrame, feature: str, level: float, n_grid: int = 25) -> np.ndarray:
    """Individual conditional expectation curves: for each row, the predicted `level` quantile as
    `feature` moves across its observed 5-95% range, other features held at the row's values.
    Shape (rows, n_grid)."""
    grid = np.quantile(X[feature], np.linspace(0.05, 0.95, n_grid))
    j = model.levels.index(level)
    Z = X.loc[X.index.repeat(n_grid)].copy()
    Z[feature] = np.tile(grid, len(X))
    return model.predict(Z)[:, j].reshape(len(X), n_grid)


def monotonicity_violations(model, X: pd.DataFrame, feature: str, level: float, n_grid: int = 25) -> float:
    """Share of rows whose ICE curve (`ice_curves`) falls anywhere. 0 means monotone everywhere."""
    return float((np.diff(ice_curves(model, X, feature, level, n_grid), axis=1) < -1e-12).any(axis=1).mean())


def ratio_es(var_ml: np.ndarray, var_evt: np.ndarray, es_evt: np.ndarray, eps: float = 1e-4,
             clip=(1.0, 2.5)) -> tuple[np.ndarray, int]:
    """ES_ML = VaR_ML x ES_EVT / VaR_EVT with guards (Step 22 §3.7a). Returns (ES, guard hits)."""
    ratio = np.divide(es_evt, var_evt, out=np.full_like(es_evt, clip[0]), where=var_evt > eps)
    guarded = (var_evt <= eps) | (ratio < clip[0]) | (ratio > clip[1])
    es = np.maximum(var_ml * np.clip(ratio, *clip), var_ml)
    return es, int(guarded.sum())


def walk_forward_ml(make_model, X: pd.DataFrame, target: pd.Series, levels, retrain_every: int = 21,
                    min_train: int = 750, start=None, end=None, es_levels=None) -> pd.DataFrame:
    """Out-of-sample quantile forecasts for each forecast day.

    Row s of X is the forecast origin; target[s] is the loss of the next trading day.
    For forecast origin t, training uses rows s <= t-1 (their targets, dated s+1 <= t, are known).
    Output is indexed by the forecast day (origin + 1) with loss, var_<a>, and es_<a> when
    `es_levels` maps a level to the extra quantile levels averaged for the quantile-integral ES.
    """
    data = pd.concat([X, target.rename("__y")], axis=1).dropna()
    days = target.index
    next_day = pd.Series(days[1:], index=days[:-1])
    all_levels = sorted(set(levels) | {q for qs in (es_levels or {}).values() for q in qs})
    origins = data.index
    lo = max(min_train, int(origins.searchsorted(pd.Timestamp(start)))) if start is not None else min_train
    hi = int(origins.searchsorted(pd.Timestamp(end), side="right")) if end is not None else len(origins)
    rows, model, last, crossings = [], None, -10**9, 0
    for i in range(lo, hi):
        if model is None or i - last >= retrain_every:
            train = data.iloc[:i]                       # origins strictly before the current origin
            model = make_model(all_levels).fit(train.drop(columns="__y"), train["__y"])
            last = i
        pred, fixed = rearrange(model.predict(data.iloc[[i]].drop(columns="__y")))
        crossings += fixed
        q = dict(zip(all_levels, pred[0], strict=True))
        origin = origins[i]
        if origin not in next_day.index:
            continue
        row = {"date": next_day[origin], "loss": float(data["__y"].iloc[i])}
        for a in levels:
            row[f"var_{a}"] = q[a]
            row[f"hit_{a}"] = int(row["loss"] > q[a])
        for a, qs in (es_levels or {}).items():
            row[f"es_{a}"] = max(float(np.mean([q[x] for x in qs])), q[a])
        rows.append(row)
    out = pd.DataFrame(rows).set_index("date")
    out.attrs["crossings_fixed"] = crossings
    return out
