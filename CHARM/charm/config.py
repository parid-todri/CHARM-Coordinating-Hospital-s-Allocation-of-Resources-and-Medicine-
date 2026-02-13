"""
CHARM Copilot configuration — DB path, model dir, constants.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # repo root

DB_PATH: str = os.environ.get("CHARM_DB_PATH", str(BASE_DIR / "charm.db"))
MODEL_DIR: str = os.environ.get("CHARM_MODEL_DIR", str(BASE_DIR / "models"))

# ── Month helpers ────────────────────────────────────────────────────
MONTH_NAMES: list[str] = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

MONTH_NAME_TO_NUM: dict[str, int] = {m: i + 1 for i, m in enumerate(MONTH_NAMES)}
MONTH_NUM_TO_NAME: dict[int, str] = {i + 1: m for i, m in enumerate(MONTH_NAMES)}

# ── Schema ───────────────────────────────────────────────────────────
REQUIRED_COLUMNS: set[str] = {
    "order_month",
    "medication",
    "quantity",
    "purchase_date",
    "expiration_date",
    "quantity_used",
    "avg_daily_consumption",
}

# ── Defaults ─────────────────────────────────────────────────────────
DEFAULT_SAFETY_BUFFER: float = 0.20
EXPIRY_WARNING_DAYS: int = 90
OVERSTOCK_MARGIN: float = 0.50  # 50 % above buffered demand → overstock warning
