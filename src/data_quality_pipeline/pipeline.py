from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pandas as pd

from .models import DatasetSchema, PipelineResult, QualityReport, ValidationIssue
from .profiling import profile_dataframe
from .transformers import coerce_series
from .validation import validate_dataframe_with_context


@dataclass(slots=True)
class PipelineConfig:
    schema: DatasetSchema
    fail_on_error: bool = False


class DataQualityPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config

    def run(self, frame: pd.DataFrame) -> PipelineResult:
        started = perf_counter()
        source = frame.copy(deep=True).reset_index(drop=True)

        transform_started = perf_counter()
        coercion_failures: dict[str, pd.Series] = {}
        for column, rule in self.config.schema.columns.items():
            if column in source.columns:
                original = source[column].copy(deep=True)
                transformed = coerce_series(original, rule)
                if rule.dtype in {"integer", "float", "boolean", "datetime"}:
                    failure_mask = original.notna() & transformed.isna()
                    if failure_mask.any():
                        coercion_failures[column] = failure_mask
                source[column] = transformed
        transform_ms = (perf_counter() - transform_started) * 1000

        duplicate_rows_removed = 0
        structural_issues: list[ValidationIssue] = []
        if self.config.schema.drop_duplicate_rows:
            subset = self.config.schema.duplicate_subset
            missing_subset = (
                [] if subset is None else [name for name in subset if name not in source]
            )
            if missing_subset:
                structural_issues.append(
                    ValidationIssue(
                        code="missing_duplicate_column",
                        severity="error",
                        message=(
                            "Duplicate handling requires missing columns: "
                            + ", ".join(missing_subset)
                            + "."
                        ),
                        row_count=len(source),
                    )
                )
            else:
                before = len(source)
                source = source.drop_duplicates(subset=subset, keep="first")
                duplicate_rows_removed = before - len(source)

        validation_started = perf_counter()
        coercion_issues: list[ValidationIssue] = []
        for column, failure_mask in coercion_failures.items():
            if failure_mask.any():
                rule = self.config.schema.columns[column]
                coercion_issues.append(
                    ValidationIssue(
                        code="coercion_failure",
                        severity="error",
                        message=(
                            "Non-null source values could not be converted "
                            f"to {rule.dtype}."
                        ),
                        column=column,
                        row_count=int(failure_mask.sum()),
                        sample_rows=[
                            int(index)
                            for index in failure_mask[failure_mask].index[:10]
                        ],
                    )
                )
        issues = structural_issues + coercion_issues + validate_dataframe_with_context(
            source,
            self.config.schema,
            coercion_failures=coercion_failures,
        )
        validation_ms = (perf_counter() - validation_started) * 1000

        if self.config.fail_on_error and any(issue.severity == "error" for issue in issues):
            raise ValueError("Validation failed; inspect the generated quality report.")

        source = source.reset_index(drop=True)
        profile_started = perf_counter()
        profile = profile_dataframe(source)
        profile_ms = (perf_counter() - profile_started) * 1000

        report = QualityReport(
            rows_received=len(frame),
            rows_output=len(source),
            columns_received=len(frame.columns),
            duplicate_rows_removed=duplicate_rows_removed,
            issues=issues,
            profile=profile,
        )
        return PipelineResult(
            cleaned_data=source,
            report=report,
            timings_ms={
                "transform": round(transform_ms, 3),
                "validation": round(validation_ms, 3),
                "profiling": round(profile_ms, 3),
                "total": round((perf_counter() - started) * 1000, 3),
            },
        )
