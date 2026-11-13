"""
sync_assets.py
Menyalin kode, log, hasil, dan grafik dari proyek dbt ke folder modul (kode/ dan figures/)
agar folder LaTeX ini mandiri (dapat diunggah utuh ke Overleaf).
Jalankan ulang setiap kali proyek dbt berubah:
    python sync_assets.py
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COPY = {
    "inventory_dbt": ["dbt_project.yml", "profiles.yml", "models/**/*.sql", "models/**/*.yml",
                      "macros/*.sql", "tests/*.sql", "analyses/*.sql", "logs/*.txt", "results/*.csv",
                      "scripts/generate_source_data.py", "scripts/load_source.py",
                      "scripts/etl_manual_tugas1.py", "scripts/compare_tugas1_vs_dbt.py"],
    "classicmodels_dbt": ["dbt_project.yml", "profiles.yml", "models/**/*.sql", "models/**/*.yml",
                          "tests/*.sql", "logs/*.txt", "results/*.csv", "load_source.py"],
    "latihan_dbt": ["**/*.sql", "**/*.yml", "**/*.csv", "logs/*.txt"],
}
FIGS = {
    "inventory_dbt/charts/*.png": "inv_",
    "classicmodels_dbt/charts/*.png": "cm_",
}


def main() -> None:
    dest = HERE / "kode"
    if dest.exists():
        shutil.rmtree(dest)
    n = 0
    for proj, patterns in COPY.items():
        base = ROOT / proj
        if not base.exists():
            continue
        for pat in patterns:
            for f in base.glob(pat):
                if any(part in ("target", "dbt_packages", ".venv") for part in f.parts):
                    continue
                out = dest / proj / f.relative_to(base)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, out)
                n += 1
    for pat, prefix in FIGS.items():
        for f in ROOT.glob(pat):
            shutil.copy2(f, HERE / "figures" / f"{prefix}{f.name}")
            n += 1
    print(f"{n} berkas disalin ke {dest.name}/ dan figures/")
    import make_tables
    make_tables.main()


if __name__ == "__main__":
    main()
