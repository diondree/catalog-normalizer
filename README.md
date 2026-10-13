# catalog-normalizer

A lightweight Python library for transforming messy product CSV files into predictable, validated product records.

`catalog-normalizer` provides deterministic data normalization, explicit column mapping, structured validation errors, and fault-tolerant CSV processing.

The library is designed to be useful independently while serving as the normalization foundation for a larger Product & Inventory Sync platform.

> **Status:** v0.1.0 release candidate. Core functionality is implemented and undergoing final release validation.

## Why?

Product data often arrives in inconsistent formats.

One system might export:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,42.99,17
```

Another system might use:

```csv
SKU,Name,Price,Inventory
MAG001,Magnesium Citrate,42.99,17
```

Beyond inconsistent column names, real-world product data frequently contains:

- missing or incomplete values
- inconsistent monetary formatting
- invalid inventory quantities
- unexpected whitespace
- ambiguous numeric representations
- malformed individual records
- source-specific missing-value markers

Applications importing this data need a predictable way to transform it without silently introducing incorrect information.

`catalog-normalizer` allows callers to explicitly map external columns into a canonical product schema, normalize supported values, validate individual rows, and collect structured errors.

**A malformed product should not cause an entire catalog import to fail.**

The library follows a simple principle:

> Normalize what we understand. Reject what we don't. Never silently invent meaning.

---

## Features

### Data Processing

- CSV processing with incremental source reading
- Explicit source-to-canonical column mappings
- Canonical product validation using Pydantic
- Required, non-blank product SKU and name
- Whitespace normalization
- Blank optional values normalized to `None`
- Configurable missing-value markers
- Conservative US-style price normalization
- Whole-number inventory normalization

### Validation and Reliability

- Fault-tolerant row processing
- Valid records preserved when other rows fail
- Structured row-level validation errors
- Stable machine-readable error codes
- Explicit rejection of ambiguous monetary formats
- Non-negative inventory validation
- Warnings for configured missing-value normalization
- Original source values preserved in errors and warnings

### Reporting

- Total rows processed
- Valid and rejected row counts
- Number of rows containing warnings
- Detected source columns
- Unused source columns
- Multiple errors or warnings supported per row

### Engineering

- Python 3.13+
- Pydantic 2
- Type checking with Pyright
- Formatting and linting with Ruff
- Automated tests with pytest
- Minimum 90% test coverage enforced in CI
- GitHub Actions quality checks
- Wheel and source-distribution builds
- Distribution metadata validation
- Clean-environment package installation and smoke testing

---

## Installation

### Requirements

- Python 3.13 or newer

### Install from GitHub

Until the package is published to PyPI, it can be installed directly from the public GitHub repository:

```bash
python -m pip install "git+https://github.com/diondree/catalog-normalizer.git"
```

Once an official PyPI release is available, installation will use:

```bash
pip install catalog-normalizer
```

> The PyPI installation command is not available until the package has been published.

For developers contributing to the library, see [Development Setup](#development-setup).

---

## Quick Start

### 1. Create a CSV file

Create a file named `products.csv`:

```csv
Item Code,Product Desc,Retail Price,Qty,Brand
MAG001,Magnesium Citrate,42.99,17,NOW Foods
VIT002,Vitamin D3,38.50,8,Solgar
```

### 2. Normalize the products

Create a Python script in the same directory:

```python
from catalog_normalizer import Normalizer

normalizer = Normalizer()

result = normalizer.process(
    "products.csv",
    mappings={
        "Item Code": "sku",
        "Product Desc": "name",
        "Retail Price": "price",
        "Qty": "inventory",
        "Brand": "brand",
    },
)

# Successfully normalized products
for product in result.valid_records:
    print(
        product.sku,
        product.name,
        product.price,
        product.inventory,
    )

# Validation errors
for error in result.errors:
    print(f"Row {error.row_number}: {error.code} - {error.message}")

# Non-fatal warnings
for warning in result.warnings:
    print(f"Row {warning.row_number}: {warning.code}")

# Processing summary
assert result.summary is not None

