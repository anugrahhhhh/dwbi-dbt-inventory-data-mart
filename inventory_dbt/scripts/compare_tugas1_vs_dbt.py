"""
compare_tugas1_vs_dbt.py
Membandingkan data mart hasil ETL manual (Tugas I) dengan hasil dbt (Tugas II):
  - fakta & snapshot dibandingkan per baris memakai nilai natural (bukan surrogate key),
  - dimensi dibandingkan per baris memakai natural key,
  - BQ1-BQ9 dijalankan pada kedua basis data memakai SQL hasil dbt compile.

Pemakaian (dari folder inventory_dbt, setelah dbt build dan run_business_queries.py):
    python scripts/compare_tugas1_vs_dbt.py [--manual-db inventory_tugas1.duckdb]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
COMPILED = PROJECT_DIR / "target" / "compiled" / "inventory_dbt" / "analyses"

NATURAL = {
    "dim_product": "SELECT product_id, product_name, category, brand, product_status FROM {db}.main.dim_product",
    "dim_warehouse": "SELECT warehouse_id, warehouse_name, city, region, warehouse_type FROM {db}.main.dim_warehouse",
    "dim_movement_type": "SELECT movement_type, movement_group, direction_sign FROM {db}.main.dim_movement_type",
    "fact_inventory": """
        SELECT f.transaction_id, f.transfer_id, f.transfer_direction, f.date_key, p.product_id,
               w.warehouse_id, t.movement_type, f.quantity, f.signed_quantity
        FROM {db}.main.fact_inventory f
        JOIN {db}.main.dim_product p USING (product_key)
        JOIN {db}.main.dim_warehouse w USING (warehouse_key)
        JOIN {db}.main.dim_movement_type t USING (movement_type_key)""",
    "fact_inventory_daily_snapshot": """
        SELECT s.date_key, p.product_id, w.warehouse_id, s.qty_in, s.qty_out, s.stock_on_hand
        FROM {db}.main.fact_inventory_daily_snapshot s
        JOIN {db}.main.dim_product p USING (product_key)
        JOIN {db}.main.dim_warehouse w USING (warehouse_key)""",
}


def same(con, a_sql: str, b_sql: str) -> bool:
    """Identik bila multiset baris sama (EXCEPT ALL dua arah kosong)."""
    diff = con.execute(f"SELECT COUNT(*) FROM (({a_sql}) EXCEPT ALL ({b_sql})) x").fetchone()[0]
    diff += con.execute(f"SELECT COUNT(*) FROM (({b_sql}) EXCEPT ALL ({a_sql})) x").fetchone()[0]
    return diff == 0


def compare(dbt_db: Path, manual_db: Path) -> list[tuple[str, int, int, bool]]:
    con = duckdb.connect()
    con.execute(f"ATTACH '{Path(manual_db).as_posix()}' AS tugas1 (READ_ONLY)")
    con.execute(f"ATTACH '{Path(dbt_db).as_posix()}' AS inventory (READ_ONLY)")
    rows = []
    for name, tmpl in NATURAL.items():
        a, b = tmpl.format(db="tugas1"), tmpl.format(db="inventory")
        na = con.execute(f"SELECT COUNT(*) FROM ({a}) x").fetchone()[0]
        nb = con.execute(f"SELECT COUNT(*) FROM ({b}) x").fetchone()[0]
        rows.append((name, na, nb, same(con, a, b)))
    for f in sorted(COMPILED.glob("bq*.sql")):
        b = f.read_text(encoding="utf-8").strip().rstrip(";")
        a = b.replace('"inventory"."main".', '"tugas1"."main".')
        da, dbb = con.execute(a).df(), con.execute(b).df()
        key = list(da.columns)
        da = da.sort_values(key).reset_index(drop=True)
        dbb = dbb.sort_values(key).reset_index(drop=True)
        ok = da.shape == dbb.shape and da.astype(str).equals(dbb.astype(str))
        rows.append((f.stem, len(da), len(dbb), ok))
    con.close()
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual-db", type=Path, default=PROJECT_DIR / "inventory_tugas1.duckdb")
    ap.add_argument("--dbt-db", type=Path, default=PROJECT_DIR / "inventory.duckdb")
    args = ap.parse_args()
    rows = compare(args.dbt_db, args.manual_db)
    print(f"{'objek':<34}{'baris_tugas1':>13}{'baris_dbt':>11}  status")
    for name, na, nb, ok in rows:
        print(f"{name:<34}{na:>13,}{nb:>11,}  {'IDENTIK' if ok else 'BERBEDA'}")
    all_ok = all(r[3] for r in rows)
    print("KESIMPULAN: seluruh hasil identik" if all_ok else "KESIMPULAN: ada hasil yang berbeda")


if __name__ == "__main__":
    main()
