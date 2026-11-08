"""Budget estimator used by the website form.

Loads the model the Flow published (artifacts/model.joblib), runs the SAME feature preparation used in
training (ml_ops.build_features) and returns the estimate with the model's 80% range from the hold-out
set. A starting point for a conversation, not a quote.

The estimate is only shown when the last Flow run SUCCEEDED (a stopped run deletes the model), and
only when every field the model needs is filled in; otherwise the form shows "unavailable".
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from rivatar import config, vocab

UNAVAILABLE_MESSAGE = "Estimate available after the ML phase"
REQUIRED = ("event_type", "event_date", "guest_count", "region", "venue_type", "catering_level", "design_package")


def _unavailable(message: str = UNAVAILABLE_MESSAGE) -> dict:
    return {"status": "unavailable", "estimate_ils": None, "low_ils": None, "high_ils": None,
            "model_version": None, "message": message}


def model_ready() -> bool:
    if not (config.MODEL_FILE.exists() and config.RUN_STATUS.exists() and config.EVALUATION.exists()):
        return False
    try:
        return json.loads(config.RUN_STATUS.read_text(encoding="utf-8")).get("status") == "SUCCEEDED"
    except (OSError, ValueError):
        return False


@lru_cache(maxsize=2)
def _load(model_mtime: float):
    """The model bundle and its 80% relative range; reloaded when a new run publishes a model."""
    import joblib
    bundle = joblib.load(config.MODEL_FILE)
    ev = json.loads(config.EVALUATION.read_text(encoding="utf-8"))
    return bundle, tuple(ev["prediction_interval_80pct_relative"])


def estimate_budget(event: dict, today: date | None = None) -> dict:
    """Estimate the total event budget in ILS.

    Args:
        event: event features with the shared vocabulary codes (see rivatar.leads.event_features):
            event_type, client_type, event_date, guest_count, region, venue_type, catering_level,
            design_package, extra_* flags (0/1), lead_source (not used by the model).
        today: the inquiry date (default: today), used for the lead time like in training.

    Returns:
        {"status": "ok" | "unavailable",
         "estimate_ils": float | None, "low_ils": float | None, "high_ils": float | None,
         "model_version": str | None, "message": str}
    """
    if any(event.get(k) in (None, "") for k in REQUIRED) or event.get("event_type") not in vocab.EVENT_TYPES:
        return _unavailable()
    if not model_ready():
        return _unavailable()
    import pandas as pd

    from rivatar.tools.ml_ops import build_features

    bundle, (lo, hi) = _load(config.MODEL_FILE.stat().st_mtime)
    row = {k: event[k] for k in REQUIRED}
    row["inquiry_date"] = str(today or date.today())
    row["event_date"] = str(event["event_date"])
    row.update({k: int(bool(event.get(k))) for k in vocab.EXTRAS})
    p = float(bundle["model"].predict(build_features(pd.DataFrame([row])))[0])
    # residual = (pred - true) / true  =>  true = pred / (1 + residual)
    return {"status": "ok", "estimate_ils": round(p, -2), "low_ils": round(p / (1 + hi), -2),
            "high_ils": round(p / (1 + lo), -2), "model_version": bundle["name"],
            "message": "A starting point, not a quote"}
