from pathlib import Path

import pytest
import yaml

from quantedge.config import ConfigError, load_config
from quantedge.paths import CONFIG_FILE, ROOT


def _write_variant(tmp_path: Path, mutate) -> Path:
    raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    mutate(raw)
    out = tmp_path / "config.yaml"
    out.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return out


def test_project_config_loads():
    cfg = load_config()
    assert cfg.universe == ("SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK")
    assert cfg.nav_usd == 10_000_000
    assert cfg.partition.val[0].strftime("%Y-%m-%d") == "2019-01-01"
    assert cfg.partition.test[1] is None
    assert len(cfg.sha256) == 64


def test_root_is_the_quantedge_repo():
    assert (ROOT / "config.yaml").exists()
    assert (ROOT / "src" / "quantedge").is_dir()


def test_rng_streams_are_reproducible_and_distinct():
    cfg = load_config()
    a1 = cfg.rng(1).standard_normal(5)
    a2 = cfg.rng(1).standard_normal(5)
    b = cfg.rng(2).standard_normal(5)
    assert (a1 == a2).all()
    assert not (a1 == b).all()


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda r: r["benchmark"].update(SPY=0.7), "sum"),
        (lambda r: r["benchmark"].update(QQQ=0.0), "not in the universe"),
        (lambda r: r["risk"].update(confidence_levels=[0.95, 1.0]), "confidence"),
        (lambda r: r["partition"].update(val=["2019-01-02", "2022-12-31"]), "contiguous"),
        (lambda r: r["partition"].update(test=["2022-06-01", None]), "ordered"),
    ],
)
def test_invalid_configs_are_rejected(tmp_path, mutate, message):
    with pytest.raises(ConfigError, match=message):
        load_config(_write_variant(tmp_path, mutate))
