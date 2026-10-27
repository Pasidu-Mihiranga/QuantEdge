"""Load `config.yaml` into frozen, validated dataclasses.

Every module receives a `Config` (never reads YAML itself), so a single file controls the run.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from quantedge.paths import CONFIG_FILE


class ConfigError(ValueError):
    """Raised when config.yaml is internally inconsistent."""


@dataclass(frozen=True)
class DataCfg:
    start: pd.Timestamp
    end: pd.Timestamp | None
    fred_series: tuple[str, ...]


@dataclass(frozen=True)
class CleaningCfg:
    stale_run: int
    jump_sigma: float
    jump_window: int
    ffill_limit_fred: int
    large_negative: float
    adj_break: float


@dataclass(frozen=True)
class PortfolioCfg:
    allow_cash: bool
    rebalance: str
    cost_bps_per_side: float
    estimation_window_days: int


@dataclass(frozen=True)
class RiskCfg:
    confidence_levels: tuple[float, ...]
    windows: tuple[int, ...]
    default_window: int
    mc_sims: int


@dataclass(frozen=True)
class EvtCfg:
    threshold_quantiles: tuple[float, ...]
    min_exceedances: int


@dataclass(frozen=True)
class BacktestCfg:
    oos_start: pd.Timestamp
    refit_every: int
    champion_rule: str = "lowest_pinball_passing"


@dataclass(frozen=True)
class PartitionCfg:
    dev: tuple[pd.Timestamp, pd.Timestamp]
    val: tuple[pd.Timestamp, pd.Timestamp]
    test: tuple[pd.Timestamp, pd.Timestamp | None]
    freeze_tag: str
    warmup_weights: dict[str, float]


@dataclass(frozen=True)
class Config:
    seed: int
    nav_usd: float
    universe: tuple[str, ...]
    benchmark: dict[str, float]
    market_proxy: str
    data: DataCfg
    cleaning: CleaningCfg
    portfolio: PortfolioCfg
    risk: RiskCfg
    evt: EvtCfg
    backtest: BacktestCfg
    partition: PartitionCfg
    ips: dict[str, Any] = field(default_factory=dict)
    stress: dict[str, Any] = field(default_factory=dict)
    behavioral: dict[str, Any] = field(default_factory=dict)
    ml: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    sha256: str = ""

    def rng(self, stream: int = 0) -> np.random.Generator:
        """Independent, reproducible generator for one random stream (e.g. one Monte Carlo use)."""
        return np.random.default_rng([self.seed, stream])


def _ts(value: Any) -> pd.Timestamp | None:
    return None if value is None else pd.Timestamp(value)


def _check_weights(name: str, weights: dict[str, float], universe: tuple[str, ...]) -> None:
    unknown = set(weights) - set(universe)
    if unknown:
        raise ConfigError(f"{name}: tickers {sorted(unknown)} are not in the universe")
    if any(not 0.0 <= w <= 1.0 for w in weights.values()):
        raise ConfigError(f"{name}: every weight must lie in [0, 1]")
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ConfigError(f"{name}: weights sum to {sum(weights.values())}, not 1")


def _validate(cfg: Config) -> None:
    _check_weights("benchmark", cfg.benchmark, cfg.universe)
    _check_weights("partition.warmup_weights", cfg.partition.warmup_weights, cfg.universe)
    if cfg.market_proxy not in cfg.universe:
        raise ConfigError("market_proxy must be in the universe")
    for a in cfg.risk.confidence_levels:
        if not 0.0 < a < 1.0:
            raise ConfigError(f"confidence level {a} must lie in (0, 1)")
    if cfg.risk.default_window not in cfg.risk.windows:
        raise ConfigError("risk.default_window must be one of risk.windows")

    p = cfg.partition
    if p.dev[0] != cfg.data.start:
        raise ConfigError("partition.dev must start on data.start")
    ordered = [p.dev[0], p.dev[1], p.val[0], p.val[1], p.test[0]]
    if any(b <= a for a, b in zip(ordered, ordered[1:], strict=False)):
        raise ConfigError("partition periods must be ordered: dev < val < test")
    for (end_prev, start_next) in [(p.dev[1], p.val[0]), (p.val[1], p.test[0])]:
        if start_next - end_prev != pd.Timedelta(days=1):
            raise ConfigError("partition periods must be contiguous calendar periods")


def load_config(path: Path | str = CONFIG_FILE) -> Config:
    """Read and validate the YAML configuration.

    The SHA-256 of the file is stored on the result so artifacts and the
    methodology-freeze record can prove which configuration produced them.
    """
    raw_bytes = Path(path).read_bytes()
    raw = yaml.safe_load(raw_bytes)
    part = raw["partition"]
    cfg = Config(
        seed=int(raw["seed"]),
        nav_usd=float(raw["nav_usd"]),
        universe=tuple(raw["universe"]),
        benchmark={k: float(v) for k, v in raw["benchmark"].items()},
        market_proxy=raw["market_proxy"],
        data=DataCfg(
            start=pd.Timestamp(raw["data"]["start"]),
            end=_ts(raw["data"].get("end")),
            fred_series=tuple(raw["data"]["fred_series"]),
        ),
        cleaning=CleaningCfg(**raw["cleaning"]),
        portfolio=PortfolioCfg(**raw["portfolio"]),
        risk=RiskCfg(
            confidence_levels=tuple(raw["risk"]["confidence_levels"]),
            windows=tuple(raw["risk"]["windows"]),
            default_window=int(raw["risk"]["default_window"]),
            mc_sims=int(raw["risk"]["mc_sims"]),
        ),
        evt=EvtCfg(
            threshold_quantiles=tuple(raw["evt"]["threshold_quantiles"]),
            min_exceedances=int(raw["evt"]["min_exceedances"]),
        ),
        backtest=BacktestCfg(
            oos_start=pd.Timestamp(raw["backtest"]["oos_start"]),
            refit_every=int(raw["backtest"]["refit_every"]),
            champion_rule=raw["backtest"].get("champion_rule", "lowest_pinball_passing"),
        ),
        partition=PartitionCfg(
            dev=(pd.Timestamp(part["dev"][0]), pd.Timestamp(part["dev"][1])),
            val=(pd.Timestamp(part["val"][0]), pd.Timestamp(part["val"][1])),
            test=(pd.Timestamp(part["test"][0]), _ts(part["test"][1])),
            freeze_tag=part["freeze_tag"],
            warmup_weights={k: float(v) for k, v in part["warmup_weights"].items()},
        ),
        ips=raw.get("ips") or {},
        stress=raw.get("stress") or {},
        behavioral=raw.get("behavioral") or {},
        ml=raw.get("ml") or {},
        decision=raw.get("decision") or {},
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    _validate(cfg)
    return cfg
