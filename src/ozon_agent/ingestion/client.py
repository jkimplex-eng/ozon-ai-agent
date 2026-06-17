from __future__ import annotations

import os
from typing import Any

import httpx

from ozon_agent.ingestion.endpoints import validate_read_only_path
from ozon_agent.ingestion.models import LiveOzonCredentials

DEFAULT_OZON_SELLER_API_URL = "https://api-seller.ozon.ru"


class LiveOzonCredentialsError(ValueError):
    pass


class LiveOzonReadOnlyClient:
    def __init__(
        self,
        credentials: LiveOzonCredentials,
        *,
        base_url: str = DEFAULT_OZON_SELLER_API_URL,
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not credentials.client_id or not credentials.api_key:
            raise LiveOzonCredentialsError("OZON_CLIENT_ID and OZON_API_KEY are required")
        self.credentials = credentials
        self.base_url = base_url
        self._client = http_client or httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={
                "Client-Id": credentials.client_id,
                "Api-Key": credentials.api_key,
                "Content-Type": "application/json",
            },
        )

    @classmethod
    def from_env(cls) -> LiveOzonReadOnlyClient:
        return cls(
            LiveOzonCredentials(
                client_id=os.environ.get("OZON_CLIENT_ID", ""),
                api_key=os.environ.get("OZON_API_KEY", ""),
            )
        )

    def post_read_only(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        validate_read_only_path(path)
        response = self._client.post(path, json=payload)
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, dict) else {"result": body}

    def close(self) -> None:
        self._client.close()
