"""Website leads: validate the contact/budget form and append it to data/leads.csv (gitignored).

Field names and category codes match the synthetic data (rivatar.vocab), so a saved lead can be fed
to the estimator unchanged.
"""

from __future__ import annotations

import csv
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from rivatar import vocab

LEAD_FIELDS = [
    "lead_id", "submitted_at",
    "event_type", "client_type", "event_date", "guest_count", "region", "venue_type",
    "catering_level", "design_package", *vocab.EXTRAS.keys(),
    "full_name", "phone", "email", "lead_source", "notes",
    "estimate_status", "estimate_ils",
]

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MAX_DAYS_AHEAD = 3 * 365
MAX_NOTES = 1000


def normalize_phone(raw: str) -> str | None:
    """Israeli phone -> local digits (e.g. '0501234567'); None if invalid."""
    digits = re.sub(r"[\s\-().]", "", raw or "")
    if digits.startswith("+972"):
        digits = "0" + digits[4:]
    elif digits.startswith("972") and len(digits) >= 11:
        digits = "0" + digits[3:]
    if re.fullmatch(r"0(5\d|[2-4]|[89]|7\d)\d{7}", digits):
        return digits
    return None


def validate_lead(lead: dict, today: date | None = None) -> dict[str, str]:
    """Return {field: error_key}. Empty dict = valid. Error keys match app/content.py ERRORS."""
    today = today or date.today()
    errs: dict[str, str] = {}

    et = lead.get("event_type")
    if et not in vocab.EVENT_TYPES:
        errs["event_type"] = "event_type"

    d = lead.get("event_date")
    if not isinstance(d, date) or d < today or d > today + timedelta(days=MAX_DAYS_AHEAD):
        errs["event_date"] = "event_date"

    g = lead.get("guest_count")
    if not isinstance(g, (int, float)) or isinstance(g, bool) or not (vocab.GUESTS_MIN <= g <= vocab.GUESTS_MAX) \
            or int(g) != g:
        errs["guest_count"] = "guests"

    if lead.get("region") not in vocab.REGIONS:
        errs["region"] = "region"

    v = lead.get("venue_type")
    if v not in vocab.VENUE_TYPES:
        errs["venue_type"] = "venue_type"
    elif et in vocab.EVENT_TYPES and v not in vocab.venues_for(et):
        errs["venue_type"] = "venue_business_only"

    for f, allowed in (("catering_level", vocab.CATERING_LEVELS), ("design_package", vocab.DESIGN_PACKAGES)):
        if lead.get(f) not in allowed:
            errs[f] = f

    name = (lead.get("full_name") or "").strip()
    if not (2 <= len(name) <= 80):
        errs["full_name"] = "full_name"
    if normalize_phone(lead.get("phone") or "") is None:
        errs["phone"] = "phone"
    if not _EMAIL.match((lead.get("email") or "").strip()):
        errs["email"] = "email"
    src = lead.get("lead_source")
    if src not in (None, "") and src not in vocab.LEAD_SOURCES:
        errs["lead_source"] = "lead_source"
    if len(lead.get("notes") or "") > MAX_NOTES:
        errs["notes"] = "notes"
    return errs


def _cell(value) -> str:
    """CSV-safe cell: neutralise spreadsheet formulas (=, +, -, @ at the start)."""
    s = "" if value is None else str(value)
    s = s.replace("\r", " ").replace("\n", " ").strip()
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


def build_record(lead: dict, estimate: dict | None = None, now: datetime | None = None) -> dict:
    """Normalised row for leads.csv (assumes validate_lead passed)."""
    now = now or datetime.now()
    extras = set(lead.get("extras") or [])
    rec = {
        "lead_id": f"LEAD-{now:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        "submitted_at": now.isoformat(timespec="seconds"),
        "event_type": lead["event_type"],
        "client_type": vocab.client_type_for(lead["event_type"]),
        "event_date": lead["event_date"].isoformat(),
        "guest_count": int(lead["guest_count"]),
        "region": lead["region"],
        "venue_type": lead["venue_type"],
        "catering_level": lead["catering_level"],
        "design_package": lead["design_package"],
        **{k: int(k in extras) for k in vocab.EXTRAS},
        "full_name": lead["full_name"].strip(),
        "phone": normalize_phone(lead["phone"]),
        "email": lead["email"].strip().lower(),
        "lead_source": lead.get("lead_source") or "",
        "notes": (lead.get("notes") or "").strip(),
        "estimate_status": (estimate or {}).get("status", ""),
        "estimate_ils": (estimate or {}).get("estimate_ils") or "",
    }
    return rec


def save_lead(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LEAD_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: _cell(record.get(k)) for k in LEAD_FIELDS})


def event_features(lead: dict) -> dict:
    """The part of a lead the estimator sees (no personal details)."""
    extras = set(lead.get("extras") or [])
    return {
        "event_type": lead.get("event_type"),
        "client_type": vocab.client_type_for(lead.get("event_type") or ""),
        "event_date": lead.get("event_date"),
        "guest_count": lead.get("guest_count"),
        "region": lead.get("region"),
        "venue_type": lead.get("venue_type"),
        "catering_level": lead.get("catering_level"),
        "design_package": lead.get("design_package"),
        **{k: int(k in extras) for k in vocab.EXTRAS},
        "lead_source": lead.get("lead_source") or None,
    }
