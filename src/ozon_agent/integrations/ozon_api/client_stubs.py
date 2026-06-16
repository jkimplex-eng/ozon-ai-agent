from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ozon_agent.skills.ozon_api.swagger_models import EndpointNotFoundError, OzonApiEndpoint
from ozon_agent.skills.ozon_api.swagger_registry import list_endpoints


class OzonApiExecutionDisabledError(RuntimeError):
    pass


@dataclass(frozen=True)
class OzonApiRequestStub:
    endpoint_name: str
    method: str
    path: str
    body: dict[str, Any]
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class OzonApiMethodStub:
    name: str
    category: str
    method: str
    path: str
    summary: str
    tags: list[str]
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]

    def prepare_request(self, body: dict[str, Any] | None = None) -> OzonApiRequestStub:
        return OzonApiRequestStub(
            endpoint_name=self.name,
            method=self.method,
            path=self.path,
            body=dict(body or {}),
            request_schema=self.request_schema,
            response_schema=self.response_schema,
        )

    def execute(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        raise OzonApiExecutionDisabledError(
            f"Real Ozon API execution is disabled for typed stub '{self.name}'. "
            "Use prepare_request() for read-only request inspection."
        )


@dataclass(frozen=True)
class OzonApiClientStubs:
    methods: dict[str, OzonApiMethodStub]

    def list_methods(self, category: str | None = None) -> list[OzonApiMethodStub]:
        methods = list(self.methods.values())
        if category is not None:
            normalized_category = category.strip().lower()
            methods = [
                method
                for method in methods
                if method.category.strip().lower() == normalized_category
            ]
        return sorted(methods, key=lambda item: (item.category, item.name, item.method))

    def get_method(self, name: str) -> OzonApiMethodStub:
        try:
            return self.methods[name]
        except KeyError as exc:
            raise EndpointNotFoundError(name) from exc

    def prepare_request(
        self,
        endpoint_name: str,
        body: dict[str, Any] | None = None,
    ) -> OzonApiRequestStub:
        return self.get_method(endpoint_name).prepare_request(body)

    def execute(self, endpoint_name: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.get_method(endpoint_name).execute(body)


def generate_typed_client_stubs() -> OzonApiClientStubs:
    return OzonApiClientStubs(
        methods={endpoint.name: _build_method_stub(endpoint) for endpoint in list_endpoints()}
    )


def _build_method_stub(endpoint: OzonApiEndpoint) -> OzonApiMethodStub:
    return OzonApiMethodStub(
        name=endpoint.name,
        category=endpoint.category.value,
        method=endpoint.method,
        path=endpoint.path,
        summary=endpoint.summary,
        tags=list(endpoint.tags),
        request_schema=dict(endpoint.request_schema),
        response_schema=dict(endpoint.response_schema),
    )