print(f"Processed: {result.summary.rows_processed}")
print(f"Valid: {result.summary.valid_rows}")
print(f"Rejected: {result.summary.rejected_rows}")
```

### 3. Inspect the results

The products are converted into validated `ProductSchema` instances.

For the example CSV, the summary is:

```text
Processed: 2
Valid: 2
Rejected: 0
```

Each product contains canonical field names and validated values.

For example:

```python
product = result.valid_records[0]

print(product.sku)
# MAG001

print(product.name)
# Magnesium Citrate

print(product.price)
# Decimal('42.99')

print(product.inventory)
# 17
```

The `price` field uses Python's `Decimal` type rather than a floating-point number.

---

## Canonical Product Model

All successfully normalized products conform to `ProductSchema`.

The current schema contains:

| Field | Type | Required |
|---|---|---|
| `sku` | `str` | Yes |
| `name` | `str` | Yes |
| `description` | `str \| None` | No |
| `brand` | `str \| None` | No |
| `category` | `str \| None` | No |
| `price` | `Decimal \| None` | No |
| `currency` | `str \| None` | No |
| `inventory` | `int \| None` | No |
| `status` | `str \| None` | No |

### Required Fields

Both `sku` and `name` must contain non-blank strings.

Leading and trailing whitespace is removed.

For example:

```text
"  MAG001  " → "MAG001"
```

Empty or whitespace-only values are invalid for required fields.

### Optional Fields

Optional fields may contain `None`.

For example:

```python
{
    "sku": "MAG001",
    "name": "Magnesium Citrate",
    "price": None,
    "inventory": None,
}
```

This is a valid canonical product.

### Price and Inventory

Prices are represented using `Decimal`.

Inventory quantities are represented using non-negative integers.

The CSV processing pipeline applies additional field-specific formatting rules before performing canonical model validation.

These rules are documented in [Price Formatting](#price-formatting) and [Inventory Formatting](#inventory-formatting).

---

## Column Mapping

Column mappings are supplied explicitly by the caller.

For example:

```python
mappings = {
    "Item Code": "sku",
    "Product Desc": "name",
    "Retail Price": "price",
    "Qty": "inventory",
}
```

The mapping keys represent columns in the incoming CSV.

The mapping values represent fields in the canonical product schema.

This transforms data such as:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,42.99,17
```

into canonical fields:

```python
{
    "sku": "MAG001",
    "name": "Magnesium Citrate",
    "price": "42.99",
    "inventory": "17",
}
```

The mapped values are subsequently normalized and validated into their canonical types.

### Mapping Validation

Mappings are validated before product rows are processed.

The normalizer rejects:

- unsupported canonical field names
- multiple source columns mapped to the same canonical field
- mappings missing required canonical fields
- mappings referencing source columns absent from the CSV

Invalid mappings raise `ValueError`.

Explicit mappings prevent the library from making assumptions about external product data.

Automatic column detection is not currently supported.

---

## Column Reporting

Processing summaries report both detected CSV columns and columns that were not mapped.

For example, given:

```csv
Item Code,Product Desc,Retail Price,Qty,Internal Notes
MAG001,Magnesium Citrate,42.95,12,Top seller
```

With no mapping for `Internal Notes`, the summary contains:

```python
result.summary.detected_columns == (
    "Item Code",
    "Product Desc",
    "Retail Price",
    "Qty",
    "Internal Notes",
)
```

And:

```python
result.summary.unused_columns == ("Internal Notes",)
```

Unused columns do not cause the import to fail.

They are reported so callers can identify source data that was intentionally or accidentally left unmapped.

Both properties preserve the original source column order.

---

## Processing Summary

Every successfully completed import returns a `NormalizationResult` containing a `ProcessingSummary`.

The summary includes:

| Property | Description |
|---|---|
| `rows_processed` | Total number of product rows processed |
| `valid_rows` | Number of successfully validated products |
| `rejected_rows` | Number of rejected product rows |
| `warned_rows` | Number of valid rows containing at least one warning |
| `detected_columns` | Columns detected in the source CSV |
| `unused_columns` | Source columns not included in the mapping |

### Summary Guarantees

