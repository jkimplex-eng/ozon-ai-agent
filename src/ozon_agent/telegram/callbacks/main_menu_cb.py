"""Main menu callback — EPIC 1."""
from __future__ import annotations

from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.keyboards.main_menu import main_menu_keyboard


@register("main")
async def handle_main_menu(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "menu":
        await query.edit_message_text(
            "🏪 OZON AI — Панель управления\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )
