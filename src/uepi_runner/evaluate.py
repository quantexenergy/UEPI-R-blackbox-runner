"""Compute evaluation metrics from matched alerts and flares."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import numpy as np

from uepi_runner.matching import Alert, Flare, Match, match_greedy, match_overlap


@dataclass
class Metrics:
    total_flares: int
    total_alerts: int
    hits: int
    false_alerts: int
    missed_flares: int
    coverage_days: float
    mx_coverage: float
    x_coverage: float
    precision: float
    false_per_day: float
    median_lead_min: float
    mean_lead_min: float
    p10_lead_min: float
    p90_lead_min: float

    def to_dict(self) -> dict:
        return {
            "total_flares": self.total_flares,
            "total_alerts": self.total_alerts,
            "hits": self.hits,
            "false_alerts": self.false_alerts,
            "missed_flares": self.missed_flares,
            "coverage_days": round(self.coverage_days, 1),
            "mx_coverage_pct": round(self.mx_coverage * 100, 1),
            "x_coverage_pct": round(self.x_coverage * 100, 1),
            "precision_pct": round(self.precision * 100, 1),
            "false_per_day": round(self.false_per_day, 2),
            "median_lead_min": round(self.median_lead_min, 1),
            "mean_lead_min": round(self.mean_lead_min, 1),
            "p10_lead_min": round(self.p10_lead_min, 1),
            "p90_lead_min": round(self.p90_lead_min, 1),
        }


def load_alerts_csv(path: str | Path) -> list[Alert]:
    """Load alerts from a CSV file with columns: start, end, tier."""
    alerts = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            alerts.append(Alert(
                start=datetime.fromisoformat(row["start"]),
                end=datetime.fromisoformat(row["end"]),
                tier=row["tier"],
            ))
    return alerts


def load_flare_catalog(path: str | Path, min_class: str = "M") -> list[Flare]:
    """Load NOAA flare catalog CSV.

    Expected columns: event_date, begin_time, peak_time, end_time,
    class_type, peak_flux (or similar).
    """
    min_letter = min_class[0].upper()
    class_order = {"A": 0, "B": 1, "C": 2, "M": 3, "X": 4}
    min_ord = class_order.get(min_letter, 3)

    flares = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = row.get("class_type", row.get("fl_goescls", "")).strip()
            if not cls:
                continue
            letter = cls[0].upper()
            if class_order.get(letter, -1) < min_ord:
                continue

            # Parse timestamp
            time_str = row.get("peak_time", row.get("event_date", ""))
            if not time_str:
                continue
            try:
                t = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except ValueError:
                continue

            flares.append(Flare(time=t, cls=cls))

    return flares


def compute_metrics(
    alerts: list[Alert],
    flares: list[Flare],
    method: str = "greedy",
    coverage_days: float | None = None,
) -> Metrics:
    """Compute evaluation metrics using the specified matching method."""
    if method == "greedy":
        matches, false_list, missed_list = match_greedy(alerts, flares)
    elif method == "overlap":
        matches, false_list, missed_list = match_overlap(alerts, flares)
    else:
        raise ValueError(f"Unknown matching method: {method}")

    total_flares = len(flares)
    total_alerts = len(alerts)
    hits = len(matches)
    false_alerts = len(false_list)
    missed = len(missed_list)

    # X-class coverage
    x_flares = [f for f in flares if f.cls[0].upper() == "X"]
    x_matched = {id(m.flare) for m in matches if m.flare.cls[0].upper() == "X"}
    x_total = len(x_flares)
    x_hits = len(x_matched)

    mx_coverage = hits / total_flares if total_flares > 0 else 0.0
    x_coverage = x_hits / x_total if x_total > 0 else 0.0
    precision = hits / total_alerts if total_alerts > 0 else 0.0

    if coverage_days is None:
        # Estimate from data span
        if flares:
            span = (max(f.time for f in flares) - min(f.time for f in flares))
            coverage_days = span.total_seconds() / 86400.0
        else:
            coverage_days = 0.0

    false_per_day = false_alerts / coverage_days if coverage_days > 0 else 0.0

    leads = [m.lead_minutes for m in matches]
    if leads:
        arr = np.array(leads)
        median_lead = float(np.median(arr))
        mean_lead = float(np.mean(arr))
        p10_lead = float(np.percentile(arr, 10))
        p90_lead = float(np.percentile(arr, 90))
    else:
        median_lead = mean_lead = p10_lead = p90_lead = 0.0

    return Metrics(
        total_flares=total_flares,
        total_alerts=total_alerts,
        hits=hits,
        false_alerts=false_alerts,
        missed_flares=missed,
        coverage_days=coverage_days,
        mx_coverage=mx_coverage,
        x_coverage=x_coverage,
        precision=precision,
        false_per_day=false_per_day,
        median_lead_min=median_lead,
        mean_lead_min=mean_lead,
        p10_lead_min=p10_lead,
        p90_lead_min=p90_lead,
    )
