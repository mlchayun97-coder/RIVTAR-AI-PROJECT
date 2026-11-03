"""Shared page plumbing: language from ?lang=, the first-visit intro, page start and end."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

import content as C
import ui

INTRO_COOKIE = "rv_intro"

# Runs inside a components.html iframe (same origin): marks the intro as seen for this browser session
# and lets a click skip it. If it never runs, the intro still ends by itself after ~2.5 s.
_INTRO_JS = """
<script>
(function () {
  try {
    var d = window.parent.document;
    d.cookie = "%s=1; path=/; SameSite=Lax";
    var el = d.querySelector(".intro");
    if (el) { el.addEventListener("click", function () { el.classList.add("skip"); }); }
  } catch (e) {}
})();
</script>""" % INTRO_COOKIE


def current_lang() -> str:
    return C.normalize_lang(st.query_params.get("lang"))


def ctx_for(path: str) -> ui.Ctx:
    return ui.Ctx(lang=current_lang(), path=path)


def intro_seen() -> bool:
    try:
        return bool(st.context.cookies.get(INTRO_COOKIE))
    except Exception:  # no browser context (tests)
        return True


def start(ctx: ui.Ctx, intro: bool = True) -> None:
    """Call first on every page: the intro (once per browser session) and its tiny script."""
    if intro and not intro_seen():
        st.html(ui.wrap(ctx, ui.intro(ctx)))
        with st.container(key="introjs"):
            components.html(_INTRO_JS, height=0)


def end(ctx: ui.Ctx) -> None:
    st.html(ui.wrap(ctx, ui.page_end(ctx)))
