import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def test_mutation_tests_catch_corrupted_data():
    r = subprocess.run([sys.executable, str(PROJECT / "scripts" / "mutation_test.py")],
                       cwd=PROJECT, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "assert_transfer_balanced" in r.stdout and "assert_stock_non_negative" in r.stdout
    assert "SEMUA TEST MENDETEKSI KERUSAKAN" in r.stdout
