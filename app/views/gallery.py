"""One gallery page per event (built from app/static/events/manifest.json)."""

from __future__ import annotations

import streamlit as st

import content as C
import ui


def render(slug: str) -> None:
    ev = C.event_by_slug(slug)
    if ev is None:
        st.error("Event not found")
        return
    st.html(ui.wrap(ui.masthead(on_home=False) + ui.gallery(ev) + ui.footer(on_home=False)))
