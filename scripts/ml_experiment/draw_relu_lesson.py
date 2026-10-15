"""Render a teaching diagram of ReLU inside one hidden neuron.

Inputs: invented weights (3,-1), bias 2 and two standardized input pairs.
Output: standalone PNG, preserving the earlier linear-neuron illustration.
Identity: z=2+3*x1-x2; a=max(0,z). Cases (+1,-1)->(6,6),
(-1,+1)->(-2,0). Hidden signals use arbitrary internal units, not returns.
Tier: 0, teaching illustration only; no model fitting or research data.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
    scripts/ml_experiment/draw_relu_lesson.py --output PATH.png
"""

import argparse
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402


def draw(output):
    navy, teal, gray, orange = "#19374a", "#146d76", "#536b79", "#a56838"
    fig = plt.figure(figsize=(14, 8.6), dpi=180, facecolor="white")
    page = fig.add_axes((0, 0, 1, 1))
    page.set(xlim=(0, 1), ylim=(0, 1))
    page.axis("off")

    def text(x, y, label, size=14, color=navy, weight="normal", ha="center"):
        page.text(x, y, label, fontsize=size, color=color, fontweight=weight,
                  ha=ha, va="center", fontfamily="DejaVu Sans")

    def box(x, y, width, height, fill, edge):
        page.add_patch(FancyBboxPatch((x, y), width, height,
                                     boxstyle="round,pad=0.008,rounding_size=0.014",
                                     linewidth=1.3, edgecolor=edge, facecolor=fill))

    def arrow(start, end):
        page.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=17,
                                      linewidth=1.5, color=gray))

    text(0.5, 0.947, "Adding an activation function: ReLU", 24, weight="bold")
    text(0.5, 0.887, "Keep positive weighted sums; replace negative weighted sums with zero.", 15, gray)

    box(0.047, 0.666, 0.15, 0.12, "#edf4f6", "#c8dce2")
    text(0.122, 0.744, "Inputs", 15, weight="bold")
    text(0.122, 0.698, "x1 and x2", 14, teal)
    arrow((0.209, 0.726), (0.276, 0.726))
    box(0.29, 0.638, 0.425, 0.176, "#e3f0f0", teal)
    text(0.5025, 0.789, "INSIDE ONE HIDDEN NEURON", 11, teal, "bold")
    text(0.405, 0.735, "Weighted sum", 14, weight="bold")
    text(0.405, 0.687, "z = 2 + 3x1 - x2", 13)
    arrow((0.495, 0.72), (0.541, 0.72))
    text(0.621, 0.735, "ReLU", 15, weight="bold")
    text(0.621, 0.687, "a = max(0, z)", 13)
    arrow((0.727, 0.726), (0.798, 0.726))
    box(0.812, 0.666, 0.14, 0.12, "#edf4f6", "#c8dce2")
    text(0.882, 0.744, "Hidden signal", 14, weight="bold")
    text(0.882, 0.698, "a", 18, teal)

    text(0.054, 0.568, "Same weights and bias, two input patterns", 16, weight="bold", ha="left")
    text(0.054, 0.507, "Positive case", 14, teal, "bold", "left")
    text(0.054, 0.461, "x1 = +1, x2 = -1", 13, gray, ha="left")
    text(0.054, 0.411, "Weighted sum: 2 + 3(+1) - (-1) = +6", 13, ha="left")
    text(0.054, 0.36, "ReLU passes through +6", 15, teal, "bold", "left")

    text(0.054, 0.279, "Negative case", 14, orange, "bold", "left")
    text(0.054, 0.233, "x1 = -1, x2 = +1", 13, gray, ha="left")
    text(0.054, 0.183, "Weighted sum: 2 + 3(-1) - (+1) = -2", 13, ha="left")
    text(0.054, 0.132, "ReLU outputs 0", 15, orange, "bold", "left")

    chart = fig.add_axes((0.595, 0.18, 0.35, 0.38))
    x = np.linspace(-4.5, 8.5, 261)
    chart.plot(x, np.maximum(0, x), color=teal, linewidth=2.7)
    chart.axvline(0, color="#c8dce2", linewidth=1, zorder=0)
    chart.scatter([-2, 6], [0, 6], c=[orange, teal], s=60, zorder=3)
    chart.annotate("-2 becomes 0", (-2, 0), xytext=(-3.9, 1.4), color=navy,
                   fontsize=11, arrowprops={"arrowstyle": "-", "color": gray})
    chart.annotate("+6 stays +6", (6, 6), xytext=(1.3, 7.2), color=navy,
                   fontsize=11, arrowprops={"arrowstyle": "-", "color": gray})
    chart.set(xlim=(-4.5, 8.5), ylim=(-0.6, 8.8), xticks=[-4, -2, 0, 2, 4, 6, 8], yticks=[0, 2, 4, 6, 8])
    chart.set_xlabel("Weighted sum z", color=navy, fontsize=12)
    chart.set_ylabel("Activation a", color=navy, fontsize=12)
    chart.tick_params(colors=gray, labelsize=11)
    for side in ("top", "right"):
        chart.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        chart.spines[side].set_color("#c8dce2")
    chart.set_title("The bend at zero", color=navy, fontsize=15, pad=12)

    text(0.5, 0.054, "Invented internal scores. A separate linear output can forecast positive or negative benchmark-relative returns.", 11, gray)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    draw(args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
