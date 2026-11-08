"""The Streamlit app imports cleanly, every page renders in both languages, and the form logic works."""

import importlib
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(ROOT / "scripts"))

from rivatar import vocab  # noqa: E402
from rivatar.estimator import estimate_budget  # noqa: E402
from rivatar.leads import LEAD_FIELDS, build_record, normalize_phone, save_lead, validate_lead  # noqa: E402
from translate_content import flatten  # noqa: E402

CONTENT = APP / "content"


def test_app_modules_import():
    for name in ("content", "theme", "ui", "views.common", "views.home", "views.projects", "views.about",
                 "views.services", "views.contact", "views.ml_lab", "streamlit_app"):
        importlib.import_module(name)


# ---------------------------------------------------------------- content
def test_en_and_he_have_the_same_keys():
    en = flatten(json.loads((CONTENT / "en.json").read_text(encoding="utf-8")))
    he = flatten(json.loads((CONTENT / "he.json").read_text(encoding="utf-8")))
    assert set(en) == set(he)


def test_form_vocabulary_is_translated_in_both_languages():
    import content as C
    for lang in ("en", "he"):
        for code in vocab.EVENT_TYPES:
            assert C.t(f"event_types.{code}", lang) != f"event_types.{code}"
        for field, codes in (("region", vocab.REGIONS), ("venue_type", vocab.VENUE_TYPES),
                             ("catering_level", vocab.CATERING_LEVELS), ("design_package", vocab.DESIGN_PACKAGES),
                             ("lead_source", vocab.LEAD_SOURCES)):
            for code in codes:
                assert C.t(f"options.{field}.{code}", lang) != f"options.{field}.{code}"
        for code in vocab.EXTRAS:
            assert C.t(f"extras.{code}", lang) != f"extras.{code}"
    assert C.t("errors.guests", "he", min=10, max="1,500").count("10") == 1


def test_hebrew_falls_back_to_english(monkeypatch):
    import content as C
    monkeypatch.setattr(C, "strings", lambda lang: {"en": {"a": {"b": "hello"}}, "he": {}}[lang])
    assert C.t("a.b", "he") == "hello"
    assert C.t("missing.key", "he") == "missing.key"


def test_projects_use_folder_spelling_and_shared_codes():
    import content as C
    names = {p["slug"]: p["name"]["en"] for p in C.projects()}
    assert names == {"evyatar-rivka": "Evyatar & Rivka", "avigail-nuri": "Avigail & Nuri", "aaron-bar-mitzvah": "Aaron",
                     "eden-binyamin": "Eden & Binyamin", "bailey-motel": "Bailey & Motel", "david-bar-mitzvah": "David",
                     "shaindel-meir": "Shaindel & Meir"}
    for p in C.projects():
        assert p["event_type"] in vocab.EVENT_TYPES
        assert p["text"]["en"] and p["text"]["he"]
        assert 35 <= len(p["text"]["en"].split()) <= 75
        assert p["cover"]["photo"]


def test_palettes_are_valid_and_marked_with_their_source():
    import content as C
    import ui
    for p in C.projects():
        pal = p.get("palette")
        if not pal:
            continue
        assert len(pal["colors"]) == 4 and all(ui.HEX.fullmatch(c) for c in pal["colors"]), p["slug"]
        assert pal["photo"], p["slug"]
        assert p.get("palette_source") in ("designer", "extracted"), p["slug"]


def test_project_with_two_venues_lists_both():
    import content as C
    import ui
    david = C.project("david-bar-mitzvah")
    assert C.venues(david["location"], "en") == ["Psagot Winery", "Emil Botta, Jerusalem"]
    body = ui.project_body(ui.Ctx("en"), david)
    assert ">Venues<" in body and ">Psagot Winery<" in body and ">Emil Botta, Jerusalem<" in body
    assert "Psagot Winery" in ui.cover(ui.Ctx("en"), david) and "Emil Botta" not in ui.cover(ui.Ctx("en"), david)
    assert ">מקומות<" in ui.project_body(ui.Ctx("he"), david)


