"""Tests for telegram/callbacks/router.py."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from ozon_agent.telegram.callbacks.router import _parse_callback_data, route_callback, _HANDLERS


def test_parse_callback_data():
    ns, action, params = _parse_callback_data("today.show")
    assert ns == "today"
    assert action == "show"
    assert params == []


def test_parse_callback_data_with_params():
    ns, action, params = _parse_callback_data("rec.approve|abc123")
    assert ns == "rec"
    assert action == "approve"
    assert params == ["abc123"]


def test_parse_callback_data_noop():
    ns, action, params = _parse_callback_data("noop")
    assert ns == "noop"
    assert action == ""
    assert params == []


def test_parse_callback_data_multi_params():
    ns, action, params = _parse_callback_data("test.action|arg1|arg2")
    assert ns == "test"
    assert action == "action"
    assert params == ["arg1", "arg2"]


@pytest.mark.asyncio
async def test_route_callback_noop():
    query = MagicMock()
    query.data = "noop"
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    context = MagicMock()
    await route_callback(update, context)
    query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_route_callback_unknown_namespace():
    query = MagicMock()
    query.data = "unknown.action"
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    context = MagicMock()
    await route_callback(update, context)
    query.answer.assert_called_once()
    query.edit_message_text.assert_not_called()


@pytest.mark.asyncio
async def test_route_callback_handler_error():
    _HANDLERS["test_error"] = AsyncMock(side_effect=RuntimeError("test"))
    query = MagicMock()
    query.data = "test_error.fail"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    context = MagicMock()
    await route_callback(update, context)
    query.edit_message_text.assert_called()
    assert "Ошибка" in str(query.edit_message_text.call_args)
    del _HANDLERS["test_error"]


def test_all_namespaces_registered():
    from ozon_agent.telegram.callbacks import (  # noqa: F401
        main_menu_cb, today_cb, business_cb, logistics_cb, ads_cb,
        finance_cb, risks_cb, tasks_cb, experiments_cb, system_cb,
        store_cb, quick_cb, rec_cb, owner_cb,
    )
    expected = {
        "main", "today", "business", "logistics", "ads",
        "finance", "risks", "tasks", "experiments", "system",
        "store", "quick", "rec", "owner",
    }
    assert expected.issubset(set(_HANDLERS.keys()))