For every completed import:

```python
rows_processed == valid_rows + rejected_rows
```

And:

```python
warned_rows <= valid_rows
```

A row may produce multiple errors or warnings.

However, each row is counted only once in the corresponding summary totals.

For example:

```text
Rows processed: 5
Valid rows:     3
Rejected rows:  2
Warned rows:    1

Error objects:   2
Warning objects: 2
```

A single valid row can produce two warnings while contributing only one to `warned_rows`.

### Empty Imports

A CSV containing headers but no product rows produces a summary with:

```text
Rows processed: 0
Valid rows:     0
Rejected rows:  0
Warned rows:    0
```

Detected and unused columns are still reported.

### Complete Failures

An import where every product row is rejected still returns a `NormalizationResult`.

Its `valid_records` collection will be empty, while `errors` and `summary` describe the failed import.

A CSV without a header row is handled differently: it raises `ValueError` because the file cannot be processed using column mappings.

---

## Partial Failure

A malformed product row does not cause the entire import to fail.

For example:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,42.99,17
,Vitamin D3,38.50,8
ZINC003,Zinc,21.50,4
```

The second product is invalid because its SKU is missing.

The expected summary is:

```text
Rows processed: 3
Valid rows:     2
Rejected rows:  1
```

The two valid products remain available in:

```python
result.valid_records
```

Validation problems are available in:

```python
result.errors
```

This behavior allows applications to retain valid products while presenting actionable feedback about rejected records.

---

## Structured Errors

Validation errors are represented using `RowError`.

Each error contains:

| Property | Description |
|---|---|
| `row_number` | Row number associated with the rejected record |
| `field` | Canonical field associated with the error, when available |
| `code` | Machine-readable error identifier |
| `message` | Human-readable explanation |
| `raw_value` | Original source value associated with the error |

For example:

```python
RowError(
    row_number=3,
    field="price",
    code="invalid_price",
    message="Invalid price value.",
    raw_value="$abc",
)
```

The original source value is preserved rather than replaced with an intermediate normalized value.

### Stable Error Codes

Field-specific error codes currently include:

| Code | Meaning |
|---|---|
| `invalid_price` | Unsupported or invalid price representation |
| `invalid_inventory` | Unsupported or invalid inventory representation |
| `negative_inventory` | Inventory quantity is negative |

Other schema validation failures use the corresponding Pydantic validation error codes.

These structured errors are intended to support both developer workflows and user interfaces explaining import problems.

---

## Missing Values

Blank or whitespace-only CSV values are normalized to `None`.

For example:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,,
```

Becomes conceptually:

```python
{
    "sku": "MAG001",
    "name": "Magnesium Citrate",
    "price": None,
    "inventory": None,
}
```

Because `price` and `inventory` are optional, the product remains valid.

Required fields such as `sku` and `name` cannot be blank.

### Configurable Missing-Value Markers

External systems may represent missing values using strings such as:

```text
N/A
NULL
```

These markers can be configured explicitly:

```python
from catalog_normalizer import (
    Normalizer,
    NormalizerConfig,
)

normalizer = Normalizer(
    config=NormalizerConfig(
        missing_values={"N/A", "NULL"},
    )
)
```

Configured markers are normalized to `None`.

For example:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,N/A,NULL
```

Results in a valid product containing:

```python
{
    "price": None,
    "inventory": None,
}
```

### Matching Rules

Configured missing-value matching is currently case-sensitive.

For example:

```text
Configured marker: N/A
Incoming value:    N/A
Result:            None
```

However:

```text
Configured marker: N/A
Incoming value:    n/a
Result:            Not treated as a configured missing marker
```

Leading and trailing whitespace is ignored when matching markers.

The original source values remain available in warning records.

---

## Warnings

Warnings describe non-fatal normalization decisions made for otherwise valid rows.

Configured missing-value markers produce a warning when converted to `None`.

For example:

```python
from catalog_normalizer import (
    Normalizer,
    NormalizerConfig,
)

normalizer = Normalizer(
    config=NormalizerConfig(
        missing_values={"N/A"},
    )
)
```

Given:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,N/A,12
```

