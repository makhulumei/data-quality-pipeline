import json
import sys

import pandas as pd
import pytest
from pydantic import ValidationError

from data_quality_pipeline.cli import main


def test_cli_writes_cleaned_output_and_report(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "input.csv"
    schema = tmp_path / "schema.json"
    output = tmp_path / "clean.csv"
    report = tmp_path / "report.json"
    pd.DataFrame({"id": ["1", "1"]}).to_csv(source, index=False)
    schema.write_text(
        json.dumps(
            {
                "columns": {"id": {"dtype": "integer"}},
                "duplicate_subset": ["id"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dq-pipeline",
            str(source),
            "--schema",
            str(schema),
            "--output",
            str(output),
            "--report",
            str(report),
        ],
    )
    main()
    assert pd.read_csv(output)["id"].tolist() == [1]
    assert json.loads(report.read_text())["report"]["duplicate_rows_removed"] == 1


def test_cli_rejects_invalid_schema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "input.csv"
    schema = tmp_path / "schema.json"
    pd.DataFrame({"id": [1]}).to_csv(source, index=False)
    schema.write_text('{"columns": {"id": {"minumum": 1}}}', encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["dq-pipeline", str(source), "--schema", str(schema)],
    )
    with pytest.raises(ValidationError):
        main()
