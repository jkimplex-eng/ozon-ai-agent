"""Business dashboard callback — EPIC 4."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import pct, rub
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("business")
async def handle_business(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_business(query)


async def _show_business(query: Any) -> None:
    daily = load_payload(Path("data") / "analytics" / "daily_summary.json")

    if not daily:
        await query.edit_message_text(
            "📈 Бизнес\n\n📭 Нет данных",
            reply_markup=back_to_menu(),
        )
        return

    total_revenue = sum(float(d.get("revenue") or 0) for d in daily)
    total_profit = sum(float(d.get("gross_profit") or 0) for d in daily)
    total_ad = sum(float(d.get("advertising") or 0) for d in daily)
    avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    avg_drr = (total_ad / total_revenue * 100) if total_revenue > 0 else 0
    avg_roi = (total_profit / total_ad * 100) if total_ad > 0 else 0

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "📈 Бизнес",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"Выручка: {rub(total_revenue)}",
        f"Прибыль: {rub(total_profit)}",
        f"Маржа: {pct(avg_margin)}",
        f"ДРР: {pct(avg_drr)}",
        f"ROI: {pct(avg_roi)}",
        "",
        "━━━━━━━━━━━━━━━━━━",
    ]

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
