#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# CHARM AI Copilot — end-to-end pipeline
# ──────────────────────────────────────────────────────────────
set -euo pipefail

echo "══════════════════════════════════════════════════════════"
echo "  CHARM AI Copilot — Full Pipeline"
echo "══════════════════════════════════════════════════════════"

echo ""
echo "▶ Step 1: Install dependencies"
pip install -r requirements.txt

echo ""
echo "▶ Step 2: Initialise database"
python -m charm.db init

echo ""
echo "▶ Step 3: Ingest CSV data"
python -m charm.ingest --csv data/nene_tereza_synthetic_orders_2025_with_consumption.csv

echo ""
echo "▶ Step 4: Train forecasting model"
python -m charm.train --model-dir models

echo ""
echo "▶ Step 5: Run Copilot recommendations (April, 20% buffer)"
python -m charm.copilot --month April --stock-json examples/current_stock.json --safety 0.2

echo ""
echo "▶ Step 6: Run tests"
pytest tests/ -q

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✅ All steps complete!"
echo "══════════════════════════════════════════════════════════"
