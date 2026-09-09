"""Render docs/architecture.png without Graphviz."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "docs" / "architecture.png"

fig, ax = plt.subplots(figsize=(12, 6.2))
ax.set_xlim(0, 12)
ax.set_ylim(0, 6.4)
ax.axis("off")
fig.patch.set_facecolor("white")

boxes = [
    (0.3, 4.6, 1.8, 1.2, "Sources\ncore / dialer\nWA SMS field pay"),
    (2.5, 4.6, 1.6, 1.2, "Raw\nimmutable"),
    (4.5, 4.6, 1.6, 1.2, "Staging\ntypes / land"),
    (6.5, 4.6, 1.6, 1.2, "Clean\ndedupe / IST"),
    (8.5, 4.6, 1.6, 1.2, "Golden\nentities"),
    (10.3, 4.6, 1.5, 1.2, "Account-\nmonth"),
    (4.5, 2.5, 1.6, 1.1, "Rejected\nledger"),
    (6.5, 2.5, 1.6, 1.1, "DQ tests"),
    (8.5, 2.5, 1.6, 1.1, "Metrics"),
    (10.3, 2.5, 1.5, 1.1, "CEO\ndashboard"),
    (8.5, 0.6, 3.3, 1.1, "Monitors: per-day z, dup %, partial month"),
]


def draw(x, y, w, h, text):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.15",
            facecolor="#F4F7FB", edgecolor="#1F3A5F", linewidth=1.2,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8, color="#1F3A5F")


for b in boxes:
    draw(*b)

arrows = [
    ((2.1, 5.2), (2.5, 5.2)),
    ((4.1, 5.2), (4.5, 5.2)),
    ((6.1, 5.2), (6.5, 5.2)),
    ((8.1, 5.2), (8.5, 5.2)),
    ((10.1, 5.2), (10.3, 5.2)),
    ((7.3, 4.6), (7.3, 3.6)),
    ((5.3, 4.6), (5.3, 3.6)),
    ((9.3, 4.6), (9.3, 3.6)),
    ((10.1, 3.05), (10.3, 3.05)),
    ((9.3, 2.5), (10.0, 1.7)),
]
for a, b in arrows:
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="#1F3A5F", lw=1.2))

ax.set_title("Collections analytics — production flow", loc="left", fontsize=12, color="#1F3A5F", pad=8)
fig.tight_layout()
fig.savefig(out, dpi=140)
print("wrote", out)
