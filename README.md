# RIVATAR – Event Budget Estimator

Final project (AI developer course) for **RIVATAR PRODUCTIONS**, a boutique and luxury event-production
company (weddings, bar/bat mitzvahs, conferences, product launches, corporate events). The system
estimates the total budget of an event (₪) from the details a client fills in on the company website.

Stack: Python 3.12 · CrewAI Flow (two crews × 4 agents) · scikit-learn · Streamlit.

> The training data is **synthetic** (built from the company's business logic). Model accuracy shows
> that the method works; it is not a statement about RIVATAR's real prices.

## Setup (Windows / PowerShell)

Python **3.12** is required (CrewAI does not support 3.13+).

```powershell
# one-time: create the venv outside the project folder
py -3.12 -m venv "$env:USERPROFILE\.venvs\ai-course-light"

# every session
& "$env:USERPROFILE\.venvs\ai-course-light\Scripts\Activate.ps1"
python --version          # must print 3.12.x
pip install -r requirements.txt

# secrets: copy the template and fill in your key (never commit .env)
Copy-Item .env.example .env
```

## Run the website

From the project root:

```powershell
streamlit run app/streamlit_app.py
```

Then open http://localhost:8501. Pages:
- `/`: home (hero, selected stories, approach, services, about, contact and budget form)
- `/story-<event>`: one gallery per event, e.g. `/story-avigail-nuri`
- `/ml-lab`: pipeline status (placeholder until phase 4)

Form submissions are validated and saved to `data/leads.csv` (gitignored). The estimate box shows
"Estimate available after the ML phase" until phase 3 replaces `src/rivatar/estimator.py`.

All site text lives in `app/content.py`. Text in `[brackets]` is a placeholder and shows as a dashed
TODO on the site. Client names appear **only** as set in `content.py` (`EVENTS`); set `"show": False` to
hide an event. Fonts are self-hosted in `app/static/fonts` (works offline).

## Website photos: `scripts/prepare_media.py`

The original photos come from a Google Drive export split into parts (`RIVATAR WEBSITE-*-001/-002/-003`)
in the project root. They are never committed. The script:

1. scans all parts as one source → `data/media_catalog.csv` (gitignored: it lists original names)
2. scores every photo (sharpness + resolution), skips near duplicates, keeps up to 12 per event with
   variety between picks
3. writes web copies to `app/static/events/<event-slug>/`: EXIF rotation applied, sRGB,
   **all EXIF/GPS stripped**, `.jfif`/`.png` → JPEG, neutral file names, 600 px thumbnails
4. keeps all committed web assets under **25 MB**, stepping quality/size down if needed, and prints the total

```powershell
python scripts/prepare_media.py                     # defaults
python scripts/prepare_media.py --per-event 10 --budget-mb 20
```

To change the photos for an event, edit `app/static/events/selection.json`: `include` (original file
names, in order; the first is used first) and `exclude`, then run the script again. Videos are skipped in phase 1.

> **Phase 1 only.** The steps above describe `--auto-select`. Its output (`app/static/events/`) is no longer
> committed: the site uses the curated photos named in the content files (`app/static/projects/`,
> `app/static/media.json`), which `python scripts/prepare_media.py` exports within a 40 MB budget.

## Synthetic data

```powershell
$env:PYTHONPATH = "src"
python -m rivatar.data_generator          # -> data/raw/events_raw.csv (1,530 rows, seed 42)
```

1,500 events + 30 duplicates, 17 columns, with injected data-quality problems (missing and negative
budgets, impossible guest counts, mixed spellings in Hebrew and English, mixed date and number
formats). The budget formula and the exact list of problems are documented in
`src/rivatar/data_generator.py`. Category codes come from `src/rivatar/vocab.py`, shared by the form,
the data and the model.

## Tests

```powershell
pytest
```

## Project layout

```
app/                      Streamlit website
  streamlit_app.py        entry point and navigation
  content.py              all site text, event display names
  theme.py, ui.py         styling and HTML building blocks
  views/                  home, gallery, ml_lab pages
  static/fonts/           self-hosted fonts (OFL)
  static/projects/        curated web photos and video loops per project (+ static/media.json)
  assets/                 logos, favicon
src/rivatar/
  config.py               paths, seed, settings (.env via python-dotenv)
  vocab.py                shared category codes (form = data = model)
  data_generator.py       synthetic dataset
  leads.py                form validation and leads.csv
  estimator.py            estimate_budget() stub (phase 3)
  crews/, tools/, flow.py placeholders (phases 2–4)
scripts/prepare_media.py  photo pipeline
tests/                    pytest
docs/design/              approved home-page design draft
data/                     generated files only (gitignored)
```

## Roadmap
| Phase | Scope |
|---|---|
| **1** | Project foundation, media pipeline, RIVATAR website in Streamlit, synthetic data generator |
| 2 | Crew 1 (4 agents): cleaning, EDA, insights, JSON data contract + validation |
| 3 | Crew 2 (4 agents): features, 3 model versions, CV selection, evaluation, Model Card + live estimate |
| 4 | CrewAI Flow with contract gate, quality and reproducibility gate, `--inject-violation` demo, ML LAB |
| 5 | CI (GitHub Actions), docs, presentation |
