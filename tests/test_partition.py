"""Leakage guards for the chronological partition (Step 22 M1)."""

import subprocess

import numpy as np
import pandas as pd
import pytest

from quantedge.config import load_config
from quantedge.data.partition import Partition, TestLockedError, is_frozen, load_returns

CFG = load_config()
PART = Partition.from_config(CFG)


@pytest.fixture
def frame():
    idx = pd.bdate_range("2004-11-18", "2025-06-30")
    return pd.DataFrame({"x": np.arange(len(idx), dtype=float)}, index=idx)


@pytest.mark.parametrize(
    "date, split",
    [("2004-11-18", "dev"), ("2018-12-31", "dev"), ("2019-01-01", "val"),
     ("2022-12-31", "val"), ("2023-01-01", "test"), ("2004-11-17", None)],
)
def test_split_of_boundaries(date, split):
    assert PART.split_of(date) == split


def test_dev_val_restrict_never_returns_test_rows(frame):
    for split in ("dev", "val", "dev+val"):
        out = PART.restrict(frame, split, frozen=False)
        assert out.index.max() <= pd.Timestamp("2022-12-31")
    assert PART.restrict(frame, "dev", frozen=False).index.max() == pd.Timestamp("2018-12-31")
    assert PART.restrict(frame, "val", frozen=False).index.min() == pd.Timestamp("2019-01-01")


@pytest.mark.parametrize("split", ["test", "all"])
def test_test_period_locked_without_freeze(frame, split):
    with pytest.raises(TestLockedError, match="methodology-freeze-v1"):
        PART.restrict(frame, split, frozen=False)


def test_test_period_available_after_freeze(frame):
    out = PART.restrict(frame, "test", frozen=True)
    assert out.index.min() == pd.Timestamp("2023-01-02")


def test_visible_end_before_and_after_freeze():
    assert PART.visible_end(frozen=False) == pd.Timestamp("2022-12-31")
    assert PART.visible_end(frozen=True) is None  # snapshot end


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_is_frozen_reads_the_git_tag(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
         "--allow-empty", "-m", "init")
    assert not is_frozen("methodology-freeze-v1", tmp_path)
    _git(tmp_path, "tag", "methodology-freeze-v1")
    assert is_frozen("methodology-freeze-v1", tmp_path)


def test_load_returns_goes_through_the_guard(tmp_path, frame):
    frame.to_parquet(tmp_path / "returns_simple.parquet")
    dev = load_returns("dev+val", CFG, frozen=False, artifacts=tmp_path)
    assert dev.index.max() <= pd.Timestamp("2022-12-31")
    with pytest.raises(TestLockedError):
        load_returns("test", CFG, frozen=False, artifacts=tmp_path)
