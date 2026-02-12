# How to Cut a Release

This guide covers both the private core wheel and the public runner.

## 1. Build and Release the Core Wheel (Private Repo)

### Prerequisites
- Push access to `uepi-core-private`
- GitHub Actions enabled with `PYPI_TOKEN` secret (if publishing)

### Steps

```bash
# 1. Update version
# Edit src/uepi_core/_version.py
__version__ = "1.1.0"  # bump as needed

# 2. Update configs if parameters changed
# Edit src/uepi_core/_configs.py — update CONFIGS dict

# 3. Commit and tag
git add -A
git commit -m "Release v1.1.0"
git tag v1.1.0
git push origin main --tags

# 4. GitHub Actions builds wheels automatically
# Go to Actions tab → "Build Wheels" workflow
# Artifacts: wheels for linux/macos × py3.11/3.12 + SHA256SUMS

# 5. Create GitHub Release
# Attach wheel files and SHA256SUMS to the release
```

### Verify the build

```bash
pip install dist/uepi_core-1.1.0-*.whl
python -c "import uepi_core; print(uepi_core.version())"
```

### Check no source leaks

```bash
unzip -l dist/uepi_core-1.1.0-*.whl | grep -E '\.(pyx|py)$'
# Should show only __init__.py — no _engine.pyx or _configs.py
```

## 2. Update the Public Runner

### Steps

```bash
cd UEPI-R-blackbox-runner

# 1. Update CHECKSUMS.json with new wheel hashes
# Copy SHA256 values from the core release's SHA256SUMS file
# Edit CHECKSUMS.json:
{
  "uepi_core-1.1.0-cp311-cp311-manylinux_x86_64.whl": "<sha256>",
  "uepi_core-1.1.0-cp311-cp311-macosx_arm64.whl": "<sha256>"
}

# 2. Run verified reproduction locally
export GH_TOKEN=<your-token>
python scripts/install_core.py
python -m uepi_runner.cli reproduce-paper --config-id paper_v1_precision_opt

# 3. Update REPRODUCIBILITY_MANIFEST.json with actual output metrics
# (if metrics changed due to algorithm updates)

# 4. Bump runner version in pyproject.toml if needed

# 5. Commit and push
git add -A
git commit -m "Update core to v1.1.0"
git push origin main

# 6. Tag the runner release
git tag v1.1.0
git push origin --tags
```

## 3. Verify End-to-End

Run the "Verified Reproduction" GitHub Action:

1. Go to Actions tab in the public repo
2. Select "Verified Reproduction" workflow
3. Click "Run workflow"
4. Set `config_id` to `paper_v1_precision_opt`
5. Wait for completion — check that all metrics match the manifest

## Version Alignment

Keep core and runner versions aligned:

| Core Version | Runner Version | Notes |
|-------------|---------------|-------|
| 1.0.0 | 1.0.0 | Initial paper submission |
| 1.1.0 | 1.1.0 | Post-review updates |
