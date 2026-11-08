"""Deterministic data operations used by Crew 1 (Data Team).

Each function reads its inputs from disk and writes its outputs to disk, so every step leaves an
inspectable artifact. The agents decide *when* to call a tool and *how to explain* the result; the
numbers come from this tested code, so a run is reproducible with or without an LLM.

Ported from the ML prototype and adapted to this project's shared vocabulary (rivatar.vocab) and to
the problems rivatar.data_generator injects (Hebrew spellings, three date formats, "₪120,000" /
"120000 ILS" budgets, כן/לא flags, client/type mismatches, duplicates).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from rivatar import config, vocab  # noqa: E402
from rivatar.data_generator import NO, SPELLINGS, YES  # noqa: E402

SERVICES = list(vocab.EXTRAS)
CATEGORICAL = ["event_type", "client_type", "region", "venue_type", "catering_level",
               "design_package", "lead_source"]
DATE_COLS = ["inquiry_date", "event_date"]
PEAK_MONTHS = (5, 6, 9, 10)  # matches the generator's season multipliers


def _norm(s) -> str | float:
    if pd.isna(s):
        return np.nan
    return " ".join(str(s).strip().lower().split())


def _code_map(col: str, codes: dict[str, str]) -> dict[str, str]:
    """Every known spelling of a category (code, Hebrew label, generator variants) -> code."""
    m: dict[str, str] = {}
    for code, he in codes.items():
        for v in [code, code.replace("_", " "), code.replace("_", "-"), he,
                  *SPELLINGS.get(col, {}).get(code, [])]:
            m[_norm(v)] = code
    return m


MAPS = {
    "event_type": _code_map("event_type", vocab.EVENT_TYPES),
    "region": _code_map("region", vocab.REGIONS),
    "venue_type": _code_map("venue_type", vocab.VENUE_TYPES),
    "catering_level": _code_map("catering_level", vocab.CATERING_LEVELS),
    "design_package": _code_map("design_package", vocab.DESIGN_PACKAGES),
    "lead_source": _code_map("lead_source", vocab.LEAD_SOURCES),
}
BOOL_MAP = {**{_norm(v): True for v in YES}, **{_norm(v): False for v in NO}}


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_date(s) -> pd.Timestamp:
    """ISO (2025-06-01), day-first (01/06/2025) or year-first with slashes (2025/06/01)."""
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip().split(" ")[0]
    if "/" in s:
        fmt = "%Y/%m/%d" if len(s.split("/")[0]) == 4 else "%d/%m/%Y"
    else:
        fmt = "%Y-%m-%d"
    return pd.to_datetime(s, format=fmt, errors="coerce")


def _parse_money(v) -> float:
    if pd.isna(v):
        return np.nan
    s = str(v).replace("₪", "").replace("ILS", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


# ---------------------------------------------------------------- cleaning
def clean_data(raw_path=config.RAW_DATA, out_path=config.CLEAN_DATA, report_path=config.CLEANING_REPORT) -> dict:
    df = pd.read_csv(raw_path, dtype=str, keep_default_na=True)
    report: dict = {"rows_in": int(len(df)), "steps": []}

    def log(step: str, **kw):
        report["steps"].append({"step": step, **kw})

    before = len(df)
    df = df.drop_duplicates(subset=[config.ID_COLUMN], keep="first")
    log("drop_duplicate_event_ids", removed=before - len(df))

    unknown: dict[str, list[str]] = {}
    for col, mapping in MAPS.items():
        def to_code(v, col=col, mapping=mapping):
            k = _norm(v)
            if pd.isna(k):
                return np.nan
            if k not in mapping:
                unknown.setdefault(col, []).append(k)
            return mapping.get(k, np.nan)
        df[col] = df[col].map(to_code)
    log("normalize_category_spellings", unknown_values={k: sorted(set(v))[:5] for k, v in unknown.items()})

    # client_type follows event_type by definition; the CRM sometimes has it wrong.
    expected = df["event_type"].map(vocab.client_type_for, na_action="ignore")
    wrong = int(((df["client_type"].map(_norm) != expected) & expected.notna()).sum())
    df["client_type"] = expected
    log("derive_client_type_from_event_type", corrected=wrong)

    for s in SERVICES:
        df[s] = df[s].map(lambda v: BOOL_MAP.get(_norm(v), False) if not pd.isna(v) else False)
    log("normalize_yes_no_flags", columns=SERVICES)

    for c in DATE_COLS:
        df[c] = df[c].map(_parse_date)
    log("parse_mixed_date_formats", formats=["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"])

    df[config.TARGET] = df[config.TARGET].map(_parse_money)
    before = len(df)
    df = df[df[config.TARGET].notna() & (df[config.TARGET] > 0)]
    log("drop_missing_or_non_positive_budget", removed=before - len(df))

    before = len(df)
    df = df[df["event_type"].notna() & df["inquiry_date"].notna() & df["event_date"].notna()]
    log("drop_rows_without_event_type_or_dates", removed=before - len(df))

    before = len(df)
    df = df[df["event_date"] >= df["inquiry_date"]]
    log("drop_event_before_inquiry", removed=before - len(df))

    df["guest_count"] = pd.to_numeric(df["guest_count"], errors="coerce")
    invalid = ~df["guest_count"].between(vocab.GUESTS_MIN, vocab.GUESTS_MAX)
    n_invalid = int((invalid & df["guest_count"].notna()).sum())
    n_missing = int(df["guest_count"].isna().sum())
    df.loc[invalid, "guest_count"] = np.nan
    med = df.groupby("event_type")["guest_count"].transform("median")
    df["guest_count"] = df["guest_count"].fillna(med).round().astype(int)
    log("impute_guest_count_by_event_type_median", impossible_values_nulled=n_invalid,
        missing_imputed=n_missing + n_invalid)

    imputed = {}
    for c in ["catering_level", "region", "venue_type", "design_package"]:
        n = int(df[c].isna().sum())
        mode = df.groupby("event_type")[c].transform(lambda s: s.mode().iloc[0] if s.notna().any() else np.nan)
        df[c] = df[c].fillna(mode)
        imputed[c] = n
    # company offices are only valid for business events
    bad_venue = (df["venue_type"] == "company_office") & (df["client_type"] == "private")
    df.loc[bad_venue, "venue_type"] = "hall"
    imputed["private_event_at_company_office(->hall)"] = int(bad_venue.sum())
    n_ls = int(df["lead_source"].isna().sum())
    df["lead_source"] = df["lead_source"].fillna("unknown")
    imputed["lead_source(->unknown)"] = n_ls
    log("impute_categoricals", imputed=imputed)

    df = df.sort_values(config.ID_COLUMN).reset_index(drop=True)
    for c in DATE_COLS:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    df[config.TARGET] = df[config.TARGET].astype(float)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8", lineterminator="\n")
    report["rows_out"] = int(len(df))
    report["remaining_nulls"] = {k: int(v) for k, v in df.isna().sum().items() if v}
    report["output_sha256"] = file_sha256(out_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


# --------------------------------------------------------------------- EDA
INK, MUTED, GOLD, GRID = "#2B2622", "#8A8178", "#A8833A", "#E7E1D8"


def _style(ax, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=10)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig, path) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=110, metadata={"Software": None})  # no timestamp/software tag: stable files
    plt.close(fig)
    return path.name


def run_eda(clean_path=config.CLEAN_DATA, out_dir=config.EDA_DIR, summary_path=config.EDA_SUMMARY) -> dict:
    df = pd.read_csv(clean_path, parse_dates=DATE_COLS)
    out_dir.mkdir(parents=True, exist_ok=True)
    y = df[config.TARGET]
    df["month"] = df["event_date"].dt.month
    df["lead_days"] = (df["event_date"] - df["inquiry_date"]).dt.days
    df["budget_per_guest"] = y / df["guest_count"]

    def grp(col):
        g = df.groupby(col)[config.TARGET].agg(["count", "median", "mean"]).round(0)
        return {str(k): {kk: float(vv) for kk, vv in v.items()} for k, v in g.to_dict("index").items()}

    service_lift = {}
    for s in SERVICES:
        with_s, without = y[df[s]].median(), y[~df[s]].median()
        service_lift[s] = {"median_with": float(with_s), "median_without": float(without),
                           "lift_pct": round(float(with_s / without - 1) * 100, 1)}

    summary = {
        "n_rows": int(len(df)),
        "date_range": [df["event_date"].min().strftime("%Y-%m-%d"), df["event_date"].max().strftime("%Y-%m-%d")],
        "target_stats": {k: round(float(v), 1) for k, v in y.describe().items()},
        "target_skew": round(float(y.skew()), 3),
        "log_target_skew": round(float(np.log(y).skew()), 3),
        "correlation_with_target": {c: round(float(df[c].corr(y)), 3) for c in ["guest_count", "lead_days"]},
        "budget_per_guest_median": round(float(df["budget_per_guest"].median()), 1),
        "by_event_type": grp("event_type"),
        "by_region": grp("region"),
        "by_catering_level": grp("catering_level"),
        "by_design_package": grp("design_package"),
        "by_month": grp("month"),
        "service_lift": service_lift,
        "plots": [],
    }

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(y / 1000, bins=40, color=GOLD, edgecolor="white", linewidth=0.6)
    _style(ax, "Distribution of total event budget", "Budget (thousand ₪)", "Events")
    summary["plots"].append(_save(fig, out_dir / "budget_distribution.png"))

    med = df.groupby("event_type")[config.TARGET].median().sort_values() / 1000
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(med.index, med.values, color=GOLD, height=0.6)
    for i, v in enumerate(med.values):
        ax.text(v + 2, i, f"{v:,.0f}K", va="center", fontsize=8, color=INK)
    _style(ax, "Median budget by event type", "Median budget (thousand ₪)")
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    summary["plots"].append(_save(fig, out_dir / "budget_by_event_type.png"))

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(df["guest_count"], y / 1000, s=10, color=GOLD, alpha=0.45, linewidths=0)
    _style(ax, "Guests vs. budget", "Guest count", "Budget (thousand ₪)")
    summary["plots"].append(_save(fig, out_dir / "guests_vs_budget.png"))

    bym = df.groupby("month")["budget_per_guest"].median()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(bym.index, bym.values, color=GOLD, linewidth=2, marker="o", markersize=5)
    ax.set_xticks(range(1, 13))
    _style(ax, "Median budget per guest by event month", "Month", "₪ per guest")
    summary["plots"].append(_save(fig, out_dir / "budget_per_guest_by_month.png"))

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


# ---------------------------------------------------------------- insights
def write_insights(summary_path=config.EDA_SUMMARY, cleaning_path=config.CLEANING_REPORT,
                   out_path=config.INSIGHTS_MD, narrative: str | None = None) -> str:
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    c = json.loads(cleaning_path.read_text(encoding="utf-8"))
    et, dp, cat, reg, mon = (s["by_event_type"], s["by_design_package"], s["by_catering_level"],
                             s["by_region"], s["by_month"])
    top = max(et, key=lambda k: et[k]["median"])
    low = min(et, key=lambda k: et[k]["median"])
    peak = [str(m) for m in PEAK_MONTHS if str(m) in mon]
    off = [m for m in mon if int(m) not in PEAK_MONTHS]
    peak_med = float(np.median([mon[m]["median"] for m in peak])) if peak else float("nan")
    off_med = float(np.median([mon[m]["median"] for m in off])) if off else float("nan")
    lifts = sorted(s["service_lift"].items(), key=lambda kv: -kv[1]["lift_pct"])

    lines = [
        "# RIVATAR – Data Insights", "",
        "## Data quality",
        f"- Raw rows: **{c['rows_in']}**, clean rows: **{c['rows_out']}** ({c['rows_in'] - c['rows_out']} removed).",
    ]
    for st in c["steps"]:
        extra = {k: v for k, v in st.items() if k != "step"}
        lines.append(f"- `{st['step']}`: {extra}")
    lines += [
        "", "## Key findings",
        f"1. **Event type drives budget.** `{top}` has the highest median budget (₪{et[top]['median']:,.0f}); "
        f"`{low}` the lowest (₪{et[low]['median']:,.0f}).",
        f"2. **Guest count is the strongest numeric driver** (correlation "
        f"{s['correlation_with_target']['guest_count']}). Median spend per guest is ₪{s['budget_per_guest_median']:,.0f}.",
        f"3. **Design package matters:** luxury median ₪{dp['luxury']['median']:,.0f} vs standard "
        f"₪{dp['standard']['median']:,.0f}. Catering luxury ₪{cat['luxury']['median']:,.0f} vs basic "
        f"₪{cat['basic']['median']:,.0f}.",
        f"4. **Location:** events abroad have median ₪{reg.get('abroad', {}).get('median', float('nan')):,.0f}; "
        f"Jerusalem ₪{reg.get('jerusalem', {}).get('median', float('nan')):,.0f}.",
        f"5. **Seasonality:** peak months (May, Jun, Sep, Oct) median ₪{peak_med:,.0f} vs other months ₪{off_med:,.0f}.",
        "6. **Services with the largest lift:** " + ", ".join(f"`{k}` (+{v['lift_pct']}%)" for k, v in lifts[:3]) + ".",
        f"7. **The target is right-skewed** (skew {s['target_skew']}; after log {s['log_target_skew']}), "
        "so the modelling team should train on log(budget).",
        "", "## Recommendations for the modelling team",
        "- Use guest_count, event_type, design_package, catering_level, region, venue_type and the extra-service flags.",
        "- Derive season / weekday / lead time from the dates; do not feed raw dates.",
        "- `client_type` is fully determined by `event_type` – keep one of them to avoid redundancy.",
        "- `event_id` and `lead_source` should not influence price; exclude them from features.",
    ]
    if narrative:
        lines += ["", "## Analyst narrative (LLM agent)", "", narrative.strip()]
    text = "\n".join(lines) + "\n"
    out_path.write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------- data contract
def build_data_contract(clean_path=config.CLEAN_DATA, out_path=config.DATA_CONTRACT) -> dict:
    """Describe the clean dataset as a machine-checkable JSON contract."""
    df = pd.read_csv(clean_path)
    cols: dict = {
        config.ID_COLUMN: {"dtype": "string", "nullable": False, "unique": True, "pattern": r"^EVT-\d{5}$"},
        "inquiry_date": {"dtype": "date", "nullable": False, "format": "%Y-%m-%d"},
        "event_date": {"dtype": "date", "nullable": False, "format": "%Y-%m-%d"},
        "event_type": {"dtype": "category", "nullable": False, "allowed_values": sorted(vocab.EVENT_TYPES)},
        "client_type": {"dtype": "category", "nullable": False, "allowed_values": sorted(vocab.CLIENT_TYPES)},
        "guest_count": {"dtype": "integer", "nullable": False, "min": vocab.GUESTS_MIN, "max": vocab.GUESTS_MAX},
        "region": {"dtype": "category", "nullable": False, "allowed_values": sorted(vocab.REGIONS)},
        "venue_type": {"dtype": "category", "nullable": False, "allowed_values": sorted(vocab.VENUE_TYPES)},
        "catering_level": {"dtype": "category", "nullable": False, "allowed_values": sorted(vocab.CATERING_LEVELS)},
        "design_package": {"dtype": "category", "nullable": False, "allowed_values": sorted(vocab.DESIGN_PACKAGES)},
        **{s: {"dtype": "boolean", "nullable": False} for s in SERVICES},
        "lead_source": {"dtype": "category", "nullable": False,
                        "allowed_values": sorted([*vocab.LEAD_SOURCES, "unknown"])},
        config.TARGET: {"dtype": "float", "nullable": False, "min": 1000.0, "max": 5_000_000.0},
    }
    contract = {
        "contract_name": "rivatar_events_clean",
        "version": "1.0.0",
        "owner": "Data Team (Crew 1)",
        "consumer": "ML Team (Crew 2)",
        "dataset_path": clean_path.relative_to(config.ROOT).as_posix(),
        "dataset_sha256": file_sha256(clean_path),
        "row_count": int(len(df)),
        "min_rows": config.MIN_ROWS_AFTER_CLEANING,
        "primary_key": config.ID_COLUMN,
        "target": config.TARGET,
        "columns": cols,
        "rules": [
            {"name": "event_after_inquiry", "expression": "event_date >= inquiry_date"},
            {"name": "client_type_matches_event_type", "expression": "client_type == client_type_for(event_type)"},
        ],
        "event_client_type": {k: vocab.client_type_for(k) for k in vocab.EVENT_TYPES},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    return contract
