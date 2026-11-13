"""load_postgres diuji dengan koneksi tiruan (tidak ada server PostgreSQL di lingkungan uji)."""
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import load_source  # noqa: E402
from generate_source_data import generate  # noqa: E402


class FakeCursor:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, *a):
        self.log.append(("execute", sql))

    def executemany(self, sql, rows):
        self.log.append(("executemany", sql, len(list(rows))))

    def fetchone(self):
        return (0,)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, log):
        self.log = log

    def cursor(self):
        return FakeCursor(self.log)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def log(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(psycopg2, "connect", lambda **kw: FakeConn(calls))
    monkeypatch.setattr(psycopg2.extras, "execute_values",
                        lambda cur, sql, rows, page_size=100: calls.append(("execute_values", sql, len(rows), page_size)))
    for k in ("NEON_HOST", "NEON_USER", "NEON_PASSWORD", "NEON_DB"):
        monkeypatch.setenv(k, "x")
    generate(tmp_path, seed=42)
    load_source.load_postgres(tmp_path)
    return calls


def test_drop_uses_cascade_so_rerun_after_dbt_build_works(log):
    # view analytics_dbt.stg_* bergantung pada public.source_*; DROP tanpa CASCADE gagal di PostgreSQL
    drops = [c[1] for c in log if c[0] == "execute" and "DROP TABLE" in c[1]]
    assert len(drops) == 3 and all("CASCADE" in d for d in drops)


def test_rows_are_sent_in_batches_not_one_round_trip_per_row(log):
    assert not [c for c in log if c[0] == "executemany"]
    batches = [c for c in log if c[0] == "execute_values"]
    assert sum(c[2] for c in batches) == 50 + 15 + 10_000
    assert all(c[3] >= 1000 for c in batches)
