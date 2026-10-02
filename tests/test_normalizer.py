from pathlib import Path

from catalog_normalizer import Normalizer

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