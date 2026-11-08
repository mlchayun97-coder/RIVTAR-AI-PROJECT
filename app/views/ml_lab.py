"""ML LAB: behind-the-scenes page. Placeholder until phase 4 (Flow run, gates, EDA, model comparison)."""

from __future__ import annotations

import json
from html import escape

import streamlit as st

import ui
from rivatar import config
from views import common

STAGE_PHASES = (1, 2, 4, 3, 4, 3)


def _raw_rows() -> int | None:
    if not config.RAW_EVENTS_CSV.exists():
        return None
    with config.RAW_EVENTS_CSV.open(encoding="utf-8") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def stages_html(ctx: ui.Ctx) -> str:
    rows = _raw_rows()
    items = []
    for i, phase in enumerate(STAGE_PHASES, start=1):
        if phase == 1 and rows is not None:
            pill = f'<span class="pill ok">{escape(ctx.t("lab.ready", n=f"{rows:,}"))}</span>'
        elif phase == 1:
            pill = f'<span class="pill">{escape(ctx.t("lab.run_generator"))}</span>'
        else:
            pill = f'<span class="pill">{escape(ctx.t("lab.phase", n=phase))}</span>'
        items.append(f'<li class="lab-stage"><span class="n">{i:02d}</span>'
                     f'<span class="t">{escape(ctx.t(f"lab.stage{i}_t"))}</span>'
                     f'<span class="d">{escape(ctx.t(f"lab.stage{i}_d"))}</span>{pill}</li>')
    return f'<ol class="lab-stages">{"".join(items)}</ol>'


def render() -> None:
    ctx = common.ctx_for("ml-lab")
    common.start(ctx, intro=False)
    head = f"""
<section class="page-head"><h1>{escape(ctx.t("lab.title"))}</h1><p>{escape(ctx.t("lab.intro"))}</p></section>
{stages_html(ctx)}
<p class="lab-note">{escape(ctx.t("lab.synthetic"))}</p>"""
    st.html(ui.wrap(ctx, ui.masthead(ctx, "lab") + head))
    with st.container(key="labinfo"):
        state = ctx.t("lab.key_set") if config.has_openai_key() else ctx.t("lab.key_unset")
        st.caption(ctx.t("lab.llm", model=config.LLM_MODEL, state=state))
        status = config.REPORTS_DIR / "run_status.json"
        if status.exists():
            st.json(json.loads(status.read_text(encoding="utf-8")))
    common.end(ctx)
