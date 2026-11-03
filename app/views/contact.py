"""Contact: the inquiry form on a light "letter" that rises out of an envelope.

Streamlit cannot place its widgets inside custom HTML, so the letter IS the form's container
(st.container(key="letter")), styled as paper and animated with CSS; the envelope pocket is drawn in
HTML right after it. After a saved submission the page shows the letter going back into the envelope.
Every animation ends in the visible state, so the form works even when animations do not run.
"""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

import streamlit as st

import content as C
import ui
from rivatar import config, vocab
from rivatar.estimator import estimate_budget
from rivatar.leads import MAX_DAYS_AHEAD, build_record, event_features, save_lead, validate_lead
from views import common

OPTION_FIELDS = ("region", "venue_type", "catering_level", "design_package", "lead_source")


def _select(ctx: ui.Ctx, field: str, codes, key: str, fmt=None):
    return st.selectbox(ctx.t(f"form.{field}"), list(codes), index=None, placeholder=ctx.t("form.choose"),
                        format_func=fmt or (lambda c: ctx.t(f"options.{field}.{c}")), key=key)


def _case_line(ctx: ui.Ctx, lead: dict) -> str:
    return " · ".join([ctx.t(f"event_types.{lead['event_type']}"),
                       f'{int(lead["guest_count"]):,} {ctx.t("estimate.guests_unit")}',
                       ctx.t(f"options.region.{lead['region']}")])


def _error_text(ctx: ui.Ctx, key: str) -> str:
    return ctx.t(f"errors.{key}", min=vocab.GUESTS_MIN, max=f"{vocab.GUESTS_MAX:,}")


def letter_head(ctx: ui.Ctx) -> str:
    info = C.site().get("contact", {})
    parts = []
    for k in ("phone", "email"):
        v = info.get(k, "")
        parts.append(f'<span>{escape(ctx.t("contact." + k))}: {ui.txt(v)}</span>')
    parts.append(f'<a href="{ui.whatsapp_url()}" target="_blank" rel="noopener">{escape(ctx.t("contact.whatsapp"))}</a>')
    return (f'<div class="letter-head"><h1>{escape(ctx.t("contact.title"))}</h1>'
            f'<p>{escape(ctx.t("contact.intro"))}</p><div class="details">{"".join(parts)}</div></div>')


