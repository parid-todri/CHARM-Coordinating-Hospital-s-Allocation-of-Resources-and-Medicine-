"""Tests for charm.copilot — recommendation output format."""

import os

import pytest

from charm.copilot import recommend_orders
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
def pipeline(tmp_path):
    """Run the full pipeline in a temp directory and return paths."""
    db_path = str(tmp_path / "test_charm.db")
    model_dir = str(tmp_path / "models")

    init_db(db_path)
    ingest_csv(CSV_PATH, db_path=db_path)
    train_model(model_dir=model_dir, db_path=db_path)

    return db_path, model_dir


def test_recommend_orders_format(pipeline):
    db_path, model_dir = pipeline

    stock = {
        "Paracetamol 500mg tablets": 200,
        "Amoxicillin 500mg capsules": 100,
        "Ceftriaxone 1g injection": 30,
    }

    recs = recommend_orders(
        next_month="April",
        current_stock=stock,
        safety_buffer=0.20,
        model_dir=model_dir,
        db_path=db_path,
    )

    # Must return a list with all 20 medications
    assert isinstance(recs, list)
    assert len(recs) == 20

    # Check keys on each item
    required_keys = {"medication", "predicted_demand", "recommended_order", "current_stock", "warnings"}
    for r in recs:
        assert required_keys.issubset(r.keys()), f"Missing keys in {r}"
        assert r["predicted_demand"] >= 0
        assert r["recommended_order"] >= 0
        assert isinstance(r["warnings"], list)

    # Sorted descending by recommended_order
    orders = [r["recommended_order"] for r in recs]
    assert orders == sorted(orders, reverse=True)


def test_recommend_orders_zero_stock(pipeline):
    """When stock is 0 for everything, all orders should be positive."""
    db_path, model_dir = pipeline

    recs = recommend_orders(
        next_month="January",
        current_stock={},
        safety_buffer=0.20,
        model_dir=model_dir,
        db_path=db_path,
    )

    total_order = sum(r["recommended_order"] for r in recs)
    assert total_order > 0, "With zero stock, total recommended orders should be > 0."
