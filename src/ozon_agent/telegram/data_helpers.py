"""Data loading helpers extracted from bot.py."""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def payload_rows(path: Path) -> list[dict[str, Any]]:
    data = load_json_dict(path)
    rows = data.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def count_payload_rows(path: Path) -> int:
    data = load_json_dict(path)
    if isinstance(data.get("record_count"), int):
        return int(data["record_count"])
    return len(payload_rows(path))


def count_unique_skus() -> int:
    candidates = [
        Path("data") / "analytics" / "sku_history.json",
        Path("data") / "ranking" / "snapshots.json",
        Path("data") / "cogs" / "cogs.json",
    ]
    skus: set[str] = set()
    for path in candidates:
        if not path.exists():
            continue
        rows = payload_rows(path)
        if not rows:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                raw = []
            rows = [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []
        for row in rows:
            sku = str(row.get("sku") or "").strip()
            if sku:
                skus.add(sku)
        if skus:
            break
    return len(skus)


def last_update_time() -> datetime | None:
    paths = [
        Path("data") / "analytics" / "daily_summary.json",
        Path("data") / "analytics" / "daily_control.json",
        Path("data") / "signals" / "signals.json",
        Path("data") / "recommendations_v2" / "recommendations.json",
        Path("data") / "retro" / "patterns" / "retro_patterns.json",
        Path("data") / "learning" / "summary.json",
        Path("data") / "ranking" / "snapshots.json",
    ]
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    latest = max(path.stat().st_mtime for path in existing)
    return datetime.fromtimestamp(latest, tz=UTC)


def data_freshness(last_update: datetime | None, learning: dict[str, Any]) -> str:
    date_to = str(learning.get("date_to") or "").strip()
    if last_update is None and not date_to:
        return "неизвестно"
    parts: list[str] = []
    if last_update is not None:
        age = datetime.now(UTC) - last_update
        parts.append(f"обновлено {age.total_seconds() / 3600:.1f}ч назад")
    if date_to:
        parts.append(f"данные до {date_to}")
    return ", ".join(parts)


def format_dt(value: datetime | None) -> str:
    if value is None:
        return "неизвестно"
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def supervisor_status() -> str:
    try:
        result = subprocess.run(
            ["supervisorctl", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "неизвестно"
    if result.returncode != 0:
        return "недоступно"
    lines = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            status = "✅" if parts[1] == "RUNNING" else "❌"
            lines.append(f"{parts[0]}={status}")
    return ", ".join(lines) if lines else "неизвестно"


def load_payload(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        rows = data.get("rows", [])
    elif isinstance(data, list):
        rows = data
    else:
        return []
    return [r for r in rows if isinstance(r, dict)]
