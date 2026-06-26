"""Recommendation card keyboard."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def rec_keyboard(rec_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("✅ Выполнить", f"rec.approve|{rec_id}"),
         _btn("⏳ Позже", f"rec.later|{rec_id}")],
        [_btn("❌ Отклонить", f"rec.reject|{rec_id}"),
         _btn("❓ Почему", f"rec.why|{rec_id}")],
        back_to_menu(),
    ])
