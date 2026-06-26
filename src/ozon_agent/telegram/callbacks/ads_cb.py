"""Advertising callback — EPIC 6."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import pct, rub, safe_str, signal_type_business
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("ads")
async def handle_ads(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_ads(query)


async def _show_ads(query: Any) -> None:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    ad_signals = [
        s for s in signals
        if s.get("signal_type", "") in ("DRR_HIGH", "AD_SPEND_HIGH", "CTR_DECLINE")
    ]

    if not ad_signals:
        await query.edit_message_text(
            "📢 Реклама\n\n✅ Нет проблем с рекламой",
            reply_markup=back_to_menu(),
        )
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "📢 Реклама",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for s in ad_signals[:6]:
        sku = safe_str(s.get("sku"), "—")
        stype = signal_type_business(s.get("signal_type", ""))
        confidence = f"{float(s.get('confidence') or 0):.0%}"
        lines.extend([
            f"📢 {sku}",
            f"   {stype}",
            f"   Уверенность: {confidence}",
            "",
        ])

    lines.append("━━━━━━━━━━━━━━━━━━")

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
