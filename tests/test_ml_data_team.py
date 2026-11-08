"""Crew 1 (Data Team) and the data contract. Ported from the ML prototype."""
import json
import shutil

import pandas as pd
import pytest

from rivatar import config
from rivatar.contract import DataContractError, validate_contract
from rivatar import vocab
from rivatar.tools.data_ops import CATEGORICAL


# ----------------------------------------------------------- cleaning + EDA
def test_clean_data_has_no_quality_problems(data_ready):
    df = pd.read_csv(config.CLEAN_DATA)
    assert not df.isna().any().any()
    assert not df[config.ID_COLUMN].duplicated().any()
    assert df["guest_count"].between(vocab.GUESTS_MIN, vocab.GUESTS_MAX).all()
    assert (df[config.TARGET] > 0).all()
    assert (pd.to_datetime(df["event_date"]) >= pd.to_datetime(df["inquiry_date"])).all()
    for c in CATEGORICAL:
        assert df[c].str.strip().str.lower().eq(df[c]).all(), c
    for col, codes in [("event_type", vocab.EVENT_TYPES), ("region", vocab.REGIONS), ("venue_type", vocab.VENUE_TYPES),
                       ("catering_level", vocab.CATERING_LEVELS), ("design_package", vocab.DESIGN_PACKAGES)]:
        assert set(df[col]) <= set(codes), col  # only the website's codes reach the model
    assert (df["client_type"] == df["event_type"].map(vocab.client_type_for)).all()
    assert len(df) >= config.MIN_ROWS_AFTER_CLEANING


def test_crew1_outputs_exist(data_ready):
    for p in [config.CLEANING_REPORT, config.EDA_SUMMARY, config.INSIGHTS_MD, config.DATA_CONTRACT]:
        assert p.exists(), p
    assert len(list(config.EDA_DIR.glob("*.png"))) >= 4
    summary = json.loads(config.EDA_SUMMARY.read_text(encoding="utf-8"))
    assert summary["n_rows"] == pd.read_csv(config.CLEAN_DATA).shape[0]


def test_data_crew_has_at_least_three_agents():
    from rivatar.crews.data_crew import build_data_crew
    crew = build_data_crew()
    assert len(crew.agents) >= 3 and len(crew.tasks) >= 3
    assert all(a.tools for a in crew.agents)


# ------------------------------------------------------------ data contract
@pytest.fixture
def tmp_copy(data_ready, tmp_path):
    """Copies of the clean data and contract that a test may break."""
    data, contract = tmp_path / "clean.csv", tmp_path / "contract.json"
    shutil.copy(config.CLEAN_DATA, data)
    shutil.copy(config.DATA_CONTRACT, contract)
    return data, contract


def test_contract_passes_on_clean_data(data_ready):
    assert validate_contract()["status"] == "passed"


def test_contract_has_required_fields(data_ready):
    c = json.loads(config.DATA_CONTRACT.read_text(encoding="utf-8"))
    for key in ["contract_name", "version", "dataset_sha256", "row_count", "columns", "target", "primary_key"]:
        assert key in c
    assert c["target"] in c["columns"]


def test_modified_data_breaks_hash(tmp_copy):
    data, contract = tmp_copy
    df = pd.read_csv(data)
    df.loc[0, "total_budget_ils"] += 1
    df.to_csv(data, index=False)
    with pytest.raises(DataContractError) as e:
        validate_contract(contract, data)
    assert any("sha256" in v for v in e.value.violations)


@pytest.mark.parametrize("column,value,expected", [
    ("guest_count", -3, "below min"),
    ("event_type", "birthday_party", "outside allowed set"),
    ("region", None, "null values"),
])
def test_bad_values_are_reported(tmp_copy, column, value, expected):
    data, contract = tmp_copy
    df = pd.read_csv(data)
    df.loc[:2, column] = value
    df.to_csv(data, index=False)
    with pytest.raises(DataContractError) as e:
        validate_contract(contract, data)
    assert any(expected in v for v in e.value.violations), e.value.violations


def test_missing_column_is_reported(tmp_copy):
    data, contract = tmp_copy
    pd.read_csv(data).drop(columns=["catering_level"]).to_csv(data, index=False)
    with pytest.raises(DataContractError) as e:
        validate_contract(contract, data)
    assert any("missing columns" in v for v in e.value.violations)


def test_malformed_contract_is_rejected(tmp_copy):
    data, contract = tmp_copy
    contract.write_text('{"contract_name": "x"}')
    with pytest.raises(DataContractError, match="malformed"):
        validate_contract(contract, data)


def test_cleaning_undoes_exactly_what_the_generator_injected(data_ready):
    log = json.loads((config.RAW_DIR / "injection_log.json").read_text(encoding="utf-8"))
    rep = {st["step"]: st for st in json.loads(config.CLEANING_REPORT.read_text(encoding="utf-8"))["steps"]}
    assert rep["drop_duplicate_event_ids"]["removed"] == log["duplicate_rows"]
    assert rep["drop_missing_or_non_positive_budget"]["removed"] == log["budget_missing"] + log["budget_negative"]
    assert rep["drop_event_before_inquiry"]["removed"] == log["event_before_inquiry"]
    assert rep["derive_client_type_from_event_type"]["corrected"] == log["client_type_mismatch"]
    assert rep["impute_guest_count_by_event_type_median"]["missing_imputed"] == (
        log["guests_missing"] + log["guests_impossible"])
    assert rep["normalize_category_spellings"]["unknown_values"] == {}
