"""Database helpers."""

from __future__ import annotations

from importlib import resources

from sqlalchemy import Connection, Engine, create_engine, text

from .config import DATABASE_URL


def get_engine(url: str = DATABASE_URL) -> Engine:
    return create_engine(url)


def read_sql(name: str) -> str:
    return resources.files("jalaforest").joinpath("sql", name).read_text(encoding="utf-8")


def run_sql(conn: Connection, sql: str) -> None:
    # exec_driver_sql passes the script to psycopg as-is, which accepts
    # several statements in one call.
    conn.exec_driver_sql(sql)


def init_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        run_sql(conn, read_sql("schema.sql"))


def compute_overlap(conn: Connection) -> None:
    run_sql(conn, read_sql("overlap.sql"))


def scalar(conn: Connection, sql: str, **params):
    return conn.execute(text(sql), params).scalar()
