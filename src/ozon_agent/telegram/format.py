"""Telegram message formatting helpers."""
from __future__ import annotations

from typing import Any


def rub(value: float | int | None) -> str:
    if value is None:
        return "0 ₽"
    v = float(value)
    if v < 0:
        return f"-{abs(v):,.0f} ₽".replace(",", " ")
    return f"{v:,.0f} ₽".replace(",", " ")


def pct(value: float | int | None) -> str:
    if value is None:
        return "0.0%"
    return f"{float(value):.1f}%"


def divider() -> str:
    return "━━━━━━━━━━━━━━━━━━"


def no_data_message(section: str = "") -> str:
    if section:
        return f"📭 Нет данных: {section}"
    return "📭 Нет данных"


def safe_str(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s else fallback


def severity_emoji(severity: str) -> str:
    s = severity.upper()
    if s in ("HIGH", "CRITICAL"):
        return "🔴"
    if s == "MEDIUM":
        return "🟡"
    if s in ("LOW", "INFO"):
        return "🟢"
    return "⚪"


_SIGNAL_TYPE_LABELS: dict[str, str] = {
    "MARGIN_DECLINE": "Падение маржи",
    "CTR_DECLINE": "Падение CTR",
    "CVR_DECLINE": "Падение конверсии",
    "REVENUE_DECLINE": "Падение выручки",
    "ORDER_DECLINE": "Падение заказов",
    "DRR_HIGH": "Высокий ДРР",
    "STOCK_LOW": "Мало остатков",
    "STOCKOUT": "Товар закончился",
    "RETURN_HIGH": "Много возвратов",
    "REVIEW_DROP": "Падение отзывов",
    "PRICE_UNDERCUT": "Демпинг конкурентов",
    "AD_SPEND_HIGH": "Перерасход рекламы",
    "BUYOUT_LOW": "Низкий выкуп",
    "LOGISTICS_ISSUE": "Проблема логистики",
}

_SIGNAL_CAUSES: dict[str, str] = {
    "MARGIN_DECLINE": "Себестоимость выросла или цена упала",
    "CTR_DECLINE": "Фото или заголовок хуже конкурентов",
    "CVR_DECLINE": "Карточка или цена не убеждает",
    "REVENUE_DECLINE": "Снижение спроса или видимости",
    "ORDER_DECLINE": "Меньше заказов — проверить рекламу и позиции",
    "DRR_HIGH": "Реклама не окупается",
    "STOCK_LOW": "Запасы на исходе, нужна поставка",
    "STOCKOUT": "Товар отсутствует на складе",
    "RETURN_HIGH": "Качество или описание не соответствует",
    "REVIEW_DROP": "Проблемы с товаром или обслуживанием",
    "PRICE_UNDERCUT": "Конкуренты снизили цену",
    "AD_SPEND_HIGH": "Бюджет превышает норму",
    "BUYOUT_LOW": "Много отказов после доставки",
    "LOGISTICS_ISSUE": "Задержки или потери на складе",
}

_SIGNAL_CHECKLISTS: dict[str, list[str]] = {
    "MARGIN_DECLINE": ["проверить себестоимость", "проверить цену", "пересчитать логистику"],
    "CTR_DECLINE": ["обновить фото", "проверить заголовок", "сравнить с конкурентами"],
    "CVR_DECLINE": ["проверить описание", "проверить цену", "проверить отзывы"],
    "REVENUE_DECLINE": ["проверить рекламу", "проверить остатки", "проверить карточку"],
    "ORDER_DECLINE": ["проверить наличие", "проверить рекламу", "проверить цену"],
    "DRR_HIGH": ["приостановить неэффективные кампании", "проверить ставки", "проверить запросы"],
    "STOCK_LOW": ["оформить поставку", "проверить прогноз", "проверить логистику"],
    "STOCKOUT": ["срочная поставка", "приостановить рекламу", "проверить альтернативы"],
    "RETURN_HIGH": ["проверить качество", "обновить описание", "проверить фото"],
    "REVIEW_DROP": ["проверить жалобы", "улучшить упаковку", "проверить описание"],
    "PRICE_UNDERCUT": ["сравнить цены", "проверить акции", "оценить маржу"],
    "AD_SPEND_HIGH": ["проверить ставки", "приостановить слабые кампании", "проверить минус-слова"],
    "BUYOUT_LOW": ["проверить описание", "проверить фото", "проверить цену"],
    "LOGISTICS_ISSUE": ["проверить склад", "проверить трекинг", "связаться с поддержкой"],
}

_PROBLEM_LABELS: dict[str, str] = {
    "low_margin": "Низкая маржа",
    "high_drr": "Высокий ДРР",
    "low_ctr": "Низкий CTR",
    "low_cvr": "Низкая конверсия",
    "declining_orders": "Падение заказов",
    "stock_low": "Мало остатков",
    "high_returns": "Много возвратов",
    "price_undercut": "Демпинг конкурентов",
}

_RETRO_ACTION_LABELS: dict[str, str] = {
    "pause_campaign": "Остановить кампанию",
    "reduce_budget": "Снизить бюджет",
    "increase_budget": "Увеличить бюджет",
    "update_photo": "Обновить фото",
    "update_title": "Обновить заголовок",
    "update_description": "Обновить описание",
    "adjust_price": "Скорректировать цену",
    "reorder_stock": "Оформить поставку",
    "fix_card": "Исправить карточку",
    "launch_campaign": "Запустить кампанию",
}


def signal_type_business(signal_type: str) -> str:
    return _SIGNAL_TYPE_LABELS.get(signal_type, signal_type or "Неизвестно")


def signal_cause(signal_type: str) -> str:
    return _SIGNAL_CAUSES.get(signal_type, "требуется анализ")


def signal_checklist(signal_type: str) -> list[str]:
    return _SIGNAL_CHECKLISTS.get(signal_type, ["проверить карточку", "проверить цену", "проверить рекламу"])


def problem_business(problem: str) -> str:
    p = problem.lower()
    for key, label in _PROBLEM_LABELS.items():
        if key in p:
            return label
    return problem or "Проблема"


def retro_action_business(action: str) -> str:
    return _RETRO_ACTION_LABELS.get(action, action or "Действие")
