"""Crew 1 – Data Team: cleaning, EDA, insights and the JSON data contract.

Four agents work sequentially; each task's output is passed as context to
the next one.
"""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from rivatar.crews.llm import make_llm
from rivatar.tools import data_ops
from rivatar.tools.data_tools import (
    BuildContractTool, CleanDataTool, RunEDATool, ValidateContractTool, WriteInsightsTool,
)


def build_data_crew(llm=None) -> Crew:
    llm = llm or make_llm()

    cleaner = Agent(
        role="Data Cleaning Specialist",
        goal="Turn RIVATAR's messy CRM export into a clean, analysis-ready table without losing valid events.",
        backstory="You spent years cleaning event-industry CRM data and you document every change you make.",
        tools=[CleanDataTool()], llm=llm, allow_delegation=False, verbose=True,
    )
    analyst = Agent(
        role="EDA Analyst",
        goal="Describe what drives event budgets: distributions, segments, seasonality and service effects.",
        backstory="A statistician who loves clear charts and never reports a number without context.",
        tools=[RunEDATool()], llm=llm, allow_delegation=False, verbose=True,
    )
    strategist = Agent(
        role="Business Insights Strategist",
        goal="Translate the EDA into actionable insights for RIVATAR's producers and the modelling team.",
        backstory="A former event producer turned analyst; you know what a producer needs before a client call.",
        tools=[WriteInsightsTool()], llm=llm, allow_delegation=False, verbose=True,
    )
    contract_engineer = Agent(
        role="Data Contract Engineer",
        goal="Publish a strict JSON data contract for the clean dataset and verify the data satisfies it.",
        backstory="You guard the boundary between data and ML teams. Nothing ambiguous crosses it.",
        tools=[BuildContractTool(), ValidateContractTool()], llm=llm, allow_delegation=False, verbose=True,
    )

    t_clean = Task(
        description="Call the `clean_raw_events` tool exactly once. Then summarise every cleaning step and how many rows it affected.",
        expected_output="A bullet list of cleaning steps with row counts, and rows in vs rows out.",
        agent=cleaner,
    )
    t_eda = Task(
        description="Call the `run_eda` tool exactly once and report the 5 most important patterns in the statistics.",
        expected_output="Five numbered findings, each backed by a number from the EDA summary.",
        agent=analyst, context=[t_clean],
    )
    t_insights = Task(
        description=("Using the cleaning summary and EDA findings, write 4-6 business insights for RIVATAR "
                     "(pricing, packages, seasonality, upsell of services). Call `write_insights_report` "
                     "exactly once, passing your insights as `narrative`."),
        expected_output="Confirmation that insights.md was written, plus the insights you wrote.",
        agent=strategist, context=[t_clean, t_eda],
    )
    t_contract = Task(
        description=("Call `build_data_contract`, then call `validate_data_contract`. Report the contract "
                     "name, version, row count and the validation result verbatim (PASSED or FAILED + list)."),
        expected_output="Contract summary and the exact validation result.",
        agent=contract_engineer, context=[t_clean],
    )
    return Crew(agents=[cleaner, analyst, strategist, contract_engineer],
                tasks=[t_clean, t_eda, t_insights, t_contract], process=Process.sequential, verbose=True)


def run_data_team_offline() -> dict:
    """Same four tasks in the same order, executed without an LLM."""
    cleaning = data_ops.clean_data()
    eda = data_ops.run_eda()
    data_ops.write_insights()
    contract = data_ops.build_data_contract()
    return {"cleaning": cleaning, "eda_rows": eda["n_rows"], "contract_version": contract["version"]}
