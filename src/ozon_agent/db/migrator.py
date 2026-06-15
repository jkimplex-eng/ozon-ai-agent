"""Database migration runner.

Detects applied migrations, applies pending ones, keeps history.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from ozon_agent.db.connection import get_connection


@dataclass
class MigrationFile:
    filename: str
    version: str
    sql: str


@dataclass
class MigrationResult:
    filename: str
    applied: bool
    error: str | None = None


def get_migrations_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "..", "..", "migrations")


def list_migration_files(migrations_dir: str | None = None) -> list[MigrationFile]:
    directory = migrations_dir or get_migrations_dir()
    if not os.path.isdir(directory):
        return []
    files = sorted(
        f for f in os.listdir(directory)
        if f.endswith(".sql") and f[0].isdigit()
    )
    result = []
    for filename in files:
        filepath = os.path.join(directory, filename)
        with open(filepath, encoding="utf-8") as f:
            sql = f.read()
        version = filename.split("_")[0]
        result.append(MigrationFile(filename=filename, version=version, sql=sql))
    return result


def ensure_migrations_table() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        conn.commit()


def get_applied_versions() -> set[str]:
    ensure_migrations_table()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations ORDER BY version")
            rows = cur.fetchall()
    versions: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            versions.add(str(row["version"]))
        else:
            versions.add(str(row[0]))
    return versions


def get_pending_migrations(
    migrations_dir: str | None = None,
) -> list[MigrationFile]:
    all_files = list_migration_files(migrations_dir)
    applied = get_applied_versions()
    return [m for m in all_files if m.version not in applied]


def apply_migration(migration: MigrationFile) -> MigrationResult:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(migration.sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                    (migration.version, migration.filename),
                )
            conn.commit()
        return MigrationResult(filename=migration.filename, applied=True)
    except Exception as e:
        return MigrationResult(filename=migration.filename, applied=False, error=str(e))


def migrate(
    migrations_dir: str | None = None,
    dry_run: bool = False,
) -> list[MigrationResult]:
    pending = get_pending_migrations(migrations_dir)
    if not pending:
        return []
    if dry_run:
        return [
            MigrationResult(filename=m.filename, applied=False)
            for m in pending
        ]
    results = []
    for migration in pending:
        result = apply_migration(migration)
        results.append(result)
        if result.error:
            break
    return results


def migration_status(migrations_dir: str | None = None) -> dict[str, Any]:
    all_files = list_migration_files(migrations_dir)
    applied = get_applied_versions()
    pending = [m for m in all_files if m.version not in applied]
    return {
        "total": len(all_files),
        "applied": len(applied),
        "pending": len(pending),
        "applied_versions": sorted(applied),
        "pending_files": [m.filename for m in pending],
    }
