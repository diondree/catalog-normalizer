import csv
from pathlib import Path
from typing import Mapping

from pydantic import ValidationError

from catalog_normalizer.models import ProductSchema
from catalog_normalizer.result import (
    NormalizationResult,
    ProcessingSummary,
    RowError,
)

from catalog_normalizer.normalizers import normalize_field_value

class Normalizer:
    def __init__(self, schema: type[ProductSchema] = ProductSchema):
        self.schema = schema

    def process(
        self,
        file_path: str | Path,
        *,
        mappings: Mapping[str, str],
    ) -> NormalizationResult:
        """Process a CSV file and normalize its data according to the provided mappings."""
        self._validate_mappings(mappings)

        result = NormalizationResult()

        rows_processed = 0
        rejected_rows = 0

        with Path(file_path).open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                raise ValueError("CSV file does not contain a header row.")

            self._validate_source_columns(reader.fieldnames, mappings)

            for row_number, row in enumerate(reader, start=2):
                rows_processed += 1

                raw_mapped_row = self._map_raw_row(row, mappings)
                mapped_row = self._normalize_row(raw_mapped_row)

                try:
                    product = self.schema.model_validate(mapped_row)
                except ValidationError as exc:
                  rejected_rows += 1

                  for error in exc.errors():
                      field = (
                          str(error["loc"][0])
                          if error.get("loc")
                          else None
                      )

                      code, message = self._format_validation_error(
                          field=field,
                          error_type=error["type"],
                          default_message=error["msg"],
                      )

                      result.errors.append(
                          RowError(
                              row_number=row_number,
                              field=field,
                              code=code,
                              message=message,
                              raw_value=(
                                  raw_mapped_row.get(field)
                                  if field
                                  else None
                              ),
                          )
                      )

                  continue
                result.valid_records.append(product)

        result.summary = ProcessingSummary(
            rows_processed=rows_processed,
            valid_rows=len(result.valid_records),
            warned_rows=0,
            rejected_rows=rejected_rows,
        )

        return result

    def _map_raw_row(
        self,
        row: Mapping[str, str | None],
        mappings: Mapping[str, str],
    ) -> dict[str, str | None]:
        return {
            canonical_field: row.get(source_field)
            for source_field, canonical_field in mappings.items()
        }


    def _normalize_row(
        self,
        row: Mapping[str, str | None],
    ) -> dict[str, str | None]:
        return {
            field: normalize_field_value(field, value)
            for field, value in row.items()
        }

    def _validate_mappings(
        self,
        mappings: Mapping[str, str],
    ) -> None:
        """Validate that the mappings are valid for the schema."""
        supported_fields = set(self.schema.model_fields)

        mapped_fields = list(mappings.values())

        unsupported_fields = set(mapped_fields) - supported_fields

        if unsupported_fields:
            raise ValueError(
                "Mappings contain unsupported canonical fields: "
                + ", ".join(sorted(unsupported_fields))
            )

        if len(mapped_fields) != len(set(mapped_fields)):
            raise ValueError(
                "Multiple source columns cannot map to the same "
                "canonical field."
            )

        required_fields = {
            field_name
            for field_name, field_info in self.schema.model_fields.items()
            if field_info.is_required()
        }

        missing_required_fields = required_fields - set(mapped_fields)

        if missing_required_fields:
            raise ValueError(
                "Mappings are missing required fields: "
                + ", ".join(sorted(missing_required_fields))
            )

    @staticmethod
    def _validate_source_columns(
        source_columns: list[str],
        mappings: Mapping[str, str],
    ) -> None:
        """Validate that the source CSV contains all the columns specified in the mappings."""
        missing_columns = set(mappings) - set(source_columns)

        if missing_columns:
            raise ValueError(
                "CSV is missing mapped source columns: "
                + ", ".join(sorted(missing_columns))
            )

    @staticmethod
    def _format_validation_error(
        *,
        field: str | None,
        error_type: str,
        default_message: str,
    ) -> tuple[str, str]:
        if field == "price" and error_type == "decimal_parsing":
            return (
                "invalid_price",
                "Invalid price value.",
            )

        return error_type, default_message