def test_every_referenced_photo_is_exported():
    import content as C
    import ui
    for proj in C.projects():
        refs = [proj["cover"], proj["hero"], proj.get("palette") or {}] + [p for c in proj["chapters"] for p in c["photos"]]
        for ref in refs:
            if not ref.get("photo"):
                continue
            entry = ui.photo_entry(proj["slug"], ref["photo"])
            assert entry, (proj["slug"], ref["photo"])
            for w in entry["sizes"]:
                assert (APP / "static" / "projects" / proj["slug"] / f"{entry['base']}-{w}.jpg").exists()


def test_every_gallery_photo_has_alt_text_without_names():
    import content as C
    import ui
    for proj in C.projects():
        names = {w for lang in ("en", "he") for w in re.split(r"\W+", proj["name"][lang]) if len(w) > 2}
        for photo in (p for c in proj["chapters"] for p in c["photos"]):
            alt = photo.get("alt") or {}
            assert alt.get("en") and alt.get("he"), (proj["slug"], photo["photo"])
            words = set(re.split(r"\W+", alt["en"] + " " + alt["he"]))
            assert not names & words, (proj["slug"], photo["photo"], names & words)
        body = ui.project_body(ui.Ctx("he"), proj)
        assert 'alt=""' not in body.split('id="gallery"', 1)[-1].split("</section>", 1)[0], proj["slug"]


def test_gallery_never_repeats_the_hero_photo():
    import content as C
    import ui
    for proj in C.projects():
        hero = ui.media()["projects"][proj["slug"]][proj["hero"]["photo"]]["base"]
        body = ui.project_body(ui.Ctx("en"), proj)
        assert f"/{hero}-" not in body.split('id="gallery"', 1)[-1].split("</section>", 1)[0], proj["slug"]


def test_palette_block_shows_swatches_without_hex_labels():
    import ui
    proj = {"slug": "x", "palette": {"colors": ["#1E1A24", "#2F2548", "#B69785", "red;}</style>"], "photo": None}}
    html = ui.palette_block(ui.Ctx("en"), proj)
    assert html.count('<span style="background:#') == 3  # the invalid value is skipped
    assert ">#" not in html  # colours are never printed as text
    assert ui.palette_block(ui.Ctx("en"), {"slug": "x"}) == ""


def test_contact_details_everywhere():
    import ui
    from views import contact
    for lang, address in (("en", "3 Raoul Wallenberg St, Jerusalem"), ("he", "ראול ולנברג 3, ירושלים")):
        ctx = ui.Ctx(lang)
        for html in (ui.footer(ctx), contact.letter_head(ctx)):
            assert 'href="mailto:rivka@rivatar-pro.com"' in html
            assert 'href="tel:+972586968388"' in html and ">058-696-8388<" in html
            assert 'href="https://wa.me/972586968388"' in html
            assert address in html
        foot = ui.footer(ctx)
        assert foot.count("https://wa.me/972586968388") == 3  # footer link, footer icon, floating button
        assert ctx.t("footer.privacy") not in foot and ctx.t("footer.terms") not in foot


def test_ui_escapes_and_marks_todo():
    import ui
    assert 'class="todo"' in ui.txt("[phone]")
    assert "&lt;script&gt;" in ui.txt("<script>")
    ctx = ui.Ctx("he", "projects")
    assert ctx.href("contact") == "/contact?lang=he"
    assert ui.Ctx("en", "").href("projects") == "/projects"
    assert ui.Ctx("he", "about").href("about", lang="en") == "/about?lang=en"
    assert "est-pending" in ui.estimate_box(ui.Ctx(), None, estimate_budget({}))


