import json
from unittest.mock import patch

from telegram import InlineKeyboardMarkup

from ozon_agent.cli import (
    TelegramRuntimeConfig,
    _telegram_edit_message,
    _telegram_reply_markup_json,
)
from ozon_agent.telegram.keyboards.common import _btn


def test_telegram_reply_markup_json_serializes_inline_keyboard() -> None:
    markup = InlineKeyboardMarkup([[_btn("Поставки", "supply.show")]])

    payload = _telegram_reply_markup_json(markup)

    assert payload is not None
    data = json.loads(payload)
    assert data["inline_keyboard"][0][0]["text"] == "Поставки"
    assert data["inline_keyboard"][0][0]["callback_data"] == "supply.show"


def test_telegram_edit_message_uses_edit_endpoint() -> None:
    config = TelegramRuntimeConfig(request_timeout=30, retry_attempts=2, retry_backoff_seconds=0)
    with patch("ozon_agent.cli._telegram_api_json") as api_json:
        ok = _telegram_edit_message(
            opener=object(),
            base_url="https://api.telegram.org/botTOKEN",
            chat_id=123,
            message_id=456,
            text="hello",
            config=config,
            reply_markup='{"inline_keyboard": []}',
        )

    assert ok is True
    _, kwargs = api_json.call_args
    assert kwargs["action"] == "editMessageText"
