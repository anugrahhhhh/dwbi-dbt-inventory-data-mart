"""
load_source.py (ClassicModels)
Mengonversi dump MySQL `mysqlsampledatabase.sql` (MySQL Tutorial) menjadi basis data DuckDB
`classicmodels.duckdb`, sesuai Setup Step 2 pada lembar kegiatan (activity.html).

Pemakaian (dari folder classicmodels_dbt):
    python load_source.py
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
SQL_FILE = HERE / "source_download" / "mysqlsampledatabase.sql"
DB_FILE = HERE / "classicmodels.duckdb"


def mysql_to_duckdb(sql: str) -> list[str]:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)                  # komentar blok
    sql = sql.replace("\\'", "''")                                    # escape kutip MySQL -> SQL standar
    out = []
    for stmt in sql.split(";\n"):
        s = stmt.strip()
        if not s or re.match(r"(?i)(create database|use )", s):
            continue
        if s.upper().startswith("CREATE TABLE"):
            # buang baris FOREIGN KEY (urutan tabel & self-reference MySQL), lalu rapikan koma terakhir
            s = "\n".join(l for l in s.splitlines() if "FOREIGN KEY" not in l.upper())
            s = re.sub(r",\s*\)\s*$", "\n)", s)
            s = re.sub(r"(?i)\bmediumtext\b|\btext\b", "VARCHAR", s)
            s = re.sub(r"(?i)\bmediumblob\b", "BLOB", s)
            s = re.sub(r"(?i)\b(smallint|int)\(\d+\)", r"\1", s)
            s = re.sub(r"(?i)\)\s*ENGINE=.*$", ")", s, flags=re.S)
        out.append(s)
    return out


def main() -> None:
    print(f"Reading {SQL_FILE.name}...")
    stmts = mysql_to_duckdb(SQL_FILE.read_text(encoding="utf-8", errors="replace"))
    print("Converting MySQL syntax to DuckDB...")
    DB_FILE.unlink(missing_ok=True)
    con = duckdb.connect(str(DB_FILE))
    errors = 0
    for s in stmts:
        try:
            con.execute(s)
        except duckdb.Error as e:
            errors += 1
            print("  ERROR:", str(e).splitlines()[0], "|", s[:80].replace("\n", " "))
    con.close()
    print(f"Done. Executed: {len(stmts)} statements, Errors: {errors}")
    print(f"DuckDB file created: {DB_FILE.name}")


if __name__ == "__main__":
    main()
