"""
CHARM Copilot ingestion — CSV → validated → SQLite.

CLI:
    python -m charm.ingest --csv data/nene_tereza_synthetic_orders_2025_with_consumption.csv
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from charm.config import MONTH_NAME_TO_NUM
from charm.db import get_connection, init_db
from charm.schema import validate_dataframe
from charm.utils import setup_logging

logger = setup_logging()


def _row_hash(order_month: str, medication: str, purchase_date: str) -> str:
    """Compute a SHA-256 hash of the natural key to ensure idempotency."""
    key = f"{order_month}|{medication}|{purchase_date}"
    return hashlib.sha256(key.encode()).hexdigest()


def ingest_csv(csv_path: str, db_path: str | None = None) -> int:
    """Read, validate, and insert CSV rows into the orders table.

    Returns the number of **new** rows inserted (skips duplicates).
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info("Reading CSV from %s", csv_path)
    df = pd.read_csv(csv_path)

    logger.info("Validating schema (%d rows) …", len(df))
    df = validate_dataframe(df)

    # Ensure DB tables exist
    init_db(db_path)
    conn = get_connection(db_path)

    inserted = 0
    skipped = 0

    try:
        for _, row in df.iterrows():
            rh = _row_hash(row["order_month"], row["medication"], row["purchase_date"])
            month_num = MONTH_NAME_TO_NUM.get(row["order_month"].strip().capitalize(), 0)

            try:
                conn.execute(
                    """
                    INSERT INTO orders
                        (source_file, row_hash, order_month, month_num,
                         medication, quantity, purchase_date, expiration_date,
                         quantity_used, avg_daily_consumption)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        path.name,
                        rh,
                        row["order_month"],
                        month_num,
                        row["medication"],
                        int(row["quantity"]),
                        row["purchase_date"],
                        row["expiration_date"],
                        int(row["quantity_used"]),
                        float(row["avg_daily_consumption"]),
                    ),
                )
                inserted += 1
            except Exception:
                # row_hash UNIQUE constraint → duplicate, skip
                skipped += 1

        conn.commit()
        logger.info(
            "Ingestion complete — %d inserted, %d skipped (duplicates).",
            inserted,
            skipped,
        )
    finally:
        conn.close()

    return inserted


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="charm.ingest",
        description="Ingest a CSV file into the CHARM SQLite database.",
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the CSV file to ingest.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite database (default: CHARM_DB_PATH env or charm.db).",
    )
    args = parser.parse_args()
    ingest_csv(args.csv, args.db)


if __name__ == "__main__":
    main()
