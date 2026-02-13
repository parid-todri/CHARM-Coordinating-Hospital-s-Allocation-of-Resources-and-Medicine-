"""
CHARM Copilot utilities — logging setup, month helpers.
"""

import calendar
import logging
import sys

from charm.config import MONTH_NAME_TO_NUM, MONTH_NAMES


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger for the charm package."""
    logger = logging.getLogger("charm")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def month_name_to_num(name: str) -> int:
    """Convert a month name (e.g. 'April') to its number (4).

    Raises ValueError for invalid names.
    """
    key = name.strip().capitalize()
    if key not in MONTH_NAME_TO_NUM:
        raise ValueError(
            f"Invalid month name '{name}'. "
            f"Valid names: {', '.join(MONTH_NAMES)}"
        )
    return MONTH_NAME_TO_NUM[key]


def days_in_month(month_num: int, year: int = 2025) -> int:
    """Return the number of days in *month_num* for *year*."""
    if not 1 <= month_num <= 12:
        raise ValueError(f"month_num must be 1–12, got {month_num}")
    return calendar.monthrange(year, month_num)[1]
