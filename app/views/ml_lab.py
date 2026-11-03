"""ML LAB: behind-the-scenes page. Phase 1 placeholder: shows the planned pipeline and what exists.

Phase 4 adds: run-Flow button, --inject-violation demo button, run status, EDA charts, insights,
data contract, model comparison and the Model Card.
"""

from __future__ import annotations

import json
from html import escape

import streamlit as st

import content as C
import ui
from rivatar import config


def _raw_rows() -> int | None:
    if not config.RAW_EVENTS_CSV.exists():
        return None
    with config.RAW_EVENTS_CSV.open(encoding="utf-8") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def stages_html() -> str:
    rows = _raw_rows()
    items = []
    for i, (name, desc, phase) in enumerate(C.LAB_STAGES, start=1):
        if phase == 1 and rows is not None:
            pill = f'<span class="pill ok">ready · {rows:,} rows</span>'
        elif phase == 1:
            pill = '<span class="pill">run data_generator</span>'
        else:
            pill = f'<span class="pill">phase {phase}</span>'
        items.append(f'<li class="lab-stage"><span class="n">{i:02d}</span><span class="t">{escape(name)}</span>'
                     f'<span class="d">{escape(desc)}</span>{pill}</li>')
    return f'<ol class="lab-stages">{"".join(items)}</ol>'


def render() -> None:
    head = f"""
<section class="sec" style="padding-top:clamp(2rem,5vw,4rem)">
  <div class="sec-head"><h2>{escape(C.LAB_TITLE)}</h2><span class="lat">{escape(C.LAB_LATIN)}</span>
    <p class="note">{escape(C.LAB_INTRO)}</p></div>
  {stages_html()}
  <p class="lab-note">{escape(C.LAB_SYNTHETIC_NOTE)}</p>
</section>"""
    st.html(ui.wrap(ui.masthead(on_home=False) + head))

    llm = "configured" if config.has_openai_key() else "not set (offline mode)"
    st.caption(f"LLM: {config.LLM_MODEL} · OpenAI key {llm}")

    status = config.REPORTS_DIR / "run_status.json"
    if status.exists():
        st.json(json.loads(status.read_text(encoding="utf-8")))

    st.html(ui.wrap(ui.footer(on_home=False)))
