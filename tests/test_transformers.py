import pandas as pd

from data_quality_pipeline.models import ColumnRule
from data_quality_pipeline.transformers import apply_value_mapping, coerce_series


def test_string_cleaning_handles_whitespace_case_and_null_markers() -> None:
    source = pd.Series([" Alice ", "N/A", "BOB"])
    result = coerce_series(source, ColumnRule(dtype="string", lowercase=True))
    assert result.iloc[0] == "alice"
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == "bob"


def test_unique_value_mapping_applies_vectorized_corrections() -> None:
    source = pd.Series(["LHR", "KHI", "LHR", "ISB"])
    result = apply_value_mapping(source, {"LHR": "Lahore", "KHI": "Karachi"})
    assert result.tolist() == ["Lahore", "Karachi", "Lahore", "ISB"]


def test_boolean_coercion_handles_supported_values_and_invalid_input() -> None:
    source = pd.Series([" yes ", "FALSE", "unknown", None])
    result = coerce_series(source, ColumnRule(dtype="boolean"))
    assert result.iloc[0] == True  # noqa: E712
    assert result.iloc[1] == False  # noqa: E712
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])


def test_float_coercion_preserves_numeric_values() -> None:
    result = coerce_series(pd.Series(["1.5", 2, "bad"]), ColumnRule(dtype="float"))
    assert result.iloc[0] == 1.5
    assert result.iloc[1] == 2.0
    assert pd.isna(result.iloc[2])
