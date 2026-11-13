"""
check_numbers.py
Memeriksa bahwa setiap angka berformat Indonesia di narasi modul (di luar listing/tabel otomatis)
benar-benar muncul di hasil eksekusi (results/*.csv, logs/*.txt kedua proyek) atau di daftar
angka turunan yang perhitungannya dijelaskan di bawah.

    python scripts/check_numbers.py <berkas.tex> [...]
Keluar dengan kode 1 bila ada angka yang tidak dapat dilacak.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [p for proj in ("inventory_dbt", "classicmodels_dbt", "latihan_dbt")
           for sub in ("results/*.csv", "logs/*.txt") for p in (ROOT / proj).glob(sub)]

# Angka turunan yang dihitung dari hasil di atas (rumus dicantumkan agar dapat diperiksa)
DERIVED = {
    23644: "LOST 11.718 + DAMAGED 11.926 (bq7)",
    84: "23.644 / 28.094 = 84,2% (bq7)",
    213000: "unit SALE Rice Cooker mode naive = 8.520 x 25 (diverifikasi dengan kueri)",
    32292: "SUM(stock_on_hand) pada 20251231 (diverifikasi dengan kueri)",
    14075256: "SUM(stock_on_hand) seluruh tanggal (diverifikasi dengan kueri)",
    21930: "10 produk x 3 gudang x 731 hari",
    9604190.61: "total revenue ClassicModels (checkpoints.csv)",
    9.6: "9.604.190,61 dibulatkan ke juta (checkpoint activity: 'approximately $9.6 million')",
}


def known_numbers() -> set[float]:
    nums = set(DERIVED)
    for f in SOURCES:
        for tok in re.findall(r"\d[\d,.]*", f.read_text(encoding="utf-8", errors="ignore")):
            tok = tok.strip(".,")
            for cand in (tok.replace(",", ""), tok):  # format 10,000 (log) dan 157.7 (csv)
                try:
                    nums.add(round(float(cand), 2))
                except ValueError:
                    pass
    return nums


def narrative(text: str) -> str:
    text = re.sub(r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}", "", text, flags=re.S)
    text = re.sub(r"\\(lstinputlisting|input|includegraphics|label|ref|cite[tp]?|url)(\[[^\]]*\])?\{[^}]*\}", "", text)
    return re.sub(r"(?<!\\)%.*", "", text)


def indo_numbers(text: str) -> list[str]:
    # 10.000 | 157,7 | 26.594 | 0,33  (abaikan tahun 2024/2025, NIM, versi 1.11.x, tanggal)
    toks = re.findall(r"(?<![\w./-])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+)(?![\w/-])", text)
    return toks


def main(paths: list[str]) -> int:
    known = known_numbers()
    bad = []
    for p in paths:
        for tok in indo_numbers(narrative(Path(p).read_text(encoding="utf-8"))):
            val = round(float(tok.replace(".", "").replace(",", ".")), 2)
            if val not in known:
                bad.append((Path(p).name, tok))
    checked = sum(len(indo_numbers(narrative(Path(p).read_text(encoding="utf-8")))) for p in paths)
    print(f"{checked} angka diperiksa, {len(bad)} tidak terlacak")
    for f, t in bad:
        print(f"  TIDAK TERLACAK: {f}: {t}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
