# RIVATAR – Event Budget Estimator

Final project (AI developer course) for **RIVATAR PRODUCTIONS**, a boutique and luxury event-production
company. The system estimates the total budget of an event (₪) from the details a client fills in on
the company website.

Stack: Python 3.12 · CrewAI Flow (two crews × 4 agents) · scikit-learn · Streamlit.

> Work in progress. See the roadmap below.

## Roadmap
| Phase | Scope |
|---|---|
| 1 | Project foundation, media pipeline, RIVATAR website in Streamlit, synthetic data generator |
| 2 | Crew 1 (4 agents): cleaning, EDA, insights, JSON data contract + validation |
| 3 | Crew 2 (4 agents): features, 3 model versions, CV selection, evaluation, Model Card + live estimate |
| 4 | CrewAI Flow with contract gate, quality and reproducibility gate, `--inject-violation` demo, ML LAB |
| 5 | CI (GitHub Actions), docs, presentation |
