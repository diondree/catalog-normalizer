from collections.abc import Callable


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

    if normalized.startswith("$"):
        normalized = normalized[1:].strip()

    return normalized


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