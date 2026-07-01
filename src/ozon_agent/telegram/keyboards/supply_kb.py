"""Supply keyboard for FBO workflow."""
from __future__ import annotations

from telegram import InlineKeyboardMarkup

from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


def supply_keyboard(
    proposal_id: str | None = None,
    cluster_buttons: list[tuple[str, str]] | None = None,
    selected_cluster: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [_btn("📋 Последний расчёт", "supply.show"),
         _btn("🧠 Пересчитать FBO", "supply.fbo-propose")],
    ]

    buttons = [(token, name) for token, name in (cluster_buttons or []) if token and name]
    selected_token = None
    if selected_cluster:
        for token, name in buttons:
            if name == selected_cluster:
                selected_token = token
                break

    if buttons:
        rows.append([_btn("Все города", "supply.show")])
        cluster_row = []
        for token, name in buttons[:8]:
            label = name if name != selected_cluster else f"• {name}"
            cluster_row.append(_btn(label, f"supply.cluster|{token}"))
            if len(cluster_row) == 2:
                rows.append(cluster_row)
                cluster_row = []
        if cluster_row:
            rows.append(cluster_row)

    if selected_token:
        rows.append([
            _btn("✅ Согласовать", f"supply.city-approve|{selected_token}"),
            _btn("📝 Создать поставку", f"supply.city-create-draft|{selected_token}"),
        ])
        rows.append([
            _btn("🕒 Показать слоты", f"supply.city-timeslots|{selected_token}"),
            _btn("🚀 Подтвердить первый слот", f"supply.city-book-first|{selected_token}"),
        ])
    elif proposal_id:
        rows.append([_btn("ℹ️ Выберите город", "supply.show")])
    else:
        rows.append([_btn("📦 Список предложений", "supply.proposals")])

    rows.append(back_to_menu())
    return InlineKeyboardMarkup(rows)
