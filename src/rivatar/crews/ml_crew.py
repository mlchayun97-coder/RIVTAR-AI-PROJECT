"""Crew 2 – ML Team: features, model comparison + the publishing DECISION, evaluation and the Model Card.

Where an agent decides: the Model Trainer reads the cross-validation comparison and the selection
policy, then chooses which version to publish and why (`publish_selected_model`). The tool refuses
choices the policy forbids; the Flow logs the decision, compares it with the policy rule, and the
ML LAB page shows it.
"""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from rivatar import config
from rivatar.crews.llm import make_llm
from rivatar.tools import ml_ops
from rivatar.tools.ml_tools import (
    CompareModelsTool, EvaluateModelTool, PrepareFeaturesTool, PublishModelTool, WriteModelCardTool,
)


def build_ml_crew(llm=None) -> Crew:
    llm = llm or make_llm()

    feature_engineer = Agent(
        role="Feature Engineer",
        goal="Build leakage-free, well-documented features for predicting event budget.",
        backstory="You know that a good feature beats a fancy model, and you never let IDs or the target leak in.",
        tools=[PrepareFeaturesTool()], llm=llm, allow_delegation=False, verbose=True,
    )
    trainer = Agent(
        role="Model Trainer",
        goal="Compare the model versions fairly and decide which one RIVATAR should publish.",
        backstory=("An ML engineer obsessed with reproducibility and honest baselines. You publish the model a "
                   "producer can trust, not the one with the most impressive name."),
        tools=[CompareModelsTool(), PublishModelTool()], llm=llm, allow_delegation=False, verbose=True,
    )
    evaluator = Agent(
        role="Model Evaluator",
        goal="Evaluate the published model on unseen data, find where it fails and quantify uncertainty.",
        backstory="A sceptical reviewer: you look for weak segments before anyone else does.",
        tools=[EvaluateModelTool()], llm=llm, allow_delegation=False, verbose=True,
    )
    card_author = Agent(
        role="Model Card Author",
        goal="Document the model transparently for RIVATAR and for the course reviewers.",
        backstory="You write model cards that a business owner and an ML engineer can both understand.",
        tools=[WriteModelCardTool()], llm=llm, allow_delegation=False, verbose=True,
    )

    t_feat = Task(
        description="Call `prepare_features` once. List the features, which columns were excluded and why.",
        expected_output="Feature list grouped by type, excluded columns with reasons.",
        agent=feature_engineer,
    )
    t_train = Task(
        description=(
            "1. Call `compare_models` once.\n"
            f"2. DECIDE which version to publish, following this policy: {ml_ops.SELECTION_POLICY} "
            "Weigh the CV MAE difference against model complexity yourself; do not just take the lowest number.\n"
            "3. Call `publish_selected_model` with the exact version name and a 2-3 sentence reason that cites "
            "the CV numbers. If the tool answers REJECTED, read why and decide again."),
        expected_output=("A comparison table (CV MAE, MAPE, R², complexity), the version you published and why, "
                         "and the tool's confirmation."),
        agent=trainer, context=[t_feat],
    )
    t_eval = Task(
        description=("Call `evaluate_model` once. Report hold-out metrics, the weakest event types, the top "
                     "features and whether the quality gate passed."),
        expected_output="Hold-out metrics, weak segments, top features, quality gate result.",
        agent=evaluator, context=[t_train],
    )
    t_card = Task(
        description=("Write 4-6 evaluator notes (risks, recommended next steps, how producers should use the "
                     "estimate). Call `write_model_card` once, passing them as `narrative`."),
        expected_output="Confirmation that model_card.md was written, plus your notes.",
        agent=card_author, context=[t_train, t_eval],
    )
    return Crew(agents=[feature_engineer, trainer, evaluator, card_author],
                tasks=[t_feat, t_train, t_eval, t_card], process=Process.sequential, verbose=True)


def run_ml_team_offline(seed: int = config.SEED) -> dict:
    """Same four tasks in the same order without an LLM; the decision is taken by the policy rule."""
    ml_ops.prepare_features()
    comparison = ml_ops.compare_models(seed)
    decision = ml_ops.decide_and_publish_offline(seed)
    evaluation = ml_ops.evaluate_model(seed)
    ml_ops.write_model_card()
    return {"comparison": comparison, "decision": decision, "evaluation": evaluation}
