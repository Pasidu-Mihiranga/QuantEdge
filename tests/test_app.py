"""Smoke test: every app page runs without exceptions on the current artifacts (Step 15 §5)."""

from pathlib import Path

import pytest

from quantedge.paths import ARTIFACTS, ROOT

APP = ROOT / "app"
PAGES = [APP / "Home.py", *sorted((APP / "pages").glob("*.py"))]

pytestmark = pytest.mark.skipif(not (ARTIFACTS / "status.json").exists(),
                                reason="run the pipeline first to create artifacts")


@pytest.mark.parametrize("page", PAGES, ids=lambda p: Path(p).stem)
def test_page_runs(page):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(page), default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_app_never_imports_torch():
    for f in APP.rglob("*.py"):
        assert "import torch" not in f.read_text(encoding="utf-8"), f
