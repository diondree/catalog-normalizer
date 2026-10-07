# catalog-normalizer

A small Python library for transforming messy product CSV files into predictable, validated product records.

`catalog-normalizer` is being built as the normalization engine behind a larger Product & Inventory Sync platform, while remaining generic enough to be useful independently.

> Status: early v0.1 development

---

## Why?

Product data often arrives in inconsistent formats:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,42.99,17
```

Another system might call the same fields:

```csv
SKU,Name,Price,Inventory
MAG001,Magnesium Citrate,42.99,17
```

`catalog-normalizer` allows callers to explicitly map external columns into a canonical product schema, normalize values, validate each row, and collect errors without throwing away valid records because another row failed.

---

## Current Features

The current implementation supports:

- CSV processing
- explicit source-to-canonical column mappings
- canonical product validation with Pydantic
- required, non-blank product SKU and name
- whitespace cleanup
- blank optional values normalized to `None`
- partial failure
- processing summaries
- CSV input is parsed incrementally rather than loading the entire source file into memory
- US-style price normalization for supported monetary formats
- conservative rejection of ambiguous price formats
- row-level validation errors with stable machine-readable error codes
- non-negative integer inventory validation
- stable `negative_inventory` and `invalid_inventory` error codes 
- configurable missing-value markers such as `N/A` and `NULL`
- warnings for configured missing-value markers normalized to `None`
- processing summaries distinguish valid, warned, and rejected rows
- detected and unused CSV columns reported in processing summaries
- automated formatting, linting, type checking, tests, and coverage reporting in CI
- wheel and source-distribution build validation
- clean-environment installation and package smoke testing in CI

---

## Canonical Product Model

The current product schema contains:

| Field | Type | Required |
|---|---|---:|
| `sku` | `str` | Yes |
| `name` | `str` | Yes |
| `description` | `str \| None` | No |
| `brand` | `str \| None` | No |
| `category` | `str \| None` | No |
| `price` | `Decimal \| None` | No |
| `currency` | `str \| None` | No |
| `inventory` | `int \| None` | No |
| `status` | `str \| None` | No |

---

## Development Setup

This project uses Python 3.13+ and `uv`.

Clone the repository and install the project dependencies:

```bash
uv sync
```

Run the test suite:

```bash
uv run pytest -v
```

---

## Quick Start

Given a CSV such as:

```csv
Item Code,Product Desc,Retail Price,Qty,Brand
MAG001,Magnesium Citrate,42.99,17,NOW Foods
VIT002,Vitamin D3,38.50,8,Solgar
```

process it using explicit mappings:

```python
from catalog_normalizer import Normalizer

normalizer = Normalizer()

result = normalizer.process(
    "examples/products.csv",
    mappings={
        "Item Code": "sku",
        "Product Desc": "name",
        "Retail Price": "price",
        "Qty": "inventory",
        "Brand": "brand",
    },
)

for product in result.valid_records:
    print(product)

for error in result.errors:
    print(
        error.row_number,
        error.field,
        error.code,
        error.message,
    )

print(result.summary)
```

---

## Column Mapping

Mappings are explicitly supplied by the caller.

```python
mappings = {
    "Item Code": "sku",
    "Product Desc": "name",
    "Retail Price": "price",
    "Qty": "inventory",
}
```

The keys represent columns in the incoming CSV.

The values represent fields in the canonical product schema.

Explicit mappings keep normalization predictable and avoid making assumptions about external product data.

---

## Column Reporting

Processing summaries report both the columns detected in the source CSV
and any columns that were not mapped.

For example, given:

```csv
Item Code,Product Desc,Retail Price,Qty,Internal Notes
MAG001,Magnesium Citrate,42.95,12,Top seller
```

with no mapping for `Internal Notes`, the summary contains:

```python
result.summary.detected_columns == (
    "Item Code",
    "Product Desc",
    "Retail Price",
    "Qty",
    "Internal Notes",
)

result.summary.unused_columns == ("Internal Notes",)
```

Unused columns do not cause the import to fail. They are reported so callers
can identify source data that was intentionally or accidentally left unmapped.

---

## Partial Failure

A malformed row does not cause the entire import to fail.

For example:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,42.99,17
,Vitamin D3,38.50,8
ZINC003,Zinc,21.50,4
```

The second row is invalid because the SKU is missing.

The expected result is:

```text
Rows processed: 3
Valid rows:     2
Rejected rows:  1
```

The two valid products remain available in:

```python
result.valid_records
```

while validation problems are available in:

```python
result.errors
```

---

## Structured Errors

Validation errors contain useful information about the failed row:

```python
RowError(
    row_number=3,
    field="price",
    code="invalid_price",
    message="Invalid price value.",
    raw_value="$abc",
)
```

