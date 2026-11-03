"""Shared vocabulary: one set of English codes for the website form, the synthetic data
and the future model. Hebrew labels are for display only (see app/content.py).

Changing a code here changes it everywhere; keep it in sync with the data contract (phase 2).
"""

from __future__ import annotations

# code -> Hebrew label (insertion order = display order)
EVENT_TYPES: dict[str, str] = {
    "wedding": "חתונה",
    "bar_mitzvah": "בר מצווה",
    "bat_mitzvah": "בת מצווה",
    "family_event": "אירוע משפחתי",
    "product_launch": "השקת מוצר",
    "conference": "כנס",
    "corporate_event": "אירוע חברה",
    "business_dinner": "דינר עסקי",
}

# Event types whose client is a business. Others are private clients.
BUSINESS_EVENT_TYPES: frozenset[str] = frozenset(
    {"product_launch", "conference", "corporate_event", "business_dinner"}
)

CLIENT_TYPES: dict[str, str] = {"private": "פרטי", "business": "עסקי"}

REGIONS: dict[str, str] = {
    "jerusalem": "ירושלים",
    "tel_aviv": "תל אביב",
    "center": "מרכז",
    "north": "צפון",
    "south": "דרום",
    "abroad": 'חו"ל',
}

VENUE_TYPES: dict[str, str] = {
    "hall": "אולם",
    "garden": "גן אירועים",
    "hotel": "מלון",
    "outdoor": "לוקיישן חוץ",
    "company_office": "משרדי החברה",
}

# Venue types allowed only for business events.
BUSINESS_ONLY_VENUES: frozenset[str] = frozenset({"company_office"})

CATERING_LEVELS: dict[str, str] = {
    "basic": "בסיסי",
    "premium": "פרימיום",
    "luxury": "יוקרה",
}

DESIGN_PACKAGES: dict[str, str] = {
    "standard": "סטנדרט",
    "premium": "פרימיום",
    "luxury": "יוקרה",
}

# Extra services: boolean columns in the data, chips in the form.
EXTRAS: dict[str, str] = {
    "extra_lighting": "תאורה",
    "extra_photography": "צלמים",
    "extra_music_talent": "מוסיקה וטאלנטים",
    "extra_shuttles": "הסעות",
    "extra_social_promo": "קידום ברשתות",
}

LEAD_SOURCES: dict[str, str] = {
    "instagram": "אינסטגרם",
    "referral": "המלצה",
    "google": "גוגל",
    "facebook": "פייסבוק",
    "returning_client": "לקוח חוזר",
    "vendor_venue": "ספק/מקום",
}

GUESTS_MIN = 10
GUESTS_MAX = 1500


def client_type_for(event_type: str) -> str:
    return "business" if event_type in BUSINESS_EVENT_TYPES else "private"


def venues_for(event_type: str) -> list[str]:
    """Venue codes valid for an event type (company offices: business events only)."""
    if event_type in BUSINESS_EVENT_TYPES:
        return list(VENUE_TYPES)
    return [v for v in VENUE_TYPES if v not in BUSINESS_ONLY_VENUES]
