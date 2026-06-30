"""Ozon Seller API client."""
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from typing import Any

import httpx


class OzonClient:
    def __init__(
        self,
        client_id: str | None = None,
        api_key: str | None = None,
    ):
        self.client_id = client_id or os.environ.get("OZON_CLIENT_ID", "")
        self.api_key = api_key or os.environ.get("OZON_API_KEY", "")
        self.base_url = "https://api-seller.ozon.ru"
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Client-Id": self.client_id,
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def _post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._client.post(path, json=data or {})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text.strip()
            message = f"{exc}"
            if body:
                message = f"{message} | response={body}"
            raise RuntimeError(message) from exc
        return response.json()  # type: ignore[no-any-return]

    def get_products(self, limit: int = 1000, page: int = 1) -> dict[str, Any]:
        return self._post("/v3/product/list", {
            "filter": {},
            "last_id": "",
            "limit": limit,
        })

    def get_product_info(self, product_ids: list[int]) -> dict[str, Any]:
        return self._post("/v3/product/info/list", {
            "product_id": product_ids,
        })

    def get_product_info_stocks(self, product_ids: list[int]) -> dict[str, Any]:
        return self._post("/v4/product/info/stocks", {
            "filter": {"product_id": product_ids},
            "limit": 100,
        })

    def get_stocks_warehouse(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return self._post("/v1/product/info/stocks-by-warehouse/fbs", {
            "limit": limit,
            "offset": offset,
        })

    def get_orders(
        self,
        date_from: datetime,
        date_to: datetime,
        status: str = "",
        limit: int = 100,
        offset: int = 0,
        scheme: str = "FBO",
    ) -> dict[str, Any]:
        return self._post(f"/v3/posting/{scheme.lower()}/list", {
            "dir": "ASC",
            "filter": {
                "since": date_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": date_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
                **({"status": status} if status else {}),
            },
            "limit": limit,
            "offset": offset,
            "with": {
                "analytics_data": True,
                "financial_data": True,
            },
        })

    def get_finance_orders(
        self,
        date_from: datetime,
        date_to: datetime,
        page: int = 1,
        page_size: int = 1000,
    ) -> dict[str, Any]:
        return self._post("/v1/finance/realization", {
            "date": {
                "from": date_from.strftime("%Y-%m-%dT00:00:00.000Z"),
                "to": date_to.strftime("%Y-%m-%dT23:59:59.999Z"),
            },
            "with_details": True,
            "page": page,
            "page_size": page_size,
        })

    def get_finance_operations(
        self,
        date_from: datetime,
        date_to: datetime,
        page: int = 1,
        page_size: int = 1000,
    ) -> dict[str, Any]:
        return self._post("/v3/finance/transaction/list", {
            "filter": {
                "date": {
                    "from": date_from.strftime("%Y-%m-%dT00:00:00.000Z"),
                    "to": date_to.strftime("%Y-%m-%dT23:59:59.999Z"),
                },
            },
            "page": page,
            "page_size": page_size,
        })

    def get_reviews(
        self,
        product_id: int,
        last_id: str = "",
        limit: int = 100,
    ) -> dict[str, Any]:
        return self._post("/v1/review/list", {
            "filter": {"product_id": product_id},
            "last_id": last_id,
            "limit": limit,
        })

    def close(self) -> None:
        self._client.close()


def create_client() -> OzonClient:
    return OzonClient()

