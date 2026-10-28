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


def _risk_page_with(portfolio: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "pages" / "4_Risk_Dashboard.py"), default_timeout=180)
    at.run()
    box = next(b for b in at.sidebar.selectbox if b.label == "Portfolio")
    box.set_value(portfolio).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_risk_page_checks_another_candidate_live_and_fits_heavy_models_on_request():
    at = _risk_page_with("60/40 benchmark")
    assert any("live check" in h.value for h in at.subheader)
    assert any("breached" in e.value for e in at.error)          # SPY 60% breaches the 40% cap
    button = next(b for b in at.button if "GARCH-FHS" in b.label)
    button.click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert not any("GARCH-FHS and EVT" in b.label for b in at.button)


def test_risk_page_accepts_custom_weights():
    at = _risk_page_with("Custom weights")
    assert any("live check" in h.value for h in at.subheader)
    assert any(n.label == "AGG" for n in at.sidebar.number_input)
