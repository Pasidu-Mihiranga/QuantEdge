"""Memo and tear sheet render from the current artifacts with consistent numbers (Steps 13 and 17)."""

import pytest

from quantedge.config import load_config
from quantedge.paths import ARTIFACTS

pytestmark = pytest.mark.skipif(not (ARTIFACTS / "decision_numbers.json").exists(),
                                reason="run the pipeline first to create artifacts")


def test_memo_and_tear_sheet_state_the_final_numbers():
    import json

    from quantedge.reports import final

    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    memo, sheet = final.memo(n), final.tear_sheet(n)
    for text in (memo, sheet):
        assert f"{n['expected_return']:.2%}" in text and f"{n['objective']['required_return']:.2%}" in text
        assert final.money(n["risk"]["worst_crisis_loss"] * n["nav_usd"]) in text
        assert "REJECT" not in text or n["verdict"].startswith("REJECT")
    assert "accepts the mandate" in memo if n["verdict"] == "ACCEPT" else True
    assert "tax" in memo.lower() and len(memo.split()) < 520          # one page, and the tax condition is stated


def test_memo_wording_follows_the_verdict():
    import json

    from quantedge.reports import final

    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    assert "adjusts the risk limit" in final.headline({**n, "verdict": "ADJUST THE RISK LIMIT"})
    assert "rejects the mandate" in final.headline({**n, "verdict": "REJECT"})


def test_report_keeps_team_narrative_and_includes_generated_tables(tmp_path, monkeypatch):
    from quantedge.reports import report

    monkeypatch.setattr(report, "NARRATIVE", tmp_path / "narrative")
    report.ensure_narrative()
    mine = tmp_path / "narrative" / "00_executive_summary.md"
    mine.write_text("We recommend the bond-led allocation, subject to committee approval.", encoding="utf-8")
    report.ensure_narrative()                       # a re-run must not overwrite the team's text
    assert "We recommend" in mine.read_text(encoding="utf-8")
    html_out = report.render(load_config())
    assert "We recommend the bond-led allocation" in html_out
    assert "One-shot final test" in html_out and "Assumptions and limitations" in html_out
    assert html_out.count("class='team'") == len(report.SECTIONS) - 1


def test_md_to_html_escapes_and_formats():
    from quantedge.reports.report import md_to_html

    out = md_to_html("A **bold** <script> line\n\n- one\n- two")
    assert "<b>bold</b>" in out and "&lt;script&gt;" in out and "<li>two</li>" in out
