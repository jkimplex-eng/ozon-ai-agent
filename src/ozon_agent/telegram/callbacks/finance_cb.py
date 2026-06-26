"""Finance callback — EPIC 7 (partial)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import pct, rub
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("finance")
async def handle_finance(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_finance(query)


async def _show_finance(query: Any) -> None:
    daily = load_payload(Path("data") / "analytics" / "daily_summary.json")

    if not daily:
        await query.edit_message_text(
            "💰 Финансы\n\n📭 Нет данных",
            reply_markup=back_to_menu(),
        )
        return

    total_revenue = sum(float(d.get("revenue") or 0) for d in daily)
    total_ad = sum(float(d.get("advertising") or 0) for d in daily)
    total_cogs = sum(float(d.get("cogs") or 0) for d in daily)
    total_commission = sum(float(d.get("commission") or 0) for d in daily)
    total_logistics = sum(float(d.get("logistics") or 0) for d in daily)
    total_profit = sum(float(d.get("gross_profit") or 0) for d in daily)
    avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "💰 Финансы",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"Выручка: {rub(total_revenue)}",
        f"Себестоимость: {rub(total_cogs)}",
        f"Реклама: {rub(total_ad)}",
        f"Комиссия: {rub(total_commission)}",
        f"Логистика: {rub(total_logistics)}",
        "",
        f"Прибыль: {rub(total_profit)}",
        f"Маржа: {pct(avg_margin)}",
        "━━━━━━━━━━━━━━━━━━",
    ]

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
