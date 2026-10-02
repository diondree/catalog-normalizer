from catalog_normalizer.normalizers import normalize_price


def test_normalize_price_removes_currency_symbol() -> None:
    assert normalize_price("$42.95") == "42.95"


def test_normalize_price_preserves_plain_decimal() -> None:
    assert normalize_price("42.95") == "42.95"


def test_normalize_price_returns_none_for_blank_value() -> None:
    assert normalize_price("") is None