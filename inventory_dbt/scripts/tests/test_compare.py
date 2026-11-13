import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
PY = sys.executable


def run(*args):
    r = subprocess.run([PY, *map(str, args)], cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_manual_etl_matches_dbt(tmp_path):
    db = tmp_path / "tugas1.duckdb"
    out = run(PROJECT / "scripts" / "etl_manual_tugas1.py", "--db", db)
    assert "pengecekan kualitas: semua lulus" in out.lower()
    cmp = run(PROJECT / "scripts" / "compare_tugas1_vs_dbt.py", "--manual-db", db)
    assert "BERBEDA" not in cmp
    assert "KESIMPULAN: seluruh hasil identik" in cmp


def test_naive_manual_etl_differs(tmp_path):
    db = tmp_path / "naive.duckdb"
    run(PROJECT / "scripts" / "etl_manual_tugas1.py", "--db", db, "--naive")
    cmp = run(PROJECT / "scripts" / "compare_tugas1_vs_dbt.py", "--manual-db", db)
    lines = {l.split()[0]: l for l in cmp.splitlines() if l.strip() and not l.startswith(" ")}
    assert "BERBEDA" in lines["fact_inventory"]
    assert "BERBEDA" in lines["bq8_units_sold_by_category"]
    assert "KESIMPULAN: ada hasil yang berbeda" in cmp
