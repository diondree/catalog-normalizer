from pathlib import Path

from catalog_normalizer import Normalizer, NormalizerConfig

from decimal import Decimal

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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,,\n"
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,$42.95,17\n"
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
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    product = result.valid_records[0]

    assert product.price == Decimal("42.95")


def test_price_with_currency_symbol_and_thousands_separator_is_normalized(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            'Item Code,Product Desc,Retail Price,Qty\n'
            'MAG001,Magnesium Citrate,"$1,299.99",17\n'
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            'MAG001,Magnesium Citrate,"1,99",17\n'
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,42.95,-3\n"
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,42.95,0\n"
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
    assert result.summary.valid_rows == 1
    assert result.summary.rejected_rows == 0

    assert result.valid_records[0].inventory == 0


def test_malformed_inventory_is_rejected(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,42.95,twelve\n"
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,42.95,12.5\n"
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,N/A,NULL\n"
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
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,N/A,12\n"
        ),
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
    assert (
        warning.message
        == "Configured missing value was normalized to None."
    )
    assert warning.raw_value == "N/A"

    assert result.valid_records[0].price is None

def test_blank_optional_value_does_not_produce_warning(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "products.csv"

    csv_file.write_text(
        (
            "Item Code,Product Desc,Retail Price,Qty\n"
            "MAG001,Magnesium Citrate,,12\n"
        ),
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