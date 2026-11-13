"""
load_source.py
Tahap Extract & Load: memuat CSV di data/ ke basis data sebagai tabel source_*.
dbt tidak memindahkan data; langkah ini dikerjakan di luar dbt.

Pemakaian (dari folder inventory_dbt):
    python scripts/load_source.py                      # DuckDB lokal: inventory.duckdb
    python scripts/load_source.py --target postgres    # PostgreSQL/Neon (baca env NEON_*)
Menjalankan ulang aman: tabel diganti (CREATE OR REPLACE), bukan ditambah.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
TABLES = ["source_products", "source_warehouses", "source_inventory_movements"]
TYPES = {
    "source_products": {"product_id": "VARCHAR", "product_name": "VARCHAR", "category": "VARCHAR",
                        "brand": "VARCHAR", "product_status": "VARCHAR", "updated_at": "TIMESTAMP"},
    "source_warehouses": {"warehouse_id": "VARCHAR", "warehouse_name": "VARCHAR", "city": "VARCHAR",
                          "region": "VARCHAR", "warehouse_type": "VARCHAR", "updated_at": "TIMESTAMP"},
    "source_inventory_movements": {"transaction_id": "VARCHAR", "transfer_id": "VARCHAR",
                                   "transfer_direction": "VARCHAR", "product_id": "VARCHAR",
                                   "warehouse_id": "VARCHAR", "movement_type": "VARCHAR",
                                   "quantity": "INTEGER", "transaction_timestamp": "TIMESTAMP"},
}
NULLABLE = {"transfer_id", "transfer_direction"}  # kosong di CSV = NULL; kolom lain tetap string kosong


def _read(data_dir: Path, table: str) -> pd.DataFrame:
    df = pd.read_csv(data_dir / f"{table}.csv", dtype=str, keep_default_na=False)
    for col in NULLABLE & set(df.columns):
        df[col] = df[col].replace("", None)
    return df


def load(db_path: Path, data_dir: Path) -> dict[str, int]:
    """Muat ketiga CSV ke DuckDB di db_path. Mengembalikan jumlah baris per tabel."""
    import duckdb

    con = duckdb.connect(str(db_path))
    counts = {}
    for t in TABLES:
        df = _read(Path(data_dir), t)
        cols = ", ".join(f'CAST("{c}" AS {ty}) AS {c}' for c, ty in TYPES[t].items())
        con.register("tmp_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT {cols} FROM tmp_df")
        con.unregister("tmp_df")
        counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()
    return counts


def load_postgres(data_dir: Path, schema: str = "public") -> dict[str, int]:
    """Muat ketiga CSV ke PostgreSQL (mis. Neon). Kredensial dibaca dari env NEON_*."""
    import psycopg2

    con = psycopg2.connect(host=os.environ["NEON_HOST"], user=os.environ["NEON_USER"],
                           password=os.environ["NEON_PASSWORD"], dbname=os.environ["NEON_DB"],
                           port=int(os.environ.get("NEON_PORT", "5432")), sslmode="require")
    counts = {}
    with con, con.cursor() as cur:
        for t in TABLES:
            pg = {"VARCHAR": "TEXT"}
            ddl = ", ".join(f"{c} {pg.get(ty, ty)}" for c, ty in TYPES[t].items())
            cur.execute(f"DROP TABLE IF EXISTS {schema}.{t}; CREATE TABLE {schema}.{t} ({ddl})")
            df = _read(Path(data_dir), t)
            rows = [tuple(None if v is None else v for v in r) for r in df.itertuples(index=False)]
            ph = ", ".join(["%s"] * len(df.columns))
            cur.executemany(f"INSERT INTO {schema}.{t} VALUES ({ph})", rows)
            cur.execute(f"SELECT COUNT(*) FROM {schema}.{t}")
            counts[t] = cur.fetchone()[0]
    con.close()
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["duckdb", "postgres"], default="duckdb")
    ap.add_argument("--db", type=Path, default=PROJECT_DIR / "inventory.duckdb")
    ap.add_argument("--data", type=Path, default=PROJECT_DIR / "data")
    args = ap.parse_args()
    if args.target == "duckdb":
        counts = load(args.db, args.data)
        print(f"Basis data: {args.db}")
    else:
        counts = load_postgres(args.data)
        print(f"Basis data: PostgreSQL {os.environ['NEON_HOST']} / {os.environ['NEON_DB']}")
    for t, n in counts.items():
        print(f"  {t:<28} {n:>6,} baris dimuat")


if __name__ == "__main__":
    main()
