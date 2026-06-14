"""Tests for migration runner."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from ozon_agent.db.migrator import (
    MigrationFile,
    get_pending_migrations,
    list_migration_files,
    migration_status,
)


def test_list_migration_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("SELECT 1;")
        with open(os.path.join(tmpdir, "002_other.sql"), "w") as f:
            f.write("SELECT 2;")
        files = list_migration_files(tmpdir)
        assert len(files) == 2
        assert files[0].version == "001"
        assert files[1].version == "002"


def test_list_migration_files_ignores_non_sql() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("SELECT 1;")
        with open(os.path.join(tmpdir, "notes.txt"), "w") as f:
            f.write("ignore me")
        files = list_migration_files(tmpdir)
        assert len(files) == 1


def test_list_migration_files_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        files = list_migration_files(tmpdir)
        assert files == []


def test_list_migration_files_missing_dir() -> None:
    files = list_migration_files("/nonexistent/path")
    assert files == []


def test_migration_file_dataclass() -> None:
    m = MigrationFile(filename="001_test.sql", version="001", sql="SELECT 1;")
    assert m.filename == "001_test.sql"
    assert m.version == "001"


def test_migration_status_no_db() -> None:
    with patch("ozon_agent.db.migrator.get_applied_versions", return_value=set()):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
                f.write("SELECT 1;")
            status = migration_status(tmpdir)
            assert status["total"] == 1
            assert status["applied"] == 0
            assert status["pending"] == 1
            assert "001_test.sql" in status["pending_files"]


def test_pending_migrations_with_applied() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "001_test.sql"), "w") as f:
            f.write("SELECT 1;")
        with open(os.path.join(tmpdir, "002_other.sql"), "w") as f:
            f.write("SELECT 2;")
        with patch(
            "ozon_agent.db.migrator.get_applied_versions", return_value={"001"}
        ):
            pending = get_pending_migrations(tmpdir)
            assert len(pending) == 1
            assert pending[0].version == "002"
