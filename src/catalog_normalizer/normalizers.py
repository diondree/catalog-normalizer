import re
from collections.abc import Callable, Collection


PRICE_PATTERN = re.compile(
    r"^\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$"
)


def normalize_missing_value(
    value: str | None,
    missing_values: Collection[str] = (),
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if normalized == "":
        return None

    if normalized in missing_values:
        return None

    return normalized


def normalize_price(
    value: str | None,
    missing_values: Collection[str] = (),
) -> str | None:
    normalized = normalize_missing_value(
        value,
        missing_values,
    )

    if normalized is None:
        return None

    if PRICE_PATTERN.fullmatch(normalized) is None:
        return normalized

    if normalized.startswith("$"):
        normalized = normalized[1:]

    return normalized.replace(",", "")


FieldNormalizer = Callable[
    [str | None, Collection[str]],
    str | None,
]


FIELD_NORMALIZERS: dict[str, FieldNormalizer] = {
    "price": normalize_price,
}


def normalize_field_value(
    field: str,
    value: str | None,
    *,
    missing_values: Collection[str] = (),
) -> str | None:
    normalizer = FIELD_NORMALIZERS.get(
        field,
        normalize_missing_value,
    )

    return normalizer(
        value,
        missing_values,
    )