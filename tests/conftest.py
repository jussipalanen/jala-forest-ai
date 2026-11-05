import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from jalaforest.config import DATABASE_URL, describe_database_url, is_local_database_url
from jalaforest.db import init_schema

# The database tests create and drop a whole database, so never point them at a cloud one.
if not is_local_database_url(DATABASE_URL):
    pytest.exit(f"Refusing to run tests against {describe_database_url(DATABASE_URL)}: "
                "tests use the local PostGIS only (unset DATABASE_URL).", returncode=2)

TEST_DB = "jalaforest_test"


@pytest.fixture(scope="session")
def test_database_url():
    """A separate database for tests.

    Tests must never share a database with real data: unqualified statements such as
    DROP TABLE IF EXISTS fall through search_path to `public` when the table is missing
    from the test schema.
    """
    admin = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    except OperationalError:
        pytest.skip("PostGIS is not running (start it with ./dev up)")
    url = make_url(DATABASE_URL).set(database=TEST_DB)
    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION postgis"))
    eng.dispose()
    yield url
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture
def engine(test_database_url):
    """Engine bound to a throwaway schema in the test database."""
    admin = create_engine(test_database_url)
    schema = f"test_{uuid.uuid4().hex[:8]}"
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    eng = create_engine(test_database_url, connect_args={"options": f"-csearch_path={schema},public"})
    init_schema(eng)
    try:
        yield eng
    finally:
        eng.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
