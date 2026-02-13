"""
CHARM Copilot model training — global GradientBoostingRegressor.

CLI:
    python -m charm.train --model-dir models
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from charm.config import MODEL_DIR
from charm.db import get_connection
from charm.features import build_features, get_feature_columns
from charm.utils import setup_logging

logger = setup_logging()

TARGET = "quantity_used"


def train_model(
    model_dir: str | None = None,
    db_path: str | None = None,
) -> Path:
    """Train a global GradientBoostingRegressor and save artifacts.

    Saves:
        <model_dir>/model.joblib   — the trained model
        <model_dir>/columns.joblib — ordered list of feature column names

    Returns the model directory Path.
    """
    model_dir_path = Path(model_dir or MODEL_DIR)
    model_dir_path.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    try:
        df = build_features(conn=conn)
    finally:
        conn.close()

    feature_cols = get_feature_columns(df)
    X = df[feature_cols].values
    y = df[TARGET].values

    logger.info("Training GradientBoostingRegressor on %d samples, %d features …", X.shape[0], X.shape[1])

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X, y)

    # Quick in-sample metrics (we have only 240 rows; real eval would need CV)
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    logger.info("In-sample MAE: %.2f | R²: %.4f", mae, r2)

    # Save artifacts
    model_path = model_dir_path / "model.joblib"
    cols_path = model_dir_path / "columns.joblib"
    joblib.dump(model, model_path)
    joblib.dump(feature_cols, cols_path)
    logger.info("Model saved to %s", model_path)
    logger.info("Feature columns saved to %s", cols_path)

    return model_dir_path


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="charm.train",
        description="Train the CHARM demand-forecasting model.",
    )
    parser.add_argument(
        "--model-dir",
        default=None,
        help="Directory to save model artifacts (default: models/).",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to SQLite database (default: CHARM_DB_PATH env or charm.db).",
    )
    args = parser.parse_args()
    train_model(args.model_dir, args.db)


if __name__ == "__main__":
    main()
