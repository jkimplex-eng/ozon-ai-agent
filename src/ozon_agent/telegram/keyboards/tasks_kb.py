"""Tasks keyboard."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def tasks_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("Сегодня", "tasks.today"),
         _btn("Просрочены", "tasks.overdue")],
        [_btn("В работе", "tasks.in_progress"),
         _btn("Выполнены", "tasks.done")],
        back_to_menu(),
    ])
