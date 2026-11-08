"""Shared fixtures for the ML pipeline tests (ported from the ML prototype).

Everything runs offline: the agents are built but never called, so neither the tests nor CI need an API
key. A dummy key is set BEFORE rivatar.config loads .env (which never overrides an existing variable),
so a real key in .env is never used by the tests.
"""
import os
import shutil
import tempfile

import pytest

# Every file the pipeline and the form write (data/, artifacts/, reports/, leads.csv) goes to a
# temporary folder, so running the tests never overwrites the real reports/ that ML LAB shows.
# Set BEFORE rivatar.config is imported (config reads it once, at import).
_OUTPUT = tempfile.mkdtemp(prefix="rivatar-tests-")
os.environ["RIVATAR_OUTPUT_DIR"] = _OUTPUT


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_OUTPUT, ignore_errors=True)


os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ["OPENAI_API_KEY"] = "sk-test-not-used"  # agents are built, never called, in tests


@pytest.fixture(scope="session")
def data_ready():
    """Raw data + Crew 1 outputs (offline)."""
    from rivatar import config
    from rivatar.crews.data_crew import run_data_team_offline
    from rivatar.data_generator import generate_raw_dataset
    config.ensure_dirs()
    generate_raw_dataset()
    return run_data_team_offline()


@pytest.fixture(scope="session")
def ml_ready(data_ready):
    """Crew 2 outputs on top of Crew 1 outputs (offline)."""
    from rivatar.crews.ml_crew import run_ml_team_offline
    return run_ml_team_offline()


@pytest.fixture(scope="session")
def pipeline():
    """The whole CrewAI Flow, offline."""
    from rivatar.flow import run_flow
    state = run_flow(offline=True)
    assert state.status == "SUCCEEDED", state.violations
    return state
