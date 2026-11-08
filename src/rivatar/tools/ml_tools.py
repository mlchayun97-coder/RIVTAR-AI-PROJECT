"""CrewAI tools for Crew 2 (ML Team) – wrappers around the deterministic operations.

The numbers come from tested Python code. What the agents add is judgement: the Model Trainer
*decides* which version to publish by calling `publish_selected_model` with a model name and a reason;
the tool enforces the hard limits of the selection policy and records the decision.
"""
from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from rivatar import config
from rivatar.tools import ml_ops

NOTES_MODEL_CARD = config.REPORTS_DIR / "model_card_notes.md"


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)[:6000]


class _NoArgs(BaseModel):
    pass


class _Narrative(BaseModel):
    narrative: str = Field(..., description="Your written analysis in Markdown (3-8 bullet points).")


class _Decision(BaseModel):
    model_name: str = Field(..., description="Exactly one version name from the comparison, e.g. v1_ridge_baseline.")
    reason: str = Field(..., description="Two or three sentences: why this version, citing the CV numbers and the policy.")


class PrepareFeaturesTool(BaseTool):
    name: str = "prepare_features"
    description: str = "Build the model feature table from the clean dataset and save the feature spec. Returns the spec."
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        return _j(ml_ops.prepare_features())


class CompareModelsTool(BaseTool):
    name: str = "compare_models"
    description: str = ("Cross-validate three model versions (Ridge baseline, Random Forest, Hist Gradient "
                        "Boosting) with a fixed seed. Returns CV MAE / MAPE / R² and complexity per version, "
                        "plus the selection policy. It does not choose a model: you do.")
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        return _j(ml_ops.compare_models())


class PublishModelTool(BaseTool):
    name: str = "publish_selected_model"
    description: str = ("Publish the model version YOU chose, with your reason. Fits it and saves "
                        "artifacts/model.joblib. Rejects unknown versions and versions whose CV MAPE is not "
                        "below the allowed maximum; if rejected, choose again.")
    args_schema: Type[BaseModel] = _Decision

    def _run(self, model_name: str, reason: str) -> str:
        try:
            d = ml_ops.publish_model(model_name, reason, decided_by=f"Model Trainer agent ({config.LLM_MODEL})")
        except ml_ops.ModelDecisionError as e:
            return f"REJECTED: {e}"
        return _j({k: d[k] for k in ("chosen_model", "decided_by", "agrees_with_policy_rule", "policy_rule_choice")})


class EvaluateModelTool(BaseTool):
    name: str = "evaluate_model"
    description: str = ("Evaluate all versions on the hold-out set, compute per-event-type errors, feature "
                        "importance and the 80% prediction range. Returns the evaluation report.")
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        return _j(ml_ops.evaluate_model())


class WriteModelCardTool(BaseTool):
    name: str = "write_model_card"
    description: str = "Write reports/model_card.md from the comparison, decision and evaluation, appending your evaluator notes."
    args_schema: Type[BaseModel] = _Narrative

    def _run(self, narrative: str) -> str:
        NOTES_MODEL_CARD.write_text(narrative, encoding="utf-8")
        text = ml_ops.write_model_card(narrative=narrative)
        return f"model_card.md written ({len(text)} chars)"
