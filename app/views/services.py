"""Services: an accordion (<details>, no JavaScript) with uppercase serif titles and pill chips."""

from __future__ import annotations

from html import escape

import streamlit as st

import ui
from rivatar import vocab
from views import common

ROWS = ("weddings", "mitzvah", "corporate")


def render() -> None:
    ctx = common.ctx_for("services")
    common.start(ctx)
    rows = []
    for i, key in enumerate(ROWS):
        chips = "".join(f'<span class="chip">{escape(c)}</span>' for c in ctx.t(f"services.chips_{key}").split("|"))
        rows.append(f"""<details{' open' if i == 0 else ''}><summary>{escape(ctx.t(f"services.{key}_title"))}</summary>
  <div class="body"><p>{escape(ctx.t(f"services.{key}_text"))}</p><div class="chips">{chips}</div></div></details>""")
    extras = "".join(f'<span class="chip">{escape(ctx.t(f"extras.{c}"))}</span>' for c in vocab.EXTRAS)
    rows.append(f"""<details><summary>{escape(ctx.t("services.addons_title"))}</summary>
  <div class="body"><p>{escape(ctx.t("services.addons_text"))}</p><div class="chips">{extras}</div></div></details>""")
    head = f"""
<section class="page-head"><h1>{escape(ctx.t("services.title"))}</h1><p>{escape(ctx.t("services.intro"))}</p></section>
<div class="acc">{"".join(rows)}</div>"""
    st.html(ui.wrap(ctx, ui.masthead(ctx, "services") + head))
    common.end(ctx)
