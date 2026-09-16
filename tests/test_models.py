import pytest
from pydantic import ValidationError

from data_quality_pipeline.models import ColumnRule, DatasetSchema


def test_unknown_column_rule_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="minumum"):
        ColumnRule.model_validate({"dtype": "integer", "minumum": 1})


def test_unknown_dataset_schema_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unexpected"):
        DatasetSchema.model_validate({"columns": {"id": {}}, "unexpected": True})


def test_contradictory_case_rules_are_rejected() -> None:
    with pytest.raises(ValidationError, match="cannot both be enabled"):
        ColumnRule(lowercase=True, uppercase=True)


def test_duplicate_subset_must_reference_declared_columns() -> None:
    with pytest.raises(ValidationError, match="undeclared columns: missing"):
        DatasetSchema.model_validate(
            {"columns": {"id": {}}, "duplicate_subset": ["id", "missing"]}
        )


def test_maximum_cannot_be_below_minimum() -> None:
    with pytest.raises(ValidationError, match="greater than or equal"):
        ColumnRule(minimum=10, maximum=5)


def test_pattern_length_is_bounded() -> None:
    with pytest.raises(ValidationError, match="512"):
        ColumnRule(pattern="x" * 513)


def test_invalid_regular_expression_is_rejected() -> None:
    with pytest.raises(ValidationError, match="valid regular expression"):
        ColumnRule(pattern="[")
