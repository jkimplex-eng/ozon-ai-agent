from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ozon_agent.ingestion.models import LiveOzonDataset

DEFAULT_LIVE_OZON_ROOT = Path("data") / "live_ozon"


def live_ozon_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env_root = os.environ.get("OZON_AGENT_LIVE_OZON_ROOT")
    return Path(env_root) if env_root else DEFAULT_LIVE_OZON_ROOT


def save_raw_payload(
    dataset: LiveOzonDataset,
    payload: dict[str, Any],
    requested_at: str,
    root: str | Path | None = None,
) -> Path:
    return _write_json("raw", dataset, payload, requested_at, root)


def save_normalized_rows(
    dataset: LiveOzonDataset,
    rows: list[dict[str, Any]],
    requested_at: str,
    root: str | Path | None = None,
) -> Path:
    return _write_json("normalized", dataset, {"rows": rows}, requested_at, root)


def _write_json(
    folder: str,
    dataset: LiveOzonDataset,
    payload: dict[str, Any],
    requested_at: str,
    root: str | Path | None,
) -> Path:
    safe_timestamp = requested_at.replace(":", "").replace("+", "Z")
    base = live_ozon_root(root) / folder / dataset.value
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{safe_timestamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
