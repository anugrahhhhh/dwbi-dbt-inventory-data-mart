import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from generate_source_data import generate  # noqa: E402
from load_source import load  # noqa: E402

SIGN = {"PURCHASE": 1, "FOUND": 1, "SALE": -1, "LOST": -1, "DAMAGED": -1}


@pytest.fixture(scope="module")
def dfs(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("data"), seed=42)


def test_counts(dfs):
    p, w, m = dfs["source_products"], dfs["source_warehouses"], dfs["source_inventory_movements"]
    assert len(p) == 50 and p.product_id.nunique() == 10
    assert len(w) == 15 and w.warehouse_id.nunique() == 3
    assert len(m) == 10_000
    assert m.transaction_id.is_unique


def test_categories(dfs):
    latest = dfs["source_products"].sort_values("updated_at").groupby("product_id").tail(1)
    assert set(latest.category.str.strip()) == {
        "Air Fryer", "Blender", "Coffee Maker", "Electric Kettle",
        "Electric Stove", "Hand Mixer", "Microwave", "Rice Cooker"}
    names = set(dfs["source_warehouses"].warehouse_name.str.strip())
    assert {"Warehouse Jawa", "Warehouse Sumatra", "Warehouse Kalimantan"} <= names


def test_movement_mix(dfs):
    m = dfs["source_inventory_movements"]
    assert set(m.movement_type) == {"PURCHASE", "SALE", "TRANSFER", "LOST", "DAMAGED", "FOUND"}
    share = m.movement_type.value_counts(normalize=True)
    assert 0.30 <= share["TRANSFER"] <= 0.36
    assert share["FOUND"] < 0.01
    ts = pd.to_datetime(m.transaction_timestamp)
    assert ts.min() >= pd.Timestamp("2024-01-01") and ts.max() < pd.Timestamp("2026-01-01")


def test_transfer_pairs(dfs):
    t = dfs["source_inventory_movements"].query("movement_type == 'TRANSFER'")
    g = t.groupby("transfer_id")
    assert (g.size() == 2).all()
    assert (g.transfer_direction.apply(lambda s: set(s) == {"OUT", "IN"})).all()
    assert (g.quantity.nunique() == 1).all()
    assert (g.warehouse_id.nunique() == 2).all()
    assert dfs["source_inventory_movements"].query("movement_type != 'TRANSFER'").transfer_id.isna().all()


def test_stock_never_negative(dfs):
    m = dfs["source_inventory_movements"].copy()
    m["ts"] = pd.to_datetime(m.transaction_timestamp)
    m["signed"] = [
        q * (SIGN[t] if t != "TRANSFER" else (1 if d == "IN" else -1))
        for q, t, d in zip(m.quantity, m.movement_type, m.transfer_direction)
    ]
    # OUT side sorted before IN side when timestamps tie
    m["order"] = (m.transfer_direction == "IN").astype(int)
    m = m.sort_values(["ts", "order", "transaction_id"])
    running = m.groupby(["product_id", "warehouse_id"]).signed.cumsum()
    assert running.min() >= 0


def test_dirty_values_present(dfs):
    p = dfs["source_products"]
    assert (p.product_name != p.product_name.str.strip()).any()
    assert (p.brand == "").any()


def test_load_is_idempotent(tmp_path):
    data = tmp_path / "data"
    generate(data, seed=42)
    db = tmp_path / "x.duckdb"
    load(db, data)
    counts = load(db, data)
    assert counts == {"source_products": 50, "source_warehouses": 15,
                      "source_inventory_movements": 10_000}
    con = duckdb.connect(str(db), read_only=True)
    assert con.execute("select count(*) from source_inventory_movements").fetchone()[0] == 10_000


def test_runs_from_other_cwd(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPTS / "generate_source_data.py"),
                        "--out", str(tmp_path)], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "source_inventory_movements.csv").exists()
