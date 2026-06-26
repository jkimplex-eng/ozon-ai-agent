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
