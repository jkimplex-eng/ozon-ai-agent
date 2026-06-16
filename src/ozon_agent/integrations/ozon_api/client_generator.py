from __future__ import annotations

from typing import Any

from ozon_agent.skills.ozon_api.swagger_registry import list_endpoints


def generate_client_blueprint() -> dict[str, Any]:
    return {
        "client_name": "ozon_api_client",
        "request_execution": "disabled",
        "endpoint_count": len(list_endpoints()),
        "modules": [
            "products",
            "stocks",
            "prices",
            "orders",
            "analytics",
            "finance",
            "returns",
            "reviews",
            "fbo",
            "fbs",
        ],
    }
