"""Telegram bot for recommendation approvals and business UI."""
from __future__ import annotations

from ozon_agent.telegram.bot import create_app, format_rec_message, handle_message

__all__ = ["create_app", "format_rec_message", "handle_message"]
