"""
make_overleaf_zip.py
Membuat Modul_Overleaf.zip: folder LaTeX modul yang mandiri untuk diunggah ke Overleaf
(New Project -> Upload Project). Berisi Makalah.tex, kultem.sty, references.bib, contents/,
figures/, images/, dan kode/ (hasil sync_assets.py), tanpa berkas bantu hasil kompilasi.

    python make_overleaf_zip.py
"""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "Modul_Overleaf.zip"
INCLUDE_FILES = ["Makalah.tex", "kultem.sty", "references.bib"]
INCLUDE_DIRS = ["contents", "figures", "images", "kode"]
SKIP_SUFFIX = {".aux", ".log", ".toc", ".out", ".idx", ".ind", ".ilg", ".bbl", ".blg", ".lof", ".lot",
               ".lol", ".maf", ".gz", ".pdf"}


def files():
    for name in INCLUDE_FILES:
        yield HERE / name
    for d in INCLUDE_DIRS:
        for f in sorted((HERE / d).rglob("*")):
            if f.is_file() and f.suffix not in SKIP_SUFFIX and not f.suffix.startswith(".mtc") \
                    and f.name != ".DS_Store":
                yield f


def main() -> None:
    n = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files():
            z.write(f, f.relative_to(HERE).as_posix())
            n += 1
    print(f"{OUT.name}: {n} berkas, {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
