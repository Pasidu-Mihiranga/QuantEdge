import numpy as np
import pandas as pd
import pytest

from quantedge.config import load_config
from quantedge.data.cleaning import CleaningLog, align_fred, build_clean_dataset
from quantedge.data.load import RawData
from quantedge.data.quality import run_quality_checks
from quantedge.data.stats import stationarity_table

CFG = load_config()


def _clean_walk(n, seed, start="2010-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)


@pytest.fixture
def planted():
    """One clean column per rule, each with exactly one planted problem."""
    n = 300
    cols = {name: _clean_walk(n, seed) for seed, name in
            enumerate(["STALE", "JUMP", "NEG", "NONPOS", "ADJ", "CLEAN"])}
    adj = pd.DataFrame(cols)
    idx = adj.index
    adj.loc[idx[150:156], "STALE"] = adj.at[idx[150], "STALE"]          # 6 identical prices
    adj.loc[idx[200]:, "JUMP"] *= 1.12                                  # +12% one-day jump
    adj.loc[idx[220]:, "NEG"] *= 0.70                                   # -30% day
    adj.loc[idx[-1], "NONPOS"] = 0.0                                    # invalid price, last day
    close = adj.copy()
    close.loc[idx[250]:, "ADJ"] *= 1.05                                 # adj/close ratio break
    zeros = pd.DataFrame(0.0, index=idx, columns=adj.columns)
    return adj, close, zeros


def test_each_rule_fires_on_its_planted_problem_and_nothing_is_deleted(planted):
    adj, close, zeros = planted
    before = adj.copy()
    flags = run_quality_checks(adj, close, zeros, zeros, CFG.cleaning)
    pd.testing.assert_frame_equal(adj, before)
    by_rule = flags.groupby("rule")
    idx = adj.index
    stale = by_rule.get_group("stale_price")
    assert list(zip(stale.ticker, stale.date, strict=True)) == [("STALE", idx[150])]
    assert ("JUMP", idx[200]) in set(zip(by_rule.get_group("jump").ticker,
                                          by_rule.get_group("jump").date, strict=True))
    neg = by_rule.get_group("large_negative")
    assert ("NEG", idx[220]) in set(zip(neg.ticker, neg.date, strict=True))
    nonpos = by_rule.get_group("non_positive_price")
    assert list(zip(nonpos.ticker, nonpos.date, strict=True)) == [("NONPOS", idx[-1])]
    adjb = by_rule.get_group("adjustment_break")
    assert list(zip(adjb.ticker, adjb.date, strict=True)) == [("ADJ", idx[250])]
    assert "CLEAN" not in set(flags.loc[flags.rule != "structural_break", "ticker"])
    assert (flags["action"] == "flagged").all()


def test_adjustment_break_on_dividend_date_is_not_flagged(planted):
    adj, close, zeros = planted
    divs = zeros.copy()
    divs.loc[adj.index[250], "ADJ"] = 0.5
    flags = run_quality_checks(adj, close, divs, zeros, CFG.cleaning)
    assert "adjustment_break" not in set(flags.rule)


def test_jump_rule_uses_only_past_volatility():
    s = _clean_walk(120, 7)
    df = s.to_frame("X")
    flags_a = run_quality_checks(df, df, df * 0, df * 0, CFG.cleaning)
    df2 = df.copy()
    df2.iloc[-1] *= 3  # a huge move on the last day must not change flags on earlier days
    flags_b = run_quality_checks(df2, df2, df2 * 0, df2 * 0, CFG.cleaning)
    early_a = flags_a[(flags_a.rule == "jump") & (flags_a.date < df.index[-1])]
    early_b = flags_b[(flags_b.rule == "jump") & (flags_b.date < df.index[-1])]
    pd.testing.assert_frame_equal(early_a.reset_index(drop=True), early_b.reset_index(drop=True))


def test_random_walk_has_unit_root_and_its_differences_do_not():
    walk = pd.Series(np.cumsum(np.random.default_rng(1).normal(size=2000)))
    table = stationarity_table({"level": walk, "diff": walk.diff()})
    assert table.loc["level", "adf_p"] > 0.05
    assert table.loc["level", "verdict"] == "unit root"
    assert table.loc["diff", "adf_p"] < 0.01


def test_iid_noise_is_judged_stationary_at_about_the_nominal_rate():
    """KPSS wrongly rejects stationarity ~5% of the time by design, so judge many draws."""
    series = {f"s{i}": pd.Series(np.random.default_rng(i).normal(size=1000)) for i in range(20)}
    verdicts = stationarity_table(series)["verdict"]
    assert (verdicts == "stationary").mean() >= 0.85


def test_fred_forward_fill_never_exceeds_limit():
    dates = pd.bdate_range("2020-01-01", periods=20)
    obs = pd.Series([1.0, 2.0], index=pd.DatetimeIndex([dates[0], dates[10]]), name="X")
    log = CleaningLog()
    out = align_fred(obs, dates, limit=3, log=log)
    assert out.iloc[0:4].tolist() == [1.0] * 4          # observation + 3 carried days
    assert out.iloc[4:10].isna().all()                  # older than 3 business days
    assert out.iloc[10:14].tolist() == [2.0] * 4
    assert log.entries[-1]["n_affected"] == 6


def _synthetic_raw(start="2004-11-18", end="2024-06-28"):
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(3)
    adj = pd.DataFrame({t: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx))))
                        for t in CFG.universe}, index=idx)
    adj.iloc[5, 0] = np.nan  # one ticker misses one day -> that date is dropped
    zeros = adj * 0
    fred = {sid: pd.Series(rng.uniform(1, 3, len(idx)), index=idx, name=sid)
            for sid in CFG.data.fred_series}
    return RawData(adj_close=adj, close=adj.copy(), volume=zeros, dividends=zeros,
                   splits=zeros, fred=fred)


def test_build_clean_dataset_logs_drops_and_locks_test_period():
    raw = _synthetic_raw()
    data = build_clean_dataset(CFG, raw=raw, frozen=False, write=False)
    assert len(data.prices) == len(raw.adj_close) - 1
    drops = data.log[data.log.step == "align_etf"]
    assert drops["n_affected"].sum() >= 1
    assert data.analysis_end <= pd.Timestamp("2022-12-31")
    assert (data.stationarity["n"] <= len(data.prices.loc[:"2022-12-31"])).all()
    assert data.prices.index.max() > pd.Timestamp("2023-01-01")  # mechanical cleaning covers all dates