Errors are designed to eventually be useful to both:

- developers consuming the library
- user interfaces explaining import problems to business users

---

## Missing Values

Blank or whitespace-only CSV values are currently normalized to `None`.

For example:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,,
```

becomes conceptually:

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

---

## Warnings

Some normalization behavior preserves a valid row while still reporting
that source data was changed.

For example, if `N/A` is explicitly configured as a missing-value marker:

```python
normalizer = Normalizer(
    config=NormalizerConfig(
        missing_values={"N/A"},
    )
)
```

then:

```csv
Item Code,Product Desc,Retail Price,Qty
MAG001,Magnesium Citrate,N/A,12
```

remains a valid product, but produces:

```python
RowWarning(
    row_number=2,
    field="price",
    code="missing_value_normalized",
    message="Configured missing value was normalized to None.",
    raw_value="N/A",
)
```

Ordinary blank optional values are normalized to `None` without producing
a warning.

---

## Price Formatting

v0.1 supports a deliberately narrow set of unambiguous US-style
monetary formats.

Supported examples include:

- `0`
- `42`
- `42.95`
- `$42.95`
- `1,299`
- `1,299.99`
- `$1,299.99`
- `1,000,000.00`

Leading and trailing whitespace is ignored.

Unsupported or ambiguous formats are rejected rather than interpreted
automatically. Examples include:

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

Unsupported values produce the stable error code `invalid_price`.

The normalizer intentionally avoids guessing when monetary formatting
is ambiguous.

---

## Inventory Formatting

v0.1 accepts non-negative whole-number inventory values.

Supported examples include:

- `0`
- `12`
- `0012`
- `12.0`
- `12.00`
- `1000`

Whole-number decimal representations such as `12.00` are normalized
to integer inventory values.

Leading and trailing whitespace is ignored.

Unsupported representations are rejected with the stable error code
`invalid_inventory`. Examples include:

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

Negative inventory values are rejected separately with the stable
error code `negative_inventory`.

---

## Current Limitations

The project is intentionally small while the v0.1 API is being developed.

The current implementation does not yet provide:

- advanced inventory normalization
- Excel/XLSX support
- automatic column detection
- AI-assisted mapping
- database persistence
- web APIs
- retailer-specific rules
- product deduplication
- normalized records are currently accumulated in memory in `NormalizationResult`; a streaming result API is planned for larger workloads

These capabilities will be introduced incrementally as their behavior is defined and tested.

---

## Development Philosophy

The core library should remain:

- boring
- deterministic
- explicit
- testable
- trustworthy

Normalization should not silently guess when data is ambiguous.

The goal is to turn unreliable external product data into predictable application input while making assumptions and failures visible.

---

## Testing

Run all tests:

```bash
uv run pytest -v
```

Stop on the first failure:

```bash
uv run pytest -x -v
```

Run a specific test file:

```bash
uv run pytest tests/test_normalizer.py -v
```

Run coverage:

```bash
uv run pytest --cov=catalog_normalizer --cov-report=term-missing
```

Large CSV behavior is covered by a regression test using a synthetic
10,000-row catalog.

The current implementation reads CSV input incrementally, but accepted
records are retained in `NormalizationResult`, so memory usage still grows
with the number of accepted products.

---

## Continuous Integration

Every push and pull request runs the project quality gates through
GitHub Actions.

The CI pipeline currently verifies:

- Ruff formatting
- Ruff linting
- Pyright type checking
- pytest
- test coverage reporting with a minimum 90% coverage gate
- wheel and source-distribution builds
- clean-environment installation of the built wheel
- smoke testing through the package's public API

The same checks can be run locally:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest --cov=catalog_normalizer --cov-report=term-missing
```

CI installs dependencies from the committed `uv.lock` file so dependency
resolution remains reproducible.

---

## Planned v0.1 Work

Upcoming work includes:

1. additional inventory edge cases
2. configurable missing-value handling
3. additional price-format edge cases
4. additional warning cases
5. improved processing summaries
6. larger-file tests
7. tagged `v0.1.0` release

---

## Project Structure

```text
catalog-normalizer/
├── examples/
│   └── products.csv
├── src/
│   └── catalog_normalizer/
│       ├── __init__.py
│       ├── models.py
│       ├── normalizer.py
│       ├── normalizers.py
│       └── result.py
├── tests/
│    ├── test_normalizer.py
│    └── test_normalizers.py
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## Long-Term Direction

`catalog-normalizer` is intended to remain the deterministic normalization layer used by a larger Product & Inventory Sync SaaS.

Commercial concerns such as authentication, multi-tenancy, persistence, asynchronous jobs, external integrations, billing, and customer-specific workflows will remain outside this package.

This keeps the library reusable and its responsibilities clear.