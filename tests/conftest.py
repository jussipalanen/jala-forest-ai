import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from jalaforest.config import DATABASE_URL
from jalaforest.db import init_schema


@pytest.fixture
def engine():
    """Engine bound to a throwaway schema so tests never touch real data."""
    admin = create_engine(DATABASE_URL)
    try:
        with admin.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip("PostGIS is not running (start it with ./dev up)")

    schema = f"test_{uuid.uuid4().hex[:8]}"
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    eng = create_engine(DATABASE_URL, connect_args={"options": f"-csearch_path={schema},public"})
    init_schema(eng)
    try:
        yield eng
    finally:
        eng.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
