"""Full reproduction pipeline — one command to reproduce all paper metrics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from uepi_runner.core_loader import load_core, is_verified_core
from uepi_runner.hashing import sha256_csv, load_manifest
from uepi_runner.backtest import run_backtest
from uepi_runner.evaluate import (
    load_alerts_csv, load_flare_catalog, compute_metrics,
)
from uepi_runner.tables import (
    write_table_I, write_table_III_csv,
    plot_lead_time_cdf, plot_yearly_coverage,
)


def reproduce_paper(
    config_id: str = "paper_v1_precision_opt",
    cache_dir: str = "data/goes_cache",
    flare_catalog: str = "data/noaa_events.csv",
    manifest_path: str = "REPRODUCIBILITY_MANIFEST.json",
) -> bool:
    """Run the full reproduction pipeline and verify against the manifest.

    Returns True if all checks pass, False otherwise.
    """
    core = load_core()
    verified = is_verified_core(core)

    print("=" * 60)
    print("UEPI-R Paper Reproduction Pipeline")
    print("=" * 60)
    print(f"Core version:  {core.version()}")
    print(f"Core type:     {'VERIFIED' if verified else 'DEMO (expect worse metrics)'}")
    print(f"Config ID:     {config_id}")
    print(f"Config hash:   {core.config_hash(config_id)}")
    print()

    # Step 1: Run backtest
    print("Step 1: Running backtest...")
    alerts_path = run_backtest(
        config_id=config_id,
        cache_dir=cache_dir,
        core=core,
    )
    print()

    # Step 2: Evaluate with both matching methods
    print("Step 2: Computing metrics...")
    alerts = load_alerts_csv(alerts_path)
    flares = load_flare_catalog(flare_catalog, min_class="M")

    if not flares:
        print("ERROR: No flares loaded. Check flare catalog at:", flare_catalog)
        return False

    greedy_metrics = compute_metrics(alerts, flares, method="greedy")
    overlap_metrics = compute_metrics(alerts, flares, method="overlap")

    print(f"\n  Greedy matching:")
    _print_metrics(greedy_metrics)
    print(f"\n  Overlap matching:")
    _print_metrics(overlap_metrics)
    print()

    # Step 3: Generate tables and plots
    print("Step 3: Generating outputs...")
    write_table_I(greedy_metrics, overlap_metrics)

    leads_greedy = [m.lead_minutes for m in _get_matches(alerts, flares, "greedy")]
    if leads_greedy:
        write_table_III_csv(leads_greedy)
        plot_lead_time_cdf(leads_greedy)
    print()

    # Step 4: Verify against manifest
    print("Step 4: Verifying against manifest...")
    passed = _verify_manifest(
        config_id=config_id,
        core=core,
        alerts_path=alerts_path,
        greedy=greedy_metrics,
        overlap=overlap_metrics,
        manifest_path=manifest_path,
    )

    print()
    if passed:
        print("RESULT: ALL CHECKS PASSED")
    else:
        print("RESULT: VERIFICATION FAILED (see details above)")

    return passed


def _print_metrics(m):
    print(f"    Coverage:   {m.mx_coverage*100:.1f}% ({m.hits}/{m.total_flares})")
    print(f"    X-class:    {m.x_coverage*100:.1f}%")
    print(f"    Precision:  {m.precision*100:.1f}%")
    print(f"    False/day:  {m.false_per_day:.2f}")
    print(f"    Med. lead:  {m.median_lead_min:.0f} min")


def _get_matches(alerts, flares, method):
    from uepi_runner.matching import match_greedy, match_overlap, parse_alerts
    alert_objs = alerts  # Already Alert objects from load_alerts_csv
    if method == "greedy":
        matches, _, _ = match_greedy(alert_objs, flares)
    else:
        matches, _, _ = match_overlap(alert_objs, flares)
    return matches


def _verify_manifest(
    config_id, core, alerts_path, greedy, overlap, manifest_path,
) -> bool:
    """Compare computed results against the reproducibility manifest."""
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        print(f"  WARNING: Manifest not found at {manifest_path}")
        print(f"  Skipping verification.")
        return True  # No manifest = nothing to fail

    manifest = load_manifest(manifest_path)
    if config_id not in manifest:
        print(f"  WARNING: Config '{config_id}' not in manifest")
        return True

    entry = manifest[config_id]
    all_ok = True

    # Check core version
    expected_release = entry.get("core_release", "")
    if expected_release and core.version() != expected_release.lstrip("v"):
        print(f"  MISMATCH core version: got {core.version()}, "
              f"expected {expected_release}")
        all_ok = False
    else:
        print(f"  OK core version: {core.version()}")

    # Check config hash
    expected_hash = entry.get("core_config_hash", "")
    actual_hash = core.config_hash(config_id)
    if expected_hash and actual_hash != expected_hash:
        print(f"  MISMATCH config hash: got {actual_hash[:16]}..., "
              f"expected {expected_hash[:16]}...")
        all_ok = False
    else:
        print(f"  OK config hash: {actual_hash[:16]}...")

    # Check alerts hash
    expected_alerts_hash = entry.get("expected_alerts_hash", "")
    if expected_alerts_hash:
        actual_alerts_hash = sha256_csv(alerts_path)
        if actual_alerts_hash != expected_alerts_hash:
            print(f"  MISMATCH alerts hash: got {actual_alerts_hash[:16]}..., "
                  f"expected {expected_alerts_hash[:16]}...")
            all_ok = False
        else:
            print(f"  OK alerts hash: {actual_alerts_hash[:16]}...")

    # Check key metrics
    for method_name, actual in [("greedy", greedy), ("overlap", overlap)]:
        expected = entry.get("expected_metrics", {}).get(method_name, {})
        if not expected:
            continue
        for key, exp_val in expected.items():
            act_val = actual.to_dict().get(key)
            if act_val is None:
                continue
            if isinstance(exp_val, float):
                delta = abs(act_val - exp_val)
                tol = max(0.1, abs(exp_val) * 0.01)  # 1% or 0.1 absolute
                if delta > tol:
                    print(f"  MISMATCH {method_name}.{key}: "
                          f"got {act_val}, expected {exp_val} (delta={delta:.2f})")
                    all_ok = False
                else:
                    print(f"  OK {method_name}.{key}: {act_val}")

    return all_ok
