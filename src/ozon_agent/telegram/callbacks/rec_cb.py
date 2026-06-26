"""Recommendation card callback — EPIC 3 (CEO Card)."""
from __future__ import annotations

from typing import Any

from ozon_agent.telegram.callbacks.router import register
from ozon_agent.telegram.keyboards.common import _btn, back_to_menu
from ozon_agent.telegram.outcome_store import record_outcome


@register("rec")
async def handle_rec(query: Any, context: Any, action: str, params: list[str]) -> None:
    if action == "show" and params:
        await _show_rec(query, params[0])
    elif action == "approve" and params:
        await _approve_rec(query, params[0])
    elif action == "reject" and params:
        await _reject_rec(query, params[0])
    elif action == "later" and params:
        await _later_rec(query, params[0])
    elif action == "why" and params:
        await _why_rec(query, params[0])


async def _show_rec(query: Any, rec_id: str) -> None:
    from telegram import InlineKeyboardMarkup
    from ozon_agent.approval.repository import get_recommendation

    rec = get_recommendation(rec_id)
    if rec is None:
        await query.edit_message_text(
            f"Рекомендация {rec_id[:8]}... не найдена",
            reply_markup=back_to_menu(),
        )
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        f"📦 {rec.sku}",
        f"{rec.reason}",
        "",
        f"Ожидаемый эффект",
        f"{rec.expected_effect}",
        "",
        f"Уверенность: {rec.confidence_score:.0%}" if rec.confidence_score else "",
        f"Источник: {rec.source or 'Agent'}",
        "━━━━━━━━━━━━━━━━━━",
    ]

    kb = InlineKeyboardMarkup([
        [_btn("✅ Выполнить", f"rec.approve|{rec_id}"),
         _btn("⏳ Позже", f"rec.later|{rec_id}")],
        [_btn("❌ Отклонить", f"rec.reject|{rec_id}"),
         _btn("❓ Почему", f"rec.why|{rec_id}")],
        back_to_menu(),
    ])

    await query.edit_message_text("\n".join(lines), reply_markup=kb)


async def _approve_rec(query: Any, rec_id: str) -> None:
    try:
        from ozon_agent.approval.workflow import approve_recommendation
        approve_recommendation(rec_id, approved_by="telegram")
        await query.edit_message_text(
            f"✅ Рекомендация {rec_id[:8]}... одобрена",
            reply_markup=back_to_menu(),
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}", reply_markup=back_to_menu())


async def _reject_rec(query: Any, rec_id: str) -> None:
    try:
        from ozon_agent.approval.workflow import reject_recommendation
        reject_recommendation(rec_id, rejected_by="telegram", reason="отклонено из Telegram")
        await query.edit_message_text(
            f"❌ Рекомендация {rec_id[:8]}... отклонена",
            reply_markup=back_to_menu(),
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}", reply_markup=back_to_menu())


async def _later_rec(query: Any, rec_id: str) -> None:
    record_outcome(
        recommendation_id=rec_id,
        sku="",
        action="defer",
        result="OBSERVING",
        user="telegram",
    )
    await query.edit_message_text(
        f"⏳ Рекомендация {rec_id[:8]}... отложена",
        reply_markup=back_to_menu(),
    )


async def _why_rec(query: Any, rec_id: str) -> None:
    try:
        from ozon_agent.approval.repository import get_recommendation
        rec = get_recommendation(rec_id)
        if rec:
            await query.edit_message_text(
                f"❓ Почему {rec.sku}?\n\n{rec.reason}\n\n"
                f"Гипотеза: {getattr(rec, 'hypothesis', rec.reason)}",
                reply_markup=back_to_menu(),
            )
        else:
            await query.edit_message_text("Рекомендация не найдена", reply_markup=back_to_menu())
    except Exception:
        await query.edit_message_text("Ошибка при загрузке", reply_markup=back_to_menu())