def test_language_switch_keeps_the_page():
    import ui
    html = ui.masthead(ui.Ctx("en", "project-evyatar-rivka"), "projects")
    assert 'href="/project-evyatar-rivka?lang=he"' in html
    html = ui.masthead(ui.Ctx("he", "contact"), "contact")
    assert 'href="/contact?lang=en"' in html and 'aria-current="page"' in html


# ---------------------------------------------------------------- pages render in both languages
SLUGS = [p.stem for p in sorted((CONTENT / "projects").glob("*.json"))]
PAGES = (["home.render()", "projects.render_index()", "about.render()", "services.render()", "contact.render()",
          "ml_lab.render()"] + [f"projects.render_project({slug!r})" for slug in SLUGS])
PLACEHOLDER = re.compile(r">\s*\[[^<\]]*\]\s*<")


@pytest.mark.parametrize("lang", ["en", "he"])
@pytest.mark.parametrize("call", PAGES)
def test_every_page_renders_in_both_languages(call, lang):
    from streamlit.testing.v1 import AppTest
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "import streamlit as st\n"
              f"st.query_params['lang'] = {lang!r}\n"
              "import theme\nfrom views import home, projects, about, services, contact, ml_lab\n"
              "theme.inject()\n" + call)
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    assert not at.exception
    html = " ".join(str(h.proto.body) for h in at.get("html"))
    assert f'lang="{lang}"' in html
    assert 'class="todo"' not in html and not PLACEHOLDER.search(html), PLACEHOLDER.search(html)
    if lang == "he":
        assert 'dir="rtl"' in html


def test_full_app_runs():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception


def test_contact_empty_submit_shows_errors_and_saves_nothing(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "from rivatar import config\n"
              f"config.LEADS_CSV = __import__('pathlib').Path({str(tmp_path / 'leads.csv')!r})\n"
              "import theme\nfrom views import contact\ntheme.inject()\ncontact.render()")
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    at.button[0].click().run()
    assert not at.exception
    html = " ".join(str(h.proto.body) for h in at.get("html"))
    assert "form-errors" in html
    assert not (tmp_path / "leads.csv").exists()


# ---------------------------------------------------------------- form logic (unchanged from phase 1)
def _lead(**kw):
    base = dict(event_type="wedding", event_date=date.today() + timedelta(days=200), guest_count=250,
                region="jerusalem", venue_type="hall", catering_level="premium", design_package="standard",
                extras=["extra_photography"], full_name="ישראל ישראלי", phone="050-123-4567",
                email="a@b.co", lead_source="instagram", notes="")
    base.update(kw)
    return base


def test_validate_lead_ok_and_errors():
    assert validate_lead(_lead()) == {}
    errs = validate_lead(_lead(event_type=None, guest_count=5, phone="123", email="x", venue_type="company_office",
                               event_date=date.today() - timedelta(days=1)))
    assert set(errs) == {"event_type", "guest_count", "phone", "email", "event_date"}
    assert validate_lead(_lead(venue_type="company_office"))["venue_type"] == "venue_business_only"
    assert validate_lead(_lead(event_type="conference", venue_type="company_office")) == {}


def test_phone_normalisation():
    assert normalize_phone("+972 50 123 4567") == "0501234567"
    assert normalize_phone("02-6251234") == "026251234"
    assert normalize_phone("12345") is None


def test_save_lead_csv(tmp_path):
    rec = build_record(_lead(notes="=HYPERLINK(evil)"), estimate_budget({}))
    path = tmp_path / "leads.csv"
    save_lead(rec, path)
    save_lead(rec, path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == LEAD_FIELDS and len(lines) == 3
    assert "'=HYPERLINK" in lines[1]                 # formula injection neutralised
    assert rec["client_type"] == "private" and rec["extra_photography"] == 1


def test_estimator_stub_contract():
    r = estimate_budget({"event_type": "wedding"})
    assert r["status"] == "unavailable" and r["estimate_ils"] is None
    assert r["message"] == "Estimate available after the ML phase"
