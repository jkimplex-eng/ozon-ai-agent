from __future__ import annotations

from collections import defaultdict

from ozon_agent.research.models import (
    MarketplaceComparison,
    PricePosition,
    ResearchObservation,
)


def compare_marketplace(
    own_observations: list[ResearchObservation],
    competitor_observations: list[ResearchObservation],
) -> list[MarketplaceComparison]:
    own_by_sku = _first_by_sku(own_observations)
    competitor_by_sku = _group_by_sku(competitor_observations)
    all_skus = sorted(set(own_by_sku) | set(competitor_by_sku))
    return [
        _compare_sku(sku, own_by_sku.get(sku), competitor_by_sku.get(sku, []))
        for sku in all_skus
    ]


def _compare_sku(
    sku: str,
    own: ResearchObservation | None,
    competitors: list[ResearchObservation],
) -> MarketplaceComparison:
    competitor_prices = [item.price for item in competitors if item.price is not None]
    competitor_ratings = [item.rating for item in competitors if item.rating is not None]
    competitor_reviews = [
        item.review_count for item in competitors if item.review_count is not None
    ]
    avg_price = _average(competitor_prices)
    own_price = own.price if own else None
    return MarketplaceComparison(
        sku=sku,
        product_name=own.product_name if own else "",
        competitor_count=len(competitors),
        own_price=own_price,
        min_competitor_price=min(competitor_prices) if competitor_prices else None,
        avg_competitor_price=avg_price,
        max_competitor_price=max(competitor_prices) if competitor_prices else None,
        price_position=_price_position(own_price, avg_price),
        rating_gap=_gap(own.rating if own else None, _average(competitor_ratings)),
        review_gap=_int_gap(
            own.review_count if own else None,
            int(_average(competitor_reviews) or 0) if competitor_reviews else None,
        ),
        metrics={
            "competitor_urls": [item.source_url for item in competitors if item.source_url],
            "own_available": own.available if own else None,
            "competitor_available_count": sum(1 for item in competitors if item.available is True),
        },
    )


def _first_by_sku(observations: list[ResearchObservation]) -> dict[str, ResearchObservation]:
    result: dict[str, ResearchObservation] = {}
    for observation in observations:
        normalized_sku = observation.normalized_sku()
        if normalized_sku and normalized_sku not in result:
            result[normalized_sku] = observation
    return result


def _group_by_sku(
    observations: list[ResearchObservation],
) -> dict[str, list[ResearchObservation]]:
    result: dict[str, list[ResearchObservation]] = defaultdict(list)
    for observation in observations:
        normalized_sku = observation.normalized_sku()
        if normalized_sku:
            result[normalized_sku].append(observation)
    return dict(result)


def _price_position(own_price: float | None, avg_competitor_price: float | None) -> PricePosition:
    if own_price is None or avg_competitor_price is None or avg_competitor_price <= 0:
        return PricePosition.UNKNOWN
    ratio = own_price / avg_competitor_price
    if ratio >= 1.10:
        return PricePosition.ABOVE_MARKET
    if ratio <= 0.90:
        return PricePosition.BELOW_MARKET
    return PricePosition.MARKET_ALIGNED


def _average(values: list[float] | list[int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _gap(own_value: float | None, market_value: float | None) -> float | None:
    if own_value is None or market_value is None:
        return None
    return own_value - market_value


def _int_gap(own_value: int | None, market_value: int | None) -> int | None:
    if own_value is None or market_value is None:
        return None
    return own_value - market_value
