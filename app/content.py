"""All website text in one place.

Text in [square brackets] is a placeholder still waiting for real content. It is rendered as a
visible dashed "TODO" on the site, as in the approved design draft (rivatar-home.html).
Dropdown values come from the shared vocabulary in src/rivatar/vocab.py (one set of English codes for
the form, the synthetic data and the model); only their Hebrew labels are shown here.
"""

from __future__ import annotations

from rivatar import vocab

BRAND = "RIVATAR Productions"

# ------------------------------------------------------------------ navigation
NAV = [  # (label, anchor on the home page)
    ("אירועים", "stories"),
    ("הגישה", "approach"),
    ("שירותים", "services"),
    ("רבקה", "about"),
]
NAV_CTA = ("צרו קשר", "contact")
NAV_LAB = "ML LAB"
MENU_LABEL = "תפריט"

# ------------------------------------------------------------------ hero
# Cover photo: first landscape image of this event (change the slug to change the cover).
HERO_EVENT = "evyatar-rivka"
HERO_TAG = "צילום פתיחה · אווירה רחבה"
HERO_TITLE = "כל אירוע הוא סיפור שמתחיל בפרט אחד"
HERO_LEDE = (
    "הפקת אירועי בוטיק ויוקרה, מחתונות ובר ובת מצווה ועד כנסים, השקות מוצר ואירועי חברה. "
    "קונספט, עיצוב וניהול מלא תחת יד אחת."
)
HERO_SIDE_EVENT = "avigail-nuri"
HERO_SIDE_TAG = "תקריב פרט"
HERO_SIDE_CAPTION = "[כיתוב לתמונה: שם האירוע · מיקום]"
DISCIPLINES = ["חתונות", "בר ובת מצווה", "כנסים", "השקות מוצר", "אירועי חברה"]
DISCIPLINES_LATIN = "Boutique & Luxury Events"

# ------------------------------------------------------------------ stories
STORIES_TITLE = "אירועים נבחרים"
STORIES_LATIN = "Selected Stories"
STORIES_NOTE = "כל אירוע מוצג כסיפור מצולם: שם, מיקום, כמה משפטים, וגלריה ערוכה שמחליפה בין מבט רחב לפרט."
STORY_MORE = "לסיפור המלא"
GALLERY_COUNT = "{n} תמונות בגלריה"
GALLERY_BACK = "חזרה לאירועים"
GALLERY_HINT = "לחיצה על תמונה פותחת אותה בגודל מלא."

# Display names are the only place client names appear on the site. Defaults: first names + type.
# Set "show": False to hide an event. "type": a code from vocab.EVENT_TYPES, or None (shows a TODO).
# Order here = order on the home page and in the gallery navigation.
EVENTS = [
    {"slug": "evyatar-rivka", "name": "Evyatar & Rivka", "type": "wedding",
     "location": "[מיקום]", "desc": "[2–3 משפטים: הקונספט, האווירה, והאתגר ההפקתי שנפתר]", "show": True},
    {"slug": "aaron-bar-mitzvah", "name": "Aaron", "type": "bar_mitzvah",
     "location": "[מיקום]", "desc": "[2–3 משפטים על האירוע ועל מה שהפך אותו לשלכם]", "show": True},
    {"slug": "shaindel-meir", "name": "Shaindel & Meir", "type": None,
     "location": "[מיקום]", "desc": "[2–3 משפטים: הקונספט, האווירה, והאתגר ההפקתי שנפתר]", "show": True},
    {"slug": "avigail-nuri", "name": "Avigail & Nuri", "type": "wedding",
     "location": "[מיקום]", "desc": "[2–3 משפטים: הקונספט, האווירה, והאתגר ההפקתי שנפתר]", "show": True},
    {"slug": "david-bar-mitzvah", "name": "David", "type": "bar_mitzvah",
     "location": "[מיקום]", "desc": "[2–3 משפטים על האירוע ועל מה שהפך אותו לשלכם]", "show": True},
    {"slug": "eden-binyamin", "name": "Eden & Binyamin", "type": "wedding",
     "location": "[מיקום]", "desc": "[2–3 משפטים: הקונספט, האווירה, והאתגר ההפקתי שנפתר]", "show": True},
    {"slug": "bailey-motel", "name": "Bailey & Motel", "type": None,
     "location": "[מיקום]", "desc": "[2–3 משפטים: הקונספט, האווירה, והאתגר ההפקתי שנפתר]", "show": True},
]
EVENT_TYPE_TODO = "[סוג אירוע]"

