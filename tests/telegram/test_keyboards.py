"""Tests for telegram/keyboards/."""
from __future__ import annotations

from ozon_agent.telegram.keyboards.common import (
    back_button,
    back_to_menu,
    confirm_cancel_row,
    noop_button,
    pagination_row,
)
from ozon_agent.telegram.keyboards.main_menu import main_menu_keyboard
from ozon_agent.telegram.keyboards.rec_kb import rec_keyboard
from ozon_agent.telegram.keyboards.owner_kb import owner_keyboard


def test_back_to_menu():
    row = back_to_menu()
    assert len(row) == 1
    assert row[0].text == "🏠 Главная"
    assert row[0].callback_data == "main.menu"


def test_back_button():
    row = back_button("today.show")
    assert len(row) == 1
    assert row[0].text == "⬅️ Назад"
    assert row[0].callback_data == "today.show"


def test_confirm_cancel_row():
    row = confirm_cancel_row("yes|123", "no|123")
    assert len(row) == 2
    assert row[0].callback_data == "yes|123"
    assert row[1].callback_data == "no|123"


def test_pagination_row_first_page():
    row = pagination_row(0, 5, "items")
    assert len(row) == 2  # page indicator + next
    assert row[0].callback_data == "noop"  # page indicator


def test_pagination_row_middle():
    row = pagination_row(2, 5, "items")
    assert len(row) == 3  # prev + page indicator + next


def test_pagination_row_last_page():
    row = pagination_row(4, 5, "items")
    assert len(row) == 2  # prev + page indicator


def test_noop_button():
    btn = noop_button("Page 1")
    assert btn.text == "Page 1"
    assert btn.callback_data == "noop"


def test_main_menu_keyboard():
    kb = main_menu_keyboard()
    assert len(kb.inline_keyboard) == 5  # 5 rows
    total_buttons = sum(len(row) for row in kb.inline_keyboard)
    assert total_buttons == 10  # 10 buttons total


def test_main_menu_callback_data():
    kb = main_menu_keyboard()
    all_data = []
    for row in kb.inline_keyboard:
        for btn in row:
            all_data.append(btn.callback_data)
    assert "today.show" in all_data
    assert "business.show" in all_data
    assert "logistics.show" in all_data
    assert "ads.show" in all_data
    assert "finance.show" in all_data
    assert "risks.show" in all_data
    assert "tasks.show" in all_data
    assert "experiments.show" in all_data
    assert "system.show" in all_data
    assert "store.show" in all_data


def test_rec_keyboard():
    kb = rec_keyboard("test-id")
    assert len(kb.inline_keyboard) == 3  # approve/later, reject/why, back
    all_data = []
    for row in kb.inline_keyboard:
        for btn in row:
            all_data.append(btn.callback_data)
    assert "rec.approve|test-id" in all_data
    assert "rec.reject|test-id" in all_data
    assert "rec.why|test-id" in all_data
    assert "rec.later|test-id" in all_data
    assert "main.menu" in all_data


def test_owner_keyboard():
    kb = owner_keyboard("test-id")
    assert len(kb.inline_keyboard) == 2  # approve, back
    assert "main.menu" in [
        btn.callback_data
        for row in kb.inline_keyboard
        for btn in row
    ]
