"""Run the sealed core detector on historical data and write alert CSVs."""
from __future__ import annotations

import csv
from pathlib import Path
from types import ModuleType

from uepi_runner.core_loader import load_core, is_verified_core
from uepi_runner.data_fetch import fetch_goes_xrs


def run_backtest(
    config_id: str,
    start: str = "2010-01-01",
    end: str = "2025-12-31",
    cache_dir: str = "data/goes_cache",
    output_dir: str = "outputs/alerts",
    core: ModuleType | None = None,
) -> Path:
    """Run the detector over a date range and write an alerts CSV.

    Parameters
    ----------
    config_id : str
        Frozen config identifier (e.g. "paper_v1_precision_opt").
    start, end : str
        ISO date strings for the backtest range.
    cache_dir : str
        Directory for cached GOES data.
    output_dir : str
        Directory for output alert CSVs.
    core : ModuleType, optional
        Pre-loaded core module. If None, will load automatically.

    Returns
    -------
    Path
        Path to the written alerts CSV.
    """
    if core is None:
        core = load_core()

    verified = is_verified_core(core)
    mode = "verified" if verified else "demo"
    print(f"Core: {core.version()} ({mode})")
    print(f"Config: {config_id}")
    print(f"Config hash: {core.config_hash(config_id)}")
    print(f"Range: {start} to {end}")
    print()

    from datetime import date
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    # Process year by year to manage memory
    all_alerts: list[dict] = []
    current_year = start_date.year

    while current_year <= end_date.year:
        year_start = max(start_date, date(current_year, 1, 1))
        year_end = min(end_date, date(current_year, 12, 31))

        print(f"Processing {current_year}...", end=" ", flush=True)

        records = fetch_goes_xrs(year_start, year_end, cache_dir)
        if not records:
            print(f"no data")
            current_year += 1
            continue

        xrs_b = [r["xrs_b"] for r in records]
        xrs_a = [r["xrs_a"] for r in records] if records[0].get("xrs_a") is not None else None
        timestamps = [r["timestamp"] for r in records]

        alerts = core.detect_alerts(xrs_b, xrs_a, timestamps, config_id)
        print(f"{len(records)} samples, {len(alerts)} alerts")
        all_alerts.extend(alerts)

        current_year += 1

    # Write output
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"alerts_{config_id}.csv"

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["start", "end", "tier"])
        writer.writeheader()
        writer.writerows(all_alerts)

    print(f"\nWrote {len(all_alerts)} alerts to {output_path}")
    return output_path
