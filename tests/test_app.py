"""Smoke test: every page of the committee app runs without exceptions on the current artifacts (Step 15 §5)."""

from pathlib import Path

import pytest

from quantedge.paths import ARTIFACTS, ROOT

APP = ROOT / "app"
VIEWS = sorted((APP / "views").glob("*.py"))

pytestmark = pytest.mark.skipif(not (ARTIFACTS / "decision_numbers.json").exists(),
                                reason="run the pipeline (after the freeze tag) to create the decision numbers")


@pytest.mark.parametrize("view", VIEWS, ids=lambda p: Path(p).stem)
def test_page_runs(view):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=180)
    at.run()
    at.switch_page(f"views/{view.name}")
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_every_view_is_in_the_navigation():
    home = (APP / "Home.py").read_text(encoding="utf-8")
    assert all(f"views/{v.name}" in home for v in VIEWS)


def test_no_raw_dollar_pairs_in_markdown():
    # Streamlit reads two $ in one Markdown string as LaTeX; pages must escape them (esc) or use HTML entities.
    for v in VIEWS:
        for line in v.read_text(encoding="utf-8").splitlines():
            if "st.markdown(f\"" in line and line.count("$") >= 2 and "esc(" not in line:
                raise AssertionError(f"{v.name}: unescaped dollar signs in {line.strip()[:80]}")


def test_app_never_imports_torch():
    for f in APP.rglob("*.py"):
        assert "import torch" not in f.read_text(encoding="utf-8"), f
