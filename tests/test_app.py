"""The Streamlit app imports cleanly, renders without exceptions, and the form logic works."""

import importlib
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

from rivatar import vocab  # noqa: E402
from rivatar.estimator import estimate_budget  # noqa: E402
from rivatar.leads import LEAD_FIELDS, build_record, normalize_phone, save_lead, validate_lead  # noqa: E402


def test_app_modules_import():
    for name in ("content", "theme", "ui", "views.home", "views.gallery", "views.ml_lab", "streamlit_app"):
        importlib.import_module(name)


def test_content_uses_shared_vocabulary():
    import content as C
    assert list(C.LABELS["event_type"]) == list(vocab.EVENT_TYPES) and len(vocab.EVENT_TYPES) == 8
    assert C.EVENT_TYPE_TODO == "[סוג אירוע]"
    for e in C.EVENTS:
        assert e["type"] is None or e["type"] in vocab.EVENT_TYPES
    shown = {e["slug"]: e for e in C.EVENTS}
    assert shown["bailey-motel"]["type"] is None and shown["shaindel-meir"]["type"] is None
    assert C.display_name(shown["avigail-nuri"]) == "Avigail & Nuri · Wedding"


def test_ui_renders_todo_and_escapes():
    import ui
    assert 'class="todo"' in ui.txt("[מיקום]")
    assert "&lt;script&gt;" in ui.txt("<script>")
    assert "est-pending" in ui.estimate_box(None, estimate_budget({}))


def test_home_renders_without_exceptions():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception
    assert at.button  # the form submit button exists
    # empty submit -> validation messages, no exception
    at.button[0].click().run()
    assert not at.exception


@pytest.mark.parametrize("call", ["gallery.render('avigail-nuri')", "ml_lab.render()"])
def test_subpages_render_without_exceptions(call):
    from streamlit.testing.v1 import AppTest
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "import theme\nfrom views import gallery, ml_lab\ntheme.inject()\n" + call)
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    assert not at.exception


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
