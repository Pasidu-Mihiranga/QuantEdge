"""Smoke test: every page and every technical topic of the committee app runs without exceptions (Step 15 §5)."""

from pathlib import Path

import pytest

from quantedge.paths import ARTIFACTS, ROOT

APP = ROOT / "app"
VIEWS = sorted((APP / "views").glob("*.py"))
TOPICS = ["Data and quality checks", "All risk models, 2008–2022", "Tail risk (EVT) diagnostics",
          "Regimes, risk overlay, copula and FX", "Formulas, conventions and AI disclosure"]

pytestmark = pytest.mark.skipif(not (ARTIFACTS / "decision_numbers.json").exists(),
                                reason="run the pipeline (after the freeze tag) to create the decision numbers")


def _open(page: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=180)
    at.run()
    at.switch_page(page)
    at.run()
    return at


@pytest.mark.parametrize("view", VIEWS, ids=lambda p: Path(p).stem)
def test_page_runs(view):
    at = _open(f"views/{view.name}")
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("topic", TOPICS)
def test_every_technical_topic_runs_from_the_dropdown(topic):
    at = _open("views/assumptions.py")
    at.selectbox(key="tech_topic").select(topic).run()
    assert not at.exception, [e.value for e in at.exception]


def test_every_view_is_in_the_navigation_and_the_app_stays_small():
    home = (APP / "Home.py").read_text(encoding="utf-8")
    assert all(f"views/{v.name}" in home for v in VIEWS)
    assert len(VIEWS) <= 5                      # low cognitive load: five pages, technical detail behind one dropdown


def test_no_raw_dollar_pairs_in_markdown():
    # Streamlit reads two $ in one Markdown string as LaTeX; pages must escape them (esc/say) or use HTML entities.
    for v in VIEWS:
        for line in v.read_text(encoding="utf-8").splitlines():
            if "st.markdown(f\"" in line and line.count("$") >= 2 and "esc(" not in line:
                raise AssertionError(f"{v.name}: unescaped dollar signs in {line.strip()[:80]}")


def test_app_never_imports_torch():
    for f in APP.rglob("*.py"):
        assert "import torch" not in f.read_text(encoding="utf-8"), f
