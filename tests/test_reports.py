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


def test_report_tables_use_the_final_weights():
    import json
    import re

    from quantedge.reports import report

    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    out = report.render(load_config())
    assert "Page budget" not in out and "cdn.jsdelivr" not in out        # finished document, no network needed
    assert f"{n['largest_es_share']:.2%}" in out                         # Euler shares of the recommended weights
    assert f"{n['weights']['SPY']:.2%}" in out and "8.50%" not in out    # not the provisional candidate
    assert len(re.findall(r"<svg", out)) == 5 and "Table 16" in out
    assert not re.search(r"<p>\{\{\w+\}\}</p>", out)                     # every placed block exists


def test_memo_page_is_html_with_every_section():
    import json

    from quantedge.reports import final

    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    page = final.memo_page(n)
    assert final.TEAM in page and "<table>" in page and page.count("<h2>") == 5 and "**" not in page and "|--" not in page


def test_pdfs_meet_the_booklet_page_limits():
    from quantedge.paths import ROOT

    pdf = ROOT / "reports" / "QuantEdge_Technical_Report.pdf"
    if not pdf.exists():
        pytest.skip("run scripts/build_pdfs.py first")
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_pdfs", ROOT / "scripts" / "build_pdfs.py")
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    assert 7 <= b.pages(pdf) <= 15
    assert b.pages(ROOT / "reports" / "Investment_Committee_Memo.pdf") == 1
    assert b.pages(ROOT / "reports" / "Executive_Tear_Sheet.pdf") == 1


def test_rarity_never_prints_an_absurd_return_period():
    from quantedge.stress.reverse import rarity, rarity_text

    assert rarity(1e27) == "rarer than once in a million years" and rarity(40.2) == "about once in 40 years"
    assert rarity_text(1e27, 2e6).endswith("even in a crisis") and "in calm markets" in rarity_text(1e27, 40)


def test_judge_facing_documents_name_no_internal_records():
    import json

    from quantedge.paths import ROOT
    from quantedge.reports import final, report

    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    body = report.render(load_config()).split("AI disclosure</h2>")[0]      # only the disclosure section may name them
    for text in (body, final.memo(n), final.tear_sheet(n), readme):
        assert "inputs_lock" not in text and "ai_log" not in text


def test_report_carries_the_ai_disclosure_word_for_word():
    import html
    import re

    from quantedge.paths import ROOT
    from quantedge.reports import report

    source = (ROOT / "AI_DISCLOSURE.md").read_text(encoding="utf-8")
    words = lambda t: " ".join(re.sub(r"[*#]", "", t).split())  # noqa: E731
    assert words(source) == words(html.unescape(re.sub(r"<[^>]+>", " ", report.disclosure_html()))).replace(" :", ":")
