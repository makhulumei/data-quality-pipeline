from __future__ import annotations

import os
import re

import pandas as pd
from sqlalchemy import create_engine


def write_dataframe(frame: pd.DataFrame, table_name: str, database_url: str | None = None) -> int:
    """Persist cleaned data with SQLAlchemy; PostgreSQL is the intended production target."""

    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required to persist cleaned data.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise ValueError("table_name must be a simple SQL identifier")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            frame.to_sql(table_name, connection, if_exists="append", index=False, method="multi")
    finally:
        engine.dispose()
    return len(frame)
