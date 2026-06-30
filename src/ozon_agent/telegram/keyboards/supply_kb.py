"""Supply keyboard for FBO workflow."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def supply_keyboard(proposal_id: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [_btn("📋 Последний расчёт", "supply.show"),
         _btn("🧠 Пересчитать FBO", "supply.fbo-propose")],
    ]

    if proposal_id:
        rows.append([
            _btn("✅ Согласовать", f"supply.approve|{proposal_id}"),
            _btn("📝 Создать поставку", f"supply.create-draft|{proposal_id}"),
        ])
        rows.append([
            _btn("🕒 Показать слоты", f"supply.timeslots|{proposal_id}"),
            _btn("🚀 Подтвердить первый слот", f"supply.book-first|{proposal_id}"),
        ])
    else:
        rows.append([_btn("📦 Список предложений", "supply.proposals")])

    rows.append(back_to_menu())
    return InlineKeyboardMarkup(rows)
