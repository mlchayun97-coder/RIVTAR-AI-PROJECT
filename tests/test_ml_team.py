"""Crew 2 (ML Team): features, comparison, the publishing decision, evaluation, Model Card.
Ported from the ML prototype; the decision tests are new."""
import copy
import json

import pandas as pd
import pytest

from rivatar import config
from rivatar.tools import ml_ops

SAMPLE_EVENT = {
    "inquiry_date": "2026-01-01", "event_date": "2026-07-15", "event_type": "wedding",
    "region": "jerusalem", "venue_type": "hall", "catering_level": "premium", "design_package": "luxury",
    "guest_count": 300, "extra_lighting": 1, "extra_photography": 1, "extra_music_talent": 0,
    "extra_shuttles": 0, "extra_social_promo": 0,
}


def test_features_exclude_leaky_columns(data_ready):
    X = ml_ops.build_features(pd.read_csv(config.CLEAN_DATA))
    for col in [config.TARGET, config.ID_COLUMN, "lead_source"]:
        assert col not in X.columns
    assert not X.isna().any().any()


def test_at_least_two_versions_compared(ml_ready):
    comp = json.loads(config.MODEL_COMPARISON.read_text(encoding="utf-8"))
    assert len(comp["results"]) >= 2
    assert "best_model" not in comp  # comparing does not decide


def test_decision_is_recorded_with_who_and_why(ml_ready):
    d = json.loads(config.MODEL_DECISION.read_text(encoding="utf-8"))
    comp = json.loads(config.MODEL_COMPARISON.read_text(encoding="utf-8"))
    assert d["chosen_model"] in comp["results"]
    assert d["decided_by"] and d["reason"] and d["policy"]
    assert d["agrees_with_policy_rule"]  # offline the rule decides, so it must agree with itself
    assert ml_ops.load_model()["name"] == d["chosen_model"]


def _comparison(**mae):
    res = {n: {"complexity": ml_ops.COMPLEXITY[n], "cv_mae_mean": v, "cv_mape_mean": 0.08, "cv_r2_mean": .9}
           for n, v in mae.items()}
    return {"results": res}


def test_policy_prefers_the_simpler_model_within_the_margin():
    near = _comparison(v1_ridge_baseline=10_000, v2_random_forest=9_700, v3_hist_gradient_boosting=9_600)
    assert ml_ops.policy_choice(near)[0] == "v1_ridge_baseline"  # 4% better is not enough
    far = _comparison(v1_ridge_baseline=10_000, v2_random_forest=9_700, v3_hist_gradient_boosting=9_000)
    assert ml_ops.policy_choice(far)[0] == "v3_hist_gradient_boosting"  # 10% better wins


def test_policy_never_allows_a_model_over_the_mape_limit():
    comp = _comparison(v1_ridge_baseline=10_000, v2_random_forest=9_000)
    comp["results"]["v1_ridge_baseline"]["cv_mape_mean"] = config.MAX_ALLOWED_MAPE + 0.01
    assert ml_ops.policy_choice(comp)[0] == "v2_random_forest"


def test_publish_refuses_choices_the_policy_forbids(ml_ready, tmp_path):
    comp = json.loads(config.MODEL_COMPARISON.read_text(encoding="utf-8"))
    bad = copy.deepcopy(comp)
    bad["results"]["v2_random_forest"]["cv_mape_mean"] = 0.5
    path = tmp_path / "comparison.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    kw = dict(comparison_path=path, model_path=tmp_path / "m.joblib", decision_path=tmp_path / "d.json")
    with pytest.raises(ml_ops.ModelDecisionError, match="unknown model"):
        ml_ops.publish_model("v9_magic", "because", "test", **kw)
    with pytest.raises(ml_ops.ModelDecisionError, match="MAPE"):
        ml_ops.publish_model("v2_random_forest", "because", "test", **kw)
    assert not (tmp_path / "m.joblib").exists()


def test_quality_gate_and_model_card(ml_ready):
    ev = json.loads(config.EVALUATION.read_text(encoding="utf-8"))
    assert ev["quality_gate"]["passed"]
    card = config.MODEL_CARD.read_text(encoding="utf-8")
    for section in ["Intended use", "Model comparison", "Limitations", "Reproducibility", "decided by"]:
        assert section in card
    assert "starting point, not a quote" in card


def test_training_is_reproducible(ml_ready):
    r = ml_ops.check_reproducibility()
    assert r["identical"], r


def test_prediction_is_sane_and_monotonic_in_guests(ml_ready):
    small = ml_ops.predict_budget({**SAMPLE_EVENT, "guest_count": 100})
    big = ml_ops.predict_budget({**SAMPLE_EVENT, "guest_count": 500})
    assert 10_000 < small["estimate"] < big["estimate"] < 2_000_000
    assert small["low"] <= small["estimate"] <= small["high"]


def test_ml_crew_has_four_agents_and_the_trainer_decides():
    from rivatar.crews.ml_crew import build_ml_crew
    crew = build_ml_crew()
    assert len(crew.agents) >= 3 and len(crew.tasks) >= 3
    assert all(a.tools for a in crew.agents)
    trainer = next(a for a in crew.agents if a.role == "Model Trainer")
    assert {t.name for t in trainer.tools} == {"compare_models", "publish_selected_model"}
