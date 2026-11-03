"""Site content: read-only access to the JSON files in this folder.

- en.json / he.json: interface text, same keys. A key missing in he.json falls back to English.
- site.json: settings (home photos, project order, contact details).
- projects/<slug>.json: one file per project (names, texts, cover, gallery), both languages inside.

The app never translates at runtime; it only reads these files. Text in [brackets] is a placeholder
that is shown as a visible TODO.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = CONTENT_DIR / "projects"
LANGS = ("en", "he")
DEFAULT_LANG = "en"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@lru_cache(maxsize=4)
def strings(lang: str) -> dict:
    return _read(CONTENT_DIR / f"{lang}.json")


@lru_cache(maxsize=1)
def site() -> dict:
    return _read(CONTENT_DIR / "site.json")


def _lookup(tree: dict, key: str):
    node = tree
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def normalize_lang(lang: str | None) -> str:
    return lang if lang in LANGS else DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, **fmt) -> str:
    """Text for a dotted key. Hebrew falls back to English; an unknown key returns the key itself."""
    value = _lookup(strings(normalize_lang(lang)), key)
    if value is None:
        value = _lookup(strings(DEFAULT_LANG), key)
    if value is None:
        return key
    return value.format(**fmt) if fmt and isinstance(value, str) else value


def loc(field: dict | str | None, lang: str = DEFAULT_LANG) -> str:
    """A {"en": ..., "he": ...} field in the given language (falls back to English)."""
    if isinstance(field, dict):
        return field.get(normalize_lang(lang)) or field.get(DEFAULT_LANG) or ""
    return field or ""


def is_todo(text: str | None) -> bool:
    return bool(text) and text.strip().startswith("[") and text.strip().endswith("]")


# ---------------------------------------------------------------- projects
@lru_cache(maxsize=1)
def _all_projects() -> dict[str, dict]:
    return {p.stem: _read(p) for p in sorted(PROJECTS_DIR.glob("*.json"))}


def projects(include_hidden: bool = False) -> list[dict]:
    """Projects in site.json order (unknown ones last), hidden ones skipped."""
    allp = _all_projects()
    order = [s for s in site().get("project_order", []) if s in allp]
    order += [s for s in allp if s not in order]
    return [allp[s] for s in order if include_hidden or allp[s].get("show", True)]


def project(slug: str) -> dict | None:
    p = _all_projects().get(slug)
    return p if p and p.get("show", True) else None


def next_project(slug: str) -> dict | None:
    visible = projects()
    slugs = [p["slug"] for p in visible]
    if slug not in slugs or len(slugs) < 2:
        return None
    return visible[(slugs.index(slug) + 1) % len(slugs)]


def event_type_label(code: str | None, lang: str) -> str:
    return t(f"event_types.{code}", lang) if code else t("todo", lang)


def reload() -> None:
    """Forget cached files (used by tests and after editing content)."""
    strings.cache_clear()
    site.cache_clear()
    _all_projects.cache_clear()
