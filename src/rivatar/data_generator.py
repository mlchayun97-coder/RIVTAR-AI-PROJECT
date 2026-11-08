"""Synthetic event dataset for RIVATAR PRODUCTIONS (input for Crew 1 in phase 2).

The company has no shareable historical data, so this module generates ~1,500 events that follow the
business logic of an Israeli boutique/luxury event producer, then injects the data-quality problems
of a real CRM export so the data-cleaning crew has real work to do.

Reproducible: one seed (42) drives every random choice; the same seed gives a byte-identical CSV.
The data is synthetic: the numbers demonstrate the method, they are not RIVATAR's real prices.

Columns (17, codes from rivatar.vocab):
    event_id, inquiry_date, event_date, event_type, client_type, guest_count, region, venue_type,
    catering_level, design_package, extra_lighting, extra_photography, extra_music_talent,
    extra_shuttles, extra_social_promo, lead_source, total_budget_ils

Budget formula (ILS, before noise)
----------------------------------
    variable = BASE_PER_GUEST[event_type] * guests * (guests / 250) ** -0.08     # mild economies of scale
               * CATERING[catering_level] * REGION[region] * VENUE[venue_type] * SEASON[month]
    design   = DESIGN[design_package] * (guests / 250) ** 0.3
    extras   = lighting 6,500 + photography 8,000 + music & talent 12,000
               + shuttles max(3,000, 25 * guests) + social promotion 4,500       (only the chosen ones)
    total    = (FIXED_FEE[event_type] + variable + design + extras) * LogNormal(0, 0.07), rounded to ₪100

    BASE_PER_GUEST: wedding 320, bar_mitzvah 280, bat_mitzvah 270, family_event 230,
                    product_launch 300, conference 210, corporate_event 260, business_dinner 380
    FIXED_FEE:      wedding 12,000, bar/bat mitzvah 9,000, family_event 5,000, product_launch 15,000,
                    conference 14,000, corporate_event 10,000, business_dinner 6,000
    CATERING:       basic 0.85, premium 1.00, luxury 1.35
    REGION:         jerusalem 1.00, tel_aviv 1.12, center 1.05, north 0.93, south 0.90, abroad 1.60
    VENUE:          hall 1.00, garden 1.08, hotel 1.18, outdoor 1.12, company_office 0.80
    SEASON:         May, Jun, Sep, Oct 1.10 (peak) · Dec, Jan, Feb 0.92 (low) · other months 1.00
    DESIGN:         standard 8,000, premium 18,000, luxury 35,000

    Example: wedding, 250 guests, Jerusalem, hall, premium catering, standard design, photography +
    music in a neutral month = 12,000 + 80,000 + 8,000 + 20,000 = ₪120,000 (before noise).
    After log(), the product of multipliers becomes a sum, so a linear model on log(budget) is a
    strong baseline; this is on purpose (see the proposal).

Injected data-quality problems (counts are exact for n=1500, seed 42; logged in injection_log.json)
-------------------------------------------------------------------------------------------------
    duplicate rows            30  same event_id appears twice (10 of them re-typed with other spellings)
    budget missing/negative   21  empty or e.g. -85000 (target: rows must be dropped)
    event before inquiry       7  event_date earlier than inquiry_date (typo)
    guests impossible/missing 67  empty, 0, -5, 99999, 15000
    missing categories        73  catering_level (40) and region (33) empty
    client/type mismatch       6  business event marked as private client or the reverse
    inconsistent spelling     all  Wedding / WEDDING / חתונה, TLV / JLM / Tel Aviv, Premium / PREMIUM ...
    mixed formats             all  dates ISO / dd/mm/yyyy / yyyy/mm/dd; budget as "₪120,000", "120000 ILS";
                                   extras as 1/0, yes/no, Y/N, כן/לא, True/False

Usage:
    python -m rivatar.data_generator                 # -> data/raw/events_raw.csv
    python -m rivatar.data_generator --n 1500 --seed 42 --out data/raw/events_raw.csv
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from rivatar import config, vocab

COLUMNS = [
    "event_id", "inquiry_date", "event_date", "event_type", "client_type", "guest_count", "region",
    "venue_type", "catering_level", "design_package", *vocab.EXTRAS.keys(), "lead_source", "total_budget_ils",
]

# ---------------------------------------------------------------- business logic
EVENT_TYPE_P = {"wedding": .30, "bar_mitzvah": .14, "bat_mitzvah": .12, "family_event": .08,
                "product_launch": .08, "conference": .10, "corporate_event": .12, "business_dinner": .06}
GUESTS = {  # (median, log-sd, low clip, high clip)
    "wedding": (300, .35, 60, 900), "bar_mitzvah": (220, .35, 50, 600), "bat_mitzvah": (200, .35, 50, 600),
    "family_event": (110, .45, 20, 350), "product_launch": (200, .50, 30, 900),
    "conference": (350, .55, 50, 1500), "corporate_event": (250, .50, 30, 1200),
    "business_dinner": (60, .45, 10, 200),
}
REGION_P = {
    "private": {"jerusalem": .30, "tel_aviv": .22, "center": .25, "north": .10, "south": .08, "abroad": .05},
    "business": {"jerusalem": .15, "tel_aviv": .40, "center": .30, "north": .06, "south": .04, "abroad": .05},
}
VENUE_P = {
    "private": {"hall": .35, "garden": .30, "hotel": .20, "outdoor": .15, "company_office": 0.0},
    "business": {"hall": .20, "garden": .15, "hotel": .30, "outdoor": .10, "company_office": .25},
}
CATERING_P = {"private": {"basic": .25, "premium": .45, "luxury": .30},
              "business": {"basic": .35, "premium": .45, "luxury": .20}}
# design package follows catering level (people who pay for luxury food tend to pay for design)
DESIGN_GIVEN_CATERING = {"basic": {"standard": .70, "premium": .25, "luxury": .05},
                         "premium": {"standard": .30, "premium": .50, "luxury": .20},
                         "luxury": {"standard": .08, "premium": .37, "luxury": .55}}
EXTRA_P = {  # probability of each extra service, private vs business
    "private": {"extra_lighting": .55, "extra_photography": .85, "extra_music_talent": .75,
                "extra_shuttles": .20, "extra_social_promo": .10},
    "business": {"extra_lighting": .60, "extra_photography": .60, "extra_music_talent": .35,
                 "extra_shuttles": .25, "extra_social_promo": .55},
}
LEAD_P = {"instagram": .28, "referral": .30, "google": .15, "facebook": .07, "returning_client": .12,
          "vendor_venue": .08}
LEAD_DAYS = {"private": (90, 420), "business": (21, 200)}

BASE_PER_GUEST = {"wedding": 320, "bar_mitzvah": 280, "bat_mitzvah": 270, "family_event": 230,
                  "product_launch": 300, "conference": 210, "corporate_event": 260, "business_dinner": 380}
FIXED_FEE = {"wedding": 12_000, "bar_mitzvah": 9_000, "bat_mitzvah": 9_000, "family_event": 5_000,
             "product_launch": 15_000, "conference": 14_000, "corporate_event": 10_000, "business_dinner": 6_000}
CATERING_M = {"basic": .85, "premium": 1.0, "luxury": 1.35}
REGION_M = {"jerusalem": 1.0, "tel_aviv": 1.12, "center": 1.05, "north": .93, "south": .90, "abroad": 1.60}
VENUE_M = {"hall": 1.0, "garden": 1.08, "hotel": 1.18, "outdoor": 1.12, "company_office": .80}
SEASON_M = {5: 1.10, 6: 1.10, 9: 1.10, 10: 1.10, 12: .92, 1: .92, 2: .92}
DESIGN_COST = {"standard": 8_000, "premium": 18_000, "luxury": 35_000}
EXTRA_COST = {"extra_lighting": 6_500, "extra_photography": 8_000, "extra_music_talent": 12_000,
              "extra_social_promo": 4_500}
NOISE_SD = 0.07

INQUIRY_START = date(2023, 1, 1)
INQUIRY_DAYS = 3 * 365 + 180  # inquiries until mid-2026


def budget_ils(event_type: str, guests: int, region: str, venue: str, catering: str, design: str,
               extras: dict[str, int], month: int) -> float:
    """Noise-free budget from the formula in the module docstring."""
    variable = (BASE_PER_GUEST[event_type] * guests * (guests / 250) ** -0.08
                * CATERING_M[catering] * REGION_M[region] * VENUE_M[venue] * SEASON_M.get(month, 1.0))
    design_cost = DESIGN_COST[design] * (guests / 250) ** 0.3
    extra_cost = sum(EXTRA_COST[k] for k, v in extras.items() if v and k in EXTRA_COST)
    if extras.get("extra_shuttles"):
        extra_cost += max(3_000, 25 * guests)
    return FIXED_FEE[event_type] + variable + design_cost + extra_cost


def _choice(rng: np.random.Generator, probs: dict[str, float]) -> str:
    keys = list(probs)
    p = np.array([probs[k] for k in keys], dtype=float)
    return keys[int(rng.choice(len(keys), p=p / p.sum()))]


def generate_clean(n: int = 1500, seed: int = config.SEED) -> pd.DataFrame:
    """Clean, typed events (the 'truth' before any quality problems are injected)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(1, n + 1):
        et = _choice(rng, EVENT_TYPE_P)
        ct = vocab.client_type_for(et)
        med, sd, lo, hi = GUESTS[et]
        guests = int(np.clip(round(med * np.exp(rng.normal(0, sd))), lo, hi))
        region = _choice(rng, REGION_P[ct])
        venue = _choice(rng, VENUE_P[ct])
        catering = _choice(rng, CATERING_P[ct])
        design = _choice(rng, DESIGN_GIVEN_CATERING[catering])
        extras = {k: int(rng.random() < p) for k, p in EXTRA_P[ct].items()}
        inquiry = INQUIRY_START + timedelta(days=int(rng.integers(0, INQUIRY_DAYS)))
        lo_d, hi_d = LEAD_DAYS[ct]
        event_d = inquiry + timedelta(days=int(rng.integers(lo_d, hi_d)))
        total = budget_ils(et, guests, region, venue, catering, design, extras, event_d.month)
        total = round(total * float(np.exp(rng.normal(0, NOISE_SD))), -2)
        rows.append({
            "event_id": f"EVT-{i:05d}", "inquiry_date": inquiry, "event_date": event_d, "event_type": et,
            "client_type": ct, "guest_count": guests, "region": region, "venue_type": venue,
            "catering_level": catering, "design_package": design, **extras,
            "lead_source": _choice(rng, LEAD_P), "total_budget_ils": float(total),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


# ---------------------------------------------------------------- messiness
SPELLINGS = {
    "event_type": {
        "wedding": ["Wedding", "WEDDING", "wedding ", "חתונה"],
        "bar_mitzvah": ["Bar Mitzvah", "bar-mitzvah", "BAR_MITZVAH", "בר מצווה"],
        "bat_mitzvah": ["Bat Mitzvah", "bat-mitzvah", "בת מצווה"],
        "family_event": ["Family Event", "family", "אירוע משפחתי"],
        "product_launch": ["Product Launch", "launch", "השקת מוצר"],
        "conference": ["Conference", "CONFERENCE", "כנס"],
        "corporate_event": ["Corporate", "corporate event", "אירוע חברה"],
        "business_dinner": ["Business Dinner", "dinner", "דינר עסקי"],
    },
    "region": {
        "jerusalem": ["JLM", "Jerusalem", "jerusalem ", "ירושלים"],
        "tel_aviv": ["TLV", "Tel Aviv", "tel-aviv", "תל אביב"],
        "center": ["Center", "CENTER", "מרכז"],
        "north": ["North", "צפון"],
        "south": ["South", "דרום"],
        "abroad": ["Abroad", "ABROAD", 'חו"ל'],
    },
    "venue_type": {
        "hall": ["Hall", "HALL", "אולם"], "garden": ["Garden", "גן אירועים"], "hotel": ["Hotel", "מלון"],
        "outdoor": ["Outdoor", "לוקיישן חוץ"], "company_office": ["Office", "משרדי החברה"],
    },
    "catering_level": {"basic": ["Basic", "BASIC", "בסיסי"], "premium": ["Premium", "PREMIUM", "פרימיום"],
                       "luxury": ["Luxury", "LUXURY", "יוקרה"]},
    "design_package": {"standard": ["Standard", "STANDARD", "סטנדרט"], "premium": ["Premium", "פרימיום"],
                       "luxury": ["Luxury", "יוקרה"]},
    "lead_source": {"instagram": ["Instagram", "IG"], "referral": ["Referral", "המלצה"],
                    "google": ["Google", "GOOGLE"], "facebook": ["Facebook", "FB"],
                    "returning_client": ["Returning", "לקוח חוזר"], "vendor_venue": ["Vendor", "ספק"]},
}
YES = ["1", "yes", "Y", "כן", "True"]
NO = ["0", "no", "N", "לא", "False"]
SPELLING_RATE = 0.30  # share of cells written with a non-canonical spelling


def _fmt_date(d: date, style: int) -> str:
    return (d.isoformat(), d.strftime("%d/%m/%Y"), d.strftime("%Y/%m/%d"))[style]


def _fmt_budget(x: float, style: int) -> str:
    return (f"{x:.0f}", f"₪{x:,.0f}", f"{x:.0f} ILS", f"{x:,.0f} ₪", f"{x:.1f}")[style]


def inject_issues(clean: pd.DataFrame, seed: int = config.SEED) -> tuple[pd.DataFrame, dict]:
    """Return (raw dataframe of strings, log of injected problems)."""
    rng = np.random.default_rng(seed + 1)
    df = clean.copy()
    n = len(df)
    idx = np.arange(n)
    log: dict[str, object] = {}

    def take(k: int, pool: np.ndarray) -> np.ndarray:
        return np.sort(rng.choice(pool, size=k, replace=False))

    # Each row gets at most one 'hard' problem, so the counts stay exact and easy to verify.
    free = idx.copy()

    def claim(k: int) -> np.ndarray:
        nonlocal free
        picked = take(k, free)
        free = np.setdiff1d(free, picked)
        return picked

    out = df.astype(object)

    # budget missing / negative (21)
    miss_b, neg_b = claim(12), claim(9)
    out.loc[miss_b, "total_budget_ils"] = None
    out.loc[neg_b, "total_budget_ils"] = -df.loc[neg_b, "total_budget_ils"].to_numpy()
    log["budget_missing"], log["budget_negative"] = len(miss_b), len(neg_b)

    # event before inquiry (7): event date moved to before the inquiry date
    early = claim(7)
    for i in early:
        out.at[i, "event_date"] = df.at[i, "inquiry_date"] - timedelta(days=int(rng.integers(5, 120)))
    log["event_before_inquiry"] = len(early)

    # guests impossible / missing (67)
    g_missing, g_bad = claim(35), claim(32)
    out.loc[g_missing, "guest_count"] = None
    out.loc[g_bad, "guest_count"] = rng.choice([0, -5, 99999, 15000], size=len(g_bad))
    log["guests_missing"], log["guests_impossible"] = len(g_missing), len(g_bad)

    # missing categories (73)
    m_cat, m_reg = claim(40), claim(33)
    out.loc[m_cat, "catering_level"] = None
    out.loc[m_reg, "region"] = None
    log["catering_missing"], log["region_missing"] = len(m_cat), len(m_reg)

    # client type does not match event type (6)
    mism = claim(6)
    out.loc[mism, "client_type"] = ["business" if c == "private" else "private" for c in df.loc[mism, "client_type"]]
    log["client_type_mismatch"] = len(mism)

    # inconsistent spelling, everywhere
    for col, variants in SPELLINGS.items():
        for i in idx:
            v = out.at[i, col]
            if v is not None and rng.random() < SPELLING_RATE:
                out.at[i, col] = variants[v][int(rng.integers(len(variants[v])))]
    for i in idx:
        if rng.random() < 0.15:
            out.at[i, "client_type"] = {"private": "Private", "business": "BUSINESS"}[out.at[i, "client_type"]]

    # mixed formats: dates, budget text, yes/no flags
    for col in ("inquiry_date", "event_date"):
        styles = rng.choice(3, size=n, p=[.6, .25, .15])
        out[col] = [_fmt_date(d, int(s)) for d, s in zip(out[col], styles)]
    b_styles = rng.choice(5, size=n, p=[.55, .2, .1, .1, .05])
    out["total_budget_ils"] = [None if b is None else _fmt_budget(float(b), int(s))
                               for b, s in zip(out["total_budget_ils"], b_styles)]
    for col in vocab.EXTRAS:
        s = rng.choice(5, size=n, p=[.6, .1, .1, .1, .1])
        out[col] = [(YES if v else NO)[int(k)] for v, k in zip(out[col], s)]
    out["guest_count"] = [None if g is None else str(int(g)) for g in out["guest_count"]]

    # duplicates (30): same event_id again; 10 of them re-typed with other spellings
    dup_src = take(30, free)  # from rows without another hard problem, so all counts stay exact
    dups = out.loc[dup_src].copy()
    for j, i in enumerate(dup_src[:10]):
        et = clean.at[i, "event_type"]
        dups.at[i, "event_type"] = SPELLINGS["event_type"][et][0]
    out = pd.concat([out, dups], ignore_index=True)
    log["duplicate_rows"] = len(dups)

    # shuffle so duplicates are not at the end
    out = out.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    log["rows_total"] = len(out)
    log["rows_unique_events"] = n
    return out[COLUMNS], log


def generate(n: int = 1500, seed: int = config.SEED) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    clean = generate_clean(n, seed)
    raw, log = inject_issues(clean, seed)
    return raw, clean, log


def write(raw: pd.DataFrame, log: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    (out.parent / "injection_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")


def generate_raw_dataset(path: Path = config.RAW_DATA, n: int = config.N_ROWS, seed: int = config.SEED) -> pd.DataFrame:
    """Step 1 of the Flow: write the messy raw CSV (+ injection_log.json) and return it."""
    raw, _, log = generate(n, seed)
    write(raw, log, path)
    return raw


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the synthetic RIVATAR events dataset")
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--out", type=Path, default=config.RAW_EVENTS_CSV)
    args = ap.parse_args(argv)
    raw, clean, log = generate(args.n, args.seed)
    write(raw, log, args.out)
    print(f"Wrote {len(raw):,} rows ({args.n:,} events + duplicates) -> {args.out}")
    print(f"Budget (clean): median ₪{clean['total_budget_ils'].median():,.0f}, "
          f"range ₪{clean['total_budget_ils'].min():,.0f}–₪{clean['total_budget_ils'].max():,.0f}")
    print("Injected:", json.dumps(log, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
