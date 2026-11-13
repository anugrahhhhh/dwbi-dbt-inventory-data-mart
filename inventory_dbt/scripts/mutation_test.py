"""
mutation_test.py
Membuktikan bahwa singular test benar-benar mendeteksi data yang salah.
Langkah: salin inventory.duckdb -> rusak data sumbernya -> jalankan dbt build pada salinan.
Test yang diharapkan GAGAL (FAIL) justru menandakan test tersebut bekerja.

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

MUTATIONS = {
    "assert_transfer_balanced":
        ("Hapus sisi IN dari satu transfer (TRF00001)",
         "DELETE FROM source_inventory_movements "
         "WHERE transfer_id = 'TRF00001' AND transfer_direction = 'IN'"),
    "assert_stock_non_negative":
        ("Ubah satu SALE menjadi 1.000.000 unit",
         "UPDATE source_inventory_movements SET quantity = 1000000 "
         "WHERE transaction_id = (SELECT MIN(transaction_id) FROM source_inventory_movements "
         "WHERE movement_type = 'SALE')"),
}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "inventory_mutated.duckdb"
        shutil.copy(PROJECT_DIR / "inventory.duckdb", db)
        con = duckdb.connect(str(db))
        print("Kerusakan yang disuntikkan:")
        for test, (desc, sql) in MUTATIONS.items():
            con.execute(sql)
            print(f"  - {desc}  (target: {test})")
        con.close()

        env = dict(os.environ, INVENTORY_DB=str(db))
        # run lalu test terpisah: dbt build melewati (SKIP) model hilir bila test hulunya gagal
        out = ""
        for cmd in ("run", "test"):
            r = subprocess.run([str(DBT), cmd, "--profiles-dir", ".", "--no-partial-parse"],
                               cwd=PROJECT_DIR, env=env, capture_output=True, text=True)
            out += re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)

    failed = set(re.findall(r"\d+ of \d+ FAIL \d+ (\S+)", out))
    print("\nHasil dbt run + dbt test pada data rusak:")
    print(f"  {'test':<32} {'diharapkan':<11} hasil")
    ok = True
    for test in MUTATIONS:
        hasil = "FAIL" if test in failed else "PASS"
        ok &= hasil == "FAIL"
        print(f"  {test:<32} {'FAIL':<11} {hasil}")
    print("  (test lain yang ikut gagal: " + (", ".join(sorted(failed - set(MUTATIONS))) or "-") + ")")
    summary = [line for line in out.splitlines() if "Done." in line]
    print("  " + (summary[-1].split("  ", 1)[-1].strip() if summary else "(tidak ada ringkasan)"))
    print("\nKESIMPULAN: " + ("SEMUA TEST MENDETEKSI KERUSAKAN" if ok else "ADA TEST YANG TIDAK MENDETEKSI"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
