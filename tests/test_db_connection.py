from __future__ import annotations

from pathlib import Path

from ozon_agent.db.connection import get_database_url


def test_reads_database_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://env_user:env_pass@env-host:5432/env_db")
    assert get_database_url() == "postgresql://env_user:env_pass@env-host:5432/env_db"


def test_reads_database_url_from_dotenv_when_environment_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://dotenv_user:dotenv_pass@dotenv-host:5432/dotenv_db\n",
        encoding="utf-8",
    )
    assert get_database_url() == "postgresql://dotenv_user:dotenv_pass@dotenv-host:5432/dotenv_db"


def test_falls_back_to_default_if_missing_in_environment_and_dotenv(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    assert get_database_url() == "postgresql://ozon_agent:ozon_agent@localhost:5432/ozon_agent"
