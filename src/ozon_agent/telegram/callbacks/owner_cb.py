"""Owner mode callback — EPIC 12 (minimal info: what/why/how much/one button)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import rub, safe_str, signal_type_business
from ozon_agent.telegram.keyboards.common import _btn, back_to_menu


@register("owner")
async def handle_owner(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_owner(query)


async def _show_owner(query: Any) -> None:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    critical = [
        s for s in signals
        if s.get("severity", "").upper() in ("HIGH", "CRITICAL")
    ]

    if not critical:
        await query.edit_message_text(
            "👤 Режим владельца\n\n✅ Всё хорошо. Действий не требуется.",
            reply_markup=back_to_menu(),
        )
        return

    top = critical[0]
    sku = safe_str(top.get("sku"), "—")
    stype = signal_type_business(top.get("signal_type", ""))
    impact = rub(float(top.get("value") or 0))

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "👤 Режим владельца",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"Что сделать:",
        f"  {stype} — товар {sku}",
        "",
        f"Почему:",
        f"  Потери {impact}",
        "",
        f"Сколько заработаем:",
        f"  {impact}",
        "━━━━━━━━━━━━━━━━━━",
    ]

    from telegram import InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([
        [_btn("✅ Выполнить", f"rec.approve|{top.get('id', '')}")],
        back_to_menu(),
    ])

    await query.edit_message_text("\n".join(lines), reply_markup=kb)
