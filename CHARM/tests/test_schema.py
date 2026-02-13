"""Tests for charm.schema — column validation, dtype checks, cleaning."""

import pandas as pd
import pytest

from charm.schema import SchemaError, validate_columns, coerce_dtypes, clean_rows, validate_dataframe


def _good_row() -> dict:
    return {
        "order_month": "January",
        "medication": "Paracetamol 500mg tablets",
        "quantity": 100,
        "purchase_date": "2025-01-06",
        "expiration_date": "2026-12-27",
        "quantity_used": 80,
        "avg_daily_consumption": 2.58,
    }


def test_validate_columns_pass():
    df = pd.DataFrame([_good_row()])
    validate_columns(df)  # should not raise


def test_validate_columns_missing():
    row = _good_row()
    del row["quantity_used"]
    df = pd.DataFrame([row])
    with pytest.raises(SchemaError, match="Missing required columns"):
        validate_columns(df)


def test_coerce_dtypes_valid():
    df = pd.DataFrame([_good_row()])
    result = coerce_dtypes(df)
    assert result["quantity"].dtype == int
    assert result["quantity_used"].dtype == int
    assert result["avg_daily_consumption"].dtype == float


def test_coerce_dtypes_invalid():
    row = _good_row()
    row["quantity"] = "abc"
    df = pd.DataFrame([row])
    with pytest.raises(SchemaError, match="Dtype coercion failed"):
        coerce_dtypes(df)


def test_clean_rows_drops_negative():
    rows = [_good_row(), {**_good_row(), "quantity": -5}]
    df = pd.DataFrame(rows)
    result = clean_rows(df)
    assert len(result) == 1


def test_clean_rows_drops_invalid_month():
    rows = [_good_row(), {**_good_row(), "order_month": "Foobar"}]
    df = pd.DataFrame(rows)
    result = clean_rows(df)
    assert len(result) == 1


def test_validate_dataframe_full():
    df = pd.DataFrame([_good_row()])
    result = validate_dataframe(df)
    assert len(result) == 1
    assert result.iloc[0]["purchase_date"] == "2025-01-06"
