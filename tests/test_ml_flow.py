"""The CrewAI Flow end to end, offline: gates, the stop on a broken contract, CLI exit codes.
Ported from the ML prototype."""
import json

from rivatar import config


def test_successful_run_records_status(pipeline):
    status = json.loads(config.RUN_STATUS.read_text(encoding="utf-8"))
    assert status["status"] == "SUCCEEDED"
    steps = [s["step"] for s in status["steps"]]
    assert steps.index("validate_data_contract") < steps.index("run_ml_team") < steps.index("agent_decision")
    assert status["reproducibility"]["identical"]
    assert status["decision"]["chosen_model"] == status["best_model"]


def test_decision_is_in_the_run_log(pipeline):
    log = config.RUN_LOG.read_text(encoding="utf-8")
    assert "[agent_decision]" in log and "decided_by" in log and "reason" in log


def test_broken_contract_stops_before_training(pipeline):
    from rivatar.flow import run_flow
    try:
        state = run_flow(offline=True, inject_violation=True)
        assert state.status == "STOPPED"
        assert state.failed_gate == "data_contract"
        assert state.violations
        assert any("birthday_party" in v for v in state.violations)
        assert "run_ml_team" not in [s["step"] for s in state.steps]
        assert not config.MODEL_FILE.exists()
        assert json.loads(config.RUN_STATUS.read_text(encoding="utf-8"))["status"] == "STOPPED"
    finally:
        assert run_flow(offline=True).status == "SUCCEEDED"  # restore artifacts for the app


def test_cli_exit_codes(monkeypatch):
    from rivatar.main import main
    assert main(["--offline", "--inject-violation"]) == 1
    assert main(["--offline"]) == 0
    monkeypatch.delenv("OPENAI_API_KEY")
    assert main([]) == 2  # no key and not offline: refuse, do not crash


def test_no_secret_in_reports(pipeline):
    """The key must never reach a report or log (tests run with a dummy key)."""
    for p in [*config.REPORTS_DIR.glob("*.json"), *config.REPORTS_DIR.glob("*.md"), config.RUN_LOG]:
        assert "sk-" not in p.read_text(encoding="utf-8"), p
