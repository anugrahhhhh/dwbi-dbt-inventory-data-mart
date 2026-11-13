"""
generate_source_data.py
Membangkitkan tiga tabel sumber (OLTP) Data Mart Inventory secara sintetis:
  - source_products            : 50 baris (10 produk unik + 40 versi lama/duplikat)
  - source_warehouses          : 15 baris (3 gudang unik + 12 versi lama/duplikat)
  - source_inventory_movements : 10.000 baris pergerakan stok 2024-01-01 s.d. 2025-12-31

Karakteristik meniru data Tugas I kelompok (lihat slide "Database Sumber (OLTP)").
Data sengaja memuat "kotoran" (spasi berlebih, string kosong, duplikat versi lama)
agar lapisan staging dan dimensi dbt punya pekerjaan nyata.

Pemakaian (dari folder inventory_dbt):
    python scripts/generate_source_data.py            # tulis ke data/
    python scripts/generate_source_data.py --out DIR  # tulis ke folder lain
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
START = datetime(2024, 1, 1)
END = datetime(2026, 1, 1)  # eksklusif

PRODUCTS = [  # product_id, nama, kategori, merek
    ("P001", "Philips Air Fryer HD9200", "Air Fryer", "Philips"),
    ("P002", "Miyako Blender BL-152", "Blender", "Miyako"),
    ("P003", "Philips Blender HR2115", "Blender", "Philips"),
    ("P004", "Krups Coffee Maker KM305", "Coffee Maker", "Krups"),
    ("P005", "Sharp Electric Kettle EKJ-178", "Electric Kettle", "Sharp"),
    ("P006", "Rinnai Electric Stove RI-511", "Electric Stove", "Rinnai"),
    ("P007", "Cosmos Hand Mixer CM-1679", "Hand Mixer", "Cosmos"),
    ("P008", "Panasonic Microwave NN-ST34", "Microwave", "Panasonic"),
    ("P009", "Cosmos Rice Cooker CRJ-6023", "Rice Cooker", "Cosmos"),
    ("P010", "Miyako Rice Cooker MCM-528", "Rice Cooker", "Miyako"),
]
WAREHOUSES = [  # warehouse_id, nama, kota, region, tipe
    ("W01", "Warehouse Jawa", "Jakarta", "Jawa", "Distribution Center"),
    ("W02", "Warehouse Sumatra", "Medan", "Sumatra", "Regional Warehouse"),
    ("W03", "Warehouse Kalimantan", "Balikpapan", "Kalimantan", "Regional Warehouse"),
]
# Jumlah "kejadian" per tipe; TRANSFER menghasilkan 2 baris (OUT + IN) per kejadian.
EVENT_COUNTS = {"PURCHASE": 1673, "SALE": 1602, "LOST": 1691, "DAMAGED": 1691,
                "FOUND": 33, "TRANSFER": 1655}
QTY_RANGE = {"PURCHASE": (20, 80), "SALE": (5, 30), "LOST": (2, 12),
             "DAMAGED": (2, 12), "FOUND": (1, 5), "TRANSFER": (5, 30)}
OUTFLOW = {"SALE", "LOST", "DAMAGED"}


def _products(rng: random.Random) -> pd.DataFrame:
    rows = []
    for pid, name, cat, brand in PRODUCTS:
        base = datetime(2025, 12, 1) - timedelta(days=rng.randint(0, 60))
        # versi terbaru (yang benar); sebagian nama diberi spasi berlebih
        cur_name = f"  {name} " if pid in ("P002", "P007", "P009") else name
        rows.append((pid, cur_name, cat, brand, "Active", base))
        # 4 versi lama dengan updated_at lebih awal
        for v in range(4):
            old_ts = base - timedelta(days=90 * (v + 1) + rng.randint(0, 30))
            old_brand = "" if v == 1 else brand
            old_status = ["Inactive", "Active", "", "Discontinued"][v]
            rows.append((pid, f"{name} (v{v + 1})", f" {cat}", old_brand, old_status, old_ts))
    rng.shuffle(rows)
    return pd.DataFrame(rows, columns=["product_id", "product_name", "category",
                                       "brand", "product_status", "updated_at"])


def _warehouses(rng: random.Random) -> pd.DataFrame:
    rows = []
    for wid, name, city, region, wtype in WAREHOUSES:
        base = datetime(2025, 11, 1) - timedelta(days=rng.randint(0, 30))
        rows.append((wid, name, city, region, wtype, base))
        for v in range(4):
            old_ts = base - timedelta(days=120 * (v + 1) + rng.randint(0, 20))
            old_city = "" if v == 2 else f"{city} "
            rows.append((wid, f" {name} Lama", old_city, region, "Gudang Transit", old_ts))
    rng.shuffle(rows)
    return pd.DataFrame(rows, columns=["warehouse_id", "warehouse_name", "city",
                                       "region", "warehouse_type", "updated_at"])


def _movements(rng: random.Random) -> pd.DataFrame:
    events = [t for t, n in EVENT_COUNTS.items() for _ in range(n)]
    rng.shuffle(events)
    # 40 kejadian pertama dipaksa PURCHASE (stok awal); tukar dengan PURCHASE di belakang
    for i in range(40):
        if events[i] != "PURCHASE":
            j = next(k for k in range(len(events) - 1, i, -1) if events[k] == "PURCHASE")
            events[i], events[j] = events[j], events[i]

    span = int((END - START).total_seconds())
    stamps = sorted(START + timedelta(seconds=rng.randrange(span)) for _ in events)
    pids = [p[0] for p in PRODUCTS]
    wids = [w[0] for w in WAREHOUSES]
    # Blender & Rice Cooker lebih laku (bobot penjualan lebih besar)
    weight = {p: (2 if p in ("P002", "P003", "P009", "P010") else 1) for p in pids}
    stock = {(p, w): 0 for p in pids for w in wids}

    rows, trx, trf = [], 0, 0

    def add(ts, pid, wid, mtype, qty, tid=None, direction=None):
        nonlocal trx
        trx += 1
        rows.append((f"TRX{trx:06d}", tid, direction, pid, wid, mtype, qty,
                     ts.replace(microsecond=0)))

    for ts, mtype in zip(stamps, events):
        lo, hi = QTY_RANGE[mtype]
        qty = rng.randint(lo, hi)
        pid = rng.choices(pids, weights=[weight[p] for p in pids])[0]
        wid = rng.choice(wids)
        if mtype in ("PURCHASE", "FOUND"):
            stock[(pid, wid)] += qty
            add(ts, pid, wid, mtype, qty)
            continue
        # keluar: pilih kombinasi yang stoknya cukup; bila tidak ada, kurangi qty
        if stock[(pid, wid)] < qty:
            ok = [k for k, s in stock.items() if s >= qty]
            if ok:
                pid, wid = rng.choice(ok)
            else:
                pid, wid = max(stock, key=stock.get)
                qty = stock[(pid, wid)]
        if mtype in OUTFLOW:
            stock[(pid, wid)] -= qty
            add(ts, pid, wid, mtype, qty)
        else:  # TRANSFER: OUT dari gudang asal, IN ke gudang tujuan, timestamp sama
            trf += 1
            tid = f"TRF{trf:05d}"
            dest = rng.choice([w for w in wids if w != wid])
            stock[(pid, wid)] -= qty
            stock[(pid, dest)] += qty
            add(ts, pid, wid, "TRANSFER", qty, tid, "OUT")
            add(ts, pid, dest, "TRANSFER", qty, tid, "IN")

    return pd.DataFrame(rows, columns=["transaction_id", "transfer_id", "transfer_direction",
                                       "product_id", "warehouse_id", "movement_type",
                                       "quantity", "transaction_timestamp"])


def generate(out_dir: Path, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Bangkitkan ketiga tabel sumber, tulis sebagai CSV ke out_dir, dan kembalikan DataFrame-nya."""
    rng = random.Random(seed)
    dfs = {
        "source_products": _products(rng),
        "source_warehouses": _warehouses(rng),
        "source_inventory_movements": _movements(rng),
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in dfs.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    return dfs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", type=Path, default=PROJECT_DIR / "data")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    dfs = generate(args.out, args.seed)
    m = dfs["source_inventory_movements"]
    print(f"Folder keluaran : {args.out}")
    for name, df in dfs.items():
        print(f"  {name:<28} {len(df):>6,} baris")
    print(f"Produk unik     : {dfs['source_products'].product_id.nunique()}")
    print(f"Gudang unik     : {dfs['source_warehouses'].warehouse_id.nunique()}")
    print(f"Transfer unik   : {m.transfer_id.nunique()}")
    print("Distribusi movement_type:")
    for t, n in m.movement_type.value_counts().sort_index().items():
        print(f"  {t:<10} {n:>6,}")


if __name__ == "__main__":
    main()
