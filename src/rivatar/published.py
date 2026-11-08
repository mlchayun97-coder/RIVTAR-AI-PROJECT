"""Where the website reads the published run from.

Locally, the Flow writes artifacts/ and reports/ (both git-ignored). On a host that only has the
repository (Streamlit Community Cloud), those folders do not exist, so the site falls back to
deploy/snapshot/: a small committed copy of the live run (the model, its reports and the agent's
decision). Synthetic data only; nothing from data/.

The real run always wins when it exists, including a STOPPED run (the site then shows the stop).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rivatar import config

SNAPSHOT_DIR = config.ROOT / "deploy" / "snapshot"


@dataclass(frozen=True)
class PublishedRun:
    artifacts: Path
    reports: Path
    snapshot: bool  # True = the committed snapshot, not a run made on this machine

    @property
    def run_status(self) -> Path: return self.reports / "run_status.json"
    @property
    def run_log(self) -> Path: return self.reports / "run_log.txt"
    @property
    def model_decision(self) -> Path: return self.reports / "model_decision.json"
    @property
    def model_comparison(self) -> Path: return self.reports / "model_comparison.json"
    @property
    def evaluation(self) -> Path: return self.reports / "evaluation.json"
    @property
    def model_card(self) -> Path: return self.reports / "model_card.md"
    @property
    def insights(self) -> Path: return self.reports / "insights.md"
    @property
    def eda_dir(self) -> Path: return self.reports / "eda"
    @property
    def data_contract(self) -> Path: return self.artifacts / "data_contract.json"
    @property
    def model_file(self) -> Path: return self.artifacts / "model.joblib"


def current() -> PublishedRun:
    """The run made here if there is one, otherwise the committed snapshot."""
    if config.RUN_STATUS.exists() or not (SNAPSHOT_DIR / "reports" / "run_status.json").exists():
        return PublishedRun(config.ARTIFACTS_DIR, config.REPORTS_DIR, snapshot=False)
    return PublishedRun(SNAPSHOT_DIR / "artifacts", SNAPSHOT_DIR / "reports", snapshot=True)
