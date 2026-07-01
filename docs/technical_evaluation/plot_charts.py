"""Publication-quality charts for the technical evaluation.

Renders each figure as 300-DPI PNG + PDF (vector) + SVG (vector), with generous
spacing, legends below the axes, deslined frames and high-contrast markers.
Run:  .venv/bin/python docs/technical_evaluation/plot_charts.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT = "docs/technical_evaluation/charts"
DPI = 400
USERS = [10, 50, 100, 200]

AVG = {
    "coverage":  [1916, 25562, 16358, 42707],
    "datex":     [1624, 11489, 13812, 27541],
    "fused":     [1582, 6343, 12091, 29639],
    "transform": [503, 5993, 12208, 27581],
    "geojson":   [7815, 23939, 37181, 64119],
    "TOTAL":     [1484, 10777, 13783, 31104],
}
THR = {
    "coverage":  [1.50, 0.56, 1.4, 1.0],
    "datex":     [1.60, 1.20, 1.5, 1.3],
    "fused":     [1.60, 1.30, 1.5, 1.3],
    "transform": [1.60, 1.30, 1.5, 1.3],
    "geojson":   [0.13, 0.18, 0.24, 0.29],
    "TOTAL":     [5.5, 4.0, 5.2, 4.5],
}
ERR_TOTAL = [0.0, 0.0, 0.0, 0.12]
PCTL_200 = {
    "coverage":  (42707, 75563, 77506),
    "datex":     (27541, 73996, 76311),
    "fused":     (29639, 75310, 77490),
    "transform": (27581, 67118, 73756),
    "geojson":   (64119, 79805, 84211),
}

plt.rcParams.update({
    "figure.dpi": DPI, "savefig.dpi": DPI,
    "font.family": "DejaVu Sans", "font.size": 12,
    "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlepad": 12,
    "axes.labelsize": 12.5, "axes.edgecolor": "#333", "axes.linewidth": 1.0,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "xtick.color": "#333", "ytick.color": "#333",
    "axes.grid": True, "grid.alpha": 0.35, "grid.linestyle": "--", "grid.linewidth": 0.7,
    "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 10.5,
    "lines.linewidth": 2.0, "lines.markersize": 7,
})
C = {"coverage": "#0072B2", "datex": "#E69F00", "fused": "#009E73",
     "transform": "#CC79A7", "geojson": "#D55E00", "TOTAL": "#000000"}
MK = {"coverage": "o", "datex": "s", "fused": "^", "transform": "D", "geojson": "v"}
LAB = {"coverage": "coverage", "datex": "datex", "fused": "fused",
       "transform": "transform", "geojson": "geojson", "TOTAL": "overall"}
LBLBOX = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9)


def save(fig, name):
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{OUT}/{name}.{ext}", dpi=DPI, bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)


def legend_below(ax, ncol):
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=ncol,
              handlelength=1.9, columnspacing=1.7, handletextpad=0.6)


def chart1_latency():
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    for ep in ["coverage", "datex", "fused", "transform", "geojson"]:
        ax.plot(USERS, AVG[ep], marker=MK[ep], color=C[ep], label=LAB[ep],
                mec="white", mew=0.8)
    ax.plot(USERS, AVG["TOTAL"], marker="*", color=C["TOTAL"], label=LAB["TOTAL"],
            lw=3.0, ms=15, mec="white", mew=0.8, zorder=5)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(USERS); ax.set_xticklabels(USERS)
    ax.set_xlabel("Concurrent users"); ax.set_ylabel("Average response time (ms)")
    ax.set_title("Response time vs. concurrent load")
    for u, v in zip(USERS, AVG["TOTAL"]):
        ax.annotate(f"{v/1000:.1f} s", (u, v), textcoords="offset points", xytext=(9, 6),
                    ha="left", fontsize=9.5, fontweight="bold", bbox=LBLBOX)
    legend_below(ax, 6)
    save(fig, "1_latency_vs_load")


def chart2_throughput():
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    for ep in ["coverage", "datex", "fused", "transform", "geojson"]:
        ax.plot(USERS, THR[ep], marker=MK[ep], color=C[ep], label=LAB[ep],
                mec="white", mew=0.8)
    ax.plot(USERS, THR["TOTAL"], marker="*", color=C["TOTAL"], label=LAB["TOTAL"],
            lw=3.0, ms=15, mec="white", mew=0.8, zorder=5)
    ax.axhline(4.8, color="#888", ls=":", lw=1.6)
    ax.text(11, 5.2, "capacity ceiling ~4.8 req/s", color="#555", fontsize=9.5)
    ax.set_xscale("log"); ax.set_xticks(USERS); ax.set_xticklabels(USERS)
    ax.set_xlabel("Concurrent users"); ax.set_ylabel("Throughput (requests / s)")
    ax.set_title("Throughput vs. concurrent load")
    for u, v in zip(USERS, THR["TOTAL"]):
        ax.annotate(f"{v:g}", (u, v), textcoords="offset points", xytext=(9, 6),
                    ha="left", fontsize=9.5, fontweight="bold", bbox=LBLBOX)
    legend_below(ax, 6)
    save(fig, "2_throughput_vs_load")


def chart3_percentiles():
    eps = list(PCTL_200.keys())
    avg = [PCTL_200[e][0] for e in eps]
    p95 = [PCTL_200[e][1] for e in eps]
    p99 = [PCTL_200[e][2] for e in eps]
    x = range(len(eps)); w = 0.26
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    ax.bar([i - w for i in x], avg, w, label="average", color="#0072B2", edgecolor="white", lw=0.6)
    ax.bar(list(x), p95, w, label="95th percentile", color="#E69F00", edgecolor="white", lw=0.6)
    ax.bar([i + w for i in x], p99, w, label="99th percentile", color="#D55E00", edgecolor="white", lw=0.6)
    ax.set_xticks(list(x)); ax.set_xticklabels([LAB[e] for e in eps], rotation=0, fontsize=10.5)
    ax.set_ylabel("Response time (ms)"); ax.set_yscale("log")
    ax.set_title("Latency distribution at 200 concurrent users")
    legend_below(ax, 3)
    save(fig, "3_percentiles_200users")


def chart4_errors():
    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    bars = ax.bar([str(u) for u in USERS], ERR_TOTAL,
                  color=["#009E73", "#009E73", "#009E73", "#D55E00"], width=0.6,
                  edgecolor="white", lw=0.8)
    ax.set_xlabel("Concurrent users"); ax.set_ylabel("Error rate (%)")
    ax.set_title("Failed requests vs. concurrent load"); ax.set_ylim(0, 0.17)
    for b, v in zip(bars, ERR_TOTAL):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.006, f"{v:.2f}%",
                ha="center", fontsize=11, fontweight="bold")
    save(fig, "4_error_rate_vs_load")


def chart5_health():
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    bars = ax.bar(["before fix", "after fix"], [13000, 200],
                  color=["#D55E00", "#009E73"], width=0.5, edgecolor="white", lw=0.8)
    ax.set_yscale("log"); ax.set_ylabel("Response time (ms, log scale)")
    ax.set_title("/health: cached row-counts")
    for b, v in zip(bars, [13000, 200]):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.20, f"{v/1000:g} s",
                ha="center", fontsize=11.5, fontweight="bold")
    ax.annotate("", xy=(1, 235), xytext=(0, 8200),
                arrowprops=dict(arrowstyle="->", color="black", lw=2.0))
    ax.text(0.5, 2400, "~65× faster", ha="center", fontsize=13, fontweight="bold", color="#333",
            bbox=LBLBOX)
    save(fig, "5_health_before_after")


if __name__ == "__main__":
    chart1_latency(); chart2_throughput(); chart3_percentiles()
    chart4_errors(); chart5_health()
    print("wrote 5 figures (png+pdf+svg) to", OUT)
