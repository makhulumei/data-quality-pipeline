import json

import pytest
from fastapi.testclient import TestClient

from data_quality_pipeline.api import _positive_int_env, _safe_filename, app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_process_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_PREVIEW_ROWS", "20")
    schema = {
        "columns": {
            "id": {"dtype": "integer", "required": True, "nullable": False, "unique": True},
            "email": {"dtype": "string", "lowercase": True, "nullable": False},
        },
        "duplicate_subset": ["id"],
    }
    response = client.post(
        "/v1/process",
        files={
            "file": (
                "records.csv",
                b"id,email\n1, A@EXAMPLE.COM \n1, A@EXAMPLE.COM \n",
                "text/csv",
            )
        },
        data={"schema": json.dumps(schema)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["duplicate_rows_removed"] == 1
    assert payload["cleaned_preview"][0]["email"] == "a@example.com"


def test_process_datetime_is_json_serializable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_PREVIEW_ROWS", "20")
    schema = {
        "columns": {
            "created_at": {"dtype": "datetime", "nullable": False},
        }
    }
    response = client.post(
        "/v1/process",
        files={"file": ("records.csv", b"created_at\n2026-09-16\n", "text/csv")},
        data={"schema": json.dumps(schema)},
    )
    assert response.status_code == 200
    assert response.json()["cleaned_preview"][0]["created_at"].startswith("2026-09-16")


def test_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/v1/process",
        files={"file": ("records.txt", b"id=1", "text/plain")},
        data={"schema": json.dumps({"columns": {}})},
    )
    assert response.status_code == 422


def test_missing_duplicate_subset_column_is_reported_without_500() -> None:
    schema = {
        "columns": {"id": {"dtype": "integer", "required": True}},
        "duplicate_subset": ["id"],
    }
    response = client.post(
        "/v1/process",
        files={"file": ("records.csv", b"email\na@example.com\n", "text/csv")},
        data={"schema": json.dumps(schema)},
    )
    assert response.status_code == 200
    codes = {issue["code"] for issue in response.json()["report"]["issues"]}
    assert codes == {"missing_column", "missing_duplicate_column"}


def test_rejects_oversized_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    response = client.post(
        "/v1/process",
        files={"file": ("records.csv", b"x" * (1024 * 1024 + 1), "text/csv")},
        data={"schema": json.dumps({"columns": {"id": {}}})},
    )
    assert response.status_code == 413


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("records.csv", b"\xff\xfe\x00"),
        ("records.json", b"{"),
        ("records.xlsx", b"not-a-zip-file"),
    ],
)
def test_rejects_malformed_uploads(filename: str, payload: bytes) -> None:
    response = client.post(
        "/v1/process",
        files={"file": (filename, payload, "application/octet-stream")},
        data={"schema": json.dumps({"columns": {"id": {}}})},
    )
    assert response.status_code == 422


def test_rejects_unknown_schema_fields() -> None:
    response = client.post(
        "/v1/process",
        files={"file": ("records.csv", b"id\n1\n", "text/csv")},
        data={"schema": json.dumps({"columns": {"id": {"minumum": 1}}})},
    )
    assert response.status_code == 422


def test_preview_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAX_PREVIEW_ROWS", raising=False)
    response = client.post(
        "/v1/process",
        files={"file": ("records.csv", b"id\n1\n", "text/csv")},
        data={"schema": json.dumps({"columns": {"id": {"dtype": "integer"}}})},
    )
    assert response.status_code == 200
    assert response.json()["cleaned_preview"] == []


def test_invalid_environment_configuration_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "invalid")
    with pytest.raises(RuntimeError, match="must be an integer"):
        _positive_int_env("MAX_UPLOAD_MB", 50)


def test_filename_is_sanitized_for_logging() -> None:
    assert _safe_filename("../../unsafe\nname.csv") == "unsafe_name.csv"
    assert _safe_filename(r"..\..\unsafe.csv") == "unsafe.csv"


def test_rejects_xlsx_expanded_beyond_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    import zipfile

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"x" * (1024 * 1024 + 1))
    monkeypatch.setenv("MAX_XLSX_EXPANDED_MB", "1")
    response = client.post(
        "/v1/process",
        files={
            "file": (
                "records.xlsx",
                payload.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"schema": json.dumps({"columns": {"id": {}}})},
    )
    assert response.status_code == 413
