"""Owner mode keyboard."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def owner_keyboard(rec_id: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("✅ Выполнить", f"rec.approve|{rec_id}")],
        back_to_menu(),
    ])
