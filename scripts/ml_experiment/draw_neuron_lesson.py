"""Render the first neural-network lesson's illustrative neuron as a PNG.

Inputs: invented standardized inputs, weights and bias from the conversation.
Output: a standalone diagram; no data, model fitting or research results.
Identity: prediction = 2 + 3*(+1) + (-1)*(-1) = +6 percentage points.
Tier: 0, teaching illustration only.
Run: PYTHONNOUSERSITE=1 PYTHONIOENCODING=utf-8 .venv/bin/python
    scripts/ml_experiment/draw_neuron_lesson.py --output PATH.png
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402


def draw(output):
    navy, teal, gray = "#19374a", "#146d76", "#536b79"
    fig, ax = plt.subplots(figsize=(13.5, 6.4), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    fig.subplots_adjust(left=0.025, right=0.975, top=0.97, bottom=0.03)

    def text(x, y, label, size=14, color=navy, weight="normal", **kwargs):
        ax.text(x, y, label, fontsize=size, color=color, fontweight=weight,
                ha="center", va="center", fontfamily="DejaVu Sans", **kwargs)

    def box(x, y, width, height, fill, edge):
        ax.add_patch(FancyBboxPatch((x, y), width, height,
                                   boxstyle="round,pad=0.008,rounding_size=0.018",
                                   linewidth=1.4, edgecolor=edge, facecolor=fill))

    text(0.5, 0.93, "One neuron: inputs, weights and bias", 23, weight="bold")
    text(0.5, 0.855, "Illustrative return prediction - invented values, not fitted results", 12, gray)
    text(0.145, 0.755, "INPUTS", 11, gray, "bold")
    text(0.555, 0.755, "ONE LINEAR NEURON", 11, gray, "bold")
    text(0.875, 0.755, "OUTPUT", 11, gray, "bold")

    box(0.035, 0.55, 0.22, 0.15, "#edf4f6", "#c8dce2")
    text(0.145, 0.65, "Ownership input", 14, weight="bold")
    text(0.145, 0.59, "x1 = +1", 17, teal)
    box(0.035, 0.275, 0.22, 0.15, "#edf4f6", "#c8dce2")
    text(0.145, 0.375, "Company-size input", 14, weight="bold")
    text(0.145, 0.315, "x2 = -1", 17, teal)

    for start, end in [((0.267, 0.625), (0.435, 0.535)),
                       ((0.267, 0.35), (0.435, 0.44)),
                       ((0.685, 0.4875), (0.785, 0.4875))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=17,
                                     linewidth=1.6, color=gray))
    text(0.35, 0.68, "Weight: +3 pp", 12, teal, "bold")
    text(0.35, 0.627, "Contribution: +3 pp", 11, gray)
    text(0.35, 0.31, "Weight: -1 pp", 12, teal, "bold")
    text(0.35, 0.257, "Contribution: +1 pp", 11, gray)

    box(0.445, 0.3925, 0.23, 0.19, "#e3f0f0", teal)
    text(0.56, 0.525, "Add weighted inputs", 14, weight="bold")
    text(0.56, 0.465, "and bias: +2 pp", 14, teal)
    box(0.795, 0.3925, 0.16, 0.19, "#edf4f6", "#c8dce2")
    text(0.875, 0.525, "Forecast", 13, weight="bold")
    text(0.875, 0.455, "+6 pp", 24, teal, "bold")

    text(0.5, 0.15, "2 + 3 x (+1) + (-1) x (-1) = +6 percentage points", 17, weight="bold")
    text(0.5, 0.065, "Inputs are standardized. Output is stock return minus benchmark return. No activation is applied here.", 11, gray)
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
