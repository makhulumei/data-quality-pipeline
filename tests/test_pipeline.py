import pandas as pd
import pytest

from data_quality_pipeline.models import DatasetSchema
from data_quality_pipeline.pipeline import DataQualityPipeline, PipelineConfig


def schema() -> DatasetSchema:
    return DatasetSchema.model_validate(
        {
            "columns": {
                "id": {"dtype": "integer", "required": True, "nullable": False, "unique": True},
                "email": {
                    "dtype": "string",
                    "nullable": False,
                    "lowercase": True,
                    "pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
                },
                "age": {"dtype": "integer", "minimum": 18, "maximum": 100},
            },
            "duplicate_subset": ["id"],
        }
    )


def test_pipeline_normalizes_deduplicates_and_reports_quality_issues() -> None:
    frame = pd.DataFrame(
        [
            {"id": "1", "email": " Alice@Example.COM ", "age": "31"},
            {"id": "1", "email": " Alice@Example.COM ", "age": "31"},
            {"id": "2", "email": "invalid", "age": "14"},
            {"id": "3", "email": None, "age": "unknown"},
        ]
    )

    result = DataQualityPipeline(PipelineConfig(schema=schema())).run(frame)

    assert len(result.cleaned_data) == 3
    assert result.report.duplicate_rows_removed == 1
    assert result.cleaned_data.loc[0, "email"] == "alice@example.com"
    assert str(result.cleaned_data["id"].dtype) == "Int64"
    assert {issue.code for issue in result.report.issues} == {
        "pattern_mismatch",
        "source_null",
        "below_minimum",
        "coercion_failure",
    }
    assert "quality_score" not in result.report.model_dump()
    assert result.timings_ms["total"] >= 0


def test_input_frame_is_not_mutated() -> None:
    frame = pd.DataFrame([{"id": "1", "email": " A@B.COM ", "age": "20"}])
    original = frame.copy(deep=True)
    DataQualityPipeline(PipelineConfig(schema=schema())).run(frame)
    pd.testing.assert_frame_equal(frame, original)


def test_missing_duplicate_column_is_a_structured_issue() -> None:
    configured = DatasetSchema.model_validate(
        {
            "columns": {"id": {"dtype": "integer", "required": True}},
            "duplicate_subset": ["id"],
        }
    )
    result = DataQualityPipeline(PipelineConfig(schema=configured)).run(
        pd.DataFrame({"email": ["a@example.com"]})
    )
    assert {issue.code for issue in result.report.issues} == {
        "missing_column",
        "missing_duplicate_column",
    }
    assert result.report.rows_output == 1


def test_coercion_failure_is_distinct_from_source_null() -> None:
    configured = DatasetSchema.model_validate(
        {
            "columns": {"value": {"dtype": "integer", "nullable": False}},
            "drop_duplicate_rows": False,
        }
    )
    result = DataQualityPipeline(PipelineConfig(schema=configured)).run(
        pd.DataFrame({"value": [None, "not-a-number", "3"]})
    )
    by_code = {issue.code: issue for issue in result.report.issues}
    assert by_code["source_null"].sample_rows == [0]
    assert by_code["coercion_failure"].sample_rows == [1]
    assert result.cleaned_data["value"].tolist() == [pd.NA, pd.NA, 3]


def test_non_integer_input_index_is_normalized_for_issue_samples() -> None:
    configured = DatasetSchema.model_validate(
        {"columns": {"value": {"dtype": "integer", "nullable": False}}}
    )
    frame = pd.DataFrame({"value": ["invalid"]}, index=["source-row"])
    result = DataQualityPipeline(PipelineConfig(schema=configured)).run(frame)
    assert result.report.issues[0].sample_rows == [0]
    assert frame.index.tolist() == ["source-row"]


def test_fail_on_error_raises_after_reportable_validation() -> None:
    configured = DatasetSchema.model_validate(
        {"columns": {"id": {"dtype": "integer", "nullable": False}}}
    )
    pipeline = DataQualityPipeline(PipelineConfig(schema=configured, fail_on_error=True))
    with pytest.raises(ValueError, match="Validation failed"):
        pipeline.run(pd.DataFrame({"id": [None]}))
