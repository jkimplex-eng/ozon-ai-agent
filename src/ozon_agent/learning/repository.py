from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_EXPERIMENT_ROOT = Path("data") / "experiments"


def experiment_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env_root = os.environ.get("OZON_AGENT_EXPERIMENT_ROOT")
    return Path(env_root) if env_root else DEFAULT_EXPERIMENT_ROOT


def ensure_storage(root: str | Path | None = None) -> Path:
    base = experiment_root(root)
    for name in ("hypotheses", "experiments", "outcomes", "insights", "statistics"):
        (base / name).mkdir(parents=True, exist_ok=True)
    return base


def write_json(
    folder: str,
    item_id: str,
    payload: dict[str, Any],
    root: str | Path | None = None,
) -> Path:
    base = ensure_storage(root)
    path = base / folder / f"{item_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_json(folder: str, item_id: str, root: str | Path | None = None) -> dict[str, Any] | None:
    path = experiment_root(root) / folder / f"{item_id}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def list_json(folder: str, root: str | Path | None = None) -> list[dict[str, Any]]:
    base = experiment_root(root) / folder
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(base.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def delete_json(folder: str, item_id: str, root: str | Path | None = None) -> bool:
    path = experiment_root(root) / folder / f"{item_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: to_jsonable(item)
            for key, item in asdict(value).items()  # type: ignore[arg-type]
        }
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value