The product remains valid, but the result contains:

```python
RowWarning(
    row_number=2,
    field="price",
    code="missing_value_normalized",
    message="Configured missing value was normalized to None.",
    raw_value="N/A",
)
```

### Warning Behavior

Warnings follow these rules:

- Warnings are emitted only for successfully validated rows.
- Rejected rows do not also produce missing-value warnings.
- Ordinary blank optional values do not produce warnings.
- Unused or unmapped CSV columns do not produce warnings.
- Multiple warnings may be produced for one valid row.
- `warned_rows` counts rows containing warnings, not warning objects.
- `raw_value` preserves the original source text.
- Configured missing-value matching is case-sensitive.

For example, a single product containing three configured missing markers may produce:

```text
Valid rows:   1
Warned rows:  1

Warnings:     3
```

This distinction makes warning reporting predictable for applications consuming the library.

---

## Price Formatting

v0.1 supports a deliberately narrow set of unambiguous US-style monetary formats.

### Supported Formats

Examples include:

| Input | Normalized Value |
|---|---|
| `0` | `0` |
| `0.00` | `0.00` |
| `$0.00` | `0.00` |
| `42` | `42` |
| `42.95` | `42.95` |
| `$42.95` | `42.95` |
| `1,299` | `1299` |
| `1,299.99` | `1299.99` |
| `$1,299.99` | `1299.99` |
| `1,000,000.00` | `1000000.00` |

Leading and trailing whitespace is ignored.

Prices are ultimately validated into Python `Decimal` values.

### Unsupported Formats

Unsupported or ambiguous formats are rejected rather than interpreted automatically.

Examples include:

- `42.`
- `.95`
- `$ 42.95`
- `+42.95`
- `-42.95`
- `1,99`
- `12,34.56`
- `1e3`
- `NaN`
- `Infinity`
- `1_000.00`

Unsupported values produce the stable error code:

```text
invalid_price
```

The normalizer intentionally avoids guessing when monetary formatting is ambiguous.

### Why Strict Formatting?

Some numeric representations are technically accepted by Python's numeric types but are not appropriate for the library's supported CSV price contract.

For example:

```text
1e3
```

Could be interpreted as:

```text
1000
```

However, `catalog-normalizer` does not silently make that interpretation.

The normalization layer verifies supported textual representations before canonical type validation.

This keeps the behavior explicit and predictable.

---

## Inventory Formatting

v0.1 accepts non-negative whole-number inventory values.

### Supported Formats

Examples include:

| Input | Normalized Value |
|---|---|
| `0` | `0` |
| `12` | `12` |
| `0012` | `12` |
| `12.0` | `12` |
| `12.00` | `12` |
| `1000` | `1000` |

Whole-number decimal representations such as `12.00` are accepted because spreadsheet exports commonly represent integer quantities this way.

Leading and trailing whitespace is ignored.

Inventory values are ultimately validated into Python integers.

### Unsupported Formats

Unsupported representations are rejected with:

```text
invalid_inventory
```

Examples include:

- `-0`
- `+12`
- `12.5`
- `.5`
- `12.`
- `1e3`
- `NaN`
- `Infinity`
- `1_000`
- `twelve`

### Negative Inventory

Recognizable negative whole-number quantities are rejected separately.

For example:

```text
-12
```

Produces:

```text
negative_inventory
```

With the message:

```text
Inventory cannot be negative.
```

This distinction separates unsupported textual representations from valid numeric representations that violate inventory domain rules.

---

## Public API

The package exposes the following classes from `catalog_normalizer`:

| Class | Purpose |
|---|---|
| `Normalizer` | Processes and normalizes CSV product data |
| `NormalizerConfig` | Configures normalization behavior |
| `ProductSchema` | Defines the canonical product representation |
| `NormalizationResult` | Contains validated records, errors, warnings, and summary |
| `ProcessingSummary` | Describes the outcomes of a completed import |
| `RowError` | Represents an individual normalization or validation error |
| `RowWarning` | Represents a non-fatal normalization warning |

Example imports:

