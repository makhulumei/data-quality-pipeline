import pandas as pd

from data_quality_pipeline.models import DatasetSchema
from data_quality_pipeline.validation import validate_dataframe


def test_missing_required_and_extra_columns_are_reported() -> None:
    schema = DatasetSchema.model_validate(
        {
            "columns": {"required_col": {"required": True}},
            "allow_extra_columns": False,
        }
    )
    issues = validate_dataframe(pd.DataFrame({"unexpected": [1]}), schema)
    assert [issue.code for issue in issues] == ["missing_column", "extra_columns"]
    assert issues[0].severity == "error"
    assert issues[1].severity == "warning"


def test_allowed_values_and_uniqueness_are_checked() -> None:
    schema = DatasetSchema.model_validate(
        {
            "columns": {
                "status": {"allowed_values": ["active", "inactive"]},
                "external_id": {"unique": True},
            }
        }
    )
    frame = pd.DataFrame(
        {
            "status": ["active", "other", "inactive"],
            "external_id": [1, 1, 2],
        }
    )
    issues = validate_dataframe(frame, schema)
    assert {issue.code for issue in issues} == {"disallowed_value", "duplicate_value"}
    assert next(issue for issue in issues if issue.code == "duplicate_value").row_count == 2


def test_maximum_constraint_and_source_null_are_reported() -> None:
    schema = DatasetSchema.model_validate(
        {
            "columns": {
                "score": {"dtype": "float", "maximum": 10, "nullable": False},
            }
        }
    )
    frame = pd.DataFrame({"score": [10.0, 10.1, None]})
    issues = validate_dataframe(frame, schema)
    assert {issue.code for issue in issues} == {"above_maximum", "source_null"}
