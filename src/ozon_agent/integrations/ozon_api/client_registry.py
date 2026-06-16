from __future__ import annotations

from ozon_agent.integrations.ozon_api.clients import (
    AnalyticsClient,
    BaseOzonClient,
    FinanceClient,
    OrdersClient,
    PricesClient,
    ProductsClient,
    ReturnsClient,
    ReviewsClient,
    StocksClient,
)
from ozon_agent.integrations.ozon_api.models import OzonMethodDescriptor

_CLIENT_FACTORIES: dict[str, type[BaseOzonClient]] = {
    "analytics": AnalyticsClient,
    "finance": FinanceClient,
    "orders": OrdersClient,
    "prices": PricesClient,
    "products": ProductsClient,
    "returns": ReturnsClient,
    "reviews": ReviewsClient,
    "stocks": StocksClient,
}


def list_clients() -> list[str]:
    return sorted(_CLIENT_FACTORIES)


def get_client(name: str) -> BaseOzonClient:
    normalized_name = _normalize_client_name(name)
    try:
        return _CLIENT_FACTORIES[normalized_name]()
    except KeyError as exc:
        raise KeyError(f"Ozon API client {name} not found") from exc


def list_methods(client: str | BaseOzonClient) -> list[str]:
    return _coerce_client(client).list_methods()


def get_method(client: str | BaseOzonClient, method: str) -> OzonMethodDescriptor:
    return _coerce_client(client).get_method(method)


def _coerce_client(client: str | BaseOzonClient) -> BaseOzonClient:
    if isinstance(client, BaseOzonClient):
        return client
    return get_client(client)


def _normalize_client_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")