def inquiry_form(ctx: ui.Ctx) -> None:
    today = date.today()
    with st.form("inquiry", border=False):
        st.html(ui.wrap(ctx, f'<p class="legend">{escape(ctx.t("form.legend_event"))}</p>'))
        a, b = st.columns(2)
        with a:
            event_type = st.selectbox(ctx.t("form.event_type"), list(vocab.EVENT_TYPES), index=None,
                                      placeholder=ctx.t("form.choose"),
                                      format_func=lambda c: ctx.t(f"event_types.{c}"), key="f_type")
            guests = st.number_input(ctx.t("form.guests"), min_value=vocab.GUESTS_MIN, max_value=vocab.GUESTS_MAX,
                                     value=None, step=10, placeholder=ctx.t("form.guests_placeholder"), key="f_guests")
        with b:
            event_date = st.date_input(ctx.t("form.event_date"), value=None, min_value=today,
                                       max_value=today + timedelta(days=MAX_DAYS_AHEAD), format="DD/MM/YYYY",
                                       key="f_date")
            region = _select(ctx, "region", vocab.REGIONS, "f_region")

        def venue_label(code: str) -> str:
            note = ctx.t("form.business_only") if code in vocab.BUSINESS_ONLY_VENUES else ""
            return ctx.t(f"options.venue_type.{code}") + note

        venue = _select(ctx, "venue_type", vocab.VENUE_TYPES, "f_venue", fmt=venue_label)

        st.html(ui.wrap(ctx, f'<p class="legend">{escape(ctx.t("form.legend_hosting"))}</p>'))
        a, b = st.columns(2)
        with a:
            catering = _select(ctx, "catering_level", vocab.CATERING_LEVELS, "f_catering")
        with b:
            design = _select(ctx, "design_package", vocab.DESIGN_PACKAGES, "f_design")
        extras = st.pills(ctx.t("form.extras"), list(vocab.EXTRAS), selection_mode="multi",
                          format_func=lambda c: ctx.t(f"extras.{c}"), key="f_extras")

        st.html(ui.wrap(ctx, f'<p class="legend">{escape(ctx.t("form.legend_contact"))}</p>'))
        a, b = st.columns(2)
        with a:
            name = st.text_input(ctx.t("form.full_name"), max_chars=80, autocomplete="name", key="f_name")
            email = st.text_input(ctx.t("form.email"), max_chars=120, autocomplete="email", key="f_email")
        with b:
            phone = st.text_input(ctx.t("form.phone"), max_chars=20, placeholder="050-1234567", autocomplete="tel",
                                  key="f_phone")
            source = _select(ctx, "lead_source", vocab.LEAD_SOURCES, "f_source")
        notes = st.text_area(ctx.t("form.notes"), max_chars=1000, key="f_notes")
        submitted = st.form_submit_button(ctx.t("form.submit"))

    if not submitted:
        return
    lead = {"event_type": event_type, "event_date": event_date, "guest_count": guests, "region": region,
            "venue_type": venue, "catering_level": catering, "design_package": design, "extras": extras or [],
            "full_name": name, "phone": phone, "email": email, "lead_source": source, "notes": notes}
    errors = validate_lead(lead, today=today)
    if errors:
        st.html(ui.wrap(ctx, ui.errors_box(ctx, [_error_text(ctx, k) for k in dict.fromkeys(errors.values())])))
        return
    estimate = estimate_budget(event_features(lead))
    try:
        save_lead(build_record(lead, estimate), config.LEADS_CSV)
    except OSError:
        st.session_state["save_failed"] = True
        st.rerun()
    st.session_state["sent"] = {"case": _case_line(ctx, lead), "estimate": estimate}
    st.session_state.pop("save_failed", None)
    st.rerun()


def render() -> None:
    ctx = common.ctx_for("contact")
    common.start(ctx)
    bg = C.site().get("contact_background", {})
    st.html(ui.wrap(ctx, ui.masthead(ctx, "contact")))
    sent = st.session_state.get("sent")
    with st.container(key="envelope"):
        # not wrapped in .site (which is position:relative): the background must cover the whole envelope area
        st.html(f'<div class="c-bg">{ui.figure(ui.ref_img(bg, sizes="100vw"))}</div>'
                f'<div class="c-side" dir="{ctx.dir}" aria-hidden="true"><span>{escape(ctx.t("contact.side_left"))}</span>'
                f'<span>{escape(ctx.t("contact.side_right"))}</span></div>')
        if sent:
            st.html(ui.wrap(ctx, f"""
<div class="sent" role="status">
  <div class="paper" aria-hidden="true"></div>
  <div class="env" aria-hidden="true"><div class="flap"></div></div>
  <div class="thanks"><h1>{escape(ctx.t("contact.sent_title"))}</h1><p>{escape(ctx.t("contact.sent_text"))}</p></div>
</div>{ui.estimate_box(ctx, sent["case"], sent["estimate"])}"""))
            with st.container(key="again"):
                if st.button(ctx.t("contact.again")):
                    st.session_state.pop("sent", None)
                    st.rerun()
        else:
            if st.session_state.get("save_failed"):
                st.html(ui.wrap(ctx, f'<div class="save-error" role="alert">{escape(ctx.t("form.save_failed"))}</div>'))
            with st.container(key="letter"):
                st.html(ui.wrap(ctx, letter_head(ctx)))
                inquiry_form(ctx)
            st.html(ui.wrap(ctx, '<div class="pocket" aria-hidden="true"></div>'))
        st.html('<div class="c-after"></div>')
    common.end(ctx)
