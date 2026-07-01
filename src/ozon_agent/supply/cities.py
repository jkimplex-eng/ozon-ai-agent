from __future__ import annotations

from typing import Any

_CITY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Москва", ("москва", "moscow")),
    ("Санкт-Петербург", ("санкт", "петербург", "saint petersburg", "st petersburg", "szo")),
    ("Казань", ("казань", "kazan")),
    ("Екатеринбург", ("екатеринбург", "yekaterinburg", "ekaterinburg")),
    ("Новосибирск", ("новосибирск", "novosibirsk")),
    ("Краснодар", ("краснодар", "krasnodar")),
)

_KNOWN_CITIES = {city for city, _patterns in _CITY_PATTERNS}
_DEFAULT_DEMAND_CITY = "Москва"

_DEFECT_TOKENS = ("возврат", "return", "негабарит", "oversize", "ювелир", "jewelry", "аптека", "pharmacy")


def canonical_supply_city(*values: Any) -> str:
    text = " ".join(str(value or "").strip() for value in values if value).strip()
    if not text:
        return "Unknown"

    lowered = text.casefold()
    for city, patterns in _CITY_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            return city

    return text


def supply_city_from_order_destination(*values: Any) -> str:
    city = canonical_supply_city(*values)
    if city in _KNOWN_CITIES:
        return city
    return _DEFAULT_DEMAND_CITY


def warehouse_priority(name: str, cluster_id: str | None = None) -> tuple[int, str]:
    lowered = str(name or "").casefold()
    score = 0
    if cluster_id:
        score += 100
    if "новый" in lowered or "new" in lowered:
        score += 10
    if "рфц" in lowered:
        score += 5
    for token in _DEFECT_TOKENS:
        if token in lowered:
            score -= 25
    return score, str(name or "")



def is_test_entity(*values: Any) -> bool:
    for value in values:
        lowered = str(value or "").strip().casefold()
        if not lowered:
            continue
        if lowered.startswith("test-sku") or lowered.startswith("test-offer"):
            return True
        if lowered.startswith("test_") or lowered.startswith("test-"):
            return True
        if lowered.startswith("тест_") or lowered.startswith("тест-"):
            return True
    return False
