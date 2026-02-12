# UEPI-R Black-Box Reproducibility Runner

Independently verify the results reported in:

> **UEPI-R: An Unsupervised Early-Warning System for M- and X-Class Solar Flares
> Using Real-Time GOES XRS Data**
> Jorge Alexander Castillo (Quantex Energy), 2026

## What This Repo Does

This repository lets anyone reproduce the paper's backtest results **without
access to the proprietary detection algorithm**. The detection core is
distributed as a pre-compiled Python wheel (`uepi-core`); this runner handles
data ingestion, evaluation, matching, and output verification.

```
┌─────────────────────────────────────────────────┐
│  GOES XRS data (public, downloaded at runtime)  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   uepi-core wheel   │  ← sealed binary, 3 functions:
            │  detect_alerts()    │     detect_alerts, version, config_hash
            │  version()          │
            │  config_hash()      │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  uepi-runner (this) │  ← open-source evaluation
            │  matching, metrics, │
            │  tables, figures    │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  Verified outputs   │  ← compared against
            │  (CSV, plots, hash) │     REPRODUCIBILITY_MANIFEST.json
            └─────────────────────┘
```

## Quick Start

### Demo Mode (no core wheel needed)

```bash
pip install -e ".[dev]"
pytest tests/ -v
python -m uepi_runner.cli --help
```

Demo mode uses a deliberately simple threshold detector. Results will **not**
match the paper — this mode exists to verify that the evaluation pipeline works.

### Verified Reproduction (requires core wheel)

```bash
# 1. Install the runner
pip install -e .

# 2. Install the sealed core (requires CORE_WHEEL_TOKEN)
export GH_TOKEN=<your-token>
python scripts/install_core.py

# 3. Verify core loaded
python -c "import uepi_core; print(uepi_core.version())"

# 4. Run full reproduction
python -m uepi_runner.cli reproduce-paper --config-id paper_v1_precision_opt
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `fetch-data` | Download GOES XRS data for a year range |
| `run-backtest` | Run the detector on historical data |
| `eval` | Compute metrics from alerts CSV + flare catalog |
| `reproduce-paper` | Full pipeline: fetch → detect → evaluate → verify |

## Matching Methods

Two alert-to-flare matching methods are implemented:

- **Greedy (1:1)**: Each alert matches at most one flare within a hazard window
  (default 24h). Prevents inflated hit rates during storm clusters.
- **Overlap**: Temporal overlap matching (12h pre-alert, 24h post-alert start).
  Multiple alerts can contribute; flare matched to longest-lead alert.

## Verification

The `reproduce-paper` command automatically verifies outputs against
`REPRODUCIBILITY_MANIFEST.json`. This file contains expected metric ranges
and config hashes for each paper configuration.

Wheel integrity is verified during installation against `CHECKSUMS.json`.

## Project Structure

```
UEPI-R-blackbox-runner/
├── src/uepi_runner/
│   ├── cli.py            # CLI entry point
│   ├── core_loader.py    # Loads sealed core or demo fallback
│   ├── demo_core.py      # Simple threshold detector (demo only)
│   ├── matching.py       # Greedy + overlap matching
│   ├── evaluate.py       # Metrics computation
│   ├── data_fetch.py     # GOES XRS data download
│   ├── backtest.py       # Backtest orchestration
│   ├── tables.py         # Table/figure generation
│   ├── reproduce.py      # Full reproduction pipeline
│   └── hashing.py        # SHA-256 utilities
├── scripts/
│   └── install_core.py   # Core wheel installer
├── tests/                # Unit tests
├── data/                 # Downloaded GOES data (gitignored)
├── outputs/              # Reproduction outputs
├── REPRODUCIBILITY_MANIFEST.json
├── CHECKSUMS.json
└── CITATION.cff
```

## GitHub Actions

- **CI Demo** (`ci_demo.yml`): Runs on every push/PR. Tests the evaluation
  pipeline with the demo core.
- **Verified Reproduction** (`verified.yml`): Manual trigger. Installs the
  sealed core wheel and runs the full reproduction pipeline.

## License

MIT. See [LICENSE](LICENSE).

## Citation

If you use this software, please cite the paper. See [CITATION.cff](CITATION.cff).
