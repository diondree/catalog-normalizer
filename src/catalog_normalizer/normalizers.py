import re
from collections.abc import Callable, Collection

PRICE_PATTERN = re.compile(r"^\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")

INVENTORY_PATTERN = re.compile(r"^\d+(?:\.0+)?$")

NEGATIVE_INVENTORY_PATTERN = re.compile(r"^-\d+(?:\.0+)?$")


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
        raise NormalizationError(
            code="invalid_price",
            message="Invalid price value.",
        )

    if normalized.startswith("$"):
        normalized = normalized[1:]

    return normalized.replace(",", "")


def normalize_inventory(
    value: str | None,
    missing_values: Collection[str] = (),
) -> str | None:
    normalized = normalize_missing_value(
        value,
        missing_values,
    )

    if normalized is None:
        return None

    if NEGATIVE_INVENTORY_PATTERN.fullmatch(normalized):
        unsigned_value = normalized[1:]
        integer_part = unsigned_value.split(".", 1)[0]

        if int(integer_part) > 0:
            raise NormalizationError(
                code="negative_inventory",
                message="Inventory cannot be negative.",
            )

        raise NormalizationError(
            code="invalid_inventory",
            message="Invalid inventory value.",
        )

    if INVENTORY_PATTERN.fullmatch(normalized) is None:
        raise NormalizationError(
            code="invalid_inventory",
            message="Invalid inventory value.",
        )

    integer_part = normalized.split(".", 1)[0]

    return str(int(integer_part))


FieldNormalizer = Callable[
    [str | None, Collection[str]],
    str | None,
]


FIELD_NORMALIZERS = {
    "price": normalize_price,
    "inventory": normalize_inventory,
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


class NormalizationError(ValueError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
