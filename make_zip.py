"""
make_zip.py
Membuat berkas lampiran DWBI_Kelompok_Inventory.zip (proyek dbt + modul LaTeX + PDF),
tanpa berkas besar/sementara (.venv, *.duckdb, target/, cache, berkas bantu LaTeX).
    python make_zip.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "DWBI_Kelompok_Inventory.zip"
INCLUDE = ["inventory_dbt", "classicmodels_dbt", "latihan_dbt", "Tugas II DWIB/Laporan Mahasiswa DWIB",
           "requirements.txt"]
SKIP_DIRS = {".venv", "target", "dbt_packages", "__pycache__", ".pytest_cache", "logs_dbt"}
SKIP_SUFFIX = {".duckdb", ".wal", ".aux", ".log", ".toc", ".out", ".idx", ".ind", ".ilg", ".bbl", ".blg",
               ".lof", ".lot", ".lol", ".maf", ".gz"}


def wanted(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts) or p.name in (".DS_Store", "dbt.log"):
        return False
    if p.suffix in SKIP_SUFFIX or p.suffix.startswith(".mtc"):
        return False
    return True


def main() -> None:
    n = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            src = ROOT / item
            files = [src] if src.is_file() else sorted(f for f in src.rglob("*") if f.is_file())
            for f in files:
                if wanted(f.relative_to(ROOT)):
                    z.write(f, Path("DWBI_Kelompok_Inventory") / f.relative_to(ROOT))
                    n += 1
    print(f"{OUT.name}: {n} berkas, {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
