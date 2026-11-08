"""Streamlit Community Cloud readiness: the committed snapshot, the fallback to it, a lean runtime
(no crewai, no matplotlib, no API key) and a form that never crashes when a lead cannot be saved."""
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
SNAP = ROOT / "deploy" / "snapshot"


def _reqs(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if "==" in line:
            name, ver = line.split("==")
            out[name.strip().lower()] = ver.strip()
    return out


# ---------------------------------------------------------------- the snapshot
def test_snapshot_is_the_live_agent_run_and_small():
    status = json.loads((SNAP / "reports" / "run_status.json").read_text(encoding="utf-8"))
    decision = json.loads((SNAP / "reports" / "model_decision.json").read_text(encoding="utf-8"))
    assert status["status"] == "SUCCEEDED"
    assert "agent" in decision["decided_by"].lower() and decision["reason"]
    assert status["decision"]["chosen_model"] == status["best_model"] == decision["chosen_model"]
    files = [p for p in SNAP.rglob("*") if p.is_file()]
    assert sum(p.stat().st_size for p in files) < 400_000
    assert not any("data" in p.relative_to(SNAP).parts for p in files)  # nothing from data/
    for p in files:
        assert b"sk-" not in p.read_bytes(), p  # no key


def test_snapshot_model_loads_with_the_pinned_scikit_learn():
    import joblib
    import sklearn
    bundle = joblib.load(SNAP / "artifacts" / "model.joblib")
    assert bundle["name"] == json.loads((SNAP / "reports" / "run_status.json").read_text(encoding="utf-8"))["best_model"]
    assert _reqs(APP / "requirements.txt")["scikit-learn"] == sklearn.__version__


# ---------------------------------------------------------------- the fallback
@pytest.fixture
def no_local_run(monkeypatch, tmp_path):
    """Like Streamlit Cloud: no artifacts/ and no reports/ on this machine."""
    from rivatar import config
    monkeypatch.setattr(config, "ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(config, "RUN_STATUS", tmp_path / "reports" / "run_status.json")


def test_without_a_local_run_the_site_reads_the_snapshot(no_local_run):
    from rivatar import published
    run = published.current()
    assert run.snapshot and run.run_status.exists() and run.model_file.exists()


def test_form_estimate_from_the_snapshot(no_local_run):
    from rivatar.estimator import estimate_budget
    from rivatar.leads import event_features
    lead = dict(event_type="wedding", event_date=date.today() + timedelta(days=200), guest_count=250,
                region="jerusalem", venue_type="hall", catering_level="premium", design_package="standard",
                extras=["extra_photography"])
    r = estimate_budget(event_features(lead))
    assert r["status"] == "ok" and r["low_ils"] < r["high_ils"]


def test_ml_lab_shows_the_agent_decision_from_the_snapshot(no_local_run):
    from streamlit.testing.v1 import AppTest
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "import theme\nfrom views import ml_lab\ntheme.inject()\nml_lab.render()\n")
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    assert not at.exception
    html = re.sub(r"<[^>]+>", "", " ".join(str(h.proto.body) for h in at.get("html")))
    assert "Model published" in html and "Model Trainer agent" in html
    assert "published snapshot of the last live run" in html


def test_a_real_run_wins_over_the_snapshot(pipeline):
    from rivatar import published
    assert not published.current().snapshot


# ---------------------------------------------------------------- lean runtime
def test_site_runtime_needs_no_crewai_matplotlib_or_key(tmp_path):
    """Render the pages and estimate a budget in a fresh process with no local run and no key:
    crewai, matplotlib and openai must never be imported."""
    code = f"""
import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]
from streamlit.testing.v1 import AppTest
for call in ["home.render()", "ml_lab.render()", "contact.render()", "about.render()"]:
    at = AppTest.from_string(f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\\nimport theme\\nfrom views import home, ml_lab, contact, about\\ntheme.inject()\\n" + call, default_timeout=60)
    at.run(); assert not at.exception, call
from datetime import date
from rivatar.estimator import estimate_budget
r = estimate_budget(dict(event_type="wedding", event_date=date(2027, 6, 10), guest_count=250, region="jerusalem",
                         venue_type="hall", catering_level="premium", design_package="premium"))
assert r["status"] == "ok", r
bad = [m for m in ("crewai", "matplotlib", "openai", "litellm") if m in sys.modules]
assert not bad, bad
print("OK")
"""
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    env["RIVATAR_OUTPUT_DIR"] = str(tmp_path)  # empty: no artifacts/, no reports/
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr[-2000:]


def test_lean_requirements_match_the_full_ones_and_skip_the_pipeline():
    lean, full = _reqs(APP / "requirements.txt"), _reqs(ROOT / "requirements.txt")
    assert {"streamlit", "pandas", "numpy", "scikit-learn", "joblib", "python-dotenv"} <= set(lean)
    assert not {"crewai", "openai", "matplotlib", "pytest"} & set(lean)
    for name, ver in lean.items():
        assert full[name] == ver, name  # same pins as development and CI


# ---------------------------------------------------------------- leads on a temporary file system
def test_form_does_not_crash_when_the_lead_cannot_be_saved(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    from rivatar import config
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(config, "LEADS_CSV", blocker / "leads.csv")  # parent is a file: saving raises OSError
    script = (f"import sys; sys.path[:0] = [{str(APP)!r}, {str(ROOT / 'src')!r}]\n"
              "import theme\nfrom views import contact\ntheme.inject()\ncontact.render()")
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    at.selectbox(key="f_type").set_value("wedding")
    at.date_input(key="f_date").set_value(date.today() + timedelta(days=200))
    at.number_input(key="f_guests").set_value(250)
    for key, val in (("f_region", "jerusalem"), ("f_venue", "hall"), ("f_catering", "premium"), ("f_design", "standard")):
        at.selectbox(key=key).set_value(val)
    at.text_input(key="f_name").input("Test Lead")
    at.text_input(key="f_phone").input("050-1234567")
    at.text_input(key="f_email").input("test@example.com")
    at.button[0].click().run()
    assert not at.exception
    html = " ".join(str(h.proto.body) for h in at.get("html"))
    assert "save-error" in html  # a clear message instead of a crash
    assert not (blocker / "leads.csv").exists()
