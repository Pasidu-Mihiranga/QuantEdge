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
    assert "Rule-engine outcome" in html_out and "Assumptions and limitations" in html_out
    assert html_out.count("class='team'") == len(report.SECTIONS) - 1


def test_md_to_html_escapes_and_formats():
    from quantedge.reports.report import md_to_html

    out = md_to_html("A **bold** <script> line\n\n- one\n- two")
    assert "<b>bold</b>" in out and "&lt;script&gt;" in out and "<li>two</li>" in out
