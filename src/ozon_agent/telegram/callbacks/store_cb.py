"""Store overview callback."""
from __future__ import annotations

from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.handlers_text import _status_dashboard
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("store")
async def handle_store(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        text = _status_dashboard()
        await query.edit_message_text(text, reply_markup=back_to_menu())
