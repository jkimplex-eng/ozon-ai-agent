"""Tasks callback — EPIC 7."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.data_helpers import load_payload
from ozon_agent.telegram.format import rub, safe_str, severity_emoji, signal_type_business
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("tasks")
async def handle_tasks(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_tasks(query)


async def _show_tasks(query: Any) -> None:
    signals = load_payload(Path("data") / "signals" / "signals.json")

    critical = [s for s in signals if s.get("severity", "").upper() in ("HIGH", "CRITICAL")]
    important = [s for s in signals if s.get("severity", "").upper() == "MEDIUM"]
    planned = [s for s in signals if s.get("severity", "").upper() not in ("HIGH", "CRITICAL", "MEDIUM")]

    if not signals:
        await query.edit_message_text(
            "✅ Задачи\n\n✅ Нет задач на сегодня",
            reply_markup=back_to_menu(),
        )
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "✅ Задачи",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if critical:
        lines.append(f"🔴 Сегодня ({len(critical)})")
        for s in critical[:3]:
            sku = safe_str(s.get("sku"), "—")
            stype = signal_type_business(s.get("signal_type", ""))
            lines.append(f"  • {sku}: {stype}")
        lines.append("")

    if important:
        lines.append(f"🟡 Важные ({len(important)})")
        for s in important[:3]:
            sku = safe_str(s.get("sku"), "—")
            stype = signal_type_business(s.get("signal_type", ""))
            lines.append(f"  • {sku}: {stype}")
        lines.append("")

    if planned:
        lines.append(f"🟢 Плановые ({len(planned)})")
        for s in planned[:3]:
            sku = safe_str(s.get("sku"), "—")
            stype = signal_type_business(s.get("signal_type", ""))
            lines.append(f"  • {sku}: {stype}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
