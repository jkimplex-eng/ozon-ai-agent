"""Database connection and session management."""
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg
from dotenv import find_dotenv, load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None
_DEFAULT_DATABASE_URL = "postgresql://ozon_agent:ozon_agent@localhost:5432/ozon_agent"


def _project_dotenv_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    )


def _load_database_env() -> None:
    discovered_path = find_dotenv(filename=".env", usecwd=True)
    dotenv_path = discovered_path or _project_dotenv_path()
    load_dotenv(dotenv_path=dotenv_path, override=False)


def get_database_url() -> str:
    _load_database_env()
    return os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL)


def init_pool(min_size: int = 2, max_size: int = 10) -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_database_url(),
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
        )
    return _pool


def get_pool() -> ConnectionPool:
    if _pool is None:
        return init_pool()
    return _pool


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


@contextmanager
def get_cursor() -> Generator[psycopg.Cursor, None, None]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            yield cur


def execute_query(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(sql, params)
        if cur.description:
            return cur.fetchall()  # type: ignore[return-value]
        return []


def execute_many(sql: str, params_list: list[tuple[Any, ...]]) -> int:
    with get_cursor() as cur:
        cur.executemany(sql, params_list)
        return cur.rowcount


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
