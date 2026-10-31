"""Smoke test: every committee and technical page runs without exceptions (Step 15 §5), plus the main controls."""

from pathlib import Path

import pytest

from quantedge.paths import ARTIFACTS, ROOT

APP = ROOT / "app"
VIEWS = sorted((APP / "views").glob("*.py"))
TECHNICAL = sorted((APP / "technical").glob("*.py"))

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


@pytest.mark.parametrize("page", TECHNICAL, ids=lambda p: Path(p).stem)
def test_every_technical_page_runs_from_the_sidebar(page):
    at = _open(f"technical/{page.name}")
    assert not at.exception, [e.value for e in at.exception]


def test_crisis_builder_shows_a_gain_with_a_plus_sign():
    at = _open("views/crises.py")
    for key, lo in {"s_y": -150, "s_o": -60, "s_v": -10, "s_d": -15, "s_c": -50}.items():
        at.slider(key=key).set_value(lo)
    at.toggle(key="s_l").set_value(False).run()
    card = next(m for m in at.metric if m.label in ("Portfolio loss", "Portfolio gain"))
    assert not at.exception and card.label == "Portfolio gain" and card.value.startswith("+$")


@pytest.mark.parametrize("model", ["Cornish-Fisher", "Historical"])
def test_risk_page_warns_only_for_cornish_fisher(model):
    at = _open("views/risk.py")
    at.selectbox(key="model").set_value(model)
    at.select_slider(key="alpha").set_value(0.90).run()
    assert not at.exception and (len(at.warning) > 0) == (model == "Cornish-Fisher")


def test_scorecard_runs_for_both_periods():
    at = _open("views/portfolio.py")
    for period in ["Since 2008", "2023 onwards (unseen test years)"]:
        at.segmented_control(key="pf_kpi_period").set_value(period).run()
        assert not at.exception and any("Sharpe ratio" in str(t.value) for t in at.table)


def test_committee_summary_matches_the_decision_numbers():
    import json
    import sys

    sys.path.insert(0, str(APP))
    from components.pack import summary_html, weights_table

    n = json.loads((ARTIFACTS / "decision_numbers.json").read_text(encoding="utf-8"))
    page = summary_html(n)
    assert n["verdict"] in page and n["decision_date"] in page
    assert weights_table(n)["usd"].sum() == pytest.approx(n["nav_usd"], rel=1e-3)


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


def test_diversification_view_runs_for_every_period():
    at = _open("views/risk.py")
    at.segmented_control(key="risk_view").set_value("Diversification").run()
    for period in at.segmented_control(key="div_period").options:
        at.segmented_control(key="div_period").set_value(period).run()
        assert not at.exception, [e.value for e in at.exception]


def test_crisis_builder_rates_the_agreed_scenario_as_extreme():
    at = _open("views/crises.py")
    badges = [m.value for m in at.markdown if "badge[" in m.value]          # st.badge renders as badge markdown
    assert not at.exception and any("rarer than 1 in 100" in v or "Beyond anything" in v for v in badges)


def test_long_text_becomes_points_and_short_text_stays_a_sentence():
    import sys

    sys.path.insert(0, str(APP))
    from components.ui import points

    assert points("One. Two.") == "One. Two."
    assert points("It fell 2.5% today. Bonds held. **Gold** rose.").count("\n- ") == 2
    assert points("Lead:\n- a\n- b") == "Lead:\n- a\n- b"


def test_pages_do_not_depend_on_the_git_tag():
    # A hosted clone may carry no tags: the app reads 2023+ returns only through ui.returns_to_decision (frozen=True).
    for v in [*VIEWS, *(APP / "technical").glob("*.py")]:
        assert 'load_returns("all"' not in v.read_text(encoding="utf-8"), v.name
