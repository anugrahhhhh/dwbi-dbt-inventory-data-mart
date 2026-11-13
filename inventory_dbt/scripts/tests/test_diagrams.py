import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def test_lineage_png_created():
    out = PROJECT / "charts" / "lineage.png"
    out.unlink(missing_ok=True)
    r = subprocess.run([sys.executable, str(PROJECT / "scripts" / "draw_diagrams.py")],
                       cwd=PROJECT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.exists() and out.stat().st_size > 10_000
    assert "12 node" in r.stdout  # 3 source + 3 staging + 4 dim + 2 fact
