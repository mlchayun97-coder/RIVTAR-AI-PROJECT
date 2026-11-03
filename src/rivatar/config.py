"""Central project configuration: paths, seed, and environment settings.

Secrets are loaded from .env with python-dotenv and are never printed or logged.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env", override=False)

SEED = 42

# ---- paths ----------------------------------------------------------------
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LEADS_CSV = DATA_DIR / "leads.csv"
MEDIA_CATALOG_CSV = DATA_DIR / "media_catalog.csv"
ARTIFACTS_DIR = ROOT / "artifacts"
REPORTS_DIR = ROOT / "reports"

APP_DIR = ROOT / "app"
STATIC_DIR = APP_DIR / "static"
EVENTS_STATIC_DIR = STATIC_DIR / "events"
SELECTION_JSON = EVENTS_STATIC_DIR / "selection.json"

# The Google Drive export arrives split into several parts; treated as one source.
MEDIA_EXPORT_GLOB = "RIVATAR WEBSITE-*"

RAW_EVENTS_CSV = RAW_DIR / "events_raw.csv"

# ---- LLM (used from phase 2) ------------------------------------------------
LLM_MODEL = os.getenv("RIVATAR_LLM_MODEL", "gpt-4o-mini")


def has_openai_key() -> bool:
    """True if an OpenAI key is configured. Never exposes the value."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())
