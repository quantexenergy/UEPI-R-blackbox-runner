"""Demo fallback detector — used when the sealed core wheel is not installed.

This implements a DELIBERATELY SIMPLE threshold detector that produces
structurally valid output but much worse metrics than the real UEPI-R
algorithm. It exists so the public repo can run end-to-end without the
private wheel.
"""
from __future__ import annotations

import hashlib
import json


_DEMO_VERSION = "0.0.0-demo"

_DEMO_CONFIGS: dict[str, dict] = {
    "paper_v1_precision_opt": {
        "threshold": 1e-5,
        "min_duration_min": 60,
        "merge_gap_min": 120,
        "warmup_min": 1440,
    },
    "paper_v1_high_sensitivity": {
        "threshold": 5e-6,
        "min_duration_min": 30,
        "merge_gap_min": 60,
        "warmup_min": 1440,
    },
}


def version() -> str:
    return _DEMO_VERSION


def config_hash(config_id: str) -> str:
    if config_id not in _DEMO_CONFIGS:
        raise ValueError(f"Unknown config_id '{config_id}'")
    canonical = json.dumps(
        _DEMO_CONFIGS[config_id], sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def detect_alerts(
    xrs_b: list[float],
    xrs_a: list[float] | None,
    timestamps: list[str],
    config_id: str,
) -> list[dict]:
    """Simple threshold detector — demo only, not the real algorithm."""
    if config_id not in _DEMO_CONFIGS:
        raise ValueError(f"Unknown config_id '{config_id}'")

    cfg = _DEMO_CONFIGS[config_id]
    threshold = cfg["threshold"]
    min_dur = cfg["min_duration_min"]
    merge_gap = cfg["merge_gap_min"]
    warmup = cfg["warmup_min"]

    n = len(xrs_b)
    if n == 0:
        return []

    alerts: list[dict] = []
    in_alert = False
    start_idx = -1
    dur = 0
    gap = 0

    for i in range(warmup, n):
        val = xrs_b[i] if xrs_b[i] is not None else 0.0
        above = val >= threshold

        if above:
            if not in_alert:
                in_alert = True
                start_idx = i
                dur = 0
            dur += 1
            gap = 0
        elif in_alert:
            gap += 1
            if gap >= merge_gap:
                end_idx = i - gap
                tier = "RED" if dur >= min_dur else "APPROACHING"
                alerts.append({
                    "start": timestamps[start_idx],
                    "end": timestamps[max(start_idx, end_idx)],
                    "tier": tier,
                })
                in_alert = False
                dur = 0
                gap = 0

    if in_alert and start_idx >= 0:
        tier = "RED" if dur >= min_dur else "APPROACHING"
        alerts.append({
            "start": timestamps[start_idx],
            "end": timestamps[n - 1],
            "tier": tier,
        })

    return alerts
