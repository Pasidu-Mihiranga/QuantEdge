"""Chart colours for the active light or dark theme, so every page draws with the same meaning per colour.

Rules (doc: the app audit): the recommendation in the accent blue, everything else grey; red only for a loss or a broken
limit, green only for a gain or a limit met; tail measures in one hue, worse is stronger. The theme itself is in
.streamlit/config.toml; these are the same colours for Altair, which does not read the theme's status colours.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class Palette:
    accent: str          # the recommendation
    grey: str            # every other portfolio or series
    ink: str             # text drawn inside charts
    muted: str           # secondary labels
    neutral: str         # the middle of a diverging scale
    good: str
    warn: str
    crit: str
    deep: str            # a second, stronger accent (the scenario, the worst tail)
    tail: tuple[str, str, str]   # VaR, ES, EVT: worse is stronger
    ramp: tuple[str, ...]        # one hue, strongest first: the funds of one portfolio, largest first


LIGHT = Palette(accent="#1F5FAE", grey="#A3ABB5", ink="#1D2733", muted="#5B6573", neutral="#F4F6F8",
                good="#0D7A2F", warn="#A15C00", crit="#B42318", deep="#1F3F73",
                tail=("#9EC1EA", "#4F86C6", "#1F3F73"),
                ramp=("#1F5FAE", "#4F86C6", "#6FA0DB", "#9EC1EA", "#BBD3F0", "#D6E4F6", "#E8EFF9"))
DARK = Palette(accent="#5B9BF0", grey="#5E6976", ink="#E6EAF0", muted="#9AA4B2", neutral="#1E2733",
               good="#3FB46A", warn="#E59A3A", crit="#F0705F", deep="#A6C8F8",
               tail=("#2D4E7E", "#4F86C6", "#A6C8F8"),
               ramp=("#7FB0F5", "#5B9BF0", "#4279C0", "#3567A3", "#2B5486", "#22426B", "#1C3352"))


def palette() -> Palette:
    """The palette for the viewer's theme (light when it is not known yet, as on the first run of a session)."""
    try:
        return DARK if st.context.theme.type == "dark" else LIGHT
    except Exception:        # bare mode and tests have no browser theme
        return LIGHT
