"""
run_business_queries.py
1) dbt compile  -> merender analyses/bq*.sql (yang memakai ref()) menjadi SQL murni
2) menjalankan SQL hasil kompilasi pada inventory.duckdb
3) menyimpan hasil ke results/bqN_*.csv dan grafik ke charts/bqN_*.png

Pemakaian (dari folder inventory_dbt, setelah dbt build):
    python scripts/run_business_queries.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
COMPILED = PROJECT_DIR / "target" / "compiled" / "inventory_dbt" / "analyses"
RESULTS = PROJECT_DIR / "results"
CHARTS = PROJECT_DIR / "charts"
DBT = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
TYPE_ORDER = ["SALE", "PURCHASE", "TRANSFER", "LOST", "DAMAGED", "FOUND"]
BLUE = "#1f77b4"


def compile_analyses() -> None:
    r = subprocess.run([str(DBT), "compile", "--profiles-dir", ".", "--select", "path:analyses"],
                       cwd=PROJECT_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("dbt compile gagal:\n" + r.stdout + r.stderr)


def run_all() -> dict[str, pd.DataFrame]:
    db = os.environ.get("INVENTORY_DB", str(PROJECT_DIR / "inventory.duckdb"))
    con = duckdb.connect(db, read_only=True)
    out = {}
    for f in sorted(COMPILED.glob("bq*.sql")):
        df = con.execute(f.read_text(encoding="utf-8")).df()
        for c in df.select_dtypes("number").columns:  # SUM bilangan bulat -> tampil tanpa ".0"
            if (df[c].dropna() % 1 == 0).all() and c not in ("aging_days", "pct"):
                df[c] = df[c].astype("Int64")
        out[f.stem] = df
        RESULTS.mkdir(exist_ok=True)
        df.to_csv(RESULTS / f"{f.stem}.csv", index=False)
    con.close()
    return out


def _save(fig, name: str) -> None:
    CHARTS.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(CHARTS / f"{name}.png", dpi=200)
    plt.close(fig)


def _bar_labels(ax, bars, fmt="{:,.0f}"):
    for b in bars:
        ax.annotate(fmt.format(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=8)


def _heatmap(df: pd.DataFrame, title: str, cbar: str, name: str, fmt: str, cmap="YlOrRd") -> None:
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(df) + 2))
    im = ax.imshow(df.values.astype(float), cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(df.columns)), df.columns, rotation=25, ha="right")
    ax.set_yticks(range(len(df.index)), df.index)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            ax.text(j, i, fmt.format(df.values[i, j]), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label=cbar)
    ax.set_title(title, fontweight="bold")
    _save(fig, name)


def charts(r: dict[str, pd.DataFrame]) -> None:
    # BQ1 bar
    df = r["bq1_aging_by_warehouse"]
    fig, ax = plt.subplots(figsize=(7, 4))
    _bar_labels(ax, ax.bar(df.warehouse_name, df.aging_days, color=BLUE), "{:,.1f}")
    ax.set(title="Rata-rata Inventory Aging per Gudang", ylabel="Aging (hari)", xlabel="Gudang")
    _save(fig, "bq1_aging_by_warehouse")

    # BQ2 pie
    df = r["bq2_activity_distribution"]
    fig, ax = plt.subplots(figsize=(6, 6))
    labels = [f"{t} ({p:.1f}%)" if p < 1 else t for t, p in zip(df.movement_type, df.pct)]
    ax.pie(df.total_activity, labels=labels, autopct=lambda v: f"{v:.1f}%" if v >= 1 else "",
           startangle=90, counterclock=False, textprops={"fontsize": 9})
    ax.set_title("Distribusi Aktivitas Inventory", fontweight="bold")
    _save(fig, "bq2_activity_distribution")

    # BQ3 heatmap gudang x tipe
    df = r["bq3_activity_heatmap"].set_index("warehouse_name")[TYPE_ORDER]
    _heatmap(df, "Heatmap Aktivitas Inventory per Gudang", "Jumlah transaksi",
             "bq3_activity_heatmap", "{:,.0f}")

    # BQ4 grouped bar
    df = r["bq4_activity_by_warehouse"].pivot(index="warehouse_name", columns="movement_type",
                                              values="total_activity")[TYPE_ORDER]
    ax = df.plot(kind="bar", figsize=(9, 4.5), rot=0, width=0.8)
    ax.set(title="Aktivitas Inventory per Gudang", ylabel="Jumlah transaksi", xlabel="Gudang")
    ax.set_ylim(0, df.values.max() * 1.3)
    ax.legend(title="Jenis", ncol=6, fontsize=8, loc="upper center")
    _save(ax.get_figure(), "bq4_activity_by_warehouse")

    # BQ5 heatmap kategori x gudang
    df = r["bq5_aging_by_category_warehouse"].pivot(index="category", columns="warehouse_name",
                                                    values="aging_days")
    _heatmap(df, "Inventory Aging per Kategori dan Gudang", "Aging (hari)",
             "bq5_aging_by_category_warehouse", "{:,.1f}")

    # BQ6 heatmap lost+damaged
    df = r["bq6_lost_damaged"].pivot(index="category", columns="warehouse_name",
                                     values="units_lost_damaged")
    _heatmap(df, "Unit Hilang dan Rusak per Kategori dan Gudang", "Unit",
             "bq6_lost_damaged", "{:,.0f}")

    # BQ7 bar
    df = r["bq7_total_activity"]
    fig, ax = plt.subplots(figsize=(7, 4))
    _bar_labels(ax, ax.bar(df.movement_type, df.total_activity, color=BLUE))
    ax.set(title="Total Aktivitas per Jenis Pergerakan", ylabel="Jumlah transaksi")
    _save(fig, "bq7_total_activity")

    # BQ8 horizontal bar
    df = r["bq8_units_sold_by_category"].sort_values("units_sold")
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(df.category, df.units_sold, color=BLUE)
    for b in bars:
        ax.text(b.get_width(), b.get_y() + b.get_height() / 2, f" {b.get_width():,.0f}",
                va="center", fontsize=8)
    ax.set(title="Total Unit Terjual per Kategori", xlabel="Unit terjual")
    _save(fig, "bq8_units_sold_by_category")

    # BQ9 bar per bulan
    df = r["bq9_transfers_per_month"]
    labels = [f"{int(m):02d}/{int(y) % 100}" for y, m in zip(df.year, df.month)]
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(labels, df.transfer_count, color=BLUE)
    for i in df.index[df.transfer_count == df.transfer_count.max()]:  # tandai bulan tertinggi
        bars[i].set_edgecolor("black")
        bars[i].set_linewidth(2)
    ax.set(title="Jumlah Transaksi Transfer per Bulan", ylabel="Transfer", xlabel="Bulan/Tahun")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    _save(fig, "bq9_transfers_per_month")


def main() -> None:
    compile_analyses()
    results = run_all()
    charts(results)
    for name, df in results.items():
        print(f"\n== {name} ({len(df)} baris) ==")
        print(df.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
