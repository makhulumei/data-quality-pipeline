from __future__ import annotations

from typing import Any

import pandas as pd

from .models import ColumnProfile


def _safe_scalar(value: Any) -> str | float | int | None:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def profile_dataframe(frame: pd.DataFrame) -> dict[str, ColumnProfile]:
    total = len(frame)
    result: dict[str, ColumnProfile] = {}
    for name in frame.columns:
        series = frame[name]
        non_null = int(series.notna().sum())
        null_count = total - non_null
        minimum = maximum = None
        if non_null:
            try:
                minimum = _safe_scalar(series.min())
                maximum = _safe_scalar(series.max())
            except (TypeError, ValueError):
                pass
        result[str(name)] = ColumnProfile(
            dtype=str(series.dtype),
            non_null_count=non_null,
            null_count=null_count,
            null_percent=round((null_count / total * 100) if total else 0.0, 2),
            distinct_count=int(series.nunique(dropna=True)),
            duplicate_value_count=int(series.duplicated(keep=False).sum()),
            minimum=minimum,
            maximum=maximum,
        )
    return result
