#!/usr/bin/env python3
"""Install the sealed uepi_core wheel from the private GitHub release.

Requires:
  GH_TOKEN           — GitHub personal access token with repo read access
  UEPI_CORE_RELEASE  — Release tag (e.g. "v0.1.0"), defaults to "latest"

Usage:
  export GH_TOKEN=ghp_...
  export UEPI_CORE_RELEASE=v0.1.0
  python scripts/install_core.py
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import requests


PRIVATE_REPO = "quantexenergy/uepi-core-private"
CHECKSUMS_FILE = Path(__file__).resolve().parent.parent / "CHECKSUMS.json"


def main() -> int:
    token = os.environ.get("GH_TOKEN", "")
    release_tag = os.environ.get("UEPI_CORE_RELEASE", "latest")

    if not token:
        print("ERROR: GH_TOKEN environment variable not set.")
        print()
        print("To install the verified UEPI-R core, you need a GitHub personal")
        print("access token with read access to the private core repository.")
        print()
        print("  export GH_TOKEN=ghp_your_token_here")
        print("  export UEPI_CORE_RELEASE=v0.1.0  # optional, defaults to latest")
        print("  python scripts/install_core.py")
        print()
        print("Without the token, the runner will use the DEMO detector")
        print("(intentionally produces worse metrics).")
        return 1

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }

    # Get release info
    if release_tag == "latest":
        url = f"https://api.github.com/repos/{PRIVATE_REPO}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{PRIVATE_REPO}/releases/tags/{release_tag}"

    print(f"Fetching release info: {release_tag}")
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 404:
        print(f"ERROR: Release '{release_tag}' not found. Check GH_TOKEN permissions.")
        return 1
    resp.raise_for_status()
    release = resp.json()

    actual_tag = release["tag_name"]
    print(f"Release: {actual_tag} ({release['name']})")

    # Find the right wheel for this platform
    wheel_asset = _find_wheel_asset(release["assets"])
    if wheel_asset is None:
        print(f"ERROR: No compatible wheel found for this platform.")
        print(f"  Platform: {platform.system()} {platform.machine()}")
        print(f"  Python:   {sys.version}")
        print(f"  Available assets:")
        for a in release["assets"]:
            print(f"    - {a['name']}")
        return 1

    print(f"Downloading: {wheel_asset['name']}")

    # Download wheel
    download_url = wheel_asset["url"]
    resp = requests.get(
        download_url,
        headers={**headers, "Accept": "application/octet-stream"},
        timeout=120,
    )
    resp.raise_for_status()

    with tempfile.TemporaryDirectory() as tmpdir:
        whl_path = Path(tmpdir) / wheel_asset["name"]
        whl_path.write_bytes(resp.content)

        # Verify checksum
        actual_sha = hashlib.sha256(resp.content).hexdigest()
        print(f"SHA-256: {actual_sha}")

        if CHECKSUMS_FILE.exists():
            with open(CHECKSUMS_FILE) as f:
                checksums = json.load(f)
            expected = checksums.get(actual_tag, {}).get(wheel_asset["name"])
            if expected:
                if actual_sha != expected:
                    print(f"ERROR: Checksum mismatch!")
                    print(f"  Expected: {expected}")
                    print(f"  Got:      {actual_sha}")
                    return 1
                print("Checksum verified OK")
            else:
                print("WARNING: No checksum on file for this asset (skipping verification)")
        else:
            print("WARNING: CHECKSUMS.json not found (skipping verification)")

        # Install
        print(f"Installing wheel...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", str(whl_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: pip install failed:\n{result.stderr}")
            return 1

    # Verify installation
    try:
        import uepi_core
        print(f"\nInstalled: uepi_core {uepi_core.version()}")
        print(f"Available configs:")
        from uepi_core._configs import available_configs
        for cid in available_configs():
            print(f"  {cid}: {uepi_core.config_hash(cid)[:16]}...")
        print("\nVerified core installed successfully!")
    except ImportError as e:
        print(f"ERROR: Installation succeeded but import failed: {e}")
        return 1

    return 0


def _find_wheel_asset(assets: list[dict]) -> dict | None:
    """Find the wheel asset matching the current platform and Python version."""
    py_ver = f"cp{sys.version_info.major}{sys.version_info.minor}"
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Map platform names to wheel tags
    if system == "linux":
        plat_tags = ["manylinux", "linux"]
    elif system == "darwin":
        plat_tags = ["macosx"]
    else:
        plat_tags = [system]

    if machine in ("x86_64", "amd64"):
        arch_tags = ["x86_64", "amd64"]
    elif machine in ("arm64", "aarch64"):
        arch_tags = ["arm64", "aarch64", "universal2"]
    else:
        arch_tags = [machine]

    for asset in assets:
        name = asset["name"]
        if not name.endswith(".whl"):
            continue
        name_lower = name.lower()
        if py_ver not in name_lower:
            continue
        if any(pt in name_lower for pt in plat_tags):
            if any(at in name_lower for at in arch_tags):
                return asset

    # Fallback: any wheel with matching Python version
    for asset in assets:
        name = asset["name"]
        if name.endswith(".whl") and py_ver in name.lower():
            return asset

    return None


if __name__ == "__main__":
    sys.exit(main())
