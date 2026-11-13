"""
mutation_test.py
Membuktikan bahwa singular test benar-benar mendeteksi data yang salah.
Setiap kerusakan disuntikkan pada SALINAN TERSENDIRI dari inventory.duckdb, lalu dbt dijalankan
pada salinan itu. Yang diharapkan: test target GAGAL (FAIL), dan test target kerusakan lain
tetap PASS, sehingga terbukti setiap test menangkap kerusakan miliknya sendiri.

Pemakaian (dari folder inventory_dbt, setelah load_source.py):
    python scripts/mutation_test.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

PROJECT_DIR = Path(__file__).resolve().parents[1]
DBT = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
if not DBT.exists():  # mis. dbt dipasang di luar venv
    DBT = Path(shutil.which("dbt") or "dbt")

MUTATIONS = {
    "assert_transfer_balanced":
        ("Sisi IN transfer TRF00001 ditambah 5 unit (OUT dan IN tidak sama)",
         "UPDATE source_inventory_movements SET quantity = quantity + 5 "
         "WHERE transfer_id = 'TRF00001' AND transfer_direction = 'IN'"),
    "assert_stock_non_negative":
        ("Satu SALE diubah menjadi 1.000.000 unit",
         "UPDATE source_inventory_movements SET quantity = 1000000 "
         "WHERE transaction_id = (SELECT MIN(transaction_id) FROM source_inventory_movements "
         "WHERE movement_type = 'SALE')"),
}


def run_on_copy(sql: str) -> tuple[set[str], str]:
    """Salin DB, suntikkan satu kerusakan, jalankan dbt run + dbt test. Kembalikan test yang FAIL."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "inventory_mutated.duckdb"
        shutil.copy(PROJECT_DIR / "inventory.duckdb", db)
        con = duckdb.connect(str(db))
        con.execute(sql)
        con.close()
        env = dict(os.environ, INVENTORY_DB=str(db))
        out = ""
        # run lalu test terpisah: dbt build melewati (SKIP) model hilir bila test hulunya gagal
        for cmd in ("run", "test"):
            r = subprocess.run([str(DBT), cmd, "--profiles-dir", ".", "--no-partial-parse"],
                               cwd=PROJECT_DIR, env=env, capture_output=True, text=True)
            out += re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
    failed = set(re.findall(r"\d+ of \d+ FAIL \d+ (\S+)", out))
    summary = [line.split("  ", 1)[-1].strip() for line in out.splitlines() if "Done." in line]
    return failed, summary[-1] if summary else "(tidak ada ringkasan)"


def main() -> int:
    ok, isolated = True, True
    print(f"{'kerusakan (pada salinan tersendiri)':<62} {'test target':<28} hasil  test target lain")
    for target, (desc, sql) in MUTATIONS.items():
        failed, summary = run_on_copy(sql)
        others = [t for t in MUTATIONS if t != target]
        other_state = ", ".join(f"{t}={'FAIL' if t in failed else 'PASS'}" for t in others)
        hit = target in failed
        ok &= hit
        isolated &= not any(t in failed for t in others)
        print(f"{desc:<62} {target:<28} {'FAIL' if hit else 'PASS':<6} {other_state}")
        print(f"{'':<62} {summary}")
    print("\nTERISOLASI: " + ("ya" if isolated else "tidak (satu kerusakan ikut menggagalkan test lain)"))
    print("KESIMPULAN: " + ("SEMUA TEST MENDETEKSI KERUSAKAN" if ok else "ADA TEST YANG TIDAK MENDETEKSI"))
    return 0 if ok and isolated else 1


if __name__ == "__main__":
    sys.exit(main())
