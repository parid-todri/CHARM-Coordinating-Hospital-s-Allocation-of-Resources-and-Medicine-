"""
CHARM Copilot recommendation engine.

Public API:
    recommend_orders(next_month, current_stock, safety_buffer=0.20)

CLI:
    python -m charm.copilot --month April --stock-json examples/current_stock.json
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import pandas as pd

from charm.config import (
    DEFAULT_SAFETY_BUFFER,
    EXPIRY_WARNING_DAYS,
    MODEL_DIR,
    MONTH_NAMES,
    OVERSTOCK_MARGIN,
)
from charm.db import get_connection
from charm.utils import days_in_month, month_name_to_num, setup_logging

logger = setup_logging()


# ── Internal helpers ─────────────────────────────────────────────────

def _load_model(model_dir: str | None = None):
    """Load model + feature columns from disk."""
    md = Path(model_dir or MODEL_DIR)
    model_path = md / "model.joblib"
    cols_path = md / "columns.joblib"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found at {model_path}. Run `python -m charm.train` first."
        )

    model = joblib.load(model_path)
    feature_cols: list[str] = joblib.load(cols_path)
    return model, feature_cols


def _build_inference_features(
    conn,
    month_num: int,
    medications: list[str],
    feature_cols: list[str],
) -> pd.DataFrame:
    """Build a feature row per medication for inference on *month_num*."""
    rows = []
    for med in medications:
        # Fetch most recent rows for this medication (ordered by month_num)
        cursor = conn.execute(
            """
            SELECT month_num, quantity, quantity_used, avg_daily_consumption
            FROM orders
            WHERE medication = ?
            ORDER BY month_num DESC
            LIMIT 3
            """,
            (med,),
        )
        history = cursor.fetchall()

        if history:
            last = history[0]
            lag_1_used = last["quantity_used"]
            lag_1_ordered = last["quantity"]
            avg_daily = last["avg_daily_consumption"]

            # Rolling mean of last 3 months quantity_used
            used_vals = [h["quantity_used"] for h in history]
            rolling_mean_3_used = sum(used_vals) / len(used_vals)
        else:
            # Fallback — no history (shouldn't happen with our data)
            avg_daily = 5.0
            dm = days_in_month(month_num)
            lag_1_used = avg_daily * dm
            lag_1_ordered = lag_1_used
            rolling_mean_3_used = lag_1_used
            logger.warning("No history for '%s'; using fallback estimates.", med)

        row: dict = {
            "medication": med,
            "month_num": month_num,
            "lag_1_used": lag_1_used,
            "lag_1_ordered": lag_1_ordered,
            "rolling_mean_3_used": rolling_mean_3_used,
            "avg_daily_consumption": avg_daily,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # One-hot encode medication to match training columns
    med_dummies = pd.get_dummies(df["medication"], prefix="med")
    df = pd.concat([df, med_dummies], axis=1)

    # Align columns with training set (add missing med cols as 0)
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0

    return df


def _expiry_info(conn, med: str) -> dict | None:
    """Return approximate expiry info for a medication."""
    row = conn.execute(
        """
        SELECT expiration_date
        FROM orders
        WHERE medication = ?
        ORDER BY month_num DESC
        LIMIT 1
        """,
        (med,),
    ).fetchone()

    if not row:
        return None

    try:
        exp = datetime.strptime(row["expiration_date"], "%Y-%m-%d")
        today = datetime.now()
        days_left = (exp - today).days
        return {"expiration_date": row["expiration_date"], "days_left": days_left}
    except Exception:
        return None


# ── Public API ───────────────────────────────────────────────────────

def recommend_orders(
    next_month: str,
    current_stock: dict[str, int],
    safety_buffer: float = DEFAULT_SAFETY_BUFFER,
    model_dir: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Generate order recommendations for *next_month*.

    Parameters
    ----------
    next_month : str
        Month name, e.g. ``"April"``.
    current_stock : dict[str, int]
        Mapping of medication name → current units on hand.
    safety_buffer : float
        Fraction added on top of predicted demand (default 0.20 = 20 %).
    model_dir : str | None
        Path to saved model artifacts.
    db_path : str | None
        Path to SQLite database.

    Returns
    -------
    list[dict]
        Sorted (desc) by ``recommended_order``. Each dict has keys:
        medication, predicted_demand, recommended_order, current_stock, warnings.
    """
    month_num = month_name_to_num(next_month)

    model, feature_cols = _load_model(model_dir)
    conn = get_connection(db_path)

    try:
        # Discover medications from DB
        med_rows = conn.execute(
            "SELECT DISTINCT medication FROM orders ORDER BY medication"
        ).fetchall()
        medications = [r["medication"] for r in med_rows]

        if not medications:
            raise RuntimeError("No medications found in DB — run ingestion first.")

        inf_df = _build_inference_features(conn, month_num, medications, feature_cols)

        X = inf_df[feature_cols].values
        predictions = model.predict(X)

        results: list[dict] = []
        for idx, med in enumerate(medications):
            pred_demand = max(0.0, float(predictions[idx]))
            stock = current_stock.get(med, 0)
            buffered_demand = pred_demand * (1 + safety_buffer)
            order_qty = max(0, math.ceil(buffered_demand - stock))

            warnings: list[str] = []

            # Expiry risk
            exp_info = _expiry_info(conn, med)
            if exp_info and 0 < exp_info["days_left"] <= EXPIRY_WARNING_DAYS:
                warnings.append(
                    f"expiry_risk (batch expires {exp_info['expiration_date']}, "
                    f"~{exp_info['days_left']}d left — approx)"
                )

            # Overstock risk
            if stock > buffered_demand * (1 + OVERSTOCK_MARGIN):
                warnings.append(
                    f"overstock_risk (stock {stock} >> buffered demand {buffered_demand:.0f})"
                )

            results.append(
                {
                    "medication": med,
                    "predicted_demand": round(pred_demand, 1),
                    "recommended_order": order_qty,
                    "current_stock": stock,
                    "safety_buffer": safety_buffer,
                    "warnings": warnings,
                }
            )

        # Sort by recommended_order descending
        results.sort(key=lambda r: r["recommended_order"], reverse=True)
    finally:
        conn.close()

    return results


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="charm.copilot",
        description="CHARM AI Copilot — recommend next-month medication orders.",
    )
    parser.add_argument(
        "--month",
        required=True,
        help="Target month name (e.g. 'April').",
    )
    parser.add_argument(
        "--stock-json",
        required=True,
        help="Path to JSON file mapping medication → current stock quantity.",
    )
    parser.add_argument(
        "--safety",
        type=float,
        default=DEFAULT_SAFETY_BUFFER,
        help=f"Safety buffer fraction (default {DEFAULT_SAFETY_BUFFER}).",
    )
    parser.add_argument(
        "--model-dir",
        default=None,
        help="Directory containing trained model artifacts.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite database.",
    )
    args = parser.parse_args()

    # Load current stock
    stock_path = Path(args.stock_json)
    if not stock_path.exists():
        raise FileNotFoundError(f"Stock JSON not found: {args.stock_json}")
    with open(stock_path) as f:
        current_stock: dict[str, int] = json.load(f)

    recs = recommend_orders(
        next_month=args.month,
        current_stock=current_stock,
        safety_buffer=args.safety,
        model_dir=args.model_dir,
        db_path=args.db,
    )

    # Pretty-print
    print(f"\n{'='*72}")
    print(f"  CHARM AI Copilot — Order Recommendations for {args.month}")
    print(f"{'='*72}\n")

    for i, r in enumerate(recs, 1):
        warn_str = ", ".join(r["warnings"]) if r["warnings"] else "—"
        print(
            f"  {i:>2}. {r['medication']:<40s} "
            f"demand={r['predicted_demand']:>8.1f}  "
            f"stock={r['current_stock']:>5d}  "
            f"ORDER → {r['recommended_order']:>5d}  "
            f"⚠ {warn_str}"
        )

    print(f"\n{'='*72}")
    print(f"  Safety buffer: {args.safety:.0%}  |  Medications: {len(recs)}")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
