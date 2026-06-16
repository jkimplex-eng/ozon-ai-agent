from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EndpointCategory(StrEnum):
    PRODUCTS = "Products"
    STOCKS = "Stocks"
    PRICES = "Prices"
    ORDERS = "Orders"
    ANALYTICS = "Analytics"
    FINANCE = "Finance"
    RETURNS = "Returns"
    REVIEWS = "Reviews"
    FBO = "FBO"
    FBS = "FBS"
    OTHER = "Other"


@dataclass(slots=True)
class OzonApiEndpoint:
    name: str
    path: str
    method: str
    summary: str
    description: str
    tags: list[str]
    request_schema: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    category: EndpointCategory = EndpointCategory.OTHER


@dataclass(slots=True)
class SwaggerDocument:
    version: str
    title: str
    description: str
    endpoints: list[OzonApiEndpoint]
    tag_groups: dict[str, list[str]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class SwaggerLoaderError(ValueError):
    pass


class SwaggerValidationError(SwaggerLoaderError):
    pass


class EndpointNotFoundError(LookupError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Endpoint {name} not found")
        self.name = name
