"""Command-line entry point for the ML pipeline.

    python -m rivatar.main                               # LLM agents (OPENAI_API_KEY in .env)
    python -m rivatar.main --offline                     # same flow, deterministic tools, no API key
    python -m rivatar.main --offline --inject-violation  # demo: the contract gate stops the run (exit 1)
    python -m rivatar.main --plot                        # save a diagram of the flow (flow_diagram.html)

Exit codes: 0 model published · 1 pipeline stopped at a gate · 2 no API key (and not --offline).
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from rivatar import config  # noqa: E402  (loads .env; the key is never printed)
from rivatar.crews.llm import llm_available  # noqa: E402
from rivatar.flow import RivatarFlow, run_flow  # noqa: E402


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="RIVATAR event-budget ML pipeline (CrewAI Flow)")
    p.add_argument("--offline", action="store_true", help="run the tools directly, without LLM agents")
    p.add_argument("--inject-violation", action="store_true", help="corrupt the clean data to demo the contract gate")
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--plot", action="store_true", help="save the flow diagram and exit")
    a = p.parse_args(argv)

    if a.plot:
        path = RivatarFlow().plot("flow_diagram.html", show=False)
        print(f"Flow diagram saved to {path}")
        return 0
    if not a.offline and not llm_available():
        print("✋ OPENAI_API_KEY is not set. Add it to .env (see .env.example), or run with --offline.")
        return 2

    state = run_flow(offline=a.offline, inject_violation=a.inject_violation, seed=a.seed)
    if state.status == "SUCCEEDED":
        h, d = state.best_holdout, state.decision
        print(f"\nDECISION by {d['decided_by']}: published `{d['chosen_model']}`. {d['reason']}")
        print(f"\n✅ SUCCEEDED · model={state.best_model} · MAE ₪{h['mae']:,.0f} · MAPE {h['mape']:.1%} · "
              f"R² {h['r2']:.3f} · reproducible={state.reproducibility['identical']}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
