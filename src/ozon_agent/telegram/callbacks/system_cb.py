"""System health callback — EPIC 8."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import (
    count_unique_skus,
    last_update_time,
    supervisor_status,
    load_json_dict,
)
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("system")
async def handle_system(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_system(query)


async def _show_system(query: Any) -> None:
    supervisor = supervisor_status()
    last_update = last_update_time()
    learning = load_json_dict(Path("data") / "learning" / "summary.json")

    def _status_emoji(service: str) -> str:
        if service in supervisor:
            return "✅" if "RUNNING" in supervisor and service in supervisor else "🔴"
        return "🟡"

    systems = [
        ("API", _status_emoji("ozon-api")),
        ("Telegram", _status_emoji("ozon-telegram-bot")),
        ("Sheets", _status_emoji("ozon-sheets-watch")),
        ("Learning", "✅" if learning.get("sales_rows") else "🔴"),
        ("Analytics", "✅" if (Path("data") / "analytics" / "daily_summary.json").exists() else "🔴"),
        ("Stocks", "✅" if (Path("data") / "signals" / "signals.json").exists() else "🟡"),
        ("Performance API", "🟡"),
        ("Knowledge", "🟡"),
        ("Data Truth", "✅" if (Path("data") / "analytics" / "sku_history.json").exists() else "🔴"),
    ]

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "⚙️ Система",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for name, status in systems:
        lines.append(f"{status} {name}")

    lines.extend([
        "",
        f"Товаров: {count_unique_skus()}",
        "━━━━━━━━━━━━━━━━━━",
    ])

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
