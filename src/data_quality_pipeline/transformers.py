from __future__ import annotations

import pandas as pd

from .models import ColumnRule

NULL_STRINGS = {"", "null", "none", "n/a", "na", "nan"}


def normalize_string_series(series: pd.Series, rule: ColumnRule) -> pd.Series:
    result = series.astype("string")
    if rule.strip:
        result = result.str.strip()
    result = result.mask(result.str.lower().isin(NULL_STRINGS))
    if rule.lowercase:
        result = result.str.lower()
    if rule.uppercase:
        result = result.str.upper()
    return result


def coerce_series(series: pd.Series, rule: ColumnRule) -> pd.Series:
    if rule.dtype is None:
        return normalize_string_series(series, rule) if series.dtype == "object" else series
    if rule.dtype == "string":
        return normalize_string_series(series, rule)
    if rule.dtype == "integer":
        return pd.to_numeric(series, errors="coerce").astype("Int64")
    if rule.dtype == "float":
        return pd.to_numeric(series, errors="coerce").astype("Float64")
    if rule.dtype == "boolean":
        mapping = {
            "true": True,
            "1": True,
            "yes": True,
            "false": False,
            "0": False,
            "no": False,
        }
        return series.astype("string").str.strip().str.lower().map(mapping).astype("boolean")
    if rule.dtype == "datetime":
        return pd.to_datetime(series, errors="coerce", utc=True)
    raise ValueError(f"Unsupported dtype: {rule.dtype}")


def apply_value_mapping(series: pd.Series, mapping: dict[object, object]) -> pd.Series:
    """Map normalized unique values back across the full Series with vectorized operations."""

    return series.map(mapping).fillna(series)
