"""About: split screen (black-and-white photo with the title, crossfading photos), approach, founder."""

from __future__ import annotations

from html import escape

import streamlit as st

import content as C
import ui
from views import common


def founder(ctx) -> str:
    """The founder section, shown once the role and bio are written (placeholders are never shown)."""
    role, bio = ctx.t("about.founder_role"), ctx.t("about.founder_bio")
    if C.is_todo(bio):
        return ""
    role_html = "" if C.is_todo(role) else ui.txt(role, tag="p", cls="label")
    paras = "".join(ui.txt(p.strip(), tag="p") for p in bio.split("\n\n") if p.strip())  # keep paragraph breaks
    return (f'<section class="sec"><div class="founder"><h3>{escape(ctx.t("about.founder"))}</h3>'
            f'{role_html}{paras}</div></section>')


def render() -> None:
    ctx = common.ctx_for("about")
    common.start(ctx)
    refs = C.site().get("about_photos", [])
    left = refs[0] if refs else {}
    top = f"""
<section class="about-split">
  <div class="about-left">
    {ui.figure(ui.ref_img(left, sizes="(max-width:700px) 100vw, 50vw"), "bw")}
    <div class="about-copy"><h1>{escape(ctx.t("about.title"))}</h1><p>{escape(ctx.t("about.text"))}</p></div>
  </div>
  <div class="about-right">{ui.xfade(ctx, refs[1:] + refs[:1])}</div>
</section>
<section class="sec"><div class="pillars">
  <div><h3>{escape(ctx.t("about.eye_title"))}</h3><p>{escape(ctx.t("about.eye_text"))}</p></div>
  <div><h3>{escape(ctx.t("about.hand_title"))}</h3><p>{escape(ctx.t("about.hand_text"))}</p></div>
</div></section>
"""
    top += founder(ctx)
    st.html(ui.wrap(ctx, ui.masthead(ctx, "about") + top))
    common.end(ctx)
