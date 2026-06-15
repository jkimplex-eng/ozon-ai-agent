"""Telegram bot for recommendation approvals.

Safety:
- Telegram can approve/reject only.
- Telegram must not execute real Ozon actions.
- No price/ad/stock API mutation.
"""
from __future__ import annotations

import importlib
from typing import Any

from ozon_agent.approval.models import RecommendationStatus, StoredRecommendation
from ozon_agent.approval.repository import get_recommendation, list_recommendations
from ozon_agent.approval.workflow import approve_recommendation, reject_recommendation


def format_rec_message(rec: StoredRecommendation) -> str:
    lines = [
        f"Recommendation ID: {rec.id}",
        f"SKU: {rec.sku}",
        f"Action: {rec.action.value}",
        f"Expected: {rec.expected_effect}",
        f"Confidence: {rec.confidence_level.value if rec.confidence_level else 'N/A'}"
        f" ({rec.confidence_score:.2f})" if rec.confidence_score is not None else "",
        f"Risk: {rec.risk_level.value if rec.risk_level else 'N/A'}"
        f" ({rec.risk_score:.2f})" if rec.risk_score is not None else "",
        f"Reason: {rec.reason}",
        "",
        "Approve:",
        f"/recommendations approve {rec.id}",
        "",
        "Reject:",
        f"/recommendations reject {rec.id} reason",
    ]
    return "\n".join(line for line in lines if line is not None)


def handle_message(text: str, user: str) -> str:
    parts = text.strip().split(maxsplit=3)
    if not parts or parts[0] != "/recommendations":
        return (
            "Available commands:\n"
            "/recommendations — list pending\n"
            "/recommendations pending — list pending\n"
            "/recommendations approve <id>\n"
            "/recommendations reject <id> <reason>\n"
            "/recommendations show <id>"
        )

    if len(parts) == 1 or (len(parts) == 2 and parts[1] == "pending"):
        return _list_pending()

    action = parts[1]

    if action == "show" and len(parts) >= 3:
        return _show(parts[2])

    if action == "approve" and len(parts) >= 3:
        return _approve(parts[2], user)

    if action == "reject" and len(parts) >= 4:
        reason = parts[3]
        return _reject(parts[2], user, reason)

    return (
        "Usage:\n"
        "/recommendations — list pending\n"
        "/recommendations approve <id>\n"
        "/recommendations reject <id> <reason>\n"
        "/recommendations show <id>"
    )


def _list_pending() -> str:
    recs = list_recommendations(status=RecommendationStatus.PENDING, limit=10)
    if not recs:
        return "No pending recommendations."
    lines = [f"Pending recommendations ({len(recs)}):", ""]
    for rec in recs:
        lines.append(
            f"  {rec.id[:8]}... | SKU: {rec.sku} | Action: {rec.action.value}"
        )
    lines.append("")
    lines.append("Use /recommendations show <id> for details.")
    return "\n".join(lines)


def _show(rec_id: str) -> str:
    rec = get_recommendation(rec_id)
    if rec is None:
        full_id = _resolve_short_id(rec_id)
        if full_id:
            rec = get_recommendation(full_id)
    if rec is None:
        return f"Recommendation {rec_id} not found."
    return format_rec_message(rec)


def _approve(rec_id: str, user: str) -> str:
    full_id = _resolve_short_id(rec_id)
    target = full_id or rec_id
    try:
        rec = approve_recommendation(target, approved_by=user)
        return f"Approved {rec.id[:8]}... by {user}"
    except Exception as e:
        return f"Failed to approve: {e}"


def _reject(rec_id: str, user: str, reason: str) -> str:
    full_id = _resolve_short_id(rec_id)
    target = full_id or rec_id
    try:
        rec = reject_recommendation(target, rejected_by=user, reason=reason)
        return f"Rejected {rec.id[:8]}... by {user}: {reason}"
    except Exception as e:
        return f"Failed to reject: {e}"


def _resolve_short_id(short_id: str) -> str | None:
    if len(short_id) >= 36:
        return short_id
    recs = list_recommendations(limit=100)
    for rec in recs:
        if rec.id.startswith(short_id):
            return rec.id
    return None


def create_app(token: str) -> Any:
    try:
        telegram_ext = importlib.import_module("telegram.ext")
    except ImportError:
        raise ImportError(
            "python-telegram-bot is required. Install with: "
            "pip install python-telegram-bot"
        )
    application_builder = getattr(telegram_ext, "ApplicationBuilder")
    command_handler = getattr(telegram_ext, "CommandHandler")

    async def recommendations_handler(update: Any, context: Any) -> None:
        del context
        if update.message is None:
            return
        text = update.message.text or ""
        user = update.effective_user
        username = user.username or user.first_name or "unknown"
        response = handle_message(text, username)
        await update.message.reply_text(response)

    app = application_builder().token(token).build()
    app.add_handler(command_handler("recommendations", recommendations_handler))
    return app
