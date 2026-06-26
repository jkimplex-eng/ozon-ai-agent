"""Logistics callback — EPIC 5."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import rub, safe_str, signal_type_business
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("logistics")
async def handle_logistics(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_logistics(query)
    elif action == "detail" and params:
        await _show_detail(query, params[0])


async def _show_logistics(query: Any) -> None:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    stock_signals = [
        s for s in signals
        if s.get("signal_type", "") in ("STOCK_LOW", "STOCKOUT", "LOGISTICS_ISSUE")
    ]

    if not stock_signals:
        await query.edit_message_text(
            "📦 Логистика\n\n✅ Нет проблем с логистикой",
            reply_markup=back_to_menu(),
        )
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "📦 Логистика",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for s in stock_signals[:8]:
        sku = safe_str(s.get("sku"), "—")
        stype = signal_type_business(s.get("signal_type", ""))
        impact = rub(float(s.get("value") or 0))
        lines.extend([
            f"📦 {sku}",
            f"   {stype}",
            f"   Ожидаемая прибыль: {impact}",
            "",
        ])

    lines.append("━━━━━━━━━━━━━━━━━━")

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())


async def _show_detail(query: Any, sku: str) -> None:
    await query.edit_message_text(
        f"📦 Детали логистики: {sku}\n\nИспользуйте /sku {sku} для полного анализа.",
        reply_markup=back_to_menu(),
    )
