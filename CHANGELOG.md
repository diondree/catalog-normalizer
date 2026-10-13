# Changelog

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - Initial Release

### Added

- CSV product normalization with explicit column mappings.
- Canonical product validation using Pydantic.
- Required, non-blank SKU and product name validation.
- Configurable missing-value markers.
- Conservative US-style monetary normalization.
- Support for whole-number inventory representations.
- Non-negative inventory validation.
- Fault-tolerant processing that preserves valid records.
- Structured row-level errors with machine-readable error codes.
- Warnings for configured missing-value normalization.
- Processing summaries for valid, rejected, and warned rows.
- Detection and reporting of unused CSV columns.
- Incremental CSV input parsing.
- Automated testing with pytest.
- Ruff formatting and linting.
- Pyright type checking.
- GitHub Actions CI with a minimum 90% coverage requirement.
- Wheel and source-distribution builds.
- Distribution metadata validation.
- Clean-environment package smoke testing.
- Automated README Quick Start verification.
- MIT licensing.

### Known Limitations

- CSV input only.
- Column mappings must be explicitly configured.
- No automatic product deduplication.
- No custom normalization pipeline API.
- Normalized records accumulate in memory.
- Python 3.13 or newer is required.