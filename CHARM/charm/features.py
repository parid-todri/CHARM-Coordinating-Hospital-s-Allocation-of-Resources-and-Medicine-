"""
CHARM Copilot feature engineering.

Builds a training-ready DataFrame from the orders table with:
- month_num
- lag_1_used, lag_1_ordered
- rolling_mean_3_used
- avg_daily_consumption
- medication one-hot columns
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from charm.db import get_connection
from charm.utils import setup_logging

logger = setup_logging()


def _load_orders(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load all rows from the orders table, sorted chronologically."""
    df = pd.read_sql_query(
        "SELECT * FROM orders ORDER BY medication, month_num",
        conn,
    )
    return df


def build_features(
    conn: sqlite3.Connection | None = None,
    db_path: str | None = None,
) -> pd.DataFrame:
    """Build the feature matrix for model training.

    Returns a DataFrame with one row per (medication, month) and columns:
        medication, month_num, quantity, quantity_used, avg_daily_consumption,
        lag_1_used, lag_1_ordered, rolling_mean_3_used,
        plus one-hot medication columns (med_<name>).
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection(db_path)

    try:
        df = _load_orders(conn)
    finally:
        if own_conn:
            conn.close()

    if df.empty:
        raise RuntimeError("No data in orders table — run ingestion first.")

    # Sort to guarantee chronological order within each medication
    df = df.sort_values(["medication", "month_num"]).reset_index(drop=True)

    # ── Lag & rolling features (per medication) ──────────────────────
    df["lag_1_used"] = df.groupby("medication")["quantity_used"].shift(1)
    df["lag_1_ordered"] = df.groupby("medication")["quantity"].shift(1)
    df["rolling_mean_3_used"] = (
        df.groupby("medication")["quantity_used"]
        .transform(lambda s: s.shift(1).rolling(window=3, min_periods=1).mean())
    )

    # Fill NaN lags for the first month with the row's own values
    df["lag_1_used"] = df["lag_1_used"].fillna(df["quantity_used"])
    df["lag_1_ordered"] = df["lag_1_ordered"].fillna(df["quantity"])
    df["rolling_mean_3_used"] = df["rolling_mean_3_used"].fillna(df["quantity_used"])

    # ── One-hot encode medication ────────────────────────────────────
    med_dummies = pd.get_dummies(df["medication"], prefix="med")
    df = pd.concat([df, med_dummies], axis=1)

    logger.info(
        "Feature matrix built: %d rows × %d cols (incl. %d medication dummies).",
        len(df),
        len(df.columns),
        len(med_dummies.columns),
    )

    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of feature column names (X columns) for the model."""
    base_features = [
        "month_num",
        "lag_1_used",
        "lag_1_ordered",
        "rolling_mean_3_used",
        "avg_daily_consumption",
    ]
    med_cols = [c for c in df.columns if c.startswith("med_")]
    return base_features + sorted(med_cols)
