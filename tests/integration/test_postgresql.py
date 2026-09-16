import os
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from data_quality_pipeline.database import write_dataframe

pytestmark = pytest.mark.integration


@pytest.fixture
def database_url() -> str:
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is not configured")
    return value


def test_postgresql_write_and_failed_batch_rolls_back(database_url: str) -> None:
    table = f"dq_integration_{uuid4().hex[:12]}"
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            )

        assert write_dataframe(
            pd.DataFrame({"id": [1], "value": ["original"]}), table, database_url
        ) == 1

        with pytest.raises(IntegrityError):
            write_dataframe(
                pd.DataFrame({"id": [2, 1], "value": ["new", "duplicate"]}),
                table,
                database_url,
            )

        with engine.connect() as connection:
            rows = connection.execute(text(f'SELECT id, value FROM "{table}"')).all()
        assert rows == [(1, "original")]
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
        engine.dispose()