```python
from catalog_normalizer import (
    Normalizer,
    NormalizerConfig,
    NormalizationResult,
    ProcessingSummary,
    ProductSchema,
    RowError,
    RowWarning,
)
```

### Normalizer

The primary entry point is:

```python
normalizer = Normalizer()
```

CSV processing is performed through:

```python
result = normalizer.process(
    "products.csv",
    mappings={
        "Item Code": "sku",
        "Product Desc": "name",
    },
)
```

The `process()` method accepts:

- `file_path`: a string or `pathlib.Path` pointing to a CSV file
- `mappings`: an explicit mapping of source columns to canonical fields

The constructor also supports an optional `NormalizerConfig` and a custom `ProductSchema` subclass.

### NormalizationResult

A completed import returns:

```python
NormalizationResult(
    valid_records=[...],
    errors=[...],
    warnings=[...],
    summary=...,
)
```

The `summary` property is populated for successfully completed processing operations.

Invalid CSV headers, mappings, or file access failures may raise exceptions instead of producing a completed result.

### Extensibility

Consumers can supply subclasses of `ProductSchema` when additional canonical fields or validation requirements are needed.

Field-specific normalization currently follows the library's supported normalization rules.

Additional custom normalization behavior is outside the v0.1 public API.

---

## Current Scope and Limitations

`catalog-normalizer` is intentionally focused on deterministic product-data normalization and validation.

It is not intended to become a complete commerce platform.

### Current Limitations

The current implementation does not provide:

- Excel/XLSX input support
- Automatic column detection
- AI-assisted column mapping
- Product deduplication
- Retailer-specific normalization rules
- Configurable normalization pipelines
- Streaming result consumption
- Advanced inventory and location models

### Memory Behavior

CSV input is parsed incrementally rather than loading the entire source file into memory.

However, successfully normalized records are accumulated in:

```python
NormalizationResult.valid_records
```

Therefore, total memory usage still grows with the number of accepted products.

A streaming result API may be considered in a future release for larger workloads.

### Outside the Library's Scope

The following responsibilities belong to applications consuming the library:

- Database persistence
- Authentication and multi-tenancy
- Product synchronization
- Conflict resolution
- Background job processing
- External platform adapters
- Billing and customer workflows
- Web APIs

These capabilities will be developed separately within the larger Product & Inventory Sync platform.

Keeping these responsibilities separate allows `catalog-normalizer` to remain independently useful.

---

## Development Setup

This project uses Python 3.13+ and `uv`.

### Clone the Repository

```bash
git clone https://github.com/diondree/catalog-normalizer.git

cd catalog-normalizer
```

### Install Dependencies

```bash
uv sync
```

Dependencies are managed through `pyproject.toml` and `uv.lock`.

The committed lockfile ensures reproducible dependency resolution for development and CI.

### Run the Test Suite

```bash
uv run pytest -v
```

### Formatting

Format Python files:

```bash
uv run ruff format .
```

Check formatting without modifying files:

```bash
uv run ruff format --check .
```

### Linting

```bash
uv run ruff check .
```

### Type Checking

```bash
uv run pyright
```

---

## Testing

The project uses pytest for automated testing.

### Run All Tests

```bash
uv run pytest -v
```

### Stop on the First Failure

```bash
uv run pytest -x -v
```

### Run a Specific Test File

```bash
uv run pytest tests/test_normalizer.py -v
```

### Run Coverage

```bash
uv run pytest \
  --cov=catalog_normalizer \
  --cov-report=term-missing \
  --cov-fail-under=90
```

The project enforces a minimum test coverage threshold of 90%.

### Test Coverage Areas

The test suite covers:

- Explicit column mapping
- Required canonical fields
- Partial failure handling
- Price normalization and edge cases
- Inventory normalization and edge cases
- Configurable missing-value markers
- Structured validation errors
- Warning generation
- Warning count semantics
- Empty imports
- Mixed successful and rejected imports
- Fully rejected imports
- Detected and unused column reporting
- Processing summary consistency
- Large CSV processing

Large-file behavior is covered by a regression test using a synthetic 10,000-row product catalog.

The test verifies processing behavior but does not imply constant-memory result storage.

