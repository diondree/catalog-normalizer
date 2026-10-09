from decimal import Decimal
from pathlib import Path

import pytest

from catalog_normalizer import Normalizer, NormalizerConfig


def test_valid_rows_are_returned_when_another_row_is_invalid(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,42.99,17\n"
            ",Vitamin D3,38.50,8\n"
            "ZINC003,Zinc,21.50,4\n"
        ),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.rows_processed == 3
    assert result.summary.valid_rows == 2
    assert result.summary.rejected_rows == 1

    assert len(result.valid_records) == 2
    assert result.valid_records[0].sku == "MAG001"
    assert result.valid_records[1].sku == "ZINC003"

    assert len(result.errors) >= 1
    assert result.errors[0].row_number == 3


def test_blank_optional_values_are_normalized_to_none(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,,\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    product = result.valid_records[0]

    assert product.price is None
    assert product.inventory is None


def test_price_with_currency_symbol_is_normalized(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,$42.95,17\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    product = result.valid_records[0]

    assert product.price == Decimal("42.95")


def test_price_with_currency_symbol_and_thousands_separator_is_normalized(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ('Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,"$1,299.99",17\n'),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    product = result.valid_records[0]

    assert product.price == Decimal("1299.99")


def test_invalid_price_rejects_only_affected_row(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,$42.95,17\n"
            "VIT002,Vitamin D3,$abc,8\n"
        ),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.rows_processed == 2
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 1

    assert len(result.valid_records) == 1
    assert result.valid_records[0].sku == "MAG001"

    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.row_number == 3
    assert error.field == "price"
    assert error.code == "invalid_price"
    assert error.raw_value == "$abc"


def test_ambiguous_price_format_is_rejected(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ('Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,"1,99",17\n'),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 1

    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.field == "price"
    assert error.code == "invalid_price"
    assert error.raw_value == "1,99"


def test_negative_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,42.95,-3\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.rows_processed == 1
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 1

    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.row_number == 2
    assert error.field == "inventory"
    assert error.code == "negative_inventory"
    assert error.message == "Inventory cannot be negative."
    assert error.raw_value == "-3"


def test_zero_inventory_is_valid(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,42.95,0\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    assert result.valid_records[0].inventory == 0


def test_malformed_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,42.95,twelve\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.rows_processed == 1
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 1

    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.row_number == 2
    assert error.field == "inventory"
    assert error.code == "invalid_inventory"
    assert error.message == "Invalid inventory value."
    assert error.raw_value == "twelve"


def test_decimal_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,42.95,12.5\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 1

    error = result.errors[0]

    assert error.field == "inventory"
    assert error.code == "invalid_inventory"
    assert error.raw_value == "12.5"


def test_configured_missing_values_are_normalized_to_none(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,N/A,NULL\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer(
        config=NormalizerConfig(
            missing_values={"N/A", "NULL"},
        )
    )

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    product = result.valid_records[0]

    assert product.price is None
    assert product.inventory is None


def test_configured_missing_value_produces_warning(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,N/A,12\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer(
        config=NormalizerConfig(
            missing_values={"N/A"},
        )
    )

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.rows_processed == 1
    assert result.summary.valid_rows == 1
    assert result.summary.warned_rows == 1
    assert result.summary.rejected_rows == 0

    assert len(result.warnings) == 1

    warning = result.warnings[0]

    assert warning.row_number == 2
    assert warning.field == "price"
    assert warning.code == "missing_value_normalized"
    assert warning.message == "Configured missing value was normalized to None."
    assert warning.raw_value == "N/A"

    assert result.valid_records[0].price is None


def test_blank_optional_value_does_not_produce_warning(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,,12\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer(
        config=NormalizerConfig(
            missing_values={"N/A"},
        )
    )

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.warned_rows == 0

    assert result.warnings == []


def test_summary_reports_detected_and_unused_columns(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty,Internal Notes\n"
            "MAG001,Magnesium Citrate,42.95,12,Top seller\n"
        ),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.detected_columns == (
        "Item Code",
        "Product Desc",
        "Retail Price",
        "Qty",
        "Internal Notes",
    )

    assert result.summary.unused_columns == ("Internal Notes",)


def test_summary_has_no_unused_columns_when_all_columns_are_mapped(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        ("Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,42.95,12\n"),
        encoding="utf-8",
    )

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.unused_columns == ()


def test_large_csv_can_be_processed(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    row_count = 10_000

    with csv_file.open(
        mode="w",
        encoding="utf-8",
        newline="",
    ) as file:
        file.write("Item Code,Product Desc,Retail Price,Qty\n")

        for index in range(row_count):
            file.write(f"SKU{index:05d},Product {index},42.95,{index}\n")

    normalizer = Normalizer()

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.rows_processed == row_count
    assert result.summary.valid_rows == row_count
    assert result.summary.rejected_rows == 0

    assert len(result.valid_records) == row_count

    assert result.valid_records[0].sku == "SKU00000"
    assert result.valid_records[-1].sku == "SKU09999"


@pytest.mark.parametrize(
    ("raw_price", "expected_price"),
    [
        ("0", Decimal("0")),
        ("0.00", Decimal("0.00")),
        ("$0.00", Decimal("0.00")),
        ("999", Decimal("999")),
        ("999.9", Decimal("999.9")),
        ("1,000", Decimal("1000")),
        ("$1,000", Decimal("1000")),
        ("$1,000.00", Decimal("1000.00")),
        ("  $42.95  ", Decimal("42.95")),
        ("1,000,000.00", Decimal("1000000.00")),
        ("01.99", Decimal("1.99")),
    ],
)
def test_supported_price_formats_are_accepted(
    tmp_path: Path,
    raw_price: str,
    expected_price: Decimal,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (f'Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,"{raw_price}",12\n'),
        encoding="utf-8",
    )

    result = Normalizer().process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    assert result.valid_records[0].price == expected_price


@pytest.mark.parametrize(
    "raw_price",
    [
        "42.",
        ".95",
        "$ 42.95",
        "+42.95",
        "-42.95",
        "1,99",
        "12,34.56",
        "1e3",
        "NaN",
        "Infinity",
        "1_000.00",
    ],
)
def test_unsupported_price_formats_are_rejected(
    tmp_path: Path,
    raw_price: str,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (f'Item Code,Product Desc,Retail Price,Qty\nMAG001,Magnesium Citrate,"{raw_price}",12\n'),
        encoding="utf-8",
    )

    result = Normalizer().process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 1

    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.field == "price"
    assert error.code == "invalid_price"
    assert error.raw_value == raw_price


@pytest.mark.parametrize(
    ("raw_inventory", "expected_inventory"),
    [
        ("0", 0),
        ("12", 12),
        ("0012", 12),
        (" 12 ", 12),
        ("12.0", 12),
        ("12.00", 12),
        ("1000", 1000),
    ],
)
def test_supported_inventory_formats_are_accepted(
    tmp_path: Path,
    raw_inventory: str,
    expected_inventory: int,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            f'MAG001,Magnesium Citrate,42.95,"{raw_inventory}"\n'
        ),
        encoding="utf-8",
    )

    result = Normalizer().process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    assert result.valid_records[0].inventory == expected_inventory


@pytest.mark.parametrize(
    "raw_inventory",
    [
        "-0",
        "+12",
        "12.5",
        ".5",
        "12.",
        "1e3",
        "NaN",
        "Infinity",
        "1_000",
        "twelve",
    ],
)
def test_unsupported_inventory_formats_are_rejected(
    tmp_path: Path,
    raw_inventory: str,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            f'MAG001,Magnesium Citrate,42.95,"{raw_inventory}"\n'
        ),
        encoding="utf-8",
    )

    result = Normalizer().process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 1

    assert len(result.errors) == 1

    error = result.errors[0]

    assert error.field == "inventory"
    assert error.code == "invalid_inventory"
    assert error.raw_value == raw_inventory


def test_header_only_csv_produces_empty_summary(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        "Item Code,Product Desc,Retail Price,Qty,Legacy Code\n",
        encoding="utf-8",
    )

    result = Normalizer().process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.rows_processed == 0
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 0
    assert result.summary.warned_rows == 0

    assert result.summary.detected_columns == (
        "Item Code",
        "Product Desc",
        "Retail Price",
        "Qty",
        "Legacy Code",
    )

    assert result.summary.unused_columns == ("Legacy Code",)

    assert result.valid_records == []
    assert result.errors == []
    assert result.warnings == []


def test_summary_remains_consistent_with_mixed_row_outcomes(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty,Legacy Code\n"
            "MAG001,Magnesium Citrate,42.95,17,X1\n"
            "VIT002,Vitamin D3,N/A,NULL,X2\n"
            ",Zinc,21.50,4,X3\n"
            "OMEGA004,Omega 3,invalid,8,X4\n"
            "CAL005,Calcium,0,0,X5\n"
        ),
        encoding="utf-8",
    )

    normalizer = Normalizer(
        config=NormalizerConfig(
            missing_values={"N/A", "NULL"},
        )
    )

    result = normalizer.process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    summary = result.summary

    assert summary.rows_processed == 5
    assert summary.valid_rows == 3
    assert summary.rejected_rows == 2
    assert summary.warned_rows == 1

    assert len(result.valid_records) == 3
    assert len(result.errors) == 2
    assert len(result.warnings) == 2

    assert summary.rows_processed == (summary.valid_rows + summary.rejected_rows)

    assert summary.warned_rows <= summary.valid_rows

    assert summary.unused_columns == ("Legacy Code",)


def test_summary_handles_all_rejected_rows(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            ",Magnesium Citrate,42.95,17\n"
            "VIT002,Vitamin D3,invalid,8\n"
        ),
        encoding="utf-8",
    )

    result = Normalizer().process(
        csv_file,
        mappings={
            "Item Code": "sku",
            "Product Desc": "name",
            "Retail Price": "price",
            "Qty": "inventory",
        },
    )

    assert result.summary is not None

    assert result.summary.rows_processed == 2
    assert result.summary.valid_rows == 0
    assert result.summary.rejected_rows == 2
    assert result.summary.warned_rows == 0

    assert result.valid_records == []
    assert len(result.errors) == 2
    assert result.warnings == []
