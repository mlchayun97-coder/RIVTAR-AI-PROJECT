"""Projects: the cover grid, and one page per project."""

from __future__ import annotations

from html import escape

import streamlit as st

import content as C
import ui
from views import common


def render_index() -> None:
    ctx = common.ctx_for("projects")
    common.start(ctx)
    head = f"""
<section class="page-head">
  <h1>{escape(ctx.t("projects.title"))}</h1>
  <p>{escape(ctx.t("projects.intro"))}</p>
</section>"""
    st.html(ui.wrap(ctx, ui.masthead(ctx, "projects") + head + ui.covers(ctx, C.projects())))
    common.end(ctx)


def render_project(slug: str) -> None:
    ctx = common.ctx_for(ui.project_path(slug))
    common.start(ctx)
    proj = C.project(slug)
    if proj is None:
        st.html(ui.wrap(ctx, ui.masthead(ctx, "projects", solid=True)))
        st.error("Project not found")
        return
    st.html(ui.wrap(ctx, ui.masthead(ctx, "projects") + ui.project_hero(ctx, proj) + ui.project_body(ctx, proj)))
    common.end(ctx)
