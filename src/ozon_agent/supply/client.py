from __future__ import annotations

import logging
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.supply.models import (
    Cluster,
    DataSource,
    DraftInfo,
    DraftPayload,
    SupplyOrder,
    Timeslot,
    Warehouse,
)

logger = logging.getLogger(__name__)


class SupplyAPIClient:
    """Client for Ozon Supply API."""

    def __init__(self, ozon_client: OzonClient) -> None:
        self._client = ozon_client

    def list_fbo_warehouses(self) -> list[Warehouse]:
        cities = [
            "Москва",
            "Санкт-Петербург",
            "Казань",
            "Екатеринбург",
            "Новосибирск",
            "Краснодар",
        ]
        all_warehouses: list[dict[str, Any]] = []
        for city in cities:
            try:
                city_response = self._client._post(
                    "/v1/warehouse/fbo/list",
                    {
                        "search": city,
                        "filter_by_supply_type": ["CREATE_TYPE_DIRECT"],
                    },
                )
                result = city_response.get("result", {})
                city_warehouses = (
                    city_response.get("search")
                    or city_response.get("warehouses")
                    or result.get("warehouses")
                    or result.get("search")
                    or []
                )
                all_warehouses.extend(city_warehouses)
            except Exception:
                continue

        warehouses = []
        seen_ids = set()
        for wh_data in all_warehouses:
            warehouse_id = wh_data.get("warehouse_id")
            if warehouse_id in seen_ids:
                continue
            seen_ids.add(warehouse_id)
            warehouses.append(
                Warehouse(
                    warehouse_id=warehouse_id,
                    name=wh_data.get("name", ""),
                    cluster_id=wh_data.get("cluster_id"),
                    cluster_name=wh_data.get("cluster_name"),
                    is_active=wh_data.get("is_active", True),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return warehouses

    def list_clusters(self) -> list[Cluster]:
        response = self._client._post("/v1/cluster/list", {"cluster_type": "CLUSTER_TYPE_OZON"})
        result = response.get("result", {})
        clusters_data = response.get("clusters") or result.get("clusters") or []

        clusters = []
        for cl_data in clusters_data:
            logistic_clusters = cl_data.get("logistic_clusters") or []
            warehouses_count = cl_data.get("warehouses_count")
            if warehouses_count is None and logistic_clusters:
                warehouses_count = len(logistic_clusters[0].get("warehouses", []))
            clusters.append(
                Cluster(
                    cluster_id=str(cl_data.get("cluster_id") or cl_data.get("id") or ""),
                    name=cl_data.get("name", ""),
                    cluster_type=cl_data.get("type", "OZON"),
                    warehouses_count=int(warehouses_count or 0),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return clusters

    def list_supply_orders(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SupplyOrder]:
        payload = {
            "filter": {"states": ["DATA_FILLING", "READY_TO_SUPPLY", "IN_TRANSIT", "COMPLETED"]},
            "limit": limit,
            "offset": offset,
            "sort_by": "ORDER_CREATION",
            "sort_dir": "DESCENDING",
        }
        if status:
            payload["filter"]["states"] = [status]

        response = self._client._post("/v3/supply-order/list", payload)

        orders = []
        for order_data in response.get("result", {}).get("orders", []):
            orders.append(
                SupplyOrder(
                    supply_id=order_data["supply_id"],
                    status=order_data.get("status", "unknown"),
                    warehouse_id=order_data.get("warehouse_id"),
                    items_count=order_data.get("items_count", 0),
                    created_at=order_data.get("created_at"),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return orders

    def get_draft_info(self, draft_id: str) -> DraftInfo:
        response = self._client._post("/v1/draft/create/info", {"draft_id": draft_id})

        result = response.get("result", {})
        return DraftInfo(
            draft_id=draft_id,
            warehouse_id=result.get("warehouse_id"),
            items=result.get("items", []),
            status=result.get("status", "unknown"),
            created_at=result.get("created_at"),
            data_source=DataSource.REAL_DATA,
        )

    def get_timeslots(self, draft_id: str) -> list[Timeslot]:
        response = self._client._post("/v1/draft/timeslot/info", {"draft_id": draft_id})

        timeslots = []
        for ts_data in response.get("result", {}).get("timeslots", []):
            timeslots.append(
                Timeslot(
                    timeslot_id=ts_data["timeslot_id"],
                    date=ts_data.get("date"),
                    time_from=ts_data.get("time_from"),
                    time_to=ts_data.get("time_to"),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return timeslots

    def create_draft(self, payload: DraftPayload) -> dict[str, Any]:
        logger.warning("MUTATION: create_draft called")
        response = self._client._post("/v1/draft/create", payload.to_api_dict())
        draft_id = response.get("result", {}).get("draft_id")
        if not draft_id:
            raise RuntimeError(f"Failed to create draft: {response}")
        return response

    def create_supply_from_draft(self, draft_id: str, timeslot_id: str) -> dict[str, Any]:
        logger.warning("MUTATION: create_supply_from_draft called")
        response = self._client._post(
            "/v1/draft/supply/create",
            {"draft_id": draft_id, "timeslot_id": timeslot_id},
        )
        task_id = response.get("result", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Failed to create supply: {response}")
        return response
