def normalize_missing_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if normalized == "":
        return None

    return normalized