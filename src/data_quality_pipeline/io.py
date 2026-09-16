from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import BinaryIO

import pandas as pd

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".json"}


def read_dataframe(source: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Read a supported tabular source into a DataFrame."""

    suffix = Path(filename or str(source)).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported input format: {suffix or 'unknown'}")
    try:
        if suffix == ".csv":
            return pd.read_csv(source)
        if suffix == ".xlsx":
            return pd.read_excel(source, engine="openpyxl")
        if suffix == ".json":
            return pd.read_json(source)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        raise ValueError(f"Could not parse {suffix} input: {exc}") from exc
    raise AssertionError("unreachable")


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def parse_schema_json(raw: str | bytes) -> dict:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def bytes_buffer(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)
