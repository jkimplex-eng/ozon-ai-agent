"""Experiments callback."""
from __future__ import annotations

from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.keyboards.common import back_to_menu


@register("experiments")
async def handle_experiments(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show":
        await _show_experiments(query)


async def _show_experiments(query: Any) -> None:
    try:
        from ozon_agent.experiments.repository import list_experiments
        exps = list_experiments(limit=10)
    except Exception:
        exps = []

    if not exps:
        await query.edit_message_text(
            "📚 Эксперименты\n\nНет экспериментов",
            reply_markup=back_to_menu(),
        )
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        f"📚 Эксперименты ({len(exps)})",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for exp in exps:
        lines.extend([
            f"🔬 {exp.id[:8]}...",
            f"   SKU: {exp.sku}",
            f"   Статус: {exp.status.value}",
            f"   Действие: {exp.action}",
            "",
        ])

    lines.append("━━━━━━━━━━━━━━━━━━")

    await query.edit_message_text("\n".join(lines), reply_markup=back_to_menu())
