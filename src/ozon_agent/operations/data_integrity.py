"""Data Integrity — atomic JSON writes and repository validation."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically using tmp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=path.stem,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        logger.debug("Atomic write: %s", path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically using tmp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=path.stem,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def validate_json_file(path: Path, required_fields: list[str] | None = None) -> list[str]:
    """Validate a JSON file. Returns list of errors."""
    errors: list[str] = []

    if not path.exists():
        errors.append(f"File not found: {path}")
        return errors

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return errors

    if required_fields:
        if isinstance(data, dict):
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        elif isinstance(data, list):
            for i, item in enumerate(data[:5]):
                if isinstance(item, dict):
                    for field in required_fields:
                        if field not in item:
                            errors.append(f"Item {i}: missing field: {field}")

    return errors


def validate_repository(
    repo_dir: Path,
    required_fields: list[str] | None = None,
) -> dict[str, list[str]]:
    """Validate all JSON files in a repository directory."""
    results: dict[str, list[str]] = {}

    if not repo_dir.exists():
        return {"_error": [f"Directory not found: {repo_dir}"]}

    for json_file in sorted(repo_dir.glob("*.json")):
        errors = validate_json_file(json_file, required_fields)
        if errors:
            results[json_file.name] = errors

    return results


def safe_load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    """Safely load JSON with validation."""
    if not path.exists():
        return None

    try:
        data: dict[str, Any] | list[Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path, e)
        return None


def safe_save_json(path: Path, data: Any) -> bool:
    """Safely save JSON with atomic write."""
    try:
        atomic_write_json(path, data)
        return True
    except Exception as e:
        logger.error("Failed to save %s: %s", path, e)
        return False
