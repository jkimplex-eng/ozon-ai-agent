"""Today dashboard callback — EPIC 2."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import rub, signal_type_business
from ozon_agent.telegram.keyboards.common import back_to_menu
from ozon_agent.telegram.outcome_store import load_success_patterns


@register("today")
async def handle_today(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_today(query)


async def _show_today(query: Any) -> None:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    recs = load_payload(Path("data") / "recommendations_v2" / "recommendations.json")

    total_impact = 0.0
    for s in signals:
        total_impact += float(s.get("value") or s.get("evidence", {}).get("spend") or 0)

    critical = sum(1 for s in signals if s.get("severity", "").upper() in ("HIGH", "CRITICAL"))
    important = sum(1 for s in signals if s.get("severity", "").upper() == "MEDIUM")
    planned = sum(1 for s in signals if s.get("severity", "").upper() not in ("HIGH", "CRITICAL", "MEDIUM"))

    total_actions = len(signals)
    health_score = max(0, min(100, 100 - critical * 15 - important * 5))

    profit_str = f"+{rub(total_impact)}" if total_impact > 0 else rub(total_impact)

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "📅 Сегодня",
        "",
        f"Ожидаемая прибыль",
        profit_str,
        "",
        f"Health",
        f"{health_score}/100",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "Сегодня необходимо выполнить",
        f"{total_actions} действий",
        "",
        "━━━━━━━━━━━━━━━━━━",
        f"🔴 Критичных",
        f"{critical}",
        "",
        f"🟡 Важных",
        f"{important}",
        "",
        f"🟢 Плановых",
        f"{planned}",
        "━━━━━━━━━━━━━━━━━━",
    ]

    from ozon_agent.telegram.keyboards.common import _btn
    from telegram import InlineKeyboardMarkup

    kb = InlineKeyboardMarkup([
        [_btn("✅ Задачи", "tasks.show")],
        [_btn("📦 Логистика", "logistics.show"),
         _btn("📢 Реклама", "ads.show")],
        [_btn("💰 Финансы", "finance.show"),
         _btn("⚠️ Риски", "risks.show")],
        back_to_menu(),
    ])

    await query.edit_message_text("\n".join(lines), reply_markup=kb)
