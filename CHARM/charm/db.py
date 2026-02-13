"""
CHARM Copilot database layer — SQLite init, connection, and CLI.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from charm.config import DB_PATH
from charm.utils import setup_logging

logger = setup_logging()

# ── SQL statements ───────────────────────────────────────────────────

CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file           TEXT,
    row_hash              TEXT UNIQUE,
    order_month           TEXT    NOT NULL,
    month_num             INTEGER NOT NULL,
    medication            TEXT    NOT NULL,
    quantity              INTEGER NOT NULL,
    purchase_date         TEXT    NOT NULL,
    expiration_date       TEXT    NOT NULL,
    quantity_used         INTEGER NOT NULL,
    avg_daily_consumption REAL    NOT NULL
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_orders_medication_purchase_date "
    "ON orders (medication, purchase_date);",
    "CREATE INDEX IF NOT EXISTS idx_orders_month_med "
    "ON orders (month_num, medication);",
]


# ── Public API ───────────────────────────────────────────────────────

def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a SQLite connection (WAL mode, foreign keys on)."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create tables and indexes (idempotent)."""
    conn = get_connection(db_path)
    try:
        conn.execute(CREATE_ORDERS_TABLE)
        for idx_sql in CREATE_INDEXES:
            conn.execute(idx_sql)
        conn.commit()
        logger.info("Database initialised at %s", db_path or DB_PATH)
    finally:
        conn.close()


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="charm.db",
        description="Initialise the CHARM SQLite database.",
    )
    parser.add_argument(
        "command",
        choices=["init"],
        help="Sub-command to run (currently only 'init').",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite database file (default: CHARM_DB_PATH env or charm.db).",
    )
    args = parser.parse_args()

    if args.command == "init":
        init_db(args.db)


if __name__ == "__main__":
    main()
