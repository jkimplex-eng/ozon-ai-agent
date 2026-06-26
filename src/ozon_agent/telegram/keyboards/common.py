"""Shared keyboard utilities — back, home, pagination, confirm/cancel."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import InlineKeyboardButton


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    from telegram import InlineKeyboardButton
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def noop_button(text: str) -> InlineKeyboardButton:
    return _btn(text, "noop")


def back_button(callback_data: str) -> list[InlineKeyboardButton]:
    return [_btn("⬅️ Назад", callback_data)]


def back_to_menu() -> list[InlineKeyboardButton]:
    return [_btn("🏠 Главная", "main.menu")]


def confirm_cancel_row(
    confirm_data: str,
    cancel_data: str,
    confirm_text: str = "✅ Выполнить",
    cancel_text: str = "❌ Отмена",
) -> list[InlineKeyboardButton]:
    return [_btn(confirm_text, confirm_data), _btn(cancel_text, cancel_data)]


def pagination_row(
    page: int,
    total_pages: int,
    namespace: str,
    **extra_args: str,
) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    extra = "|".join(f"{k}={v}" for k, v in extra_args.items())
    suffix = f"|{extra}" if extra else ""
    if page > 0:
        buttons.append(_btn("◀️", f"{namespace}.page|{page - 1}{suffix}"))
    buttons.append(_btn(f"{page + 1}/{total_pages}", "noop"))
    if page < total_pages - 1:
        buttons.append(_btn("▶️", f"{namespace}.page|{page + 1}{suffix}"))
    return buttons
