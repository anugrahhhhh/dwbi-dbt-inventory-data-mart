"""
draw_diagrams.py
Menggambar lineage graph (DAG) proyek dbt dari target/manifest.json.
Jalankan setelah `dbt docs generate` (atau dbt run/build).

    python scripts/draw_diagrams.py                                   # proyek inventory_dbt
    python scripts/draw_diagrams.py --project ../classicmodels_dbt    # proyek lain
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
LAYERS = [("Source", "#d9ead3"), ("Staging (view)", "#fff2cc"),
          ("Dimensi (table)", "#cfe2f3"), ("Fakta (table)", "#f4cccc")]
# urutan vertikal khusus proyek inventory agar garis tidak bersilangan
INVENTORY_ORDER = {"source_products": 0, "stg_products": 0, "dim_product": 0,
                   "source_warehouses": 1, "stg_warehouses": 1, "dim_warehouse": 1,
                   "source_inventory_movements": 2, "stg_inventory_movements": 2,
                   "dim_movement_type": 2, "dim_date": 3,
                   "fact_inventory": 1, "fact_inventory_daily_snapshot": 2.6}


def layer_of(name: str, is_source: bool) -> int:
    if is_source:
        return 0
    if name.startswith("stg_"):
        return 1
    if name.startswith("dim_"):
        return 2
    return 3


def load_graph(manifest_path: Path) -> tuple[dict[str, int], list[tuple[str, str]]]:
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    layer, edges = {}, []
    for node in m["nodes"].values():
        if node["resource_type"] != "model":
            continue
        layer[node["name"]] = layer_of(node["name"], False)
        for dep in node["depends_on"]["nodes"]:
            name = dep.split(".")[-1]
            layer.setdefault(name, layer_of(name, dep.startswith("source.")))
            edges.append((name, node["name"]))
    return layer, edges


def draw(layer: dict[str, int], edges: list[tuple[str, str]], out: Path) -> None:
    pos = {}
    rows = max(sum(1 for v in layer.values() if v == i) for i in range(4))
    height = max(4.0, rows * 1.05 + 1)
    fig, ax = plt.subplots(figsize=(13, max(5.2, height * 1.1)))
    fixed = set(layer) == set(INVENTORY_ORDER)
    for col, (title, color) in enumerate(LAYERS):
        names = sorted(n for n, lv in layer.items() if lv == col)
        kids = {n: [b for a, b in edges if a == n and b in names] for n in names}
        members = []
        for n in names:  # model turunan (fact-on-fact) diletakkan tepat di bawah induknya
            if not any(n in v for v in kids.values()):
                members += [n] + kids[n]
        x = col * 3.3
        ax.text(x, height - 0.3, title, ha="center", va="center", fontsize=12, fontweight="bold")
        for i, n in enumerate(members):
            y = height - 1.1 - (INVENTORY_ORDER[n] if fixed else i) * 1.05
            pos[n] = (x, y)
            ax.add_patch(FancyBboxPatch((x - 1.35, y - 0.3), 2.7, 0.6,
                                        boxstyle="round,pad=0.02,rounding_size=0.15",
                                        fc=color, ec="#555555", lw=1))
            ax.text(x, y, n, ha="center", va="center", fontsize=8.5, family="monospace")
    for a, b in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if x1 == x2:  # fact-on-fact atau dim-on-dim: panah vertikal di kolom yang sama
            ax.annotate("", xy=(x2, y2 + (0.32 if y2 < y1 else -0.32)),
                        xytext=(x1, y1 - (0.32 if y2 < y1 else -0.32)),
                        arrowprops=dict(arrowstyle="->", color="#c00000", lw=1.4))
            ax.text(x1 - 0.08, (y1 + y2) / 2, "fact-on-fact", fontsize=8, color="#c00000", ha="right")
            continue
        ax.annotate("", xy=(x2 - 1.37, y2), xytext=(x1 + 1.37, y1),
                    arrowprops=dict(arrowstyle="->", color="#444444", lw=0.9,
                                    connectionstyle="arc3,rad=0.06"))
    ax.set_xlim(-1.6, 3 * 3.3 + 1.6)
    ax.set_ylim(-0.2, height + 0.2)
    ax.axis("off")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=PROJECT_DIR)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    layer, edges = load_graph(args.project / "target" / "manifest.json")
    out = args.out or args.project / "charts" / "lineage.png"
    draw(layer, edges, out)
    print(f"Lineage: {len(layer)} node, {len(edges)} edge -> {out}")


if __name__ == "__main__":
    main()
