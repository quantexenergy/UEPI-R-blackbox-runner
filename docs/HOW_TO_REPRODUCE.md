# How to Run Verified Reproduction

This guide walks through reproducing the paper's results step by step.

## Prerequisites

- Python 3.10+
- ~2 GB disk space for GOES XRS data
- Internet connection (for data download)
- For verified mode: access token for the private core wheel

## Option A: Demo Mode (No Token Needed)

Demo mode runs the full pipeline with a simple threshold detector. Results
will **not** match the paper, but this verifies the evaluation infrastructure.

```bash
# Install
git clone https://github.com/alexcastillo/UEPI-R-blackbox-runner.git
cd UEPI-R-blackbox-runner
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run demo backtest (single year)
python -m uepi_runner.cli fetch-data --start-year 2024 --end-year 2024
python -m uepi_runner.cli run-backtest --start-year 2024 --end-year 2024
python -m uepi_runner.cli eval --alerts outputs/alerts.csv --flares outputs/flares.csv
```

## Option B: Verified Reproduction

### Step 1: Install the runner

```bash
git clone https://github.com/alexcastillo/UEPI-R-blackbox-runner.git
cd UEPI-R-blackbox-runner
pip install -e .
```

### Step 2: Install the sealed core

You need a GitHub token with access to the private `uepi-core-private` repo:

```bash
export GH_TOKEN=<your-token>
python scripts/install_core.py
```

The installer will:
1. Download the latest wheel from the private repo's releases
2. Verify the SHA-256 checksum against `CHECKSUMS.json`
3. Install the wheel via pip

### Step 3: Verify the core loaded

```bash
python -c "
import uepi_core
print(f'Version: {uepi_core.version()}')
print(f'Config hash: {uepi_core.config_hash(\"paper_v1_precision_opt\")}')
"
```

### Step 4: Run full reproduction

```bash
python -m uepi_runner.cli reproduce-paper --config-id paper_v1_precision_opt
```

This will:
1. Download GOES XRS-B data for 2010-2025
2. Run the sealed detector on each year
3. Match alerts to M/X-class flares (greedy 1:1 matching)
4. Compute coverage, precision, false alert rate, lead times
5. Generate Tables I-III and Figures 1-2
6. Verify all outputs against `REPRODUCIBILITY_MANIFEST.json`
7. Print PASS/FAIL for each metric

### Step 5: Check outputs

```
outputs/
├── alerts_all_years.csv      # All detected alerts
├── matches_greedy.csv        # Alert-flare matches (greedy)
├── matches_overlap.csv       # Alert-flare matches (overlap)
├── metrics_summary.json      # Aggregate metrics
├── table_I_year_sweep.md     # Year-by-year results
├── table_II_greedy.csv       # Greedy matching table
├── table_III_overlap.csv     # Overlap matching table
├── figure_1_coverage.png     # Coverage by year
└── figure_2_lead_times.png   # Lead time distribution
```

## Interpreting Results

### Expected Metrics (paper_v1_precision_opt)

| Metric | Expected | Tolerance |
|--------|----------|-----------|
| M/X Coverage | ~64% | +/- 2% |
| X-Class Coverage | ~97% | +/- 2% |
| Precision | ~40% | +/- 3% |
| False Alerts/Day | ~0.36 | +/- 0.05 |
| Median Lead Time | ~6h | +/- 30min |

### If Metrics Don't Match

1. Check core version: `python -c "import uepi_core; print(uepi_core.version())"`
2. Check config hash matches manifest
3. Verify data integrity: check for download errors in `data/`
4. File an issue with your `outputs/metrics_summary.json`

## CI Reproduction

The "Verified Reproduction" GitHub Action automates this entire process.
It requires the `CORE_WHEEL_TOKEN` secret to be set in the repository.

To trigger manually:
1. Go to Actions > "Verified Reproduction"
2. Click "Run workflow"
3. Set `config_id` (default: `paper_v1_precision_opt`)
4. Outputs are uploaded as artifacts
