# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly:

1. **Do not** open a public GitHub issue.
2. Email: jcastillo@quantex-energy.com
3. Include a description of the vulnerability and steps to reproduce.
4. You will receive a response within 72 hours.

## Scope

This repository contains only the public reproducibility runner. The core
detection algorithm (`uepi-core`) is distributed as a pre-compiled wheel and
is not part of this repository's security scope.

## Data Integrity

- All core wheel checksums are verified against `CHECKSUMS.json` during
  installation via `scripts/install_core.py`.
- Reproduction outputs are verified against `REPRODUCIBILITY_MANIFEST.json`.
- SHA-256 is used for all integrity checks.
