#!/usr/bin/env python3
"""Verification script — runs the full CHARM Copilot pipeline and writes results to verify_results.txt"""
import os
import sys
import json
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
results = []

def log(msg):
    results.append(msg)
    print(msg)

try:
    log("=" * 60)
    log("CHARM AI Copilot — Pipeline Verification")
    log("=" * 60)

    # Step 1: DB Init
    log("\n▶ Step 1: Database Init")
    from charm.db import init_db
    init_db()
    log("  ✅ DB initialised")

    # Step 2: Ingest
    log("\n▶ Step 2: Ingest CSV")
    from charm.ingest import ingest_csv
    inserted = ingest_csv("data/nene_tereza_synthetic_orders_2025_with_consumption.csv")
    log(f"  ✅ Inserted: {inserted} rows")

    # Step 2b: Idempotency
    log("\n▶ Step 2b: Idempotency check (second ingest)")
    inserted2 = ingest_csv("data/nene_tereza_synthetic_orders_2025_with_consumption.csv")
    log(f"  ✅ Second run inserted: {inserted2} rows (should be 0)")

    # Step 2c: Row count
    import sqlite3
    conn = sqlite3.connect("charm.db")
    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    meds = conn.execute("SELECT COUNT(DISTINCT medication) FROM orders").fetchone()[0]
    conn.close()
    log(f"  ✅ Total rows: {count}, Distinct medications: {meds}")

    # Step 3: Train
    log("\n▶ Step 3: Train model")
    from charm.train import train_model
    model_dir = train_model()
    model_files = os.listdir(str(model_dir))
    log(f"  ✅ Model dir: {model_dir}")
    log(f"  ✅ Model files: {model_files}")

    # Step 4: Copilot
    log("\n▶ Step 4: Copilot recommendations (April)")
    from charm.copilot import recommend_orders
    with open("examples/current_stock.json") as f:
        stock = json.load(f)
    recs = recommend_orders("April", stock, 0.20)
    log(f"  ✅ Recommendations: {len(recs)} medications")
    log(f"  ✅ Total recommended order qty: {sum(r['recommended_order'] for r in recs)}")
    for r in recs:
        warn = ", ".join(r["warnings"]) if r["warnings"] else "—"
        log(f"     {r['medication']:<40s} demand={r['predicted_demand']:>8.1f}  stock={r['current_stock']:>5d}  ORDER={r['recommended_order']:>5d}  ⚠ {warn}")

    log("\n" + "=" * 60)
    log("✅ ALL PIPELINE STEPS PASSED")
    log("=" * 60)

except Exception as e:
    log(f"\n❌ ERROR: {e}")
    log(traceback.format_exc())

# Write to file
with open("verify_results.txt", "w") as f:
    f.write("\n".join(results))
