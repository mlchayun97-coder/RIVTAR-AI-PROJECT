"""Shared page plumbing: language from ?lang=, the first-visit intro, page start and end."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

import content as C
import ui

INTRO_COOKIE = "rv_intro"
INTRO_KEY = "rv_intro_seen"  # sessionStorage key

# Runs inside a components.html iframe (same origin as the page). Remembers the intro for this visit in
# sessionStorage (and a cookie, which the server can read locally), removes it at once if this tab has
# already seen it, and lets a click skip it. Every storage call is wrapped: private mode or blocked
# storage must never break the page. If the script never runs, the intro still ends by itself (~2.5 s).
_INTRO_JS = """
<script>
(function () {
  var d;
  try { d = window.parent.document; } catch (e) { return; }
  var el = d.querySelector(".intro");
  var seen = false;
  try { seen = window.parent.sessionStorage.getItem("%(key)s") === "1"; } catch (e) {}
  if (seen && el) { el.remove(); return; }
  try { window.parent.sessionStorage.setItem("%(key)s", "1"); } catch (e) {}
  try { d.cookie = "%(cookie)s=1; path=/; SameSite=Lax"; } catch (e) {}
  if (el) { el.addEventListener("click", function () { el.classList.add("skip"); }); }
})();
</script>""" % {"key": INTRO_KEY, "cookie": INTRO_COOKIE}


def current_lang() -> str:
    return C.normalize_lang(st.query_params.get("lang"))


def ctx_for(path: str) -> ui.Ctx:
    return ui.Ctx(lang=current_lang(), path=path)


def intro_seen() -> bool:
    try:
        return bool(st.context.cookies.get(INTRO_COOKIE))
    except Exception:  # no browser context (tests)
        return True


def should_show_intro(path: str, query: dict, seen: bool) -> bool:
    """Only on the FIRST entry to the home page: never on another page, never when the URL already has a
    parameter (internal links carry intro=0, a language switch carries lang=...), never once seen."""
    return path == "" and not query and not seen


def start(ctx: ui.Ctx, intro: bool = True) -> None:
    """Call first on every page: the intro (first visit to the home page only) and its tiny script."""
    if intro and should_show_intro(ctx.path, dict(st.query_params), intro_seen()):
        st.html(ui.wrap(ctx, ui.intro(ctx)))
        with st.container(key="introjs"):
            components.html(_INTRO_JS, height=0)


def end(ctx: ui.Ctx) -> None:
    st.html(ui.wrap(ctx, ui.page_end(ctx)))
