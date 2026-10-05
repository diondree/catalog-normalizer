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
- required product SKU and name
- whitespace cleanup
- blank optional values normalized to `None`
- row-level validation errors
- partial failure
- processing summaries
- rows are parsed incrementally rather than reading the entire CSV into memory at once.

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
    field="sku",
    code="...",
    message="...",
    raw_value=None,
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

## Current Limitations

The project is intentionally small while the v0.1 API is being developed.

The current implementation does not yet provide:

- configurable missing-value markers such as `N/A` or `NULL`
- advanced inventory normalization
- Excel/XLSX support
- automatic column detection
- AI-assisted mapping
- database persistence
- web APIs
- retailer-specific rules
- product deduplication

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

---

## Planned v0.1 Work

Upcoming work includes:

1. price normalization
2. inventory normalization
3. configurable missing-value handling
4. warnings
5. improved processing summaries
6. unused-column reporting
7. larger-file tests
8. package build validation
9. CI quality gates
10. tagged `v0.1.0` release

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
│   └── test_normalizer.py
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