"""The freeze and the final test are guarded (Step 22 §3.3, M6–M7)."""

import json

import pandas as pd
import pytest

from quantedge.backtest import final_test
from quantedge.config import load_config
from quantedge.data.partition import TestLockedError

CFG = load_config()


def test_final_test_refuses_without_the_freeze_tag():
    with pytest.raises(TestLockedError, match="methodology-freeze-v1"):
        final_test.check_allowed(CFG, frozen=False)


def test_final_test_runs_only_once_unless_a_deviation_is_logged(tmp_path, monkeypatch):
    result = tmp_path / "final_test_result.json"
    result.write_text(json.dumps({"run_utc": "x"}), encoding="utf-8")
    monkeypatch.setattr(final_test, "RESULT", result)
    with pytest.raises(RuntimeError, match="runs once"):
        final_test.check_allowed(CFG, frozen=True)
    final_test.check_allowed(CFG, frozen=True, deviation="data vendor revised one day")   # allowed, logged


def test_adoption_condition_3():
    scores = pd.DataFrame({"pinball": [1.00, 1.015, 1.05], "exceptions": [10, 11, 12], "kupiec_p": 0.5,
                           "cc_p": 0.5, "passes": True}, index=["Champion", "Close", "Worse"])
    out = final_test.adoption_condition_3(scores, "Champion", 0.02)
    assert out["condition_3"].to_dict() == {"Champion": True, "Close": True, "Worse": False}


def test_freeze_script_lists_open_blocking_items():
    import importlib.util

    from quantedge.paths import ROOT

    spec = importlib.util.spec_from_file_location("freeze", ROOT / "scripts" / "freeze.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    text = "# x\n\n## Blocking\n\n- [x] done\n- [ ] horizon open\n\n## Non-blocking\n\n- [ ] later\n"
    assert freeze.open_blocking_items(text) == ["horizon open"]
    assert "3.8" in freeze.adoption_rule_text()
