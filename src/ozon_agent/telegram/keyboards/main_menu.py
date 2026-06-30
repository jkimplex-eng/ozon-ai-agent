"""Main menu keyboard — 10 sections of the OZON AI Platform."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [_btn("📊 Сегодня", "today.show"),
         _btn("📈 Бизнес", "business.show")],
        [_btn("📦 Логистика", "logistics.show"),
         _btn("📢 Реклама", "ads.show")],
        [_btn("🚚 Поставки", "supply.show"),
         _btn("💰 Финансы", "finance.show")],
        [_btn("⚠️ Риски", "risks.show"),
         _btn("✅ Задачи", "tasks.show")],
        [_btn("📚 Эксперименты", "experiments.show"),
         _btn("⚙️ Система", "system.show")],
    ]
    return InlineKeyboardMarkup(rows)
