"""SHA-256 hashing utilities for reproducibility verification."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Compute SHA-256 of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_string(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def sha256_csv(path: str | Path) -> str:
    """Deterministic hash of a CSV: sort rows, normalize whitespace."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        rows = sorted(",".join(row).strip() for row in reader)
    return sha256_string("\n".join(rows))


def data_snapshot_hash(
    flare_catalog_path: str | Path,
    goes_file_list: list[str],
) -> str:
    """Hash the combination of flare catalog content + GOES file list."""
    h = hashlib.sha256()
    # Hash flare catalog contents
    with open(flare_catalog_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    # Hash sorted GOES file list
    for fname in sorted(goes_file_list):
        h.update(fname.encode())
    return h.hexdigest()


def load_manifest(path: str | Path = "REPRODUCIBILITY_MANIFEST.json") -> dict:
    with open(path) as f:
        return json.load(f)