---

## Continuous Integration

Every push and pull request runs automated quality checks through GitHub Actions.

The CI pipeline contains two primary jobs.

### Quality

The Quality job verifies:

- Ruff formatting
- Ruff linting
- Pyright type checking
- pytest execution
- Minimum 90% test coverage

### Package

The Package job verifies:

- Wheel and source-distribution builds
- Distribution metadata validation
- Clean-environment wheel installation
- Smoke testing through the installed package's public API
- Execution of the documented Quick Start against the installed wheel

These checks help detect both implementation regressions and packaging problems.

### Documentation Verification

The README Quick Start is tested automatically in CI.

The verification script extracts the CSV and Python examples directly
from the README, executes them in an isolated temporary directory,
and verifies the expected processing summary.

This ensures that the documented example continues to work against
the installed package.

To run the verification locally after building and installing the
wheel into `.package-test`:

```bash
.package-test/bin/python scripts/check_readme_quickstart.py
```

### Run Checks Locally

```bash
uv run ruff format --check .

uv run ruff check .

uv run pyright

uv run pytest \
  --cov=catalog_normalizer \
  --cov-report=term-missing \
  --cov-fail-under=90

uv build

uvx twine check dist/*
```

CI installs project dependencies using the committed `uv.lock` file to maintain reproducibility.

---

## Release Status

The core v0.1.0 functionality is implemented and undergoing final release validation.

### Completed Milestones

- CSV processing
- Explicit column mapping
- Canonical product validation
- Price formatting and validation
- Inventory formatting and validation
- Configurable missing-value handling
- Structured errors and warnings
- Processing summaries
- Detected and unused column reporting
- Large-file regression testing
- Automated CI quality gates
- Wheel and source-distribution builds
- Clean-environment package installation
- Package metadata validation
- MIT licensing

### Remaining Release Preparation

- Final documentation and example verification
- Changelog preparation
- Tagged `v0.1.0` GitHub release

The project is currently classified as an alpha release.

The public API may evolve as real-world usage identifies additional requirements.

---

## Project Structure

```text
catalog-normalizer/
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── examples/
│   └── products.csv
│
├── src/
│   └── catalog_normalizer/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── normalizer.py
│       ├── normalizers.py
│       └── result.py
│
├── tests/
│   ├── test_normalizer.py
│   └── test_normalizers.py
│
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## Development Philosophy

The core library should remain:

- **Boring:** Favor understandable implementations over unnecessary complexity.
- **Deterministic:** The same inputs and configuration should produce predictable results.
- **Explicit:** Do not silently guess when data is ambiguous.
- **Testable:** Important behaviors should be protected by automated tests.
- **Trustworthy:** Preserve source information and make normalization failures visible.

Normalization should not silently invent meaning.

The goal is to transform unreliable external product data into predictable application input while exposing assumptions, corrections, and validation failures.

---

## Long-Term Direction

`catalog-normalizer` is intended to remain the deterministic normalization layer within a larger Product & Inventory Sync ecosystem.

The broader architecture is:

```text
               Source Adapters
        ┌──────────┼───────────┐
       CSV     QuickBooks    Shopify
        │           │            │
        └───────────┼────────────┘
                    ↓
           Canonical Commerce Model
                    ↓
           Validation / Sync Engine
                    ↓
          Destination Adapters
        ┌──────────┼────────────┐
      Strapi    Shopify    WooCommerce
```

The responsibilities are intentionally separated.

### catalog-normalizer

An open-source Python library responsible for:

- Field mapping
- Data normalization
- Canonical product validation
- Structured errors and warnings
- Processing results

### product-hub

A separate commercial application responsible for:

- Source and destination adapters
- Canonical data persistence
- Product and inventory synchronization
- Source-of-truth rules
- Change detection and reconciliation
- Background processing
- Authentication and multi-tenancy
- Operational visibility
- Customer-specific workflows

The two projects are designed to complement each other without coupling the public normalization library to a specific commercial application.

---

## License

`catalog-normalizer` is released under the MIT License.

See [LICENSE](LICENSE) for the full license text.