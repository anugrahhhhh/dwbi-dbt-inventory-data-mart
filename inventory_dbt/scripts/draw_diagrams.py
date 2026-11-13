"""
draw_diagrams.py
Menggambar lineage graph (DAG) proyek dari target/manifest.json ke charts/lineage.png.
Jalankan setelah `dbt docs generate` (atau dbt run/build) dari folder inventory_dbt.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
LAYERS = [  # (judul kolom, warna, fungsi penentu)
    ("Source", "#d9ead3", lambda n: n.startswith("source_")),
    ("Staging (view)", "#fff2cc", lambda n: n.startswith("stg_")),
    ("Dimensi (table)", "#cfe2f3", lambda n: n.startswith("dim_")),
    ("Fakta (table)", "#f4cccc", lambda n: n.startswith("fact_")),
]


def load_graph(manifest_path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    nodes, edges = set(), []
    for uid, node in m["nodes"].items():
        if node["resource_type"] != "model":
            continue
        nodes.add(node["name"])
        for dep in node["depends_on"]["nodes"]:
            src = dep.split(".")[-1]
            nodes.add(src)
            edges.append((src, node["name"]))
    return sorted(nodes), edges


def draw(nodes: list[str], edges: list[tuple[str, str]], out: Path) -> None:
    order = {"source_products": 0, "stg_products": 0, "dim_product": 0,
             "source_warehouses": 1, "stg_warehouses": 1, "dim_warehouse": 1,
             "source_inventory_movements": 2, "stg_inventory_movements": 2,
             "dim_movement_type": 2, "dim_date": 3,
             "fact_inventory": 1, "fact_inventory_daily_snapshot": 2.6}
    pos = {}
    fig, ax = plt.subplots(figsize=(13, 5.2))
    for col, (title, color, pred) in enumerate(LAYERS):
        members = [n for n in nodes if pred(n)]
        x = col * 3.3
        ax.text(x, 4.3, title, ha="center", va="center", fontsize=12, fontweight="bold")
        for n in members:
            y = 3.4 - order.get(n, 0) * 1.05
            pos[n] = (x, y)
            ax.add_patch(FancyBboxPatch((x - 1.35, y - 0.3), 2.7, 0.6,
                                        boxstyle="round,pad=0.02,rounding_size=0.15",
                                        fc=color, ec="#555555", lw=1))
            ax.text(x, y, n, ha="center", va="center", fontsize=8.5, family="monospace")
    for a, b in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if x1 == x2:  # fact-on-fact: panah vertikal di kolom yang sama
            ax.annotate("", xy=(x2, y2 + 0.32), xytext=(x1, y1 - 0.32),
                        arrowprops=dict(arrowstyle="->", color="#c00000", lw=1.4))
            ax.text(x1 + 0.08, (y1 + y2) / 2, "fact-on-fact", fontsize=8, color="#c00000")
            continue
        ax.annotate("", xy=(x2 - 1.37, y2), xytext=(x1 + 1.37, y1),
                    arrowprops=dict(arrowstyle="->", color="#444444", lw=0.9,
                                    connectionstyle="arc3,rad=0.06"))
    ax.set_xlim(-1.6, 3 * 3.3 + 1.6)
    ax.set_ylim(-0.1, 4.7)
    ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main() -> None:
    nodes, edges = load_graph(PROJECT_DIR / "target" / "manifest.json")
    out = PROJECT_DIR / "charts" / "lineage.png"
    draw(nodes, edges, out)
    print(f"Lineage: {len(nodes)} node, {len(edges)} edge -> {out}")


if __name__ == "__main__":
    main()
