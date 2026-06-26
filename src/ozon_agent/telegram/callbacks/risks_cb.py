"""Risks callback — EPIC 7 (partial)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import rub, safe_str, severity_emoji, signal_type_business
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("risks")
async def handle_risks(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_risks(query)


async def _show_risks(query: Any) -> None:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    critical = [
        s for s in signals
        if s.get("severity", "").upper() in ("HIGH", "CRITICAL")
    ]

    if not critical:
        await query.edit_message_text(
            "⚠️ Риски\n\n✅ Нет критичных рисков",
            reply_markup=back_to_menu(),
        )
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "⚠️ Риски",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for s in critical[:8]:
        sku = safe_str(s.get("sku"), "Магазин")
        sev = severity_emoji(s.get("severity", ""))
        stype = signal_type_business(s.get("signal_type", ""))
        impact = rub(float(s.get("value") or 0))
        lines.extend([
            f"{sev} {sku}",
            f"   {stype}",
            f"   Потери: {impact}",
            "",
        ])

    lines.append("━━━━━━━━━━━━━━━━━━")

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