# English type names for the "Name · Type" display format.
EVENT_TYPES_EN = {
    "wedding": "Wedding", "bar_mitzvah": "Bar Mitzvah", "bat_mitzvah": "Bat Mitzvah",
    "family_event": "Family Event", "product_launch": "Product Launch", "conference": "Conference",
    "corporate_event": "Corporate Event", "business_dinner": "Business Dinner",
}
IMAGE_TAGS = {"wide": "אווירה רחבה", "detail": "פרט", "moment": "רגע", "portrait": "דיוקן / רגע",
              "pano": "פנורמה · חלל האירוע"}

# ------------------------------------------------------------------ approach
APPROACH_TITLE = "הגישה שלנו"
APPROACH_LATIN = "Taste & Precision"
APPROACH_STATEMENT = "אסתטיקה והפקה הן אותה עבודה."
APPROACH_STATEMENT_EM = "כל החלטה עיצובית צריכה להיראות נכון, וגם לעבוד ביום עצמו."
PILLARS = [
    {"latin": "The Eye", "title": "המבט",
     "text": "קונספט, צבע, חומר ואור. בונים לכל אירוע שפה חזותית אחת שעוברת מהרושם הראשון ועד הפרט האחרון על השולחן."},
    {"latin": "The Hand", "title": "הביצוע",
     "text": "לוחות זמנים, ספקים, לוגיסטיקה וצוות בשטח. ניהול של כל השלבים, כדי שביום האירוע תוכלו להיות אורחים בו."},
]

# ------------------------------------------------------------------ services
SERVICES_TITLE = "שירותים"
SERVICES_LATIN = "Services"
SERVICES = [
    {"title": "חתונות", "latin": "Weddings", "tone": "rose",
     "text": "מהקונספט ועד הריקוד האחרון. עיצוב, תכנון והפקה מלאה של יום אחד שמספר את הסיפור שלכם."},
    {"title": "בר ובת מצווה", "latin": "Bar & Bat Mitzvah", "tone": "olive",
     "text": "בהפקה אישית, עם שפה עיצובית שנבנית סביב המשפחה ובקנה מידה שמתאים לכם."},
    {"title": "אירועי חברות", "latin": "Corporate", "tone": "dusk",
     "text": "כנסים, השקות מוצר, אירועי חברה ודינרים עסקיים. שפה חזותית שמשרתת את המותג, וניהול שעומד בלוחות זמנים מורכבים."},
]
ADDONS_LABEL = "שירותים נלווים"
ADDONS = list(vocab.EXTRAS.values())

# ------------------------------------------------------------------ about
ABOUT_LABEL = "אודות"
ABOUT_NAME = "רבקה"
ABOUT_PORTRAIT_TAG = "דיוקן של רבקה"
ABOUT_ROLE = "[תפקיד / תואר]"
ABOUT_BIO = "[פסקת אודות: הרקע של רבקה, מה הביא אותה להפקת אירועים, ומה מייחד את העבודה שלה. אכתוב אותה מתוך החומר שתשלחי]"

# ------------------------------------------------------------------ contact
CONTACT_LATIN = "Begin Your Story"
CONTACT_TITLE = "ספרו לנו על האירוע שלכם"
CONTACT_DETAILS = [("טלפון", "[להשלמה]"), ("אימייל", "[להשלמה]"), ("אינסטגרם", "[להשלמה]")]

FORM = {
    "legend_event": "האירוע",
    "legend_hosting": "אירוח ועיצוב",
    "legend_contact": "פרטים ליצירת קשר",
    "event_type": "סוג האירוע",
    "event_date": "תאריך משוער",
    "guests": "מספר אורחים",
    "guests_placeholder": "10–1,500",
    "region": "אזור",
    "venue_type": "סוג מקום",
    "catering_level": "רמת קייטרינג",
    "design_package": "חבילת עיצוב",
    "extras": "שירותים נוספים",
    "full_name": "שם מלא",
    "phone": "טלפון",
    "email": "אימייל",
    "lead_source": "איך הגעתם אלינו",
    "notes": "כמה מילים על מה שאתם מדמיינים",
    "choose": "בחרו",
    "submit": "שליחה וקבלת הערכה",
    "saved": "תודה! הפנייה נשמרה, ונחזור אליכם בהקדם.",
    "fix_errors": "כמה פרטים דורשים תיקון:",
}
VENUE_BUSINESS_NOTE = " (לאירועים עסקיים בלבד)"

