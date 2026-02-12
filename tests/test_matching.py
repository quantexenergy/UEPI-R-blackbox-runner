"""Tests for alert-to-flare matching logic."""
from datetime import datetime, timezone
from uepi_runner.matching import Alert, Flare, match_greedy, match_overlap


def _utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def test_greedy_basic_match():
    alerts = [Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED")]
    flares = [Flare(time=_utc("2024-01-01T12:00:00"), cls="M1.5")]
    matches, false_alerts, missed = match_greedy(alerts, flares)
    assert len(matches) == 1
    assert len(false_alerts) == 0
    assert len(missed) == 0
    assert matches[0].lead_minutes == 120.0


def test_greedy_one_to_one():
    """Each alert matches at most one flare."""
    alerts = [Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T14:00:00"), tier="RED")]
    flares = [
        Flare(time=_utc("2024-01-01T11:00:00"), cls="M1.0"),
        Flare(time=_utc("2024-01-01T12:00:00"), cls="M2.0"),
    ]
    matches, false_alerts, missed = match_greedy(alerts, flares)
    assert len(matches) == 1  # Only first flare matched
    assert len(missed) == 1   # Second flare unmatched
    assert matches[0].flare.cls == "M1.0"


def test_greedy_false_alert():
    alerts = [Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED")]
    flares = []  # No flares
    matches, false_alerts, missed = match_greedy(alerts, flares)
    assert len(matches) == 0
    assert len(false_alerts) == 1


def test_greedy_missed_flare():
    alerts = []  # No alerts
    flares = [Flare(time=_utc("2024-01-01T12:00:00"), cls="X1.0")]
    matches, false_alerts, missed = match_greedy(alerts, flares)
    assert len(matches) == 0
    assert len(missed) == 1


def test_overlap_basic():
    alerts = [Alert(start=_utc("2024-01-01T08:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED")]
    flares = [Flare(time=_utc("2024-01-01T12:00:00"), cls="M3.0")]
    matches, false_alerts, missed = match_overlap(alerts, flares)
    assert len(matches) == 1
    assert len(missed) == 0


def test_overlap_multi_alert():
    """Multiple alerts can contribute; flare matched to longest-lead alert."""
    alerts = [
        Alert(start=_utc("2024-01-01T06:00:00"), end=_utc("2024-01-01T09:00:00"), tier="APPROACHING"),
        Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED"),
    ]
    flares = [Flare(time=_utc("2024-01-01T12:00:00"), cls="M1.0")]
    matches, false_alerts, missed = match_overlap(alerts, flares)
    assert len(matches) == 1
    # Should match to earliest alert (longest lead)
    assert matches[0].lead_minutes == 360.0  # 6h


def test_empty_inputs():
    matches, fa, missed = match_greedy([], [])
    assert matches == [] and fa == [] and missed == []
    matches, fa, missed = match_overlap([], [])
    assert matches == [] and fa == [] and missed == []
