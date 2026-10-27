import socket

import numpy as np
import pandas as pd
import pytest

from quantedge.data.download import parse_fred_csv
from quantedge.data.load import load_raw
from quantedge.data.manifest import (
    ManifestEntry,
    ManifestError,
    sha256_file,
    verify_manifest,
    write_manifest,
)


@pytest.mark.parametrize("date_col", ["observation_date", "DATE"])
def test_parse_fred_csv_handles_both_date_columns_and_dot_nan(date_col):
    text = f"{date_col},DTB3\n2020-01-02,1.52\n2020-01-03,.\n2020-01-06,1.50\n"
    s = parse_fred_csv(text, "DTB3")
    assert s.name == "DTB3"
    assert s.dtype == float
    assert np.isnan(s.loc["2020-01-03"])
    assert s.loc["2020-01-06"] == pytest.approx(1.50)
    assert s.index.is_monotonic_increasing


def _write_snapshot(raw_dir):
    dates = pd.bdate_range("2020-01-01", periods=5)
    rows = []
    for t in ["SPY", "AGG"]:
        for i, d in enumerate(dates):
            rows.append({"date": d, "ticker": t, "open": 1.0, "high": 1.0, "low": 1.0,
                         "close": 100.0 + i, "adj_close": 99.0 + i, "volume": 1000.0,
                         "dividends": 0.0, "stock_splits": 0.0})
    prices = pd.DataFrame(rows)
    raw_dir.mkdir()
    prices.to_parquet(raw_dir / "prices.parquet", index=False)
    fred = pd.Series([1.0, 1.1], index=pd.DatetimeIndex(dates[:2], name="date"), name="DTB3")
    fred.to_frame().to_parquet(raw_dir / "fred_DTB3.parquet")
    entries = [
        ManifestEntry(f, "test", "test", "2026-01-01T00:00:00Z", 1, "2020-01-01", "2020-01-07",
                      sha256_file(raw_dir / f), {})
        for f in ["prices.parquet", "fred_DTB3.parquet"]
    ]
    manifest = raw_dir / "manifest.json"
    write_manifest(entries, manifest)
    return manifest


def test_manifest_detects_a_single_byte_change(tmp_path):
    raw = tmp_path / "raw"
    manifest = _write_snapshot(raw)
    verify_manifest(manifest, raw)
    f = raw / "fred_DTB3.parquet"
    data = bytearray(f.read_bytes())
    data[len(data) // 2] ^= 0xFF
    f.write_bytes(bytes(data))
    with pytest.raises(ManifestError, match="hash mismatch"):
        verify_manifest(manifest, raw)


def test_load_raw_works_offline(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    manifest = _write_snapshot(raw)

    def no_network(*args, **kwargs):
        raise OSError("network disabled in test")

    monkeypatch.setattr(socket, "socket", no_network)
    data = load_raw(raw, manifest)
    assert list(data.adj_close.columns) == ["AGG", "SPY"]
    assert data.adj_close.shape == (5, 2)
    assert data.fred["DTB3"].iloc[1] == pytest.approx(1.1)
