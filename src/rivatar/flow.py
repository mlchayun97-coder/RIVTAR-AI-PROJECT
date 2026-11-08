"""RIVATAR end-to-end CrewAI Flow (ported from the ML prototype).

    generate_raw_data
          │
    run_data_team                (Crew 1: clean → EDA → insights → contract)
          │
    validate_data_contract ──► "contract_invalid" ──► stop_pipeline  ✋
          │ "contract_valid"
    run_ml_team                  (Crew 2: features → compare → DECIDE + publish → evaluate → model card)
          │
    quality_and_reproducibility_gate ──► "rejected" ──► stop_pipeline  ✋
          │ "approved"
    publish_results              ✅

Every step is logged to reports/run_log.txt and reports/run_status.json, so a success and a stop both
leave a clear, machine-readable record of what happened and why. The ML LAB page reads them.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Literal

import numpy as np
import pandas as pd
from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel, Field

from rivatar import config
from rivatar.contract import DataContractError, validate_contract
from rivatar.crews.data_crew import build_data_crew, run_data_team_offline
from rivatar.crews.ml_crew import build_ml_crew, run_ml_team_offline
from rivatar.data_generator import generate_raw_dataset
from rivatar.tools import ml_ops

REQUIRED_DATA_ARTIFACTS = [config.CLEAN_DATA, config.CLEANING_REPORT, config.EDA_SUMMARY,
                           config.INSIGHTS_MD, config.DATA_CONTRACT]
REQUIRED_ML_ARTIFACTS = [config.FEATURES_SPEC, config.MODEL_COMPARISON, config.MODEL_DECISION,
                         config.EVALUATION, config.MODEL_FILE, config.MODEL_CARD]


class PipelineState(BaseModel):
    seed: int = config.SEED
    offline: bool = True
    inject_violation: bool = False
    mode: str = ""
    started_at: str = ""
    steps: list[dict] = Field(default_factory=list)
    status: str = "RUNNING"
    failed_gate: str | None = None
    violations: list[str] = Field(default_factory=list)
    contract_report: dict = Field(default_factory=dict)
    decision: dict = Field(default_factory=dict)
    best_model: str | None = None
    best_holdout: dict = Field(default_factory=dict)
    reproducibility: dict = Field(default_factory=dict)


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def _missing(paths) -> list[str]:
    return [p.relative_to(config.OUTPUT_ROOT).as_posix() for p in paths if not p.exists()]


def _read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RivatarFlow(Flow[PipelineState]):

    def _log(self, step: str, **info) -> None:
        entry = {"step": step, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **info}
        self.state.steps.append(entry)
        line = f"▶ [{step}] {json.dumps(info, ensure_ascii=False, default=str)[:400]}"
        print("\n" + line)
        with config.RUN_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{entry['at']} {line}\n")

    def _write_status(self) -> None:
        config.RUN_STATUS.write_text(json.dumps(self.state.model_dump(), indent=2, ensure_ascii=False,
                                                default=str), encoding="utf-8")

    # ------------------------------------------------------------------ 1
    @start()
    def generate_raw_data(self):
        config.ensure_dirs()
        _seed_everything(self.state.seed)
        for stale in [*REQUIRED_DATA_ARTIFACTS, *REQUIRED_ML_ARTIFACTS, config.RUN_STATUS, config.RUN_LOG,
                      config.REPORTS_DIR / "insights_notes.md", config.REPORTS_DIR / "model_card_notes.md"]:
            stale.unlink(missing_ok=True)
        self.state.mode = "offline (deterministic tools, no LLM)" if self.state.offline else f"LLM agents ({config.LLM_MODEL})"
        self.state.started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        raw = generate_raw_dataset(seed=self.state.seed)
        self._log("generate_raw_data", rows=len(raw), seed=self.state.seed, mode=self.state.mode)

    # ------------------------------------------------------------------ 2
    @listen(generate_raw_data)
    def run_data_team(self):
        if self.state.offline:
            result = run_data_team_offline()
        else:
            out = build_data_crew().kickoff()
            result = {"crew_output": str(out)[:1500]}
        self._log("run_data_team", missing_artifacts=_missing(REQUIRED_DATA_ARTIFACTS))

        if self.state.inject_violation:  # demo: a bad upstream change after the contract was signed
            df = pd.read_csv(config.CLEAN_DATA)
            df.loc[df.index[:5], "guest_count"] = -3
            df.loc[df.index[5:8], "event_type"] = "birthday_party"
            df.to_csv(config.CLEAN_DATA, index=False, lineterminator="\n")
            self._log("inject_violation", note="corrupted 8 rows of the clean data after the contract was signed")
        return result

    # ------------------------------------------------------------------ 3
    @router(run_data_team)
    def validate_data_contract(self) -> Literal["contract_valid", "contract_invalid"]:
        missing = _missing(REQUIRED_DATA_ARTIFACTS)
        if missing:
            self.state.failed_gate = "data_team_artifacts"
            self.state.violations = [f"Data team did not produce: {m}" for m in missing]
            self._log("validate_data_contract", result="FAILED", violations=self.state.violations)
            return "contract_invalid"
        try:
            self.state.contract_report = validate_contract()
        except DataContractError as e:
            self.state.failed_gate = "data_contract"
            self.state.violations = e.violations
            self._log("validate_data_contract", result="FAILED", violations=len(e.violations))
            return "contract_invalid"
        self._log("validate_data_contract", result="PASSED", **self.state.contract_report)
        return "contract_valid"

    # ------------------------------------------------------------------ 4
    @listen("contract_valid")
    def run_ml_team(self):
        _seed_everything(self.state.seed)
        if self.state.offline:
            run_ml_team_offline(self.state.seed)
        else:
            build_ml_crew().kickoff()
        self._log("run_ml_team", missing_artifacts=_missing(REQUIRED_ML_ARTIFACTS))
        if config.MODEL_DECISION.exists():
            d = _read(config.MODEL_DECISION)
            self.state.decision = d
            self._log("agent_decision", decision=d["decision"], decided_by=d["decided_by"],
                      chosen=d["chosen_model"], reason=d["reason"],
                      policy_rule_choice=d["policy_rule_choice"], agrees_with_policy_rule=d["agrees_with_policy_rule"])

    # ------------------------------------------------------------------ 5
    @router(run_ml_team)
    def quality_and_reproducibility_gate(self) -> Literal["approved", "rejected"]:
        missing = _missing(REQUIRED_ML_ARTIFACTS)
        if missing:
            self.state.failed_gate = "ml_team_artifacts"
            self.state.violations = [f"ML team did not produce: {m}" for m in missing]
            self._log("quality_and_reproducibility_gate", passed=False, violations=self.state.violations)
            return "rejected"

        ev = _read(config.EVALUATION)
        self.state.best_model = ev["best_model"]
        self.state.best_holdout = ev["best_holdout"]
        problems = []
        if ev["best_model"] != self.state.decision.get("chosen_model"):
            problems.append(f"published model {ev['best_model']} is not the decided one "
                            f"({self.state.decision.get('chosen_model')})")
        if not ev["quality_gate"]["passed"]:
            problems.append(f"MAPE {ev['best_holdout']['mape']:.1%} ≥ allowed {config.MAX_ALLOWED_MAPE:.0%}")

        # the data must still be the exact data the contract signed
        try:
            validate_contract()
        except DataContractError as e:
            problems += [f"post-training contract check: {v}" for v in e.violations]

        repro = ml_ops.check_reproducibility(self.state.seed)
        self.state.reproducibility = repro
        if not repro["identical"]:
            problems.append(f"model is not reproducible: max prediction diff {repro['max_abs_diff']:.3e}")

        self._log("quality_and_reproducibility_gate", passed=not problems, mape=ev["best_holdout"]["mape"],
                  reproducible=repro["identical"])
        if problems:
            self.state.failed_gate = "quality_or_reproducibility"
            self.state.violations = problems
            return "rejected"
        return "approved"

    # ------------------------------------------------------------------ 6
    @listen("approved")
    def publish_results(self):
        self.state.status = "SUCCEEDED"
        self._write_status()
        ml_ops.write_model_card()  # regenerate so the card includes the reproducibility result
        self._log("publish_results", model=self.state.best_model, model_card=config.MODEL_CARD.name)
        self._write_status()
        return self.state.status

    @listen(or_("contract_invalid", "rejected"))
    def stop_pipeline(self):
        self.state.status = "STOPPED"
        config.MODEL_FILE.unlink(missing_ok=True)  # never leave a model trained on unchecked data
        self._log("stop_pipeline", failed_gate=self.state.failed_gate, violations=len(self.state.violations))
        self._write_status()
        bar = "=" * 70
        print(f"\n{bar}\n✋ PIPELINE STOPPED at gate: {self.state.failed_gate}\n{bar}")
        for v in self.state.violations:
            print(f"  ✗ {v}")
        print(f"{bar}\nNo model was published. Details: {config.RUN_STATUS.relative_to(config.OUTPUT_ROOT).as_posix()}\n{bar}")
        return self.state.status


def run_flow(offline: bool = True, inject_violation: bool = False, seed: int = config.SEED) -> PipelineState:
    flow = RivatarFlow()
    flow.kickoff(inputs={"offline": offline, "inject_violation": inject_violation, "seed": seed})
    return flow.state
