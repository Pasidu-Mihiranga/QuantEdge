"""Memo and tear sheet render from the current artifacts with consistent numbers (Steps 13 and 17)."""

import pytest

from quantedge.config import load_config
from quantedge.paths import ARTIFACTS

pytestmark = pytest.mark.skipif(not (ARTIFACTS / "status.json").exists(),
                                reason="run the pipeline first to create artifacts")


def test_tearsheet_and_memo_agree_with_the_evidence():
    from quantedge.decision.evidence import build
    from quantedge.reports.tearsheet import render

    cfg = load_config()
    b = build(cfg)
    assert b is not None
    sheet = render(cfg, b)
    assert f"Rule-engine outcome: {b.verdict.status}" in sheet
    assert f"${b.evidence.return_level_10y * cfg.nav_usd:,.0f}" in sheet
    assert "investment-committee approval" in sheet
    # the once-in-10-years loss must not be smaller than the 99% ES it is reported next to
    assert b.evidence.return_level_10y >= b.evidence.es99_1d
