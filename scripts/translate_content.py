"""Draft missing Hebrew text with the OpenAI API (run by hand, never by the website).

What it translates
- app/content/en.json -> app/content/he.json (same keys)
- every {"en": ..., "he": ...} field in app/content/projects/*.json whose "he" is empty

Only keys that are MISSING in Hebrew, or whose English text CHANGED since the last run, are sent.
A hash of the English source per key is kept in app/content/he.hashes.json. Hebrew that exists without a
recorded hash (written by hand, or taken from rivatar-home.html / the proposal) is adopted as-is and
never overwritten unless its English source changes later.

Safety
- {placeholders}, [TODO markers] and brand names are masked before sending and verified afterwards;
  a translation that loses one is rejected and the key stays in English (the site falls back to it).
- A short glossary keeps names consistent (RIVATAR, venues, event names).
- The API key comes from .env (python-dotenv) and is never printed. The model comes from RIVATAR_LLM_MODEL.

Usage
    python scripts/translate_content.py --dry-run     # list what would be translated, no API call
    python scripts/translate_content.py               # translate and write he.json / project files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CONTENT_DIR = ROOT / "app" / "content"
HASHES_FILE = "he.hashes.json"

# Terms that must come out exactly like this in Hebrew.
BASE_GLOSSARY = {
    "RIVATAR": "RIVATAR",
    "RIVATAR PRODUCTIONS": "RIVATAR PRODUCTIONS",
    "DCity": "DCity",
    "Olmaya": "עולמיה",
    "Terasa": "טרסה",
    "Kadma": "קדמא",
    "Psagot Winery": "יקב פסגות",
    "Emil Botta": "אמיל בוטא",
    "ML Lab": "ML Lab",
    "Model Card": "Model Card",
    "WhatsApp": "WhatsApp",
}
KEEP_LATIN = ("RIVATAR PRODUCTIONS", "RIVATAR", "DCity", "ML Lab", "Model Card", "WhatsApp", "Flow", "EDA",
              "JSON", "CV", "MAPE", "seed")

Translator = Callable[[dict[str, str], dict[str, str]], dict[str, str]]

_TOKEN = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}|\[[^\[\]]+\]")


# ---------------------------------------------------------------- helpers
def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def flatten(tree: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in tree.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        elif isinstance(v, str):
            out[key] = v
    return out


def unflatten(flat: dict[str, str]) -> dict:
    tree: dict = {}
    for key, value in flat.items():
        node = tree
        *parents, last = key.split(".")
        for p in parents:
            node = node.setdefault(p, {})
        node[last] = value
    return tree


def is_todo(text: str) -> bool:
    t = text.strip()
    return t.startswith("[") and t.endswith("]") and t.count("[") == 1


def mask(text: str) -> tuple[str, list[str]]:
    """Replace {placeholders}, [TODO] segments and Latin brand terms with numbered tokens ⟦n⟧."""
    kept: list[str] = []

    def keep(m: re.Match) -> str:
        kept.append(m.group(0))
        return f"⟦{len(kept) - 1}⟧"

    out = _TOKEN.sub(keep, text)
    for term in KEEP_LATIN:
        out = re.sub(rf"(?<![\w⟦]){re.escape(term)}(?![\w⟧])", keep, out)
    return out, kept


def unmask(text: str, kept: list[str]) -> str:
    for i, original in enumerate(kept):
        text = text.replace(f"⟦{i}⟧", original)
    return text


def tokens_ok(source_masked: str, translated: str, kept: list[str]) -> bool:
    want = sorted(re.findall(r"⟦\d+⟧", source_masked))
    got = sorted(re.findall(r"⟦\d+⟧", translated))
    return want == got and source_masked.count("|") == translated.count("|")


# ---------------------------------------------------------------- translators
SYSTEM = (
    "You translate website text for RIVATAR, a boutique event-production company, from English to natural, "
    "edited Israeli Hebrew. Warm, precise and understated; no marketing clichés. Address readers in plural "
    "(אתם). Keep every token like ⟦0⟧ exactly as is, in a sensible position. Keep '|' separators and their count. "
    "Use the glossary exactly. Do not add facts. Return a JSON object with exactly the same keys."
)


def openai_translator(model: str) -> Translator:
    from openai import OpenAI  # imported lazily: tests never need it

    client = OpenAI()  # reads OPENAI_API_KEY from the environment (loaded from .env by rivatar.config)

    def translate(items: dict[str, str], glossary: dict[str, str]) -> dict[str, str]:
        gl = "\n".join(f"{en} => {he}" for en, he in glossary.items())
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": f"Glossary:\n{gl}\n\nTranslate the values:\n"
                                                  + json.dumps(items, ensure_ascii=False, indent=1)}],
        )
        return json.loads(resp.choices[0].message.content or "{}")

    return translate


# ---------------------------------------------------------------- jobs
def project_fields(proj: dict, path: str = "") -> list[tuple[str, dict]]:
    """All {"en": str, "he": ...} dicts inside a project, with a stable path."""
    found: list[tuple[str, dict]] = []
    if isinstance(proj, dict):
        if isinstance(proj.get("en"), str) and set(proj) <= {"en", "he"}:
            return [(path, proj)]
        for k, v in proj.items():
            found += project_fields(v, f"{path}.{k}" if path else k)
    elif isinstance(proj, list):
        for i, v in enumerate(proj):
            found += project_fields(v, f"{path}[{i}]")
    return found


def build_glossary(projects: dict[str, dict]) -> dict[str, str]:
    gl = dict(BASE_GLOSSARY)
    for proj in projects.values():
        name = proj.get("name", {})
        if name.get("en") and name.get("he"):
            gl[name["en"]] = name["he"]
    return gl


def plan(en: dict[str, str], he: dict[str, str], hashes: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """Keys to translate, and hashes to record for Hebrew that is adopted as-is."""
    todo, adopt = [], {}
    for key, src in en.items():
        h = sha(src)
        if key in he and he[key]:
            if key not in hashes:
                adopt[key] = h            # hand-written / seeded Hebrew: keep it
            elif hashes[key] != h:
                todo.append(key)          # English changed since it was translated
        else:
            todo.append(key)
    return todo, adopt


def translate_keys(sources: dict[str, str], translator: Translator, glossary: dict[str, str],
                   batch: int = 40) -> tuple[dict[str, str], list[str]]:
    """Translate {key: english}. TODO-only values are copied. Returns (results, rejected keys)."""
    results, rejected = {}, []
    pending: dict[str, tuple[str, list[str]]] = {}
    for key, src in sources.items():
        if is_todo(src) or not src.strip():
            results[key] = src
        else:
            pending[key] = mask(src)
    keys = list(pending)
    for i in range(0, len(keys), batch):
        chunk = {k: pending[k][0] for k in keys[i:i + batch]}
        out = translator(chunk, glossary)
        for k, masked in chunk.items():
            got = out.get(k)
            if isinstance(got, str) and tokens_ok(masked, got, pending[k][1]):
                results[k] = unmask(got, pending[k][1])
            else:
                rejected.append(k)
    return results, rejected


def run(content_dir: Path, translator: Translator | None, dry_run: bool = False) -> dict:
    en = flatten(json.loads((content_dir / "en.json").read_text(encoding="utf-8")))
    he_path = content_dir / "he.json"
    he = flatten(json.loads(he_path.read_text(encoding="utf-8"))) if he_path.exists() else {}
    hashes_path = content_dir / HASHES_FILE
    hashes = json.loads(hashes_path.read_text(encoding="utf-8")) if hashes_path.exists() else {}

    projects = {p: json.loads(p.read_text(encoding="utf-8")) for p in sorted((content_dir / "projects").glob("*.json"))}
    proj_en, proj_he, proj_ref = {}, {}, {}
    for path, proj in projects.items():
        for fpath, field in project_fields(proj):
            key = f"projects/{path.stem}:{fpath}"
            proj_en[key], proj_ref[key] = field["en"], field
            if field.get("he"):
                proj_he[key] = field["he"]

    todo, adopt = plan(en, he, hashes)
    ptodo, padopt = plan(proj_en, proj_he, hashes)
    report = {"site": todo, "projects": ptodo, "adopted": len(adopt) + len(padopt), "rejected": []}
    if dry_run or translator is None:
        return report

    glossary = build_glossary({p.stem: d for p, d in projects.items()})
    sources = {**{k: en[k] for k in todo}, **{k: proj_en[k] for k in ptodo}}
    results, rejected = translate_keys(sources, translator, glossary) if sources else ({}, [])
    report["rejected"] = rejected

    for k in todo:
        if k in results:
            he[k] = results[k]
            hashes[k] = sha(en[k])
    for k in ptodo:
        if k in results:
            proj_ref[k]["he"] = results[k]
            hashes[k] = sha(proj_en[k])
    hashes.update(adopt)
    hashes.update(padopt)

    # keep he.json in en.json's key order; drop nothing the user wrote
    ordered = {k: he[k] for k in en if k in he}
    ordered.update({k: v for k, v in he.items() if k not in ordered})
    he_path.write_text(json.dumps(unflatten(ordered), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hashes_path.write_text(json.dumps(dict(sorted(hashes.items())), ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    for path, proj in projects.items():
        path.write_text(json.dumps(proj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="list what would be translated; no API call")
    args = ap.parse_args(argv)

    from rivatar import config  # loads .env; never prints the key

    translator = None
    if not args.dry_run:
        if not config.has_openai_key():
            print("OPENAI_API_KEY is not set (.env). Nothing translated.")
            return 1
        translator = openai_translator(config.LLM_MODEL)
    report = run(CONTENT_DIR, translator, dry_run=args.dry_run)
    print(f"site keys to translate: {len(report['site'])}; project fields: {len(report['projects'])}; "
          f"adopted existing Hebrew: {report['adopted']}")
    for k in report["site"] + report["projects"]:
        print(f"  - {k}")
    if report["rejected"]:
        print(f"rejected (kept in English, placeholders or markers changed): {report['rejected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
