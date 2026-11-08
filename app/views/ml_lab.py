"""ML LAB: the Flow run behind the budget estimate.

Reads only the files the pipeline writes (reports/, artifacts/), so the page always shows the LAST run:
its status (or where it stopped and why), each step, the agent's decision, the model comparison, the EDA
charts, the insights, the data contract, the Model Card and the run log. Nothing here runs the pipeline.
"""

from __future__ import annotations

import base64
import json
import re
from html import escape

import streamlit as st

import ui
from rivatar import config
from views import common

STAGES = ("generate_raw_data", "run_data_team", "validate_data_contract", "run_ml_team",
          "quality_and_reproducibility_gate", "publish_results")
CHARTS = ("budget_distribution", "budget_by_event_type", "guests_vs_budget", "budget_per_guest_by_month")


def _json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


def _text(path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def t_bdi(ctx: ui.Ctx, key: str, **values) -> str:
    """ctx.t with every value wrapped in <bdi>: mixed Hebrew/English lines keep the right order."""
    marks = {k: f"\uE000{k}\uE000" for k in values}
    out = escape(ctx.t(key, **marks))
    for k, v in values.items():
        out = out.replace(marks[k], f"<bdi>{escape(str(v))}</bdi>")
    return out


# ------------------------------------------------------------------ run status
def stage_states(status: dict) -> list[str]:
    """One of done / passed / failed / stopped / skipped per stage, from run_status.json steps."""
    by = {s["step"]: s for s in status.get("steps", [])}
    out = []
    for name in STAGES:
        s = by.get(name)
        if name == "validate_data_contract" and s:
            out.append("passed" if s.get("result") == "PASSED" else "failed")
        elif name == "quality_and_reproducibility_gate" and s:
            out.append("passed" if s.get("passed") else "failed")
        elif name == "publish_results" and not s and "stop_pipeline" in by:
            out.append("stopped")
        else:
            out.append("done" if s else "skipped")
    return out


def run_html(ctx: ui.Ctx, status: dict | None) -> str:
    if not status:
        return f'<section class="lab-sec"><p class="lab-empty">{escape(ctx.t("lab.no_run"))}</p></section>'
    st_ = status.get("status", "RUNNING")
    meta = t_bdi(ctx, "lab.run_meta", mode=status.get("mode", ""), seed=f'seed {status.get("seed", "")}',
                 at=(status.get("started_at") or "")[:16].replace("T", " ") + " UTC")
    if st_ == "STOPPED":
        items = "".join(f"<li>{escape(v)}</li>" for v in status.get("violations", []))
        body = (f'<p class="lab-stop-gate">{t_bdi(ctx, "lab.stopped_at", gate=status.get("failed_gate") or "")}</p>'
                f'<ul class="lab-violations" dir="ltr">{items}</ul>'
                f'<p>{escape(ctx.t("lab.no_model"))}</p>')
    elif st_ == "SUCCEEDED":
        h = status.get("best_holdout") or {}
        metrics = f"MAE ₪{h.get('mae', 0):,.0f} · MAPE {h.get('mape', 0):.1%} · R² {h.get('r2', 0):.3f}"
        body = "<p>" + t_bdi(ctx, "lab.published", model=status.get("best_model"), metrics=metrics,
                             repro=(status.get("reproducibility") or {}).get("identical")) + "</p>"
    else:
        body = ""
    return f"""
<section class="lab-sec">
  <h2>{escape(ctx.t("lab.run_title"))}</h2>
  <div class="lab-run {st_.lower()}" role="status">
    <p class="lab-run-status">{escape(ctx.t(f"lab.status_{st_}"))}</p>
    <p class="lab-run-meta">{meta}</p>
    {body}
  </div>
</section>"""


def steps_html(ctx: ui.Ctx, status: dict | None) -> str:
    states = stage_states(status) if status else ["skipped"] * len(STAGES)
    items = []
    for i, state in enumerate(states, start=1):
        cls = {"done": "ok", "passed": "ok", "failed": "fail", "stopped": "fail"}.get(state, "skip")
        items.append(f'<li class="lab-stage"><span class="n">{i:02d}</span>'
                     f'<span class="t">{escape(ctx.t(f"lab.stage{i}_t"))}</span>'
                     f'<span class="d">{escape(ctx.t(f"lab.stage{i}_d"))}</span>'
                     f'<span class="pill {cls}">{escape(ctx.t(f"lab.pill_{state}"))}</span></li>')
    return (f'<section class="lab-sec"><h2>{escape(ctx.t("lab.steps_title"))}</h2>'
            f'<ol class="lab-stages">{"".join(items)}</ol></section>')


# ------------------------------------------------------------------ decision + comparison
def _code_spans(text: str) -> str:
    """Escape, then show `name` as code (the agent and the policy rule quote model names that way)."""
    return re.sub(r"`([^`<]+)`", r"<code>\1</code>", escape(text))


def decision_html(ctx: ui.Ctx, d: dict | None) -> str:
    if not d:
        return ""
    check = t_bdi(ctx, "lab.decision_agrees" if d.get("agrees_with_policy_rule") else "lab.decision_differs",
                  rule=d.get("policy_rule_choice", ""))
    rows = [("decision_by", d.get("decided_by", "")), ("decision_chosen", d.get("chosen_model", "")),
            ("decision_reason", d.get("reason", "")), ("decision_policy", d.get("policy", "")),
            ]
    dl = "".join(f'<div><dt class="label">{escape(ctx.t("lab." + k))}</dt><dd dir="auto">{_code_spans(str(v))}</dd></div>'
                 for k, v in rows)
    dl += f'<div><dt class="label">{escape(ctx.t("lab.decision_check"))}</dt><dd>{check}</dd></div>'
    return f"""
<section class="lab-sec" id="decision">
  <h2>{escape(ctx.t("lab.decision_title"))}</h2>
  <p class="lab-q">{escape(ctx.t("lab.decision_q"))}</p>
  <dl class="lab-decision">{dl}</dl>
</section>"""


def comparison_html(ctx: ui.Ctx, comp: dict | None, ev: dict | None, d: dict | None) -> str:
    if not comp:
        return ""
    chosen = (d or {}).get("chosen_model")
    ho = (ev or {}).get("holdout_metrics", {})
    head = "".join(f"<th>{escape(ctx.t('lab.' + k))}</th>" for k in
                   ("col_version", "col_complexity", "col_cv_mae", "col_cv_mape", "col_cv_r2", "col_ho_mae", "col_ho_mape"))
    rows = []
    for name, r in comp["results"].items():
        h = ho.get(name, {})
        mark = f' <span class="pill ok">{escape(ctx.t("lab.chosen"))}</span>' if name == chosen else ""
        rows.append(f'<tr{" class=chosen" if name == chosen else ""}><td><code>{escape(name)}</code>{mark}</td>'
                    f'<td>{r.get("complexity", "")}</td><td>₪{r["cv_mae_mean"]:,.0f}</td><td>{r["cv_mape_mean"]:.1%}</td>'
                    f'<td>{r["cv_r2_mean"]:.3f}</td><td>{"₪" + format(h["mae"], ",.0f") if h else "—"}</td>'
                    f'<td>{format(h["mape"], ".1%") if h else "—"}</td></tr>')
    return (f'<section class="lab-sec"><h2>{escape(ctx.t("lab.compare_title"))}</h2>'
            f'<div class="lab-table" dir="ltr"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')


# ------------------------------------------------------------------ data team outputs
def charts_html(ctx: ui.Ctx) -> str:
    figs = []
    for name in CHARTS:
        p = config.EDA_DIR / f"{name}.png"
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            label = ctx.t(f"lab.chart_{name}")
            figs.append(f'<figure class="lab-chart"><img src="data:image/png;base64,{data}" alt="{escape(label)}" '
                        f'loading="lazy"><figcaption>{escape(label)}</figcaption></figure>')
    if not figs:
        return ""
    return f'<section class="lab-sec"><h2>{escape(ctx.t("lab.eda_title"))}</h2><div class="lab-charts">{"".join(figs)}</div></section>'


def contract_html(ctx: ui.Ctx, c: dict | None) -> str:
    if not c:
        return ""
    meta = t_bdi(ctx, "lab.contract_meta", name=c["contract_name"], version=c["version"], rows=f'{c["row_count"]:,}',
                 cols=len(c["columns"]), sha=c["dataset_sha256"][:12])

    def rule(spec: dict) -> str:
        parts = []
        if spec.get("allowed_values"):
            parts.append(", ".join(spec["allowed_values"]))
        if spec.get("min") is not None or spec.get("max") is not None:
            parts.append(f'{spec.get("min", "")} – {spec.get("max", "")}')
        if spec.get("pattern"):
            parts.append(spec["pattern"])
        if spec.get("unique"):
            parts.append("unique")
        if not spec.get("nullable", True):
            parts.append("not null")
        return " · ".join(parts)

    rows = "".join(f"<tr><td><code>{escape(n)}</code></td><td>{escape(s['dtype'])}</td><td>{escape(rule(s))}</td></tr>"
                   for n, s in c["columns"].items())
    rules = "".join(f"<li><code>{escape(r['name'])}</code>: {escape(r['expression'])}</li>" for r in c.get("rules", []))
    head = "".join(f"<th>{escape(ctx.t('lab.' + k))}</th>" for k in ("col_column", "col_type", "col_rule"))
    return f"""
<section class="lab-sec">
  <h2>{escape(ctx.t("lab.contract_title"))}</h2>
  <p class="lab-run-meta">{meta}</p>
  <div class="lab-table" dir="ltr"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>
  <ul class="lab-rules" dir="ltr">{rules}</ul>
</section>"""


def log_html(ctx: ui.Ctx, log: str) -> str:
    if not log:
        return ""
    lines = "".join(f'<span class="{"dec" if "[agent_decision]" in l else ("bad" if "FAILED" in l or "stop_pipeline" in l else "")}">{escape(l)}</span>\n'
                    for l in log.splitlines())
    return f'<section class="lab-sec"><h2>{escape(ctx.t("lab.log_title"))}</h2><pre class="lab-log" dir="ltr">{lines}</pre></section>'


def _markdown_section(ctx: ui.Ctx, key: str, title_key: str, text: str) -> None:
    if not text:
        return
    st.html(ui.wrap(ctx, f'<section class="lab-sec lab-md-head"><h2>{escape(ctx.t(title_key))}</h2></section>'))
    with st.container(key=key):
        st.markdown(text)


# ------------------------------------------------------------------ page
def render() -> None:
    ctx = common.ctx_for("ml-lab")
    common.start(ctx, intro=False)
    status = _json(config.RUN_STATUS)
    decision = _json(config.MODEL_DECISION) if status and status.get("status") == "SUCCEEDED" else None
    comparison = _json(config.MODEL_COMPARISON) if decision else None
    evaluation = _json(config.EVALUATION) if decision else None
    state = ctx.t("lab.key_set") if config.has_openai_key() else ctx.t("lab.key_unset")
    head = f"""
<section class="page-head"><h1>{escape(ctx.t("lab.title"))}</h1><p>{escape(ctx.t("lab.intro"))}</p>
<p class="lab-run-meta">{t_bdi(ctx, "lab.llm", model=config.LLM_MODEL, state=state)}</p></section>"""
    top = (head + run_html(ctx, status) + steps_html(ctx, status) + decision_html(ctx, decision)
           + comparison_html(ctx, comparison, evaluation, decision) + charts_html(ctx))
    st.html(ui.wrap(ctx, ui.masthead(ctx, "lab") + top))
    if status:
        st.html(ui.wrap(ctx, f'<p class="lab-note">{escape(ctx.t("lab.reports_lang"))}</p>'))
    _markdown_section(ctx, "labinsights", "lab.insights_title", _text(config.INSIGHTS_MD))
    st.html(ui.wrap(ctx, contract_html(ctx, _json(config.DATA_CONTRACT) if status else None)))
    if decision:
        _markdown_section(ctx, "labcard", "lab.card_title", _text(config.MODEL_CARD))
    st.html(ui.wrap(ctx, log_html(ctx, _text(config.RUN_LOG) if status else "")
                    + f'<p class="lab-note">{escape(ctx.t("lab.synthetic"))}</p>'))
    common.end(ctx)
