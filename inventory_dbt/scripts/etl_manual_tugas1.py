"""
etl_manual_tugas1.py
Pembanding gaya Tugas I: membangun data mart inventory yang SAMA dengan ETL manual
(DDL + INSERT ... SELECT ditulis tangan di dalam Python, urutan eksekusi diatur manual,
pengecekan kualitas memakai assert Python). Hasilnya dibandingkan dengan dbt oleh
compare_tugas1_vs_dbt.py.

Pemakaian (dari folder inventory_dbt):
    python scripts/etl_manual_tugas1.py                  # -> inventory_tugas1.duckdb
    python scripts/etl_manual_tugas1.py --naive          # versi keliru: dimensi tanpa dedup
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_source import load  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]

DIM_PRODUCT = """
CREATE TABLE dim_product AS
WITH ranked AS (
    SELECT NULLIF(TRIM(product_id), '') AS product_id, NULLIF(TRIM(product_name), '') AS product_name,
           NULLIF(TRIM(category), '') AS category, NULLIF(TRIM(brand), '') AS brand,
           NULLIF(TRIM(product_status), '') AS product_status,
           ROW_NUMBER() OVER (PARTITION BY TRIM(product_id) ORDER BY updated_at DESC NULLS LAST) AS rn
    FROM source_products)
SELECT CAST(ROW_NUMBER() OVER (ORDER BY product_id) AS INTEGER) AS product_key,
       product_id, product_name, category, brand, product_status
FROM ranked WHERE rn = 1 AND product_id IS NOT NULL"""

DIM_WAREHOUSE = """
CREATE TABLE dim_warehouse AS
WITH ranked AS (
    SELECT NULLIF(TRIM(warehouse_id), '') AS warehouse_id, NULLIF(TRIM(warehouse_name), '') AS warehouse_name,
           NULLIF(TRIM(city), '') AS city, NULLIF(TRIM(region), '') AS region,
           NULLIF(TRIM(warehouse_type), '') AS warehouse_type,
           ROW_NUMBER() OVER (PARTITION BY TRIM(warehouse_id) ORDER BY updated_at DESC NULLS LAST) AS rn
    FROM source_warehouses)
SELECT CAST(ROW_NUMBER() OVER (ORDER BY warehouse_id) AS INTEGER) AS warehouse_key,
       warehouse_id, warehouse_name, city, region, warehouse_type
FROM ranked WHERE rn = 1 AND warehouse_id IS NOT NULL"""

# Kesalahan khas: dimensi diambil langsung dari tabel sumber tanpa dedup versi.
DIM_PRODUCT_NAIVE = """
CREATE TABLE dim_product AS
SELECT CAST(ROW_NUMBER() OVER (ORDER BY product_id, updated_at) AS INTEGER) AS product_key,
       TRIM(product_id) AS product_id, TRIM(product_name) AS product_name, TRIM(category) AS category,
       NULLIF(TRIM(brand), '') AS brand, NULLIF(TRIM(product_status), '') AS product_status
FROM source_products"""

DIM_WAREHOUSE_NAIVE = """
CREATE TABLE dim_warehouse AS
SELECT CAST(ROW_NUMBER() OVER (ORDER BY warehouse_id, updated_at) AS INTEGER) AS warehouse_key,
       TRIM(warehouse_id) AS warehouse_id, TRIM(warehouse_name) AS warehouse_name,
       NULLIF(TRIM(city), '') AS city, TRIM(region) AS region, TRIM(warehouse_type) AS warehouse_type
FROM source_warehouses"""

DIM_MOVEMENT_TYPE = """
CREATE TABLE dim_movement_type AS
SELECT CAST(ROW_NUMBER() OVER (ORDER BY movement_type) AS INTEGER) AS movement_type_key, movement_type,
       CASE WHEN movement_type IN ('PURCHASE','FOUND') THEN 'inbound'
            WHEN movement_type IN ('SALE','LOST','DAMAGED') THEN 'outbound' ELSE 'transfer' END AS movement_group,
       CAST(CASE WHEN movement_type IN ('PURCHASE','FOUND') THEN 1
                 WHEN movement_type IN ('SALE','LOST','DAMAGED') THEN -1 ELSE 0 END AS INTEGER) AS direction_sign
FROM (SELECT DISTINCT UPPER(TRIM(movement_type)) AS movement_type FROM source_inventory_movements)"""

DIM_DATE = """
CREATE TABLE dim_date AS
WITH RECURSIVE days AS (
    SELECT DATE '2024-01-01' AS d
    UNION ALL SELECT CAST(d + INTERVAL '1 day' AS DATE) FROM days WHERE d < DATE '2025-12-31')
SELECT CAST(EXTRACT(year FROM d)*10000 + EXTRACT(month FROM d)*100 + EXTRACT(day FROM d) AS INTEGER) AS date_key,
       d AS full_date, CAST(EXTRACT(year FROM d) AS INTEGER) AS year,
       CAST(EXTRACT(quarter FROM d) AS INTEGER) AS quarter, CAST(EXTRACT(month FROM d) AS INTEGER) AS month
