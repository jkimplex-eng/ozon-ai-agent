"""Callback query router — single entry point, namespace-based dispatch."""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_HANDLERS: dict[str, Callable] = {}


def register(namespace: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        _HANDLERS[namespace] = fn
        return fn
    return decorator


def _parse_callback_data(data: str) -> tuple[str, str, list[str]]:
    namespace, _, rest = data.partition(".")
    action, _, params_str = rest.partition("|")
    params = params_str.split("|") if params_str else []
    return namespace, action, params


async def route_callback(update: Any, context: Any) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    if query.data == "noop":
        return

    namespace, action, params = _parse_callback_data(query.data)
    handler = _HANDLERS.get(namespace)

    if handler is None:
        logger.warning("Unknown callback namespace: %s", namespace)
        return

    try:
        await handler(query, context, action, params)
    except Exception as exc:
        logger.exception("Callback handler error: %s.%s", namespace, action)
        try:
            await query.edit_message_text(f"❌ Ошибка: {exc}")
        except Exception:
            pass


class _SyncQuery:
    """Mock CallbackQuery that captures text for urllib polling."""
    def __init__(self) -> None:
        self._text: str = ""
        self._reply_markup: Any = None

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, reply_markup: Any = None) -> None:
        self._text = text
        self._reply_markup = reply_markup

    @property
    def text(self) -> str:
        return self._text

    @property
    def reply_markup(self) -> Any:
        return self._reply_markup

    @property
    def data(self) -> str:
        return ""


def route_callback_payload(data: str) -> tuple[str | None, Any | None]:
    """Synchronous callback dispatch for urllib polling.

    Returns a tuple of (text, reply_markup) captured from the callback.
    """
    if data == "noop":
        return None, None

    namespace, action, params = _parse_callback_data(data)
    handler = _HANDLERS.get(namespace)

    if handler is None:
        logger.warning("Unknown callback namespace: %s", namespace)
        return None, None

    try:
        mock_query = _SyncQuery()
        result = handler(mock_query, None, action, params)
        if hasattr(result, "__await__"):
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(result)
            finally:
                loop.close()
        return (mock_query.text if mock_query.text else None, mock_query.reply_markup)
    except Exception as exc:
        logger.exception("Callback handler error: %s.%s", namespace, action)
        return f"❌ Ошибка: {exc}", None


def route_callback_data(data: str) -> str | None:
    """Backward-compatible text-only callback dispatch."""
    text, _reply_markup = route_callback_payload(data)
    return text
