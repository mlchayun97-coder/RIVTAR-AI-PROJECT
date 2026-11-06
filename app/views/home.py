"""Home: split-screen opening, selected projects, contact band, footer."""

from __future__ import annotations

from html import escape

import streamlit as st

import content as C
import ui
from views import common


def render() -> None:
    ctx = common.ctx_for("")
    common.start(ctx)
    selected = C.projects()[:3]
    strip = f"""
<section class="sec">
  <div class="sec-head"><h2>{escape(ctx.t("home.selected"))}</h2>
    <a class="link-line" href="{ctx.href("projects")}" target="_self">{escape(ctx.t("home.all_projects"))}</a></div>
</section>
{ui.covers(ctx, selected)}"""
    st.html(ui.wrap(ctx, ui.masthead(ctx, "home") + ui.home_top(ctx) + strip))
    common.end(ctx)
