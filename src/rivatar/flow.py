"""CrewAI Flow (phase 4 placeholder).

Planned steps: generate data -> Crew 1 (data) -> @router contract gate -> Crew 2 (ML)
-> @router quality & reproducibility gate -> publish model / stop_pipeline (exit code 1).
Every step writes to reports/run_status.json, which the ML LAB page reads.
"""
