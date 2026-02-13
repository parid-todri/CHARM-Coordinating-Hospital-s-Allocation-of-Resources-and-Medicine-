"""Tests for charm.train — model artifact creation."""

import os

import pytest

from charm.db import init_db
from charm.ingest import ingest_csv
from charm.train import train_model

CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "nene_tereza_synthetic_orders_2025_with_consumption.csv",
)


@pytest.fixture()
def ready_db(tmp_path):
    """Create a temp DB and ingest data."""
    db_path = str(tmp_path / "test_charm.db")
    init_db(db_path)
    ingest_csv(CSV_PATH, db_path=db_path)
    return db_path, tmp_path


def test_train_creates_artifacts(ready_db):
    db_path, tmp_path = ready_db
    model_dir = str(tmp_path / "models")

    train_model(model_dir=model_dir, db_path=db_path)

    assert os.path.isfile(os.path.join(model_dir, "model.joblib"))
    assert os.path.isfile(os.path.join(model_dir, "columns.joblib"))
