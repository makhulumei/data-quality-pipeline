import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from data_quality_pipeline.database import write_dataframe


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        write_dataframe(pd.DataFrame({"id": [1]}), "rows")


def test_table_name_must_be_safe(tmp_path) -> None:
    with pytest.raises(ValueError, match="simple SQL identifier"):
        write_dataframe(
            pd.DataFrame({"id": [1]}),
            "rows; drop table rows",
            f"sqlite:///{tmp_path / 'test.db'}",
        )


def test_sqlite_write_and_transaction_rollback(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE clean_rows (id INTEGER PRIMARY KEY, value TEXT)"))
    engine.dispose()

    assert write_dataframe(
        pd.DataFrame({"id": [1], "value": ["original"]}),
        "clean_rows",
        database_url,
    ) == 1

    with pytest.raises(IntegrityError):
        write_dataframe(
            pd.DataFrame({"id": [2, 1], "value": ["new", "duplicate"]}),
            "clean_rows",
            database_url,
        )

    engine = create_engine(database_url)
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT id, value FROM clean_rows ORDER BY id")).all()
    engine.dispose()
    assert rows == [(1, "original")]


def test_database_connection_failure_is_propagated() -> None:
    credentials = "invalid:invalid"
    database_url = f"postgresql+psycopg://{credentials}@127.0.0.1:1/missing"
    with pytest.raises(SQLAlchemyError):
        write_dataframe(
            pd.DataFrame({"id": [1]}),
            "rows",
            f"{database_url}?connect_timeout=1",
        )
