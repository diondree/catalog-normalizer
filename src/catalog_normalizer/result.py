from dataclasses import dataclass, field
from typing import Any

from catalog_normalizer.models import ProductSchema


@dataclass(frozen=True)
class RowError:
    row_number: int
    field: str | None
    code: str
    message: str
    raw_value: Any = None


@dataclass(frozen=True)
class RowWarning:
    row_number: int
    field: str | None
    code: str
    message: str
    raw_value: Any = None


@dataclass(frozen=True)
class ProcessingSummary:
    rows_processed: int
    valid_rows: int
    warned_rows: int
    rejected_rows: int


@dataclass
class NormalizationResult:
    valid_records: list[ProductSchema] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    warnings: list[RowWarning] = field(default_factory=list)
    summary: ProcessingSummary | None = None