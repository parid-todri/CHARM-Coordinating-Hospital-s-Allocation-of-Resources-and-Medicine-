"""
CHARM Copilot schema validation — column checks, dtype coercion, cleaning.
"""

from __future__ import annotations

import pandas as pd

from charm.config import MONTH_NAMES, REQUIRED_COLUMNS
from charm.utils import setup_logging

logger = setup_logging()


class SchemaError(Exception):
    """Raised when CSV data fails schema validation."""


def validate_columns(df: pd.DataFrame) -> None:
    """Ensure all required columns are present.

    Raises SchemaError on failure.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise SchemaError(f"Missing required columns: {sorted(missing)}")


def coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce columns to expected types, raising SchemaError on failure."""
    df = df.copy()
    try:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="raise").astype(int)
        df["quantity_used"] = pd.to_numeric(df["quantity_used"], errors="raise").astype(int)
        df["avg_daily_consumption"] = pd.to_numeric(
            df["avg_daily_consumption"], errors="raise"
        ).astype(float)
    except (ValueError, TypeError) as exc:
        raise SchemaError(f"Dtype coercion failed: {exc}") from exc
    return df


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise purchase_date and expiration_date to YYYY-MM-DD strings."""
    df = df.copy()
    for col in ("purchase_date", "expiration_date"):
        try:
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
        except Exception as exc:
            raise SchemaError(f"Date normalisation failed for '{col}': {exc}") from exc
    return df


def clean_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove or fix invalid rows.

    - Drop rows with negative quantity / quantity_used / avg_daily_consumption
    - Drop rows with invalid order_month
    - Log how many rows were dropped.
    """
    initial_len = len(df)
    # Negative value check
    mask_neg = (
        (df["quantity"] < 0)
        | (df["quantity_used"] < 0)
        | (df["avg_daily_consumption"] < 0)
    )
    if mask_neg.any():
        logger.warning(
            "Dropping %d rows with negative values.", mask_neg.sum()
        )
        df = df[~mask_neg]

    # Invalid month names
    valid_months = set(MONTH_NAMES)
    mask_month = ~df["order_month"].str.strip().str.capitalize().isin(valid_months)
    if mask_month.any():
        logger.warning(
            "Dropping %d rows with invalid order_month.", mask_month.sum()
        )
        df = df[~mask_month]

    dropped = initial_len - len(df)
    if dropped:
        logger.info("Total rows dropped during cleaning: %d", dropped)
    return df.reset_index(drop=True)


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Full validation pipeline: columns → dtypes → dates → cleaning."""
    validate_columns(df)
    df = coerce_dtypes(df)
    df = normalize_dates(df)
    df = clean_rows(df)
    return df
