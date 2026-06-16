from __future__ import annotations

from ozon_agent.research.models import (
    MarketplaceSource,
    MarketplaceSourceType,
    ResearchSourceStatus,
)

_SOURCES: dict[str, MarketplaceSource] = {}


def register_source(source: MarketplaceSource) -> MarketplaceSource:
    _SOURCES[_normalize_name(source.name)] = source
    return source


def unregister_source(name: str) -> None:
    _SOURCES.pop(_normalize_name(name), None)


def list_sources() -> list[MarketplaceSource]:
    if not _SOURCES:
        load_default_sources()
    return sorted(_SOURCES.values(), key=lambda source: source.name)


def get_source(name: str) -> MarketplaceSource:
    if not _SOURCES:
        load_default_sources()
    try:
        return _SOURCES[_normalize_name(name)]
    except KeyError as exc:
        raise KeyError(f"Marketplace research source {name} not found") from exc


def source_exists(name: str) -> bool:
    if not _SOURCES:
        load_default_sources()
    return _normalize_name(name) in _SOURCES


def reload_sources() -> list[MarketplaceSource]:
    _SOURCES.clear()
    return load_default_sources()


def load_default_sources() -> list[MarketplaceSource]:
    defaults = [
        MarketplaceSource(
            name="manual",
            source_type=MarketplaceSourceType.MANUAL,
            status=ResearchSourceStatus.ACTIVE,
            description="Manual or fixture observations supplied to the research engine.",
        ),
        MarketplaceSource(
            name="ozon_search",
            source_type=MarketplaceSourceType.OZON_SEARCH,
            status=ResearchSourceStatus.PLANNED,
            description="Future read-only Ozon search page capture source.",
            requires_network=True,
        ),
        MarketplaceSource(
            name="ozon_product_page",
            source_type=MarketplaceSourceType.OZON_PRODUCT_PAGE,
            status=ResearchSourceStatus.PLANNED,
            description="Future read-only Ozon product page capture source.",
            requires_network=True,
        ),
        MarketplaceSource(
            name="firecrawl",
            source_type=MarketplaceSourceType.FIRECRAWL,
            status=ResearchSourceStatus.PLANNED,
            description="Future Firecrawl-backed marketplace page extraction source.",
            requires_network=True,
        ),
    ]
    for source in defaults:
        register_source(source)
    return list_sources()


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")
