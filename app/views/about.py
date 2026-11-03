"""About: split screen (black-and-white photo with the title, crossfading photos), approach, founder."""

from __future__ import annotations

from html import escape

import streamlit as st

import content as C
import ui
from views import common


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
<section class="sec"><div class="founder">
  <h3>{escape(ctx.t("about.founder"))}</h3>
  {ui.txt(ctx.t("about.founder_role"), tag="p", cls="label")}
  {ui.txt(ctx.t("about.founder_bio"), tag="p")}
</div></section>"""
    st.html(ui.wrap(ctx, ui.masthead(ctx, "about") + top))
    common.end(ctx)
