import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_numbers.py"


def run(tmp_path, text):
    f = tmp_path / "x.tex"
    f.write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)


def test_known_numbers_pass(tmp_path):
    r = run(tmp_path, "Sumatra 190,4 hari, unit keluar 26.594, total 10.000 baris.")
    assert r.returncode == 0, r.stdout


def test_fabricated_number_fails(tmp_path):
    r = run(tmp_path, "Aging gudang 123,4 hari dan 98.765 unit.")
    assert r.returncode == 1
    assert "123,4" in r.stdout and "98.765" in r.stdout


def test_numbers_inside_listings_are_ignored(tmp_path):
    r = run(tmp_path, r"\begin{lstlisting}" + "\n98.765\n" + r"\end{lstlisting}" + "\nTeks biasa.")
    assert r.returncode == 0
