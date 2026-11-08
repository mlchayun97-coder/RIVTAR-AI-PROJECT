"""Data-contract validation – the gate between Crew 1 and Crew 2.

`validate_contract` collects *every* violation (not just the first) and
raises `DataContractError` if there is at least one, so the flow can stop
before training and print a precise list of what is wrong.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from rivatar import config
from rivatar.tools.data_ops import file_sha256


class DataContractError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("Data contract validation failed:\n  - " + "\n  - ".join(violations))


class ColumnSpec(BaseModel):
    dtype: Literal["string", "date", "category", "integer", "float", "boolean"]
    nullable: bool = False
    unique: bool = False
    pattern: str | None = None
    format: str | None = None
    allowed_values: list[str] | None = None
    min: float | None = None
    max: float | None = None


class Contract(BaseModel):
    contract_name: str
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    dataset_path: str
    dataset_sha256: str = Field(min_length=64, max_length=64)
    row_count: int
    min_rows: int
    primary_key: str
    target: str
    columns: dict[str, ColumnSpec]
    event_client_type: dict[str, str]


def load_contract(path: Path = config.DATA_CONTRACT) -> Contract:
    if not path.exists():
        raise DataContractError([f"contract file not found: {path}"])
    try:
        return Contract.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as e:
        raise DataContractError([f"contract JSON is malformed: {e}"]) from e


def validate_contract(contract_path: Path = config.DATA_CONTRACT,
                      data_path: Path | None = None) -> dict:
    """Validate a dataset against its contract. Returns a report or raises."""
    c = load_contract(contract_path)
    data_path = data_path or (config.ROOT / c.dataset_path)
    v: list[str] = []

    if not data_path.exists():
        raise DataContractError([f"dataset not found: {data_path}"])
    actual_hash = file_sha256(data_path)
    if actual_hash != c.dataset_sha256:
        v.append(f"dataset sha256 mismatch: file was changed after the contract was signed "
                 f"(expected {c.dataset_sha256[:12]}…, got {actual_hash[:12]}…)")

    df = pd.read_csv(data_path, dtype=str, keep_default_na=True)

    missing = set(c.columns) - set(df.columns)
    extra = set(df.columns) - set(c.columns)
    if missing:
        v.append(f"missing columns: {sorted(missing)}")
    if extra:
        v.append(f"unexpected columns: {sorted(extra)}")
    if c.target not in c.columns:
        v.append(f"target '{c.target}' is not declared in columns")
    if len(df) != c.row_count:
        v.append(f"row_count is {len(df)}, contract says {c.row_count}")
    if len(df) < c.min_rows:
        v.append(f"only {len(df)} rows, minimum is {c.min_rows}")

    for name, spec in c.columns.items():
        if name not in df.columns:
            continue
        col = df[name]
        nulls = int(col.isna().sum())
        if nulls and not spec.nullable:
            v.append(f"{name}: {nulls} null values in non-nullable column")
        s = col.dropna()
        if spec.unique and s.duplicated().any():
            v.append(f"{name}: {int(s.duplicated().sum())} duplicate values in unique column")
        if spec.pattern:
            bad = ~s.str.match(spec.pattern)
            if bad.any():
                v.append(f"{name}: {int(bad.sum())} values do not match pattern {spec.pattern}")
        if spec.dtype == "date":
            parsed = pd.to_datetime(s, format=spec.format or "%Y-%m-%d", errors="coerce")
            if parsed.isna().any():
                v.append(f"{name}: {int(parsed.isna().sum())} values are not valid dates")
        if spec.dtype == "category" and spec.allowed_values is not None:
            bad = sorted(set(s) - set(spec.allowed_values))
            if bad:
                v.append(f"{name}: values outside allowed set: {bad[:5]}")
        if spec.dtype == "boolean":
            bad = sorted(set(s) - {"True", "False"})
            if bad:
                v.append(f"{name}: non-boolean values {bad[:5]}")
        if spec.dtype in ("integer", "float"):
            num = pd.to_numeric(s, errors="coerce")
            if num.isna().any():
                v.append(f"{name}: {int(num.isna().sum())} non-numeric values")
            if spec.dtype == "integer" and (num.dropna() % 1 != 0).any():
                v.append(f"{name}: non-integer values in integer column")
            if spec.min is not None and (num < spec.min).any():
                v.append(f"{name}: {int((num < spec.min).sum())} values below min {spec.min}")
            if spec.max is not None and (num > spec.max).any():
                v.append(f"{name}: {int((num > spec.max).sum())} values above max {spec.max}")

    # Cross-column rules
    if {"inquiry_date", "event_date"} <= set(df.columns):
        inq = pd.to_datetime(df["inquiry_date"], errors="coerce")
        evt = pd.to_datetime(df["event_date"], errors="coerce")
        bad = int((evt < inq).sum())
        if bad:
            v.append(f"rule event_after_inquiry: {bad} rows violate it")
    if {"event_type", "client_type"} <= set(df.columns):
        expected = df["event_type"].map(c.event_client_type)
        bad = int(((expected != df["client_type"]) & expected.notna()).sum())
        if bad:
            v.append(f"rule client_type_matches_event_type: {bad} rows violate it")

    if v:
        raise DataContractError(v)
    return {"status": "passed", "contract": c.contract_name, "version": c.version,
            "rows": int(len(df)), "columns": len(c.columns), "dataset_sha256": actual_hash}


def _cli():
    try:
        r = validate_contract()
        print("✅ contract passed:", r)
    except DataContractError as e:
        print("❌", e)
        raise SystemExit(1)


if __name__ == "__main__":
    _cli()
