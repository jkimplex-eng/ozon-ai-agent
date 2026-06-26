"""Today dashboard keyboard."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def today_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_btn("✅ Задачи", "tasks.show")],
        [_btn("📦 Логистика", "logistics.show"),
         _btn("📢 Реклама", "ads.show")],
        [_btn("💰 Финансы", "finance.show"),
         _btn("⚠️ Риски", "risks.show")],
        back_to_menu(),
    ])
