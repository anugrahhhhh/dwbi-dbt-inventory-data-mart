import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT / "results"
CHARTS = PROJECT / "charts"
NAMES = ["bq1_aging_by_warehouse", "bq2_activity_distribution", "bq3_activity_heatmap",
         "bq4_activity_by_warehouse", "bq5_aging_by_category_warehouse", "bq6_lost_damaged",
         "bq7_total_activity", "bq8_units_sold_by_category", "bq9_transfers_per_month"]


@pytest.fixture(scope="module", autouse=True)
def run_queries():
    r = subprocess.run([sys.executable, str(PROJECT / "scripts" / "run_business_queries.py")],
                       cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr


def bq(name):
    return pd.read_csv(RESULTS / f"{name}.csv")


def src():
    return pd.read_csv(PROJECT / "data" / "source_inventory_movements.csv")


def test_all_outputs_exist():
    for n in NAMES:
        assert (RESULTS / f"{n}.csv").exists(), n
        assert (CHARTS / f"{n}.png").stat().st_size > 10_000, n


def test_bq7_total_is_all_movements():
    assert bq("bq7_total_activity").total_activity.sum() == 10_000


def test_bq2_percentages_sum_to_100():
    assert abs(bq("bq2_activity_distribution").pct.sum() - 100) < 0.1


def test_bq3_equals_bq4():
    long = bq("bq4_activity_by_warehouse").set_index(["warehouse_name", "movement_type"]).total_activity
    wide = bq("bq3_activity_heatmap").set_index("warehouse_name")
    for (w, t), v in long.items():
        assert wide.loc[w, t] == v


def test_bq8_matches_source_sales():
    s = src()
    assert bq("bq8_units_sold_by_category").units_sold.sum() == s.loc[s.movement_type == "SALE", "quantity"].sum()


def test_bq9_has_24_months_and_all_transfers():
    df = bq("bq9_transfers_per_month")
    assert len(df) == 24
    assert df.transfer_count.sum() == src().transfer_id.nunique()


def test_bq6_matches_source_lost_damaged():
    s = src()
    expected = s.loc[s.movement_type.isin(["LOST", "DAMAGED"]), "quantity"].sum()
    assert bq("bq6_lost_damaged").units_lost_damaged.sum() == expected


def test_aging_is_finite_and_positive():
    for n, col in [("bq1_aging_by_warehouse", "aging_days"), ("bq5_aging_by_category_warehouse", "aging_days")]:
        vals = bq(n)[col]
        assert vals.notna().all() and (vals > 0).all()
        assert all(math.isfinite(v) for v in vals)


def test_ties_are_ordered_deterministically():
    # DAMAGED dan LOST sama-sama 1.691 transaksi: urutan harus stabil (alfabetis) antar-run
    for name in ("bq2_activity_distribution", "bq7_total_activity"):
        df = bq(name)
        expected = df.sort_values(["total_activity", "movement_type"], ascending=[False, True])
        assert list(df.movement_type) == list(expected.movement_type), name
