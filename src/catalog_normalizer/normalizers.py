import re
from collections.abc import Callable


PRICE_PATTERN = re.compile(
    r"^\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$"
)


def normalize_missing_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if normalized == "":
        return None

    return normalized


def normalize_price(value: str | None) -> str | None:
    normalized = normalize_missing_value(value)

    if normalized is None:
        return None

    # Only normalize formats we explicitly understand.
    # Unknown or ambiguous values are left untouched so
    # validation can reject them rather than guessing.
    if PRICE_PATTERN.fullmatch(normalized) is None:
        return normalized

    if normalized.startswith("$"):
        normalized = normalized[1:]

    return normalized.replace(",", "")


FieldNormalizer = Callable[[str | None], str | None]


FIELD_NORMALIZERS: dict[str, FieldNormalizer] = {
    "price": normalize_price,
}


def normalize_field_value(
    field: str,
    value: str | None,
) -> str | None:
    normalizer = FIELD_NORMALIZERS.get(
        field,
        normalize_missing_value,
    )

    return normalizer(value)