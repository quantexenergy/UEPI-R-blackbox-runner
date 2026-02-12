"""Tests for metrics computation."""
from datetime import datetime, timezone
from uepi_runner.matching import Alert, Flare
from uepi_runner.evaluate import compute_metrics


def _utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def test_perfect_detection():
    alerts = [
        Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED"),
        Alert(start=_utc("2024-01-02T10:00:00"), end=_utc("2024-01-02T13:00:00"), tier="RED"),
    ]
    flares = [
        Flare(time=_utc("2024-01-01T12:00:00"), cls="M1.0"),
        Flare(time=_utc("2024-01-02T12:00:00"), cls="M2.0"),
    ]
    m = compute_metrics(alerts, flares, method="greedy", coverage_days=2.0)
    assert m.hits == 2
    assert m.false_alerts == 0
    assert m.mx_coverage == 1.0
    assert m.precision == 1.0


def test_no_alerts():
    flares = [Flare(time=_utc("2024-01-01T12:00:00"), cls="X1.0")]
    m = compute_metrics([], flares, method="greedy", coverage_days=1.0)
    assert m.hits == 0
    assert m.missed_flares == 1
    assert m.mx_coverage == 0.0


def test_all_false():
    alerts = [
        Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED"),
    ]
    m = compute_metrics(alerts, [], method="greedy", coverage_days=1.0)
    assert m.false_alerts == 1
    assert m.false_per_day == 1.0


def test_x_class_coverage():
    alerts = [
        Alert(start=_utc("2024-01-01T10:00:00"), end=_utc("2024-01-01T13:00:00"), tier="RED"),
    ]
    flares = [
        Flare(time=_utc("2024-01-01T12:00:00"), cls="X5.0"),
        Flare(time=_utc("2024-01-02T12:00:00"), cls="M1.0"),
    ]
    m = compute_metrics(alerts, flares, method="greedy", coverage_days=2.0)
    assert m.x_coverage == 1.0  # X flare was detected
    assert m.mx_coverage == 0.5  # 1/2 total
