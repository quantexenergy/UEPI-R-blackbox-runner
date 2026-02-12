"""CLI entry point for the UEPI-R blackbox runner.

Usage:
    python -m uepi_runner.cli fetch-data --start 2010-01-01 --end 2025-12-31
    python -m uepi_runner.cli run-backtest --config-id paper_v1_precision_opt
    python -m uepi_runner.cli eval --alerts outputs/alerts/alerts_*.csv --flare-catalog data/noaa_events.csv
    python -m uepi_runner.cli reproduce-paper --config-id paper_v1_precision_opt
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="uepi_runner",
        description="UEPI-R Blackbox Runner — reproducibility framework",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── fetch-data ──
    p_fetch = sub.add_parser("fetch-data", help="Download GOES XRS data")
    p_fetch.add_argument("--start", default="2010-01-01", help="Start date (ISO)")
    p_fetch.add_argument("--end", default="2025-12-31", help="End date (ISO)")
    p_fetch.add_argument("--cache-dir", default="data/goes_cache",
                         help="Cache directory")

    # ── run-backtest ──
    p_bt = sub.add_parser("run-backtest", help="Run detector on historical data")
    p_bt.add_argument("--config-id", required=True,
                      help="Frozen config ID (e.g. paper_v1_precision_opt)")
    p_bt.add_argument("--start", default="2010-01-01")
    p_bt.add_argument("--end", default="2025-12-31")
    p_bt.add_argument("--cache-dir", default="data/goes_cache")
    p_bt.add_argument("--output-dir", default="outputs/alerts")

    # ── eval ──
    p_eval = sub.add_parser("eval", help="Evaluate alerts against flare catalog")
    p_eval.add_argument("--alerts", required=True, help="Path to alerts CSV")
    p_eval.add_argument("--flare-catalog", required=True,
                        help="Path to NOAA flare catalog CSV")
    p_eval.add_argument("--method", choices=["greedy", "overlap"], default="greedy",
                        help="Matching method")
    p_eval.add_argument("--min-class", default="M",
                        help="Minimum flare class (default: M)")
    p_eval.add_argument("--output-json", default=None,
                        help="Write metrics to JSON file")

    # ── reproduce-paper ──
    p_repro = sub.add_parser("reproduce-paper",
                             help="Full reproduction pipeline with verification")
    p_repro.add_argument("--config-id", default="paper_v1_precision_opt")
    p_repro.add_argument("--cache-dir", default="data/goes_cache")
    p_repro.add_argument("--flare-catalog", default="data/noaa_events.csv")
    p_repro.add_argument("--manifest", default="REPRODUCIBILITY_MANIFEST.json")

    args = parser.parse_args(argv)

    if args.command == "fetch-data":
        return cmd_fetch_data(args)
    elif args.command == "run-backtest":
        return cmd_run_backtest(args)
    elif args.command == "eval":
        return cmd_eval(args)
    elif args.command == "reproduce-paper":
        return cmd_reproduce_paper(args)
    return 1


def cmd_fetch_data(args) -> int:
    from datetime import date
    from uepi_runner.data_fetch import fetch_goes_xrs, fetch_flare_catalog

    print(f"Fetching GOES XRS data: {args.start} to {args.end}")
    print(f"Cache directory: {args.cache_dir}")
    print()

    records = fetch_goes_xrs(
        date.fromisoformat(args.start),
        date.fromisoformat(args.end),
        args.cache_dir,
    )
    print(f"\nTotal records: {len(records)}")

    fetch_flare_catalog()
    return 0


def cmd_run_backtest(args) -> int:
    from uepi_runner.backtest import run_backtest

    run_backtest(
        config_id=args.config_id,
        start=args.start,
        end=args.end,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
    )
    return 0


def cmd_eval(args) -> int:
    from uepi_runner.evaluate import load_alerts_csv, load_flare_catalog, compute_metrics

    alerts = load_alerts_csv(args.alerts)
    flares = load_flare_catalog(args.flare_catalog, min_class=args.min_class)

    if not flares:
        print("ERROR: No flares loaded from catalog.", file=sys.stderr)
        return 1

    metrics = compute_metrics(alerts, flares, method=args.method)

    print(f"Method:       {args.method}")
    print(f"Total flares: {metrics.total_flares}")
    print(f"Total alerts: {metrics.total_alerts}")
    print(f"Hits:         {metrics.hits}")
    print(f"Coverage:     {metrics.mx_coverage*100:.1f}%")
    print(f"X-class cov:  {metrics.x_coverage*100:.1f}%")
    print(f"Precision:    {metrics.precision*100:.1f}%")
    print(f"False/day:    {metrics.false_per_day:.2f}")
    print(f"Median lead:  {metrics.median_lead_min:.0f} min")
    print(f"Mean lead:    {metrics.mean_lead_min:.0f} min")

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
            f.write("\n")
        print(f"\nWrote metrics to {args.output_json}")

    return 0


def cmd_reproduce_paper(args) -> int:
    from uepi_runner.reproduce import reproduce_paper

    passed = reproduce_paper(
        config_id=args.config_id,
        cache_dir=args.cache_dir,
        flare_catalog=args.flare_catalog,
        manifest_path=args.manifest,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