FROM days"""

FACT = """
CREATE TABLE fact_inventory AS
SELECT TRIM(m.transaction_id) AS transaction_id, NULLIF(TRIM(m.transfer_id), '') AS transfer_id,
       UPPER(NULLIF(TRIM(m.transfer_direction), '')) AS transfer_direction,
       CAST(EXTRACT(year FROM m.transaction_timestamp)*10000 + EXTRACT(month FROM m.transaction_timestamp)*100
            + EXTRACT(day FROM m.transaction_timestamp) AS INTEGER) AS date_key,
       p.product_key, w.warehouse_key, t.movement_type_key,
       m.transaction_timestamp, CAST(m.quantity AS BIGINT) AS quantity,
       CAST(CASE WHEN t.movement_type = 'TRANSFER' AND UPPER(m.transfer_direction) = 'IN' THEN m.quantity
                 WHEN t.movement_type = 'TRANSFER' THEN -m.quantity
                 ELSE m.quantity * t.direction_sign END AS BIGINT) AS signed_quantity
FROM source_inventory_movements m
JOIN dim_product p ON TRIM(m.product_id) = p.product_id
JOIN dim_warehouse w ON TRIM(m.warehouse_id) = w.warehouse_id
JOIN dim_movement_type t ON UPPER(TRIM(m.movement_type)) = t.movement_type"""

SNAPSHOT = """
CREATE TABLE fact_inventory_daily_snapshot AS
WITH h AS (
    SELECT date_key, product_key, warehouse_key,
           SUM(CASE WHEN signed_quantity > 0 THEN signed_quantity ELSE 0 END) AS qty_in,
           SUM(CASE WHEN signed_quantity < 0 THEN -signed_quantity ELSE 0 END) AS qty_out
    FROM fact_inventory GROUP BY 1, 2, 3),
k AS (SELECT d.date_key, p.product_key, w.warehouse_key
      FROM dim_date d CROSS JOIN dim_product p CROSS JOIN dim_warehouse w)
SELECT k.date_key, k.product_key, k.warehouse_key,
       CAST(COALESCE(h.qty_in, 0) AS BIGINT) AS qty_in, CAST(COALESCE(h.qty_out, 0) AS BIGINT) AS qty_out,
       CAST(COALESCE(h.qty_in, 0) - COALESCE(h.qty_out, 0) AS BIGINT) AS net_change,
       CAST(SUM(COALESCE(h.qty_in, 0) - COALESCE(h.qty_out, 0)) OVER (
            PARTITION BY k.product_key, k.warehouse_key ORDER BY k.date_key
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS BIGINT) AS stock_on_hand
FROM k LEFT JOIN h USING (date_key, product_key, warehouse_key)"""

TABLES = ["fact_inventory_daily_snapshot", "fact_inventory", "dim_date",
          "dim_movement_type", "dim_warehouse", "dim_product"]


def quality_checks(con) -> list[tuple[str, bool]]:
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    return [
        ("dim_product: product_id unik", q("SELECT COUNT(*) = COUNT(DISTINCT product_id) FROM dim_product")),
        ("dim_warehouse: warehouse_id unik", q("SELECT COUNT(*) = COUNT(DISTINCT warehouse_id) FROM dim_warehouse")),
        ("dim_date: 731 hari", q("SELECT COUNT(*) = 731 FROM dim_date")),
        ("fakta: jumlah baris = sumber",
         q("SELECT (SELECT COUNT(*) FROM fact_inventory) = (SELECT COUNT(*) FROM source_inventory_movements)")),
        ("fakta: tidak ada FK NULL",
         q("SELECT COUNT(*) = 0 FROM fact_inventory WHERE product_key IS NULL OR warehouse_key IS NULL "
           "OR movement_type_key IS NULL OR date_key IS NULL")),
        ("transfer seimbang",
         q("SELECT COUNT(*) = 0 FROM (SELECT transfer_id FROM fact_inventory WHERE transfer_id IS NOT NULL "
           "GROUP BY transfer_id HAVING COUNT(*) <> 2 OR SUM(signed_quantity) <> 0)")),
        ("stok tidak negatif", q("SELECT MIN(stock_on_hand) >= 0 FROM fact_inventory_daily_snapshot")),
    ]


def build(db_path: Path, data_dir: Path, naive: bool = False) -> list[tuple[str, bool]]:
    db_path = Path(db_path)
    db_path.unlink(missing_ok=True)
    load(db_path, data_dir)                       # 1. Extract & Load
    con = duckdb.connect(str(db_path))
    for t in TABLES:                              # 2. hapus tabel lama (urutan manual: fakta dulu)
        con.execute(f"DROP TABLE IF EXISTS {t}")
    steps = [DIM_PRODUCT_NAIVE if naive else DIM_PRODUCT,   # 3. urutan muat ditulis tangan:
             DIM_WAREHOUSE_NAIVE if naive else DIM_WAREHOUSE,  #    dimensi -> fakta -> snapshot
             DIM_MOVEMENT_TYPE, DIM_DATE, FACT, SNAPSHOT]
    for sql in steps:
        con.execute(sql)
    checks = quality_checks(con)                  # 4. pengecekan kualitas manual
    con.close()
    return checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=PROJECT_DIR / "inventory_tugas1.duckdb")
    ap.add_argument("--data", type=Path, default=PROJECT_DIR / "data")
    ap.add_argument("--naive", action="store_true", help="bangun dimensi tanpa dedup (kesalahan khas)")
    args = ap.parse_args()
    t0 = time.perf_counter()
    checks = build(args.db, args.data, args.naive)
    elapsed = time.perf_counter() - t0
    print(f"ETL manual{' (NAIVE)' if args.naive else ''} -> {args.db}  ({elapsed:.2f} detik)")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    failed = sum(not ok for _, ok in checks)
    print("Pengecekan kualitas: semua lulus" if failed == 0 else f"Pengecekan kualitas: {failed} gagal")


if __name__ == "__main__":
    main()
