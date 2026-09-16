from __future__ import annotations

import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .io import bytes_buffer, read_dataframe
from .models import DatasetSchema
from .pipeline import DataQualityPipeline, PipelineConfig

logger = logging.getLogger(__name__)


def _positive_int_env(name: str, default: int, *, maximum: int | None = None) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 0 or (name != "MAX_PREVIEW_ROWS" and value == 0):
        raise RuntimeError(f"{name} must be positive")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must not exceed {maximum}")
    return value


def _safe_filename(filename: str | None) -> str:
    name = Path((filename or "upload").replace("\\", "/")).name
    return "".join(
        character if character.isprintable() and character not in "\r\n\t" else "_"
        for character in name
    )[:255]


def _check_xlsx_expansion(payload: bytes, filename: str) -> None:
    if Path(filename).suffix.lower() != ".xlsx":
        return
    max_expanded_bytes = _positive_int_env("MAX_XLSX_EXPANDED_MB", 200) * 1024 * 1024
    try:
        with zipfile.ZipFile(bytes_buffer(payload)) as archive:
            expanded_bytes = sum(member.file_size for member in archive.infolist())
            if expanded_bytes > max_expanded_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Expanded XLSX content exceeds the configured size limit.",
                )
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="Uploaded XLSX file is malformed.") from exc

app = FastAPI(
    title="Data Quality Pipeline",
    version="0.1.0",
    description="Validate, normalize, profile, and clean CSV, Excel, or JSON datasets.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/process")
async def process_dataset(
    file: Annotated[UploadFile, File()],
    schema_payload: Annotated[str, Form(alias="schema")],
) -> JSONResponse:
    max_bytes = _positive_int_env("MAX_UPLOAD_MB", 50) * 1024 * 1024
    payload = await file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail="Uploaded file exceeds the configured size limit.",
        )
    try:
        safe_filename = _safe_filename(file.filename)
        _check_xlsx_expansion(payload, safe_filename)
        parsed_schema = DatasetSchema.model_validate(json.loads(schema_payload))
        frame = read_dataframe(bytes_buffer(payload), filename=safe_filename)
        result = DataQualityPipeline(PipelineConfig(schema=parsed_schema)).run(frame)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    preview_rows = _positive_int_env("MAX_PREVIEW_ROWS", 0, maximum=20)
    cleaned_preview = (
        json.loads(
            result.cleaned_data.head(preview_rows).to_json(
                orient="records", date_format="iso"
            )
        )
        if preview_rows
        else []
    )
    logger.info(
        "dataset_processed rows_received=%d rows_output=%d issues=%d",
        result.report.rows_received,
        result.report.rows_output,
        len(result.report.issues),
    )
    return JSONResponse(
        {
            "report": result.report.model_dump(mode="json"),
            "timings_ms": result.timings_ms,
            "cleaned_preview": cleaned_preview,
        }
    )
