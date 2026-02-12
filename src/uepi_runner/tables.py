"""Generate publication-style tables and plots from metrics."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from uepi_runner.evaluate import Metrics


def write_table_I(
    greedy: Metrics,
    overlap: Metrics,
    high_sens: Metrics | None = None,
    output_dir: str | Path = "outputs/tables",
) -> Path:
    """Write Table I: Backtest performance summary."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "table_I.md"

    lines = [
        "# Table I: UEPI-R Backtest Performance (2010-2025)",
        "",
        "| Configuration | Matching | M/X Cov. | X Cov. | Precision | False/day | Med. Lead | Mean Lead | Hits/N |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    def _row(label, method, m: Metrics):
        return (
            f"| {label} | {method} "
            f"| {m.mx_coverage*100:.1f}% | {m.x_coverage*100:.1f}% "
            f"| {m.precision*100:.1f}% | {m.false_per_day:.2f} "
            f"| {m.median_lead_min:.0f} min | {m.mean_lead_min:.0f} min "
            f"| {m.hits}/{m.total_flares} |"
        )

    lines.append(_row("Precision-opt.", "1:1 greedy", greedy))
    lines.append(_row("Precision-opt.", "Overlap", overlap))
    if high_sens:
        lines.append(_row("High-sensitivity", "1:1 greedy", high_sens))

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {path}")
    return path


def write_table_II_csv(
    yearly_metrics: dict[int, Metrics],
    output_dir: str | Path = "outputs/tables",
) -> Path:
    """Write Table II: Year-by-year results as CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "table_II.csv"

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "m_plus_x", "alerts", "coverage_pct",
                         "false_per_day", "median_lead_min"])
        for year in sorted(yearly_metrics.keys()):
            m = yearly_metrics[year]
            writer.writerow([
                year, m.total_flares, m.total_alerts,
                round(m.mx_coverage * 100, 1),
                round(m.false_per_day, 2),
                round(m.median_lead_min, 0),
            ])

    print(f"Wrote {path}")
    return path


def write_table_III_csv(
    lead_times_min: list[float],
    output_dir: str | Path = "outputs/tables",
) -> Path:
    """Write Table III: Cumulative lead time distribution."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "table_III.csv"

    arr = np.array(lead_times_min)
    n = len(arr)
    bins_h = [1, 2, 3, 4, 6, 8, 12, 24]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["lead_hours", "cumulative_pct", "incremental_pct"])
        prev = 0.0
        for h in bins_h:
            cum = float(np.sum(arr <= h * 60) / n * 100) if n > 0 else 0.0
            writer.writerow([h, round(cum, 1), round(cum - prev, 1)])
            prev = cum

    print(f"Wrote {path}")
    return path


def plot_lead_time_cdf(
    lead_times_min: list[float],
    output_dir: str | Path = "outputs/plots",
) -> Path:
    """Generate Figure 1: Lead time CDF."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "figure_1.png"

    arr = np.sort(lead_times_min) / 60.0  # Convert to hours
    n = len(arr)
    y = np.arange(1, n + 1) / n * 100

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(arr, y, color="#1a3a5c", linewidth=2)
    ax.fill_between(arr, 0, y, alpha=0.15, color="#d4e6f1")
    ax.set_xlabel("Lead time (hours)")
    ax.set_ylabel("Cumulative fraction of detected flares (%)")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 100)
    ax.axhline(50, color="#999", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axhline(80, color="#999", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axhline(90, color="#999", linestyle="--", linewidth=0.8, alpha=0.5)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote {path}")
    return path


def plot_yearly_coverage(
    yearly_metrics: dict[int, Metrics],
    output_dir: str | Path = "outputs/plots",
) -> Path:
    """Generate Figure 2: Yearly coverage bar chart."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "figure_2.png"

    years = sorted(yearly_metrics.keys())
    events = [yearly_metrics[y].total_flares for y in years]
    coverage = [
        yearly_metrics[y].mx_coverage * 100 if yearly_metrics[y].total_flares > 0
        else float("nan")
        for y in years
    ]

    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    colors = ["#5b8db8" if y <= 2016 else "#cccccc" if y <= 2019 else "#d4756b"
              for y in years]
    ax1.bar(years, events, color=colors, width=0.7)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("M/X-class events")

    ax2 = ax1.twinx()
    valid = [(y, c) for y, c in zip(years, coverage) if not np.isnan(c)]
    if valid:
        ax2.plot([v[0] for v in valid], [v[1] for v in valid],
                 color="#1a3a5c", linewidth=2.5, marker="o", markersize=5)
    ax2.set_ylabel("Coverage (%)")
    ax2.set_ylim(0, 105)

    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote {path}")
    return path
