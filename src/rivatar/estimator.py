"""Budget estimator used by the website form.

PHASE 1 STUB. Phase 3 replaces the body: load the model published by the Flow
(artifacts/model.joblib), run the SAME feature preparation used in training, and return the
estimate with a ±15% range. The return shape below is the contract the website already uses.
"""

from __future__ import annotations

UNAVAILABLE_MESSAGE = "Estimate available after the ML phase"


def estimate_budget(event: dict) -> dict:
    """Estimate the total event budget in ILS.

    Args:
        event: event features with the shared vocabulary codes (see rivatar.leads.event_features):
            event_type, client_type, event_date, guest_count, region, venue_type, catering_level,
            design_package, extra_* flags (0/1), lead_source.

    Returns:
        {"status": "ok" | "unavailable",
         "estimate_ils": float | None, "low_ils": float | None, "high_ils": float | None,
         "model_version": str | None, "message": str}
    """
    return {
        "status": "unavailable",
        "estimate_ils": None,
        "low_ils": None,
        "high_ils": None,
        "model_version": None,
        "message": UNAVAILABLE_MESSAGE,
    }
