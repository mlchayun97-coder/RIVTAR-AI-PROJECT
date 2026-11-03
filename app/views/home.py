"""Home page: hero, stories, approach, services, about, contact + budget form, footer."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

import content as C
import ui
from rivatar import config, vocab
from rivatar.estimator import estimate_budget
from rivatar.leads import MAX_DAYS_AHEAD, build_record, event_features, save_lead, validate_lead

F = C.FORM


def _select(field: str, label: str, options: dict, key: str, fmt=None):
    return st.selectbox(label, list(options), index=None, placeholder=F["choose"],
                        format_func=fmt or (lambda c: options[c]), key=key)


def _venue_label(code: str) -> str:
    note = C.VENUE_BUSINESS_NOTE if code in vocab.BUSINESS_ONLY_VENUES else ""
    return vocab.VENUE_TYPES[code] + note


def _case_line(lead: dict) -> str:
    parts = [vocab.EVENT_TYPES[lead["event_type"]], f'{int(lead["guest_count"]):,} אורחים',
             vocab.REGIONS[lead["region"]]]
    return " · ".join(parts)


def contact_form() -> None:
    today = date.today()
    with st.form("inquiry", border=False):
        st.html(ui.legend(F["legend_event"], first=True))
        a, b = st.columns(2)
        with a:
            event_type = _select("event_type", F["event_type"], vocab.EVENT_TYPES, "f_type")
            guests = st.number_input(F["guests"], min_value=vocab.GUESTS_MIN, max_value=vocab.GUESTS_MAX,
                                     value=None, step=10, placeholder=F["guests_placeholder"], key="f_guests")
        with b:
            event_date = st.date_input(F["event_date"], value=None, min_value=today,
                                       max_value=today + timedelta(days=MAX_DAYS_AHEAD), format="DD/MM/YYYY",
                                       key="f_date")
            region = _select("region", F["region"], vocab.REGIONS, "f_region")
        venue = _select("venue_type", F["venue_type"], vocab.VENUE_TYPES, "f_venue", fmt=_venue_label)

        st.html(ui.legend(F["legend_hosting"]))
        a, b = st.columns(2)
        with a:
            catering = _select("catering_level", F["catering_level"], vocab.CATERING_LEVELS, "f_catering")
        with b:
            design = _select("design_package", F["design_package"], vocab.DESIGN_PACKAGES, "f_design")
        extras = st.pills(F["extras"], list(vocab.EXTRAS), selection_mode="multi",
                          format_func=lambda c: vocab.EXTRAS[c], key="f_extras")

        st.html(ui.legend(F["legend_contact"]))
        a, b = st.columns(2)
        with a:
            name = st.text_input(F["full_name"], max_chars=80, autocomplete="name", key="f_name")
            email = st.text_input(F["email"], max_chars=120, autocomplete="email", key="f_email")
        with b:
            phone = st.text_input(F["phone"], max_chars=20, placeholder="050-1234567", autocomplete="tel",
                                  key="f_phone")
            source = _select("lead_source", F["lead_source"], vocab.LEAD_SOURCES, "f_source")
        notes = st.text_area(F["notes"], max_chars=1000, key="f_notes")
        submitted = st.form_submit_button(F["submit"])

    if submitted:
        lead = {"event_type": event_type, "event_date": event_date, "guest_count": guests, "region": region,
                "venue_type": venue, "catering_level": catering, "design_package": design,
                "extras": extras or [], "full_name": name, "phone": phone, "email": email,
                "lead_source": source, "notes": notes}
        errors = validate_lead(lead, today=today)
        if errors:
            st.session_state.pop("last_case", None)
            st.session_state.pop("last_estimate", None)
            st.html(ui.messages(errors=[C.ERRORS[k] for k in dict.fromkeys(errors.values())]))
        else:
            estimate = estimate_budget(event_features(lead))
            save_lead(build_record(lead, estimate), config.LEADS_CSV)
            st.session_state["last_case"] = _case_line(lead)
            st.session_state["last_estimate"] = estimate
            st.html(ui.messages(ok=F["saved"]))

    st.html(ui.estimate_box(st.session_state.get("last_case"), st.session_state.get("last_estimate")))


def render() -> None:
    st.html(ui.wrap(ui.masthead(on_home=True) + ui.hero() + ui.stories() + ui.approach()
                    + ui.services() + ui.about()))
    with st.container(key="contact"):
        head, form = st.columns([4, 7], gap="large")
        with head:
            st.html(ui.wrap(ui.contact_head()))
        with form:
            contact_form()
    st.html(ui.wrap(ui.footer(on_home=True)))
