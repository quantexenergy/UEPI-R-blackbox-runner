"""Alert-to-flare matching methods as described in the paper.

Two methods:
  1. Hazard-window matching (1:1 greedy) — conservative, each alert/flare
     can match at most once.
  2. Temporal overlap matching — counts a flare as detected if the alert
     was active at any point during a window around flare onset.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Alert:
    start: datetime
    end: datetime
    tier: str


@dataclass
class Flare:
    time: datetime
    cls: str  # e.g. "M1.2", "X3.4"
    peak_flux: float | None = None


@dataclass
class Match:
    alert: Alert
    flare: Flare
    lead_minutes: float


def parse_alerts(records: list[dict]) -> list[Alert]:
    """Parse alert dicts from the core into Alert objects."""
    alerts = []
    for r in records:
        alerts.append(Alert(
            start=datetime.fromisoformat(r["start"]),
            end=datetime.fromisoformat(r["end"]),
            tier=r["tier"],
        ))
    return alerts


# ── Hazard-window matching (1:1 greedy) ──────────────────────────────


def match_greedy(
    alerts: list[Alert],
    flares: list[Flare],
    hazard_window_h: float = 24.0,
) -> tuple[list[Match], list[Alert], list[Flare]]:
    """One-to-one greedy hazard-window matching.

    Each alert can match at most one flare (the first M1.0+ event within
    ``hazard_window_h`` hours after alert start). Each flare can be matched
    by at most one alert (greedy first-in-time assignment).

    Returns (matches, false_alerts, missed_flares).
    """
    hazard_td = timedelta(hours=hazard_window_h)

    # Sort both by time
    sorted_alerts = sorted(alerts, key=lambda a: a.start)
    sorted_flares = sorted(flares, key=lambda f: f.time)

    matched_flare_indices: set[int] = set()
    matches: list[Match] = []
    false_alerts: list[Alert] = []

    for alert in sorted_alerts:
        window_end = alert.end + hazard_td
        found = False
        for j, flare in enumerate(sorted_flares):
            if j in matched_flare_indices:
                continue
            if flare.time < alert.start:
                continue
            if flare.time > window_end:
                break
            # Match found
            lead = (flare.time - alert.start).total_seconds() / 60.0
            matches.append(Match(alert=alert, flare=flare, lead_minutes=lead))
            matched_flare_indices.add(j)
            found = True
            break
        if not found:
            false_alerts.append(alert)

    missed = [f for j, f in enumerate(sorted_flares) if j not in matched_flare_indices]

    return matches, false_alerts, missed


# ── Temporal overlap matching ─────────────────────────────────────────


def match_overlap(
    alerts: list[Alert],
    flares: list[Flare],
    pre_window_h: float = 12.0,
    post_window_h: float = 24.0,
) -> tuple[list[Match], list[Alert], list[Flare]]:
    """Temporal overlap matching.

    A flare is counted as detected if any alert was active during the
    window [flare_time - pre_window_h, flare_time + post_window_h].
    Each flare is matched to the alert with the longest lead time.

    Returns (matches, false_alerts, missed_flares).
    """
    pre_td = timedelta(hours=pre_window_h)
    post_td = timedelta(hours=post_window_h)

    sorted_alerts = sorted(alerts, key=lambda a: a.start)
    matched_alert_indices: set[int] = set()
    matches: list[Match] = []
    missed: list[Flare] = []

    for flare in flares:
        window_start = flare.time - pre_td
        window_end = flare.time + post_td
        best_match: Match | None = None

        for i, alert in enumerate(sorted_alerts):
            # Alert overlaps the window if alert.end >= window_start
            # and alert.start <= window_end
            if alert.end < window_start:
                continue
            if alert.start > window_end:
                break
            # Overlap exists — compute lead time
            lead = (flare.time - alert.start).total_seconds() / 60.0
            if lead < 0:
                lead = 0.0
            if best_match is None or lead > best_match.lead_minutes:
                best_match = Match(alert=alert, flare=flare, lead_minutes=lead)
                matched_alert_indices.add(i)

        if best_match is not None:
            matches.append(best_match)
        else:
            missed.append(flare)

    false_alerts = [
        a for i, a in enumerate(sorted_alerts) if i not in matched_alert_indices
    ]

    return matches, false_alerts, missed
