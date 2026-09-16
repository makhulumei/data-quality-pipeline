from __future__ import annotations

import re

import pandas as pd

from .models import DatasetSchema, ValidationIssue


def _issue(
    code: str,
    message: str,
    mask: pd.Series | None = None,
    column: str | None = None,
    severity: str = "error",
) -> ValidationIssue:
    rows = [] if mask is None else [int(index) for index in mask[mask].index[:10]]
    return ValidationIssue(
        code=code,
        severity=severity,
        message=message,
        column=column,
        row_count=0 if mask is None else int(mask.sum()),
        sample_rows=rows,
    )


def validate_dataframe(frame: pd.DataFrame, schema: DatasetSchema) -> list[ValidationIssue]:
    return validate_dataframe_with_context(frame, schema)


def validate_dataframe_with_context(
    frame: pd.DataFrame,
    schema: DatasetSchema,
    *,
    coercion_failures: dict[str, pd.Series] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    coercion_failures = coercion_failures or {}
    expected = set(schema.columns)
    actual = set(map(str, frame.columns))

    for missing in sorted(expected - actual):
        rule = schema.columns[missing]
        if rule.required:
            issues.append(
                _issue(
                    "missing_column",
                    f"Required column '{missing}' is absent.",
                    column=missing,
                )
            )

    extras = sorted(actual - expected)
    if extras and not schema.allow_extra_columns:
        issues.append(
            _issue(
                "extra_columns",
                f"Unexpected columns: {', '.join(extras)}.",
                severity="warning",
            )
        )

    for column, rule in schema.columns.items():
        if column not in frame.columns:
            continue
        series = frame[column]
        if not rule.nullable:
            mask = series.isna()
            if column in coercion_failures:
                failure_mask = coercion_failures[column].reindex(frame.index, fill_value=False)
                mask = mask & ~failure_mask
            if mask.any():
                issues.append(
                    _issue("source_null", "Source null values are not allowed.", mask, column)
                )
        if rule.unique:
            mask = series.notna() & series.duplicated(keep=False)
            if mask.any():
                issues.append(_issue("duplicate_value", "Values must be unique.", mask, column))
        if rule.minimum is not None:
            numeric = pd.to_numeric(series, errors="coerce")
            mask = numeric.notna() & (numeric < rule.minimum)
            if mask.any():
                issues.append(
                    _issue("below_minimum", f"Values must be >= {rule.minimum}.", mask, column)
                )
        if rule.maximum is not None:
            numeric = pd.to_numeric(series, errors="coerce")
            mask = numeric.notna() & (numeric > rule.maximum)
            if mask.any():
                issues.append(
                    _issue("above_maximum", f"Values must be <= {rule.maximum}.", mask, column)
                )
        if rule.allowed_values is not None:
            mask = series.notna() & ~series.isin(rule.allowed_values)
            if mask.any():
                issues.append(
                    _issue("disallowed_value", "Value is outside the allowed set.", mask, column)
                )
        if rule.pattern:
            compiled = re.compile(rule.pattern)
            mask = series.notna() & series.astype(str).map(compiled.fullmatch).isna()
            if mask.any():
                issues.append(
                    _issue(
                        "pattern_mismatch",
                        "Value does not match the required pattern.",
                        mask,
                        column,
                    )
                )
    return issues
