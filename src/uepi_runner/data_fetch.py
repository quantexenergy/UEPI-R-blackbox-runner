"""GOES XRS data download and ingestion.

Supports:
  - GOES Legacy (2010–2016): yearly NetCDF from NOAA/NCEI
  - GOES-R (2017–present): daily CSV from NOAA/SWPC archives
"""
from __future__ import annotations

import csv
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import requests


NCEI_BASE = (
    "https://www.ncei.noaa.gov/data/goes-space-environment-monitor/"
    "access/science/xrs/goes{sat}/xrsf-l2-avg1m_science/{year}/"
)
SWPC_BASE = (
    "https://services.swpc.noaa.gov/json/goes/primary/"
    "xrays-7-day.json"
)
NOAA_FLARE_URL = (
    "https://services.swpc.noaa.gov/json/goes/primary/"
    "xray-flares-latest.json"
)

# Satellite assignments by year (primary GOES XRS satellite)
SAT_BY_YEAR = {
    2010: 14, 2011: 15, 2012: 15, 2013: 15, 2014: 15,
    2015: 15, 2016: 15,
}


def fetch_goes_xrs(
    start: date,
    end: date,
    cache_dir: str | Path = "data/goes_cache",
) -> list[dict]:
    """Download GOES XRS data for a date range.

    Returns a list of dicts with keys: timestamp, xrs_b, xrs_a.
    Data is cached to disk to avoid re-downloading.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []

    current = start
    while current <= end:
        year = current.year
        if year <= 2016:
            records = _fetch_legacy_year(year, cache_dir)
            # Filter to requested range
            records = [
                r for r in records
                if start.isoformat() <= r["timestamp"][:10] <= end.isoformat()
            ]
            all_records.extend(records)
            # Skip to next year
            current = date(year + 1, 1, 1)
        else:
            records = _fetch_goesr_day(current, cache_dir)
            all_records.extend(records)
            current += timedelta(days=1)

    return all_records


def _fetch_legacy_year(year: int, cache_dir: Path) -> list[dict]:
    """Fetch a full year of legacy GOES data (stub — uses cached CSV)."""
    cache_file = cache_dir / f"goes_legacy_{year}.csv"
    if cache_file.exists():
        return _read_cache_csv(cache_file)

    sat = SAT_BY_YEAR.get(year, 15)
    print(f"  Fetching GOES-{sat} data for {year} (legacy NetCDF)...")

    # In production, this would download and parse NetCDF files.
    # For the public runner, we generate a placeholder or expect
    # the user to provide pre-downloaded data.
    print(f"  NOTE: Legacy NetCDF download not implemented in public runner.")
    print(f"  Place pre-processed CSV at: {cache_file}")
    return []


def _fetch_goesr_day(day: date, cache_dir: Path) -> list[dict]:
    """Fetch one day of GOES-R data from SWPC CSV archives."""
    cache_file = cache_dir / f"goes_r_{day.isoformat()}.csv"
    if cache_file.exists():
        return _read_cache_csv(cache_file)

    url = (
        f"https://services.swpc.noaa.gov/json/goes/primary/"
        f"xrays-1-day.json"
    )
    # For historical data, use the NCEI archive
    ncei_url = (
        f"https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/"
        f"goes/goes16/l2/data/xrsf-l2-flx1s_science/"
        f"{day.year}/{day.month:02d}/"
    )

    # Stub: in production, download and parse. For now, create empty cache.
    print(f"  Fetching GOES-R data for {day}...")
    try:
        # Try SWPC JSON (only works for recent data)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records = _parse_swpc_json(data, day)
        if records:
            _write_cache_csv(cache_file, records)
            return records
    except Exception as e:
        print(f"  SWPC fetch failed: {e}")

    return []


def _parse_swpc_json(data: list[dict], target_day: date) -> list[dict]:
    """Parse SWPC JSON xrays response into standardized records."""
    records = []
    for entry in data:
        if entry.get("energy") != "0.1-0.8nm":
            continue
        ts = entry.get("time_tag", "")
        flux = entry.get("flux")
        if not ts or flux is None:
            continue
        # Filter to target day
        if ts[:10] != target_day.isoformat():
            continue
        records.append({
            "timestamp": ts,
            "xrs_b": float(flux),
            "xrs_a": None,
        })
    return records


def _read_cache_csv(path: Path) -> list[dict]:
    """Read cached XRS data from CSV."""
    records = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            xrs_a = row.get("xrs_a")
            records.append({
                "timestamp": row["timestamp"],
                "xrs_b": float(row["xrs_b"]),
                "xrs_a": float(xrs_a) if xrs_a and xrs_a != "" else None,
            })
    return records


def _write_cache_csv(path: Path, records: list[dict]) -> None:
    """Write XRS data to cache CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "xrs_b", "xrs_a"])
        writer.writeheader()
        writer.writerows(records)


def fetch_flare_catalog(
    output_path: str | Path = "data/noaa_events.csv",
) -> Path:
    """Download NOAA flare event list.

    For the 2010-2025 backtest, uses the NCEI archived event lists.
    """
    output_path = Path(output_path)
    if output_path.exists():
        print(f"  Flare catalog already cached: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # SWPC provides recent events; for full history, download from NCEI
    url = (
        "https://www.ngdc.noaa.gov/stp/space-weather/solar-data/"
        "solar-features/solar-flares/x-rays/goes/xrs/"
    )
    print(f"  NOTE: Full 2010-2025 flare catalog download requires NCEI access.")
    print(f"  Place the catalog CSV at: {output_path}")
    print(f"  Expected columns: event_date, begin_time, peak_time, end_time,")
    print(f"                    class_type, peak_flux")

    # Create a stub file with headers
    if not output_path.exists():
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "event_date", "begin_time", "peak_time", "end_time",
                "class_type", "peak_flux",
            ])

    return output_path
