"""Quick actions callback — EPIC 11."""
from __future__ import annotations

from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.keyboards.main_menu import main_menu_keyboard


@register("quick")
async def handle_quick(query: Any, context: Any, action: str, params: list[str]) -> None:
    dispatch = {
        "replenish": "📦 Логистика",
        "scale": "📢 Реклама",
        "stop_ads": "⛔ Остановить рекламу",
        "fix_card": "📉 Исправить карточку",
        "profit": "💰 Финансы",
        "daily_report": "📊 Отчёт дня",
    }
    label = dispatch.get(action, action)
    await query.edit_message_text(
        f"⚡ Быстрое действие: {label}\n\nРаздел в разработке.",
        reply_markup=main_menu_keyboard(),
    )