# Validation messages (keys match rivatar.leads.validate_lead)
ERRORS = {
    "event_type": "יש לבחור סוג אירוע.",
    "event_date": "יש לבחור תאריך עתידי, עד 3 שנים מהיום.",
    "guests": f"מספר האורחים צריך להיות בין {vocab.GUESTS_MIN} ל־{vocab.GUESTS_MAX:,}.",
    "region": "יש לבחור אזור.",
    "venue_type": "יש לבחור סוג מקום.",
    "venue_business_only": "משרדי החברה זמינים לאירועים עסקיים בלבד.",
    "catering_level": "יש לבחור רמת קייטרינג.",
    "design_package": "יש לבחור חבילת עיצוב.",
    "full_name": "יש למלא שם מלא (2–80 תווים).",
    "phone": "מספר הטלפון אינו תקין (למשל 050-1234567 או ‎+972 50 123 4567).",
    "email": "כתובת האימייל אינה תקינה.",
    "lead_source": "ערך לא מוכר.",
    "notes": "ההודעה ארוכה מדי (עד 1,000 תווים).",
}

ESTIMATE = {
    "label": "הערכת תקציב ראשונית",
    "tag": "בקרוב",
    "case_empty": "מלאו את הטופס כדי לראות את פרטי האירוע",
    "unavailable_he": "ההערכה תהיה זמינה אחרי שלב ה־ML",
    "unavailable_en": "Estimate available after the ML phase",
    "fine": "טווח משוער לפי הפרטים שמילאתם. נקודת פתיחה לשיחה עם המפיקה, ולא הצעת מחיר.",
}

# ------------------------------------------------------------------ footer
FOOTER_LINE = "RIVATAR Productions · הפקת חתונות, אירועים פרטיים ואירועי חברות"
FOOTER_NAV = [("אירועים", "stories"), ("שירותים", "services"), ("רבקה", "about"), ("צרו קשר", "contact")]

# ------------------------------------------------------------------ ML LAB
LAB_TITLE = "ML LAB"
LAB_LATIN = "Behind the Scenes"
LAB_INTRO = (
    "מאחורי הקלעים של הערכת התקציב. בשלבים הבאים יוצגו כאן הרצת ה־Flow, סטטוס כל שלב, "
    "גרפי EDA, תובנות, חוזה הנתונים, השוואת המודלים וה־Model Card."
)
LAB_SYNTHETIC_NOTE = "הנתונים סינתטיים: המספרים מדגימים את השיטה, ואינם מחירים אמיתיים של RIVATAR."
LAB_STAGES = [  # (stage, description, phase)
    ("Synthetic data", "1,500 אירועים + בעיות איכות מכוונות, seed 42", 1),
    ("Crew 1 · Data", "ניקוי, EDA, תובנות, חוזה נתונים JSON", 2),
    ("Gate · Data contract", "צוות 2 רץ רק אם החוזה עבר", 4),
    ("Crew 2 · ML", "מאפיינים, 3 גרסאות מודל, בחירה לפי CV, Model Card", 3),
    ("Gate · Quality & reproducibility", "MAPE, שחזור, נתונים שלא השתנו", 4),
    ("Publish", "המודל מחובר לטופס באתר", 3),
]

# ------------------------------------------------------------------ helpers
# Hebrew labels per field, straight from the shared vocabulary
LABELS = {
    "event_type": vocab.EVENT_TYPES,
    "region": vocab.REGIONS,
    "venue_type": vocab.VENUE_TYPES,
    "catering_level": vocab.CATERING_LEVELS,
    "design_package": vocab.DESIGN_PACKAGES,
    "lead_source": vocab.LEAD_SOURCES,
    "extras": vocab.EXTRAS,
}


def is_todo(text: str | None) -> bool:
    return bool(text) and text.strip().startswith("[") and text.strip().endswith("]")


def visible_events() -> list[dict]:
    return [e for e in EVENTS if e.get("show", True)]


def event_by_slug(slug: str) -> dict | None:
    return next((e for e in EVENTS if e["slug"] == slug), None)


def event_type_label(event: dict) -> str:
    return vocab.EVENT_TYPES.get(event.get("type") or "", EVENT_TYPE_TODO)


def display_name(event: dict) -> str:
    """Default display format, e.g. 'Avigail & Nuri · Wedding'."""
    t = EVENT_TYPES_EN.get(event.get("type") or "")
    return f"{event['name']} · {t}" if t else event["name"]
