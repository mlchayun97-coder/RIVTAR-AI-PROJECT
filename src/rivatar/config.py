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
# Everything the pipeline and the form WRITE lives under OUTPUT_ROOT: the project folder by default,
# or RIVATAR_OUTPUT_DIR when set. The tests set it to a temporary folder, so running them never
# overwrites the real reports/ that the ML LAB page shows.
OUTPUT_ROOT = Path(os.environ["RIVATAR_OUTPUT_DIR"]).resolve() if os.getenv("RIVATAR_OUTPUT_DIR") else ROOT

DATA_DIR = ROOT / "data"
RAW_DIR = OUTPUT_ROOT / "data" / "raw"
PROCESSED_DIR = OUTPUT_ROOT / "data" / "processed"
LEADS_CSV = OUTPUT_ROOT / "data" / "leads.csv"
MEDIA_CATALOG_CSV = DATA_DIR / "media_catalog.csv"
ARTIFACTS_DIR = OUTPUT_ROOT / "artifacts"
REPORTS_DIR = OUTPUT_ROOT / "reports"

APP_DIR = ROOT / "app"
STATIC_DIR = APP_DIR / "static"
EVENTS_STATIC_DIR = STATIC_DIR / "events"
SELECTION_JSON = EVENTS_STATIC_DIR / "selection.json"

# The Google Drive export arrives split into several parts; treated as one source.
MEDIA_EXPORT_GLOB = "RIVATAR WEBSITE-*"

RAW_EVENTS_CSV = RAW_DIR / "events_raw.csv"

# ---- ML pipeline (phases 2-4) -------------------------------------------------
# Data stays synthetic and out of git (data/ is ignored). Every run regenerates it from SEED.
RAW_DATA = RAW_EVENTS_CSV
CLEAN_DATA = PROCESSED_DIR / "events_clean.csv"
EDA_DIR = REPORTS_DIR / "eda"

DATA_CONTRACT = ARTIFACTS_DIR / "data_contract.json"
FEATURES_SPEC = ARTIFACTS_DIR / "features_spec.json"
MODEL_FILE = ARTIFACTS_DIR / "model.joblib"
CLEANING_REPORT = REPORTS_DIR / "cleaning_report.json"
EDA_SUMMARY = REPORTS_DIR / "eda_summary.json"
INSIGHTS_MD = REPORTS_DIR / "insights.md"
MODEL_COMPARISON = REPORTS_DIR / "model_comparison.json"
MODEL_DECISION = REPORTS_DIR / "model_decision.json"
EVALUATION = REPORTS_DIR / "evaluation.json"
MODEL_CARD = REPORTS_DIR / "model_card.md"
RUN_STATUS = REPORTS_DIR / "run_status.json"
RUN_LOG = REPORTS_DIR / "run_log.txt"

TARGET = "total_budget_ils"
ID_COLUMN = "event_id"

N_ROWS = 1500
TEST_SIZE = 0.2
CV_FOLDS = 5

# Gates. The flow stops if any of these are not met.
MIN_ROWS_AFTER_CLEANING = 1000
MAX_ALLOWED_MAPE = 0.25        # the published model must have hold-out MAPE below 25%
REPRO_TOLERANCE = 1e-9         # a retrain with the same seed must give the same predictions

# Model-selection policy the agent decides with (and the offline rule applies):
# prefer the simpler model unless a more complex one lowers CV MAE by more than this share.
SIMPLER_MODEL_MARGIN = 0.05

# ---- LLM ----------------------------------------------------------------------------------
LLM_MODEL = os.getenv("RIVATAR_LLM_MODEL", "gpt-4o-mini")


def has_openai_key() -> bool:
    """True if an OpenAI key is configured. Never exposes the value."""
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, ARTIFACTS_DIR, REPORTS_DIR, EDA_DIR):
        d.mkdir(parents=True, exist_ok=True)
