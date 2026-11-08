"""translate_content.py with a fake translator: no API calls, placeholders and TODO markers survive."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import translate_content as tc  # noqa: E402


def fake_translator(calls):
    """Uppercases text, keeps tokens; records what was sent."""
    def translate(items, glossary):
        calls.append(dict(items))
        return {k: "HE:" + v for k, v in items.items()}
    return translate


def _content(tmp_path, en, he=None, hashes=None, project=None):
    d = tmp_path / "content"
    (d / "projects").mkdir(parents=True)
    (d / "en.json").write_text(json.dumps(en, ensure_ascii=False), encoding="utf-8")
    if he is not None:
        (d / "he.json").write_text(json.dumps(he, ensure_ascii=False), encoding="utf-8")
    if hashes is not None:
        (d / tc.HASHES_FILE).write_text(json.dumps(hashes), encoding="utf-8")
    if project:
        (d / "projects" / "p.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
    return d


def test_mask_keeps_placeholders_todos_and_brand():
    masked, kept = tc.mask("Between {min} and {max} at RIVATAR [to be confirmed]")
    assert "{min}" not in masked and "RIVATAR" not in masked and "[to be confirmed]" not in masked
    assert tc.unmask(masked, kept) == "Between {min} and {max} at RIVATAR [to be confirmed]"


def test_translates_only_missing_or_changed_keys(tmp_path):
    en = {"a": "Hello {name}", "b": "Kept", "c": "[TODO only]", "d": "Changed text"}
    he = {"b": "שמור", "d": "ישן"}
    hashes = {"d": tc.sha("Old text")}
    d = _content(tmp_path, en, he, hashes)
    calls = []
    report = tc.run(d, fake_translator(calls))
    sent = {k for c in calls for k in c}
    assert sent == {"a", "d"}                       # b adopted as-is, c is a TODO (copied, not sent)
    out = json.loads((d / "he.json").read_text(encoding="utf-8"))
    assert out["a"].endswith("{name}") and "{name}" in out["a"]
    assert out["b"] == "שמור"
    assert out["c"] == "[TODO only]"
    assert report["rejected"] == []
    # second run: nothing left to translate
    calls.clear()
    tc.run(d, fake_translator(calls))
    assert calls == []


def test_rejects_translation_that_drops_a_placeholder(tmp_path):
    d = _content(tmp_path, {"g": "Between {min} and {max}"}, {})
    report = tc.run(d, lambda items, gl: {k: "בלי סימנים" for k in items})
    assert report["rejected"] == ["g"]
    assert "g" not in json.loads((d / "he.json").read_text(encoding="utf-8"))


def test_project_fields_are_translated_and_glossary_has_names(tmp_path):
    project = {"slug": "p", "name": {"en": "Evyatar & Rivka", "he": "אביתר ורבקה"},
               "text": {"en": "A wedding at DCity.", "he": ""}}
    d = _content(tmp_path, {}, {}, project=project)
    seen = {}

    def translate(items, glossary):
        seen.update(glossary)
        return {k: "HE " + v for k, v in items.items()}

    tc.run(d, translate)
    out = json.loads((d / "projects" / "p.json").read_text(encoding="utf-8"))
    assert out["text"]["he"].startswith("HE ") and "DCity" in out["text"]["he"]
    assert seen["Evyatar & Rivka"] == "אביתר ורבקה" and seen["RIVATAR"] == "RIVATAR"


def test_dry_run_calls_nothing(tmp_path):
    d = _content(tmp_path, {"a": "Hi"}, {})
    report = tc.run(d, None, dry_run=True)
    assert report["site"] == ["a"]
    assert json.loads((d / "he.json").read_text(encoding="utf-8")) == {}
