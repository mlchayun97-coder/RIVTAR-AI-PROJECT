"""LLM factory for the agents (OpenAI).

The key is read from .env by rivatar.config (python-dotenv) and passed to the client through the
environment. It is never printed, logged or written to a report. Without a key the pipeline runs
offline: the same steps, executed by deterministic code instead of agents.
"""
from __future__ import annotations

from crewai import LLM

from rivatar import config


def llm_available() -> bool:
    return config.has_openai_key()


def make_llm(model: str = config.LLM_MODEL) -> LLM:
    return LLM(model=model, temperature=0)  # as deterministic as an LLM gets, for reproducibility
