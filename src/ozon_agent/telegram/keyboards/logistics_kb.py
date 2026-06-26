"""Logistics keyboard."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def logistics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("Подробнее", "logistics.detail"),
         _btn("Выполнить", "logistics.execute")],
        [_btn("Почему", "logistics.why")],
        back_to_menu(),
    ])
