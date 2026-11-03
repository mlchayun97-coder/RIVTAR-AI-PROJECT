"""The synthetic data must be reproducible and really messy (so Crew 1 has real work)."""

import hashlib

import pandas as pd
import pytest

from rivatar import data_generator as dg
from rivatar import vocab


@pytest.fixture(scope="module")
def gen():
    return dg.generate(1500, 42)


def _csv_hash(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def test_deterministic_same_seed(gen):
    raw2, clean2, log2 = dg.generate(1500, 42)
    assert _csv_hash(gen[0]) == _csv_hash(raw2)
    assert _csv_hash(gen[1]) == _csv_hash(clean2)
    assert gen[2] == log2


def test_different_seed_differs(gen):
    raw_other, _, _ = dg.generate(1500, 7)
    assert _csv_hash(gen[0]) != _csv_hash(raw_other)


def test_shape_and_columns(gen):
    raw, clean, log = gen
    assert list(raw.columns) == dg.COLUMNS and len(dg.COLUMNS) == 17
    assert len(clean) == 1500 and len(raw) == 1530
    assert log["duplicate_rows"] == 30


def test_clean_follows_vocabulary_and_rules(gen):
    clean = gen[1]
    assert set(clean.event_type) <= set(vocab.EVENT_TYPES)
    assert set(clean.region) <= set(vocab.REGIONS)
    assert set(clean.catering_level) <= set(vocab.CATERING_LEVELS)
    assert set(clean.design_package) <= set(vocab.DESIGN_PACKAGES)
    assert clean.guest_count.between(vocab.GUESTS_MIN, vocab.GUESTS_MAX).all()
    assert (clean.event_date > clean.inquiry_date).all()
    assert (clean.client_type == clean.event_type.map(vocab.client_type_for)).all()
    office = clean.venue_type == "company_office"
    assert clean.loc[office, "event_type"].isin(vocab.BUSINESS_EVENT_TYPES).all()
    assert clean.event_id.is_unique


def test_budget_formula_is_sensible(gen):
    clean = gen[1]
    assert (clean.total_budget_ils > 0).all()
    # proposal example: 250-guest wedding in Jerusalem ~ ₪118k
    b = dg.budget_ils("wedding", 250, "jerusalem", "hall", "premium", "standard",
                      {"extra_photography": 1, "extra_music_talent": 1}, 7)
    assert 100_000 < b < 140_000
    # more guests / luxury cost more
    base = dict(event_type="wedding", region="jerusalem", venue="hall", design="standard", extras={}, month=7)
    assert dg.budget_ils(guests=400, catering="premium", **base) > dg.budget_ils(guests=200, catering="premium", **base)
    assert dg.budget_ils(guests=250, catering="luxury", **base) > dg.budget_ils(guests=250, catering="basic", **base)


def test_raw_is_really_messy(gen):
    raw, _, log = gen
    # duplicates by event id
    assert raw.event_id.duplicated().sum() == 30
    # missing / negative budgets and budgets written as text with ₪
    b = raw.total_budget_ils
    assert b.isna().sum() == 12
    assert b.dropna().str.contains("-").sum() == 9      # e.g. "-85000" or "₪-85,000"
    assert b.dropna().str.contains("₪").sum() > 100
    # impossible or missing guests
    g = pd.to_numeric(raw.guest_count, errors="coerce")
    assert raw.guest_count.isna().sum() >= 35
    assert ((g < vocab.GUESTS_MIN) | (g > vocab.GUESTS_MAX)).sum() >= 32
    # missing categories
    assert raw.catering_level.isna().sum() >= 40 and raw.region.isna().sum() >= 33
    # inconsistent spelling: values outside the canonical codes, incl. Hebrew and upper case
    assert (~raw.event_type.isin(list(vocab.EVENT_TYPES))).sum() > 200
    assert raw.region.isin(["TLV", "JLM"]).any()
    assert raw.event_type.isin(["WEDDING", "חתונה"]).any()
    # mixed date formats and yes/no spellings
    d = raw.event_date.astype(str)
    assert d.str.match(r"^\d{4}-\d{2}-\d{2}$").any() and d.str.match(r"^\d{2}/\d{2}/\d{4}$").any()
    assert d.str.match(r"^\d{4}/\d{2}/\d{2}$").any()
    assert {"yes", "Y", "כן", "1"} <= set(raw.extra_photography)
    # events before the inquiry date
    ev = pd.to_datetime(raw.event_date, format="mixed", dayfirst=True)
    inq = pd.to_datetime(raw.inquiry_date, format="mixed", dayfirst=True)
    assert (ev < inq).sum() >= log["event_before_inquiry"]
