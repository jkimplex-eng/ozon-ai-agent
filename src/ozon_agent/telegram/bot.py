"""Telegram bot — thin command router.

Delegates all handler logic to handlers_text.py.
Backward-compatible: handle_message(text, user) returns same strings as before.
"""
from __future__ import annotations

import importlib
import subprocess  # noqa: F401 — re-exported for test mocks
from typing import Any

from ozon_agent.approval.repository import get_recommendation, list_recommendations
from ozon_agent.approval.workflow import approve_recommendation, reject_recommendation
from ozon_agent.telegram.handlers_text import (
    _alerts,
    _approve,
    _cogs_status,
    _daily,
    _economics,
    _experiment_list,
    _experiment_report,
    _experiment_show,
    _experiment_transition,
    _experiment_cancel,
    _handle_experiments,
    _handle_outcome,
    _help_text,
    _learn,
    _list_pending,
    _outcomes,
    _recommendations_v2,
    _reject,
    _retro,
    _show,
    _signals,
    _sku_detail,
    _status_dashboard,
    _today,
    _top_sku,
    _why_down,
    _worst_sku,
    format_rec_message,
)

__all__ = ["handle_message", "create_app", "format_rec_message"]


def handle_message(text: str, user: str) -> str:
    try:
        return _handle_message(text, user)
    except Exception as exc:
        return (
            "Команда временно недоступна.\n"
            "Я записал ошибку в лог, бот продолжает работать.\n\n"
            f"Тип ошибки: {type(exc).__name__}"
        )


def _handle_message(text: str, user: str) -> str:
    parts = text.strip().split(maxsplit=3)
    if not parts:
        return _help_text()

    if parts[0] == "/help":
        return _help_text()
    if parts[0] == "/status":
        return _status_dashboard()
    if parts[0] == "/experiments":
        return _handle_experiments(parts, user)
    if parts[0] == "/signals":
        return _signals()
    if parts[0] == "/recommendations" and len(parts) == 1:
        return _recommendations_v2()
    if parts[0] == "/daily":
        return _daily()
    if parts[0] == "/cogs":
        return _cogs_status()
    if parts[0] == "/learn":
        return _learn()
    if parts[0] == "/why_down":
        sku = parts[1] if len(parts) >= 2 else ""
        return _why_down(sku)
    if parts[0] == "/sku":
        sku = parts[1] if len(parts) >= 2 else ""
        return _sku_detail(sku)
    if parts[0] == "/economics":
        return _economics()
    if parts[0] == "/alerts":
        return _alerts()
    if parts[0] == "/retro":
        return _retro()
    if parts[0] == "/today":
        return _today()
    if parts[0] == "/outcomes":
        return _outcomes()
    if parts[0] == "/outcome":
        return _handle_outcome(parts, user)
    if parts[0] == "/top_sku":
        return _top_sku()
    if parts[0] == "/worst_sku":
        return _worst_sku()

    if parts[0] != "/recommendations":
        return _help_text()

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
        "Использование:\n"
        "/recommendations — список рекомендаций\n"
        "/recommendations approve <id>\n"
        "/recommendations reject <id> <причина>\n"
        "/recommendations show <id>"
    )


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
    callback_query_handler = getattr(telegram_ext, "CallbackQueryHandler")

    from ozon_agent.telegram.callbacks.router import route_callback
    from ozon_agent.telegram.callbacks import (  # noqa: F401 — side-effect imports for @register
        main_menu_cb, today_cb, business_cb, logistics_cb, ads_cb,
        finance_cb, risks_cb, tasks_cb, experiments_cb, system_cb,
        store_cb, quick_cb, rec_cb, owner_cb,
    )
    from ozon_agent.telegram.keyboards.main_menu import main_menu_keyboard

    async def cmd_start(update: Any, context: Any) -> None:
        del context
        if update.message is None:
            return
        await update.message.reply_text(
            "🏪 OZON AI — Панель управления\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )

    async def generic_handler(update: Any, context: Any) -> None:
        del context
        if update.message is None:
            return
        text = update.message.text or ""
        user = update.effective_user
        username = user.username or user.first_name or "unknown"
        response = handle_message(text, username)
        await update.message.reply_text(response)

    app = application_builder().token(token).build()
    app.add_handler(callback_query_handler(route_callback, block=False))
    app.add_handler(command_handler("start", cmd_start))
    app.add_handler(command_handler("help", generic_handler))
    app.add_handler(command_handler("status", generic_handler))
    app.add_handler(command_handler("daily", generic_handler))
    app.add_handler(command_handler("signals", generic_handler))
    app.add_handler(command_handler("recommendations", generic_handler))
    app.add_handler(command_handler("why_down", generic_handler))
    app.add_handler(command_handler("sku", generic_handler))
    app.add_handler(command_handler("economics", generic_handler))
    app.add_handler(command_handler("alerts", generic_handler))
    app.add_handler(command_handler("retro", generic_handler))
    app.add_handler(command_handler("today", generic_handler))
    app.add_handler(command_handler("outcomes", generic_handler))
    app.add_handler(command_handler("outcome", generic_handler))
    app.add_handler(command_handler("top_sku", generic_handler))
    app.add_handler(command_handler("worst_sku", generic_handler))
    app.add_handler(command_handler("learn", generic_handler))
    app.add_handler(command_handler("cogs", generic_handler))
    app.add_handler(command_handler("experiments", generic_handler))
    return app
