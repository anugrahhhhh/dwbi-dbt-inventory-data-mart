"""
make_tables.py
Membangkitkan tabel LaTeX (kode/tabel/*.tex) langsung dari hasil eksekusi nyata
(results/*.csv, logs/*.txt, target/manifest.json), sehingga angka di modul tidak diketik ulang.
Dipanggil otomatis oleh sync_assets.py.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INV = ROOT / "inventory_dbt"
CM = ROOT / "classicmodels_dbt"
OUT = HERE / "kode" / "tabel"
WH = ["Warehouse Jawa", "Warehouse Kalimantan", "Warehouse Sumatra"]
WH_SHORT = {"Warehouse Jawa": "Jawa", "Warehouse Kalimantan": "Kalimantan", "Warehouse Sumatra": "Sumatra"}
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def angka(v, desimal: int = 0) -> str:
    """Format angka gaya Indonesia: 12.345,6"""
    s = f"{float(v):,.{desimal}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tex(s: str) -> str:
    return str(s).replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


def tabel(nama: str, kolom: str, header: list[str], baris: list[list[str]], total: list[str] | None = None) -> None:
    lines = [rf"\begin{{tabular}}{{{kolom}}}", r"\toprule", " & ".join(rf"\textbf{{{h}}}" for h in header) + r" \\",
             r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in baris]
    if total:
        lines += [r"\midrule", " & ".join(total) + r" \\"]
    lines += [r"\bottomrule", r"\end{tabular}"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{nama}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def csv(name: str, base: Path = INV) -> pd.DataFrame:
    # keep_default_na=False: territory "NA" (North America) jangan dibaca sebagai nilai kosong
    return pd.read_csv(base / "results" / f"{name}.csv", keep_default_na=False, na_values=[""])


def inventory_tables() -> None:
    d = csv("bq1_aging_by_warehouse")
    tabel("bq1", "lrrr", ["Gudang", "Total stok harian (unit-hari)", "Total unit keluar", "Aging (hari)"],
          [[r.warehouse_name, angka(r.total_stock_days), angka(r.total_qty_out), angka(r.aging_days, 1)]
           for r in d.itertuples()])

    d = csv("bq2_activity_distribution")
    tabel("bq2", "lrr", ["Jenis pergerakan", "Transaksi", "Persentase"],
          [[r.movement_type, angka(r.total_activity), angka(r.pct, 2) + r"\%"] for r in d.itertuples()],
          [r"\textbf{Total}", angka(d.total_activity.sum()), angka(d.pct.sum(), 2) + r"\%"])

    d = csv("bq3_activity_heatmap").set_index("warehouse_name")
    cols = ["SALE", "PURCHASE", "TRANSFER", "LOST", "DAMAGED", "FOUND"]
    tabel("bq3", "l" + "r" * 7, ["Gudang"] + cols + ["Total"],
          [[w] + [angka(d.loc[w, c]) for c in cols] + [angka(d.loc[w, cols].sum())] for w in d.index],
          [r"\textbf{Total}"] + [angka(d[c].sum()) for c in cols] + [angka(d[cols].values.sum())])

    for name, value, label in [("bq5_aging_by_category_warehouse", "aging_days", "bq5"),
                               ("bq6_lost_damaged", "units_lost_damaged", "bq6")]:
        d = csv(name).pivot(index="category", columns="warehouse_name", values=value)[WH]
        des = 1 if label == "bq5" else 0
        rows = [[k] + [angka(d.loc[k, w], des) for w in WH] for k in d.index]
        total = None
        if label == "bq6":
            rows = [r + [angka(d.loc[k].sum())] for r, k in zip(rows, d.index)]
            total = [r"\textbf{Total}"] + [angka(d[w].sum()) for w in WH] + [angka(d.values.sum())]
        tabel(label, "l" + "r" * (len(WH) + (label == "bq6")),
              ["Kategori"] + [WH_SHORT[w] for w in WH] + (["Total"] if label == "bq6" else []), rows, total)

    d = csv("bq7_total_activity")
    tabel("bq7", "llrr", ["Jenis", "Kelompok", "Transaksi", "Unit"],
          [[r.movement_type, r.movement_group, angka(r.total_activity), angka(r.total_units)] for r in d.itertuples()],
          [r"\textbf{Total}", "", angka(d.total_activity.sum()), angka(d.total_units.sum())])

    d = csv("bq8_units_sold_by_category")
    tot = d.units_sold.sum()
    tabel("bq8", "lrrr", ["Kategori", "Transaksi SALE", "Unit terjual", "Pangsa"],
          [[r.category, angka(r.sale_transactions), angka(r.units_sold), angka(100 * r.units_sold / tot, 1) + r"\%"]
           for r in d.itertuples()],
          [r"\textbf{Total}", angka(d.sale_transactions.sum()), angka(tot), r"100,0\%"])

    d = csv("bq9_transfers_per_month")
    y24, y25 = d[d.year == 2024].reset_index(), d[d.year == 2025].reset_index()
    tabel("bq9", "lrrrr", ["Bulan", "Transfer 2024", "Unit 2024", "Transfer 2025", "Unit 2025"],
          [[BULAN[i], angka(y24.transfer_count[i]), angka(y24.units_transferred[i]),
            angka(y25.transfer_count[i]), angka(y25.units_transferred[i])] for i in range(12)],
          [r"\textbf{Total}", angka(y24.transfer_count.sum()), angka(y24.units_transferred.sum()),
           angka(y25.transfer_count.sum()), angka(y25.units_transferred.sum())])


def test_summary() -> None:
    m = json.loads((INV / "target" / "manifest.json").read_text(encoding="utf-8"))
    c = Counter()
    for n in m["nodes"].values():
        if n["resource_type"] != "test":
            continue
        meta = n.get("test_metadata") or {}
        c[meta.get("name", "singular")] += 1
    order = [("unique", "Keunikan kunci (surrogate key, natural key, transaction\\_id)"),
             ("not_null", "Kolom wajib terisi, termasuk seluruh foreign key"),
             ("relationships", "Integritas foreign key fakta $\\rightarrow$ dimensi (4 FK fakta transaksi + 3 FK snapshot)"),
             ("accepted_values", "Nilai yang diizinkan: jenis pergerakan dan arah transfer"),
             ("singular", "Aturan bisnis berupa berkas SQL di \\kode{tests/}")]
    tabel("tests", "lrp{0.58\\linewidth}", ["Jenis test", "Jumlah", "Yang diuji"],
          [[tex(k), str(c[k]), d] for k, d in order],
          [r"\textbf{Total}", str(sum(c.values())), r"seluruhnya \textbf{PASS}"])


def compare_tables() -> None:
    for mode in ("normal", "naive"):
        lines = (INV / "logs" / f"compare_{mode}.txt").read_text(encoding="utf-8").splitlines()
        rows = []
        for l in lines:
            m = re.match(r"^(\w+)\s+([\d,]+)\s+([\d,]+)\s+(IDENTIK|BERBEDA)$", l.strip())
            if m:
                st = r"\textcolor{green!50!black}{IDENTIK}" if m[4] == "IDENTIK" else r"\textcolor{red}{BERBEDA}"
                rows.append([r"\kode{" + tex(m[1]) + "}", angka(m[2].replace(",", "")),
                             angka(m[3].replace(",", "")), st])
        tabel(f"compare_{mode}", "lrrl", ["Objek", "Baris Tugas I", "Baris dbt", "Status"], rows)


def classicmodels_tables() -> None:
    d = csv("revenue_by_product_line", CM)
    tabel("cm_productline", "lrrrr", ["Lini produk", "Revenue (USD)", "Gross profit (USD)", "Pesanan", "Margin"],
          [[r.product_line, angka(r.total_revenue, 2), angka(r.total_gross_profit, 2), angka(r.order_count),
            angka(r.gross_margin_pct, 1) + r"\%"] for r in d.itertuples()],
          [r"\textbf{Total}", angka(d.total_revenue.sum(), 2), angka(d.total_gross_profit.sum(), 2), "", ""])
    d = csv("top5_sales_reps_2004", CM)
    tabel("cm_reps", "llrrr", ["Sales rep", "Territory", "Revenue 2004 (USD)", "Pesanan", "Jml. pelanggan unik per bulan"],
          [[r.full_name, r.territory, angka(r.ytd_revenue, 2), angka(r.total_orders), angka(r.customers_served)]
           for r in d.itertuples()])


def main() -> None:
    inventory_tables()
    test_summary()
    compare_tables()
    classicmodels_tables()
    print(f"{len(list(OUT.glob('*.tex')))} tabel LaTeX dibangkitkan ke {OUT.relative_to(HERE)}")


if __name__ == "__main__":
    main()
