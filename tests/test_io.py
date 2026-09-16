from io import BytesIO

import pandas as pd
import pytest

from data_quality_pipeline.io import read_dataframe


def test_reads_json_records() -> None:
    frame = read_dataframe(BytesIO(b'[{"id": 1}, {"id": 2}]'), filename="records.json")
    assert frame["id"].tolist() == [1, 2]


def test_reads_xlsx(tmp_path) -> None:
    path = tmp_path / "records.xlsx"
    pd.DataFrame({"id": [1, 2]}).to_excel(path, index=False)
    frame = read_dataframe(path)
    assert frame["id"].tolist() == [1, 2]


def test_unlisted_spreadsheet_format_is_not_supported() -> None:
    with pytest.raises(ValueError, match="Unsupported input format: .ods"):
        read_dataframe(BytesIO(b"legacy"), filename="records.ods")


@pytest.mark.parametrize(
    ("filename", "payload"),
    [("records.json", b"{"), ("records.xlsx", b"not-a-workbook")],
)
def test_malformed_inputs_raise_clear_value_error(filename: str, payload: bytes) -> None:
    with pytest.raises(ValueError, match="Could not parse"):
        read_dataframe(BytesIO(payload), filename=filename)
