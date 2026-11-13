import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
DBT = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
DUCKDB_ONLY = [r"\bstrftime\s*\(", r"\bgenerate_series\s*\(", r"//", r"\blist_\w+\s*\(",
               r"\bepoch_ms\s*\(", r"\bmonthname\s*\(", r"\bdayname\s*\("]


def test_sql_has_no_duckdb_only_functions():
    files = list((PROJECT / "models").rglob("*.sql")) + list((PROJECT / "analyses").glob("*.sql")) \
        + list((PROJECT / "tests").glob("*.sql")) + list((PROJECT / "macros").glob("*.sql"))
    offenders = []
    for f in files:
        body = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
        offenders += [f"{f.name}: {p}" for p in DUCKDB_ONLY if re.search(p, body, re.I)]
    assert offenders == []


def test_parse_for_postgres_target():
    env = dict(os.environ, NEON_HOST="localhost", NEON_USER="u", NEON_PASSWORD="p", NEON_DB="d")
    r = subprocess.run([str(DBT), "parse", "--profiles-dir", ".", "--target", "postgres", "--no-partial-parse"],
                       cwd=PROJECT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_colab_notebook_valid():
    nb = nbformat.read(PROJECT / "notebooks" / "inventory_dbt_colab.ipynb", as_version=4)
    nbformat.validate(nb)
    code = [c for c in nb.cells if c.cell_type == "code"]
    assert len(code) >= 8
    for c in code:
        py = "\n".join(l for l in c.source.splitlines() if not l.lstrip().startswith(("!", "%")))
        ast.parse(py)
    text = "\n".join(c.source for c in nb.cells)
    assert "dbt build" in text and "--target postgres" in text
    assert not re.search(r"NEON_PASSWORD\s*=\s*['\"]\w", text)  # tidak ada password tertulis
