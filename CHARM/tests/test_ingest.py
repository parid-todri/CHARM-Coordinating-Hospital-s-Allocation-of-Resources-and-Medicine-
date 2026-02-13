"""Tests for charm.ingest — CSV ingestion + idempotency."""

import os
import tempfile

import pytest

from charm.db import get_connection, init_db
from charm.ingest import ingest_csv

CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "nene_tereza_synthetic_orders_2025_with_consumption.csv",
)


@pytest.fixture()
def tmp_db(tmp_path):
    """Yield a temporary SQLite DB path."""
    db_path = str(tmp_path / "test_charm.db")
    init_db(db_path)
    return db_path


def _count_rows(db_path: str) -> int:
    conn = get_connection(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    finally:
        conn.close()


def test_ingest_inserts_rows(tmp_db):
    inserted = ingest_csv(CSV_PATH, db_path=tmp_db)
    assert inserted == 240  # 12 months × 20 medications
    assert _count_rows(tmp_db) == 240


def test_ingest_idempotent(tmp_db):
    ingest_csv(CSV_PATH, db_path=tmp_db)
    count_after_first = _count_rows(tmp_db)

    # Run again — should insert 0 new rows
    inserted2 = ingest_csv(CSV_PATH, db_path=tmp_db)
    assert inserted2 == 0
    assert _count_rows(tmp_db) == count_after_first
