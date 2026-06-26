"""Advertising keyboard."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def ads_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("Увеличить", "ads.scale"),
         _btn("Уменьшить", "ads.reduce")],
        [_btn("Остановить", "ads.stop"),
         _btn("Почему", "ads.why")],
        back_to_menu(),
    ])
