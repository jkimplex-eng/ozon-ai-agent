from __future__ import annotations

from typing import Any

from ozon_agent.integrations.ozon_api.models import (
    OzonEndpointMetadata,
    OzonMethodDescriptor,
    endpoint_name_to_method_name,
)
from ozon_agent.skills.ozon_api.swagger_models import EndpointCategory, EndpointNotFoundError
from ozon_agent.skills.ozon_api.swagger_registry import list_endpoints


class BaseOzonClient:
    category: EndpointCategory

    def __init__(self) -> None:
        self.endpoint_metadata = self._load_endpoint_metadata()
        self.request_schemas = {
            name: descriptor.metadata.request_schema
            for name, descriptor in self.endpoint_metadata.items()
        }
        self.response_schemas = {
            name: descriptor.metadata.response_schema
            for name, descriptor in self.endpoint_metadata.items()
        }

    def list_methods(self) -> list[str]:
        return sorted(self.endpoint_metadata)

    def get_method(self, method_name: str) -> OzonMethodDescriptor:
        normalized_name = endpoint_name_to_method_name(method_name)
        exact_match = self.endpoint_metadata.get(normalized_name)
        if exact_match is not None:
            return exact_match
        prefix_matches = [
            (candidate_name, descriptor)
            for candidate_name, descriptor in self.endpoint_metadata.items()
            if candidate_name.startswith(f"{normalized_name}_")
        ]
        if prefix_matches:
            return sorted(prefix_matches, key=lambda item: (len(item[0]), item[0]))[0][1]
        raise EndpointNotFoundError(method_name)

    def describe_method(self, method_name: str) -> dict[str, Any]:
        return self.get_method(method_name).describe()

    def __getattr__(self, name: str) -> OzonMethodDescriptor:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.get_method(name)
        except EndpointNotFoundError as exc:
            raise AttributeError(name) from exc

    def _load_endpoint_metadata(self) -> dict[str, OzonMethodDescriptor]:
        descriptors: dict[str, OzonMethodDescriptor] = {}
        for endpoint in list_endpoints():
            if endpoint.category is not self.category:
                continue
            method_name = endpoint_name_to_method_name(endpoint.name)
            descriptors[method_name] = OzonMethodDescriptor(
                metadata=OzonEndpointMetadata(
                    name=endpoint.name,
                    method_name=method_name,
                    path=endpoint.path,
                    http_method=endpoint.method,
                    summary=endpoint.summary,
                    description=endpoint.description,
                    tags=list(endpoint.tags),
                    category=endpoint.category.value,
                    request_schema=dict(endpoint.request_schema),
                    response_schema=dict(endpoint.response_schema),
                )
            )
        return dict(sorted(descriptors.items()))
