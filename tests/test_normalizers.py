from catalog_normalizer.normalizers import normalize_price, normalize_missing_value


def test_normalize_price_removes_currency_symbol() -> None:
    assert normalize_price("$42.95") == "42.95"


def test_normalize_price_preserves_plain_decimal() -> None:
    assert normalize_price("42.95") == "42.95"


def test_normalize_price_returns_none_for_blank_value() -> None:
    assert normalize_price("") is None

def test_normalize_price_removes_thousands_separator() -> None:
    assert normalize_price("$1,299.99") == "1299.99"

def test_normalize_price_does_not_guess_ambiguous_format() -> None:
    assert normalize_price("1,99") == "1,99"

def test_normalize_price_supports_multiple_thousands_groups() -> None:
    assert normalize_price("$12,999,999.99") == "12999999.99"

def test_normalize_missing_value_respects_configured_markers() -> None:
    assert (
        normalize_missing_value(
            "N/A",
            {"N/A", "NULL"},
        )
        is None
    )

def test_unconfigured_missing_marker_is_preserved() -> None:
    assert normalize_missing_value("N/A") == "N/A"