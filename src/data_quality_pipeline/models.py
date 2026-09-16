from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ColumnRule(BaseModel):
    """Validation and normalization rules for one input column."""

    model_config = ConfigDict(extra="forbid")

    dtype: Literal["string", "integer", "float", "boolean", "datetime"] | None = None
    required: bool = False
    nullable: bool = True
    unique: bool = False
    minimum: float | None = None
    maximum: float | None = None
    allowed_values: list[str | int | float | bool] | None = None
    pattern: str | None = None
    strip: bool = True
    lowercase: bool = False
    uppercase: bool = False

    @field_validator("maximum")
    @classmethod
    def maximum_must_be_valid(cls, value: float | None, info: Any) -> float | None:
        minimum = info.data.get("minimum")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("maximum must be greater than or equal to minimum")
        return value

    @field_validator("pattern")
    @classmethod
    def pattern_must_be_bounded(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 512:
            raise ValueError("pattern must not exceed 512 characters")
        if value is not None:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(f"pattern is not a valid regular expression: {exc}") from exc
        return value

    @model_validator(mode="after")
    def case_rules_must_not_conflict(self) -> ColumnRule:
        if self.lowercase and self.uppercase:
            raise ValueError("lowercase and uppercase cannot both be enabled")
        return self


class DatasetSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: dict[str, ColumnRule] = Field(min_length=1)
    allow_extra_columns: bool = True
    drop_duplicate_rows: bool = True
    duplicate_subset: list[str] | None = None

    @model_validator(mode="after")
    def duplicate_subset_must_reference_declared_columns(self) -> DatasetSchema:
        if self.duplicate_subset is not None:
            if not self.duplicate_subset:
                raise ValueError("duplicate_subset must contain at least one column")
            unknown = sorted(set(self.duplicate_subset) - set(self.columns))
            if unknown:
                raise ValueError(
                    "duplicate_subset contains undeclared columns: " + ", ".join(unknown)
                )
        return self


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    message: str
    column: str | None = None
    row_count: int = 0
    sample_rows: list[int] = Field(default_factory=list)


class ColumnProfile(BaseModel):
    dtype: str
    non_null_count: int
    null_count: int
    null_percent: float
    distinct_count: int
    duplicate_value_count: int
    minimum: str | float | int | None = None
    maximum: str | float | int | None = None


class QualityReport(BaseModel):
    rows_received: int
    rows_output: int
    columns_received: int
    duplicate_rows_removed: int
    issues: list[ValidationIssue]
    profile: dict[str, ColumnProfile]


@dataclass(slots=True)
class PipelineResult:
    cleaned_data: Any
    report: QualityReport
    timings_ms: dict[str, float] = field(default_factory=dict)
