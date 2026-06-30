from __future__ import annotations

import logging
from datetime import date, timedelta
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
        warehouse_clusters = self._warehouse_cluster_map()
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
            warehouse_id = int(wh_data.get("warehouse_id") or 0)
            if warehouse_id in seen_ids or warehouse_id <= 0:
                continue
            seen_ids.add(warehouse_id)
            cluster_info = warehouse_clusters.get(warehouse_id, {})
            warehouses.append(
                Warehouse(
                    warehouse_id=warehouse_id,
                    name=wh_data.get("name", ""),
                    cluster_id=str(cluster_info.get("macrolocal_cluster_id") or "") or None,
                    cluster_name=cluster_info.get("cluster_name"),
                    is_active=wh_data.get("is_active", True),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return warehouses

    def list_clusters(self) -> list[Cluster]:
        clusters_data = self._cluster_rows()
        clusters = []
        for cl_data in clusters_data:
            logistic_clusters = cl_data.get("logistic_clusters") or []
            warehouses_count = cl_data.get("warehouses_count")
            if warehouses_count is None:
                warehouses_count = sum(len(item.get("warehouses", [])) for item in logistic_clusters)
            clusters.append(
                Cluster(
                    cluster_id=str(
                        cl_data.get("macrolocal_cluster_id")
                        or cl_data.get("cluster_id")
                        or cl_data.get("id")
                        or ""
                    ),
                    name=cl_data.get("name", ""),
                    cluster_type=cl_data.get("type", "OZON"),
                    warehouses_count=int(warehouses_count or 0),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return clusters

    def resolve_cluster_for_warehouse(self, warehouse_id: int) -> tuple[str, str] | None:
        cluster = self._warehouse_cluster_map().get(int(warehouse_id))
        if not cluster:
            return None
        return str(cluster["macrolocal_cluster_id"]), str(cluster["cluster_name"])

    def list_supply_orders(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SupplyOrder]:
        states = [
            status,
        ] if status else [
            "DATA_FILLING",
            "READY_TO_SUPPLY",
            "ACCEPTED_AT_SUPPLY_WAREHOUSE",
            "IN_TRANSIT",
            "ACCEPTANCE_AT_STORAGE_WAREHOUSE",
            "REPORTS_CONFIRMATION_AWAITING",
            "REPORT_REJECTED",
            "COMPLETED",
            "REJECTED_AT_SUPPLY_WAREHOUSE",
            "CANCELLED",
            "OVERDUE",
        ]
        payload = {
            "filter": {"states": states},
            "limit": limit,
            "sort_by": "ORDER_CREATION",
            "sort_dir": "DESC",
        }
        if offset:
            payload["last_id"] = str(offset)

        response = self._client._post("/v3/supply-order/list", payload)
        order_ids = response.get("order_ids") or response.get("result", {}).get("order_ids") or []
        if not order_ids:
            return []

        details = self._client._post("/v3/supply-order/get", {"order_ids": order_ids})
        orders = []
        for order_data in details.get("orders", []):
            supplies = order_data.get("supplies") or []
            first_supply = supplies[0] if supplies else {}
            storage_warehouse = first_supply.get("storage_warehouse") or {}
            orders.append(
                SupplyOrder(
                    supply_id=str(order_data.get("order_id") or ""),
                    status=str(order_data.get("state") or "unknown"),
                    warehouse_id=storage_warehouse.get("warehouse_id"),
                    items_count=len(supplies),
                    created_at=order_data.get("created_date"),
                    data_source=DataSource.REAL_DATA,
                )
            )

        return orders

    def get_draft_info(self, draft_id: str) -> DraftInfo:
        response = self._client._post("/v2/draft/create/info", {"draft_id": int(draft_id)})
        clusters = response.get("clusters") or []
        first_warehouse = None
        for cluster in clusters:
            for warehouse in cluster.get("warehouses", []):
                if warehouse.get("availability_status", {}).get("state") == "FULL_AVAILABLE":
                    first_warehouse = warehouse.get("storage_warehouse") or {}
                    break
            if first_warehouse:
                break

        return DraftInfo(
            draft_id=str(response.get("draft_id") or draft_id),
            warehouse_id=(first_warehouse or {}).get("warehouse_id"),
            warehouse_name=(first_warehouse or {}).get("name"),
            items=[],
            status=str(response.get("status") or "unknown"),
            created_at=None,
            data_source=DataSource.REAL_DATA,
        )

    def get_timeslots(
        self,
        draft_id: str,
        cluster_id: str | None = None,
        warehouse_id: int | None = None,
        supply_order_id: str | None = None,
    ) -> list[Timeslot]:
        if supply_order_id:
            response = self._client._post(
                "/v1/supply-order/timeslot/get",
                {"supply_order_id": int(supply_order_id)},
            )
            timezone = response.get("timezone", {}).get("iana_name")
            timeslots = []
            for ts_data in response.get("timeslots", []):
                start = str(ts_data.get("from") or ts_data.get("from_in_timezone") or "")
                end = str(ts_data.get("to") or ts_data.get("to_in_timezone") or "")
                timeslots.append(_timeslot_from_bounds(start, end, timezone))
            return timeslots

        if not cluster_id or not warehouse_id:
            raise ValueError("cluster_id and warehouse_id are required to read draft timeslots")

        today = date.today()
        response = self._client._post(
            "/v2/draft/timeslot/info",
            {
                "draft_id": int(draft_id),
                "date_from": today.isoformat(),
                "date_to": (today + timedelta(days=14)).isoformat(),
                "selected_cluster_warehouses": [
                    {
                        "macrolocal_cluster_id": int(cluster_id),
                        "storage_warehouse_id": int(warehouse_id),
                    }
                ],
            },
        )
        timeslots = []
        for ts_data in response.get("timeslots", []):
            start = str(ts_data.get("from") or ts_data.get("from_in_timezone") or "")
            end = str(ts_data.get("to") or ts_data.get("to_in_timezone") or "")
            timeslots.append(_timeslot_from_bounds(start, end))
        return timeslots

    def create_draft(self, payload: DraftPayload) -> dict[str, Any]:
        logger.warning("MUTATION: create_draft called")
        response = self._client._post("/v1/draft/direct/create", payload.to_api_dict())
        draft_id = response.get("draft_id") or response.get("result", {}).get("draft_id")
        if not draft_id:
            raise RuntimeError(f"Failed to create draft: {response}")
        return response

    def create_supply_from_draft(self, draft_id: str, cluster_id: str, warehouse_id: int) -> dict[str, Any]:
        logger.warning("MUTATION: create_supply_from_draft called")
        response = self._client._post(
            "/v2/draft/supply/create",
            {
                "draft_id": int(draft_id),
                "supply_type": "DIRECT",
                "selected_cluster_warehouses": [
                    {
                        "macrolocal_cluster_id": int(cluster_id),
                        "storage_warehouse_id": int(warehouse_id),
                    }
                ],
            },
        )
        return response

    def get_supply_create_status(self, draft_id: str) -> dict[str, Any]:
        return self._client._post("/v2/draft/supply/create/status", {"draft_id": int(draft_id)})

    def reserve_supply_timeslot(self, supply_order_id: str, timeslot_id: str) -> dict[str, Any]:
        logger.warning("MUTATION: reserve_supply_timeslot called")
        time_from, time_to = _parse_timeslot_id(timeslot_id)
        return self._client._post(
            "/v1/supply-order/timeslot/update",
            {
                "supply_order_id": int(supply_order_id),
                "timeslot": {
                    "from": time_from,
                    "to": time_to,
                },
            },
        )

    def get_supply_timeslot_status(self, operation_id: str) -> dict[str, Any]:
        return self._client._post(
            "/v1/supply-order/timeslot/status",
            {"operation_id": operation_id},
        )

    def _cluster_rows(self) -> list[dict[str, Any]]:
        response = self._client._post("/v1/cluster/list", {"cluster_type": "CLUSTER_TYPE_OZON"})
        result = response.get("result", {})
        return response.get("clusters") or result.get("clusters") or []

    def _warehouse_cluster_map(self) -> dict[int, dict[str, Any]]:
        mapping: dict[int, dict[str, Any]] = {}
        for cluster in self._cluster_rows():
            cluster_id = cluster.get("macrolocal_cluster_id") or cluster.get("id") or cluster.get("cluster_id")
            cluster_name = cluster.get("name") or ""
            for logistic_cluster in cluster.get("logistic_clusters", []):
                for warehouse in logistic_cluster.get("warehouses", []):
                    warehouse_id = int(warehouse.get("warehouse_id") or 0)
                    if warehouse_id <= 0:
                        continue
                    mapping[warehouse_id] = {
                        "macrolocal_cluster_id": int(cluster_id),
                        "cluster_name": cluster_name,
                    }
        return mapping


def _timeslot_from_bounds(time_from: str, time_to: str, timezone: str | None = None) -> Timeslot:
    date_value = time_from.split("T", 1)[0] if time_from else None
    identifier = f"{time_from}|{time_to}"
    if timezone:
        identifier = f"{identifier}|{timezone}"
    return Timeslot(
        timeslot_id=identifier,
        date=date_value,
        time_from=time_from,
        time_to=time_to,
        data_source=DataSource.REAL_DATA,
    )


def _parse_timeslot_id(timeslot_id: str) -> tuple[str, str]:
    parts = str(timeslot_id).split("|")
    if len(parts) < 2:
        raise ValueError(f"Invalid timeslot_id: {timeslot_id}")
    return parts[0], parts[1]



