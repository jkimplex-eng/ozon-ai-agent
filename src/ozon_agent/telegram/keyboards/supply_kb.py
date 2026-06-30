"""Supply keyboard for FBO workflow."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def supply_keyboard(
    proposal_id: str | None = None,
    cluster_names: list[str] | None = None,
    selected_cluster: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [_btn("📋 Последний расчёт", "supply.show"),
         _btn("🧠 Пересчитать FBO", "supply.fbo-propose")],
    ]

    names = [name for name in (cluster_names or []) if name]
    if names:
        rows.append([_btn("Все кластеры", "supply.show")])
        cluster_row = []
        for name in names[:6]:
            label = name if name != selected_cluster else f"• {name}"
            cluster_row.append(_btn(label, f"supply.cluster|{name}"))
            if len(cluster_row) == 2:
                rows.append(cluster_row)
                cluster_row = []
        if cluster_row:
            rows.append(cluster_row)

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
