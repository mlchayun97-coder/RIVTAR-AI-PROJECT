"""CrewAI tools for Crew 1 (Data Team) – wrappers around the deterministic operations.

Agents decide when to call a tool and how to interpret its JSON result;
the numbers themselves come from tested Python code, which keeps results
reproducible even though the agents are LLM-driven.
"""
from __future__ import annotations

import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from rivatar import config
from rivatar.contract import DataContractError, validate_contract
from rivatar.tools import data_ops

NOTES_INSIGHTS = config.REPORTS_DIR / "insights_notes.md"


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)[:6000]


class _NoArgs(BaseModel):
    pass


class _Narrative(BaseModel):
    narrative: str = Field(..., description="Your written analysis in Markdown (3-8 bullet points).")


class CleanDataTool(BaseTool):
    name: str = "clean_raw_events"
    description: str = ("Clean the raw RIVATAR events CSV: deduplicate, normalise spellings, parse dates and "
                        "prices, handle impossible values and impute missing ones. Returns the cleaning report.")
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        return _j(data_ops.clean_data())


class RunEDATool(BaseTool):
    name: str = "run_eda"
    description: str = ("Run exploratory data analysis on the clean dataset, save plots and return summary "
                        "statistics (target distribution, segments, correlations, service lift).")
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        return _j(data_ops.run_eda())


class WriteInsightsTool(BaseTool):
    name: str = "write_insights_report"
    description: str = ("Write reports/insights.md from the EDA summary and cleaning report, appending your "
                        "own business narrative for RIVATAR's producers.")
    args_schema: Type[BaseModel] = _Narrative

    def _run(self, narrative: str) -> str:
        NOTES_INSIGHTS.write_text(narrative, encoding="utf-8")
        text = data_ops.write_insights(narrative=narrative)
        return f"insights.md written ({len(text)} chars)"


class BuildContractTool(BaseTool):
    name: str = "build_data_contract"
    description: str = ("Create artifacts/data_contract.json describing schema, types, allowed values, ranges, "
                        "row count and sha256 of the clean dataset.")
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        c = data_ops.build_data_contract()
        return _j({k: c[k] for k in ("contract_name", "version", "row_count", "dataset_sha256", "target")}
                  | {"columns": list(c["columns"])})


class ValidateContractTool(BaseTool):
    name: str = "validate_data_contract"
    description: str = "Validate the clean dataset against artifacts/data_contract.json. Returns PASSED or the violations."
    args_schema: Type[BaseModel] = _NoArgs

    def _run(self) -> str:
        try:
            return "PASSED " + _j(validate_contract())
        except DataContractError as e:
            return "FAILED\n" + "\n".join(e.violations)
