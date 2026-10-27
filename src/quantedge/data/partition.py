"""Chronological partition and the test-period lock (Step 22 §3.1 and §3.3).

    development  2004-11-18 → 2018-12-31   design and fitting
    validation   2019-01-01 → 2022-12-31   walk-forward selection and tuning
    final test   2023-01-01 → snapshot     locked until the git tag `methodology-freeze-v1` exists

Walk-forward forecasting runs inside each period; the partition only decides which *decisions*
may look at which period. Any request that reaches into the test period raises
`TestLockedError` until the methodology is frozen.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quantedge.config import Config
from quantedge.paths import ARTIFACTS, ROOT

SPLITS = ("dev", "val", "dev+val", "test", "all")


class TestLockedError(PermissionError):
    """Raised when code asks for final-test data before the methodology-freeze tag exists."""

    __test__ = False  # not a pytest test class


def is_frozen(tag: str, repo: Path = ROOT) -> bool:
    """True when `tag` exists in the repository (checked with `git tag --list`)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "tag", "--list", tag],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0 and out.stdout.strip() == tag


@dataclass(frozen=True)
class Partition:
    dev: tuple[pd.Timestamp, pd.Timestamp]
    val: tuple[pd.Timestamp, pd.Timestamp]
    test_start: pd.Timestamp
    test_end: pd.Timestamp | None
    freeze_tag: str

    @classmethod
    def from_config(cls, cfg: Config) -> Partition:
        p = cfg.partition
        return cls(dev=p.dev, val=p.val, test_start=p.test[0], test_end=p.test[1],
                   freeze_tag=p.freeze_tag)

    def split_of(self, date: pd.Timestamp | str) -> str | None:
        d = pd.Timestamp(date)
        if self.dev[0] <= d <= self.dev[1]:
            return "dev"
        if self.val[0] <= d <= self.val[1]:
            return "val"
        if d >= self.test_start and (self.test_end is None or d <= self.test_end):
            return "test"
        return None

    def bounds(self, split: str) -> tuple[pd.Timestamp, pd.Timestamp | None]:
        if split not in SPLITS:
            raise ValueError(f"split must be one of {SPLITS}, got {split!r}")
        return {
            "dev": self.dev,
            "val": self.val,
            "dev+val": (self.dev[0], self.val[1]),
            "test": (self.test_start, self.test_end),
            "all": (self.dev[0], self.test_end),
        }[split]

    def frozen(self, repo: Path = ROOT) -> bool:
        return is_frozen(self.freeze_tag, repo)

    def visible_end(self, frozen: bool | None = None) -> pd.Timestamp | None:
        """Last date any analysis may use right now: end of validation before the freeze."""
        if frozen is None:
            frozen = self.frozen()
        return self.test_end if frozen else self.val[1]

    def restrict(self, obj: pd.DataFrame | pd.Series, split: str,
                 frozen: bool | None = None) -> pd.DataFrame | pd.Series:
        """Rows of `obj` (DatetimeIndex) inside `split`; test/all require the freeze tag."""
        if split in ("test", "all"):
            if frozen is None:
                frozen = self.frozen()
            if not frozen:
                raise TestLockedError(
                    f"The final-test period ({self.test_start.date()} onwards) is locked until the "
                    f"git tag '{self.freeze_tag}' exists. Use split='dev', 'val' or 'dev+val'."
                )
        start, end = self.bounds(split)
        idx = obj.index
        mask = idx >= start
        if end is not None:
            mask &= idx <= end
        return obj.loc[mask]


def load_returns(split: str, cfg: Config, kind: str = "simple",
                 frozen: bool | None = None, artifacts: Path = ARTIFACTS) -> pd.DataFrame:
    """The only sanctioned way for analysis code to read asset returns (Step 22 §3.3)."""
    if kind not in ("simple", "log"):
        raise ValueError("kind must be 'simple' or 'log'")
    df = pd.read_parquet(artifacts / f"returns_{kind}.parquet")
    return Partition.from_config(cfg).restrict(df, split, frozen=frozen)
