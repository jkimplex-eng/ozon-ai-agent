"""FBO demand planning by city."""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.db.connection import execute_query
from ozon_agent.supply.cities import (
    canonical_supply_city,
    is_test_entity,
    supply_city_from_order_destination,
    warehouse_priority,
)
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.models import Warehouse

DEFAULT_HORIZONS = (30, 60, 90)
DATA_ROOT = Path("data")
ANALYTICS_DATA_PATH = DATA_ROOT / "analytics" / "analytics_data.json"
WAREHOUSE_STOCKS_PATH = DATA_ROOT / "stocks" / "warehouse_stocks.json"
CURRENT_STOCKS_PATH = DATA_ROOT / "stocks" / "current_stocks.json"


@dataclass(frozen=True)
class FboDemandPlan:
    """Demand forecast and replenishment recommendation for one SKU in one city."""

    sku: str
    offer_id: str
    product_name: str
    cluster_id: str
    cluster_name: str
    warehouse_id: int
    warehouse_name: str
    avg_daily_sales: float
    cluster_share: float
    current_stock: int
    stock_days: float | None
    demand_30: int
    demand_60: int
    demand_90: int
    recommended_30: int
    recommended_60: int
    recommended_90: int
    city_sales: int
    planning_mode: str
    confidence: float
    data_sources: list[str]
    data_quality_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "offer_id": self.offer_id,
            "product_name": self.product_name,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse_name,
            "avg_daily_sales": self.avg_daily_sales,
            "cluster_share": self.cluster_share,
            "current_stock": self.current_stock,
            "stock_days": self.stock_days,
            "demand_30": self.demand_30,
            "demand_60": self.demand_60,
            "demand_90": self.demand_90,
            "recommended_30": self.recommended_30,
            "recommended_60": self.recommended_60,
            "recommended_90": self.recommended_90,
            "city_sales": self.city_sales,
            "planning_mode": self.planning_mode,
            "confidence": self.confidence,
            "data_sources": self.data_sources,
            "data_quality_note": self.data_quality_note,
        }


class FboPlanningEngine:
    """Calculate FBO demand for 30/60/90 days across city groups."""

    def __init__(self, client: OzonClient) -> None:
        self._client = client
        self._supply_client = SupplyAPIClient(client)

    def generate_cluster_demand(
        self,
        skus: list[str] | None = None,
        max_rows: int = 100,
        lookback_days: int = 90,
    ) -> list[FboDemandPlan]:
        warehouses = [wh for wh in self._supply_client.list_fbo_warehouses() if wh.is_active]
        if not warehouses:
            return []

        product_rows = _load_product_sales(skus=skus, lookback_days=lookback_days, limit=max_rows)
        if not product_rows:
            return []

        stock_rows = _load_stock_by_warehouse(skus=[str(row["sku"]) for row in product_rows])
        return build_fbo_demand_plans(product_rows, stock_rows, warehouses, max_rows=max_rows)


def build_fbo_demand_plans(
    product_rows: list[dict[str, Any]],
    stock_rows: list[dict[str, Any]],
    warehouses: list[Warehouse],
    max_rows: int = 100,
) -> list[FboDemandPlan]:
    stock_index = _index_stock_by_city(stock_rows)
    city_targets = _city_targets(warehouses)
    if not city_targets:
        return []

    plans: list[FboDemandPlan] = []
    for product in product_rows:
        sku = str(product.get("sku") or "")
        total_sales = float(product.get("total_sales") or 0)
        days_with_sales = int(product.get("days_with_sales") or 0)
        offer_id = str(product.get("offer_id") or "")
        product_name = str(product.get("name") or product.get("product_name") or "")
        if not sku or total_sales <= 0 or days_with_sales <= 0 or is_test_entity(sku, offer_id, product_name):
            continue

        history_days = max(1, int(product.get("history_days") or days_with_sales or 1))
        avg_daily_sales = total_sales / history_days
        shares, planning_mode, city_sales_map = _resolve_city_shares(product, city_targets, stock_index)
        if not shares:
            continue

        for city_name, warehouse in city_targets.items():
            share = shares.get(city_name, 0.0)
            if share <= 0:
                continue

            current_stock = stock_index.get((sku, city_name), 0)
            plans.append(
                _build_one_plan(
                    product=product,
                    warehouse=warehouse,
                    city_name=city_name,
                    avg_daily_sales=avg_daily_sales,
                    cluster_share=share,
                    current_stock=current_stock,
                    days_with_sales=days_with_sales,
                    total_sales=total_sales,
                    city_sales=int(city_sales_map.get(city_name, 0)),
                    planning_mode=planning_mode,
                )
            )

    return sorted(plans, key=lambda item: (-item.recommended_30, item.sku, item.cluster_name))[:max_rows]


def _build_one_plan(
    product: dict[str, Any],
    warehouse: Warehouse,
    city_name: str,
    avg_daily_sales: float,
    cluster_share: float,
    current_stock: int,
    days_with_sales: int,
    total_sales: float,
    city_sales: int,
    planning_mode: str,
) -> FboDemandPlan:
    city_daily_sales = avg_daily_sales * cluster_share
    demand = {horizon: ceil(city_daily_sales * horizon) for horizon in DEFAULT_HORIZONS}
    recommended = {horizon: max(0, demand[horizon] - current_stock) for horizon in DEFAULT_HORIZONS}
    stock_days = current_stock / city_daily_sales if city_daily_sales > 0 else None
    confidence = _confidence(days_with_sales, total_sales, cluster_share, planning_mode)
    note = str(product.get("data_quality_note") or "") or _planning_note(planning_mode)
    sources = list(product.get("data_sources") or ["products", "sales", "stocks", "supply_warehouses"])
    if "supply_warehouses" not in sources:
        sources.append("supply_warehouses")

    return FboDemandPlan(
        sku=str(product.get("sku") or ""),
        offer_id=str(product.get("offer_id") or ""),
        product_name=str(product.get("name") or product.get("product_name") or ""),
        cluster_id=warehouse.cluster_id or f"warehouse:{warehouse.warehouse_id}",
        cluster_name=city_name,
        warehouse_id=warehouse.warehouse_id,
        warehouse_name=warehouse.name,
        avg_daily_sales=round(city_daily_sales, 2),
        cluster_share=round(cluster_share, 4),
        current_stock=current_stock,
        stock_days=round(stock_days, 1) if stock_days is not None else None,
        demand_30=demand[30],
        demand_60=demand[60],
        demand_90=demand[90],
        recommended_30=recommended[30],
        recommended_60=recommended[60],
        recommended_90=recommended[90],
        city_sales=city_sales,
        planning_mode=planning_mode,
        confidence=confidence,
        data_sources=sources,
        data_quality_note=note,
    )


def _load_product_sales(skus: list[str] | None, lookback_days: int, limit: int) -> list[dict[str, Any]]:
    order_rows = _load_product_sales_from_orders_db(skus=skus, lookback_days=lookback_days, limit=limit)
    if order_rows:
        return order_rows

    db_rows = _load_product_sales_from_db(skus=skus, lookback_days=lookback_days, limit=limit)
    if db_rows:
        return db_rows

    if _allow_file_fallback():
        return _load_product_sales_from_files(skus=skus, lookback_days=lookback_days, limit=limit)
    return []


def _load_product_sales_from_orders_db(
    skus: list[str] | None,
    lookback_days: int,
    limit: int,
) -> list[dict[str, Any]]:
    params: list[Any] = [lookback_days]
    sku_filter = ""
    if skus:
        sku_filter = "AND o.sku = ANY(%s)"
        params.append([str(sku) for sku in skus])

    try:
        rows = execute_query(
            f"""
            SELECT
                p.sku,
                p.offer_id,
                p.name,
                COALESCE(NULLIF(o.city, ''), NULLIF(o.region, ''), '') AS demand_city,
                DATE(o.created_at) AS order_date,
                COALESCE(SUM(o.quantity), 0) AS city_sales
            FROM orders o
            JOIN products p ON p.sku = o.sku
            WHERE o.scheme = 'FBO'
              AND o.created_at >= CURRENT_DATE - (%s::int * INTERVAL '1 day')
              AND COALESCE(o.quantity, 0) > 0
              {sku_filter}
            GROUP BY p.sku, p.offer_id, p.name, demand_city, DATE(o.created_at)
            """,
            tuple(params),
        )
    except Exception:
        return []

    by_sku: dict[str, dict[str, Any]] = {}
    for row in rows:
        sku = str(row.get("sku") or "").strip()
        if not sku:
            continue

        qty = int(row.get("city_sales") or 0)
        if qty <= 0:
            continue

        item = by_sku.setdefault(
            sku,
            {
                "sku": sku,
                "offer_id": str(row.get("offer_id") or ""),
                "name": str(row.get("name") or ""),
                "total_sales": 0,
                "days_with_sales_set": set(),
                "city_sales_map": defaultdict(int),
                "data_sources": ["orders.city", "products"],
                "planning_mode": "orders_city_history",
                "data_quality_note": (
                    "Demand is based on real FBO order history by destination city; "
                    "Ozon warehouse routing inside the city is selected automatically."
                ),
            },
        )
        item["total_sales"] += qty

        order_date = row.get("order_date")
        if order_date:
            item["days_with_sales_set"].add(str(order_date))

        raw_city = str(row.get("demand_city") or "").strip()
        if not raw_city:
            continue

        city_name = supply_city_from_order_destination(raw_city)
        if city_name:
            item["city_sales_map"][city_name] += qty

    result: list[dict[str, Any]] = []
    for item in by_sku.values():
        city_sales_map = {
            city_name: int(qty)
            for city_name, qty in dict(item["city_sales_map"]).items()
            if int(qty) > 0
        }
        if not city_sales_map:
            continue

        result.append(
            {
                "sku": item["sku"],
                "offer_id": item["offer_id"],
                "name": item["name"],
                "total_sales": int(item["total_sales"]),
                "days_with_sales": max(1, len(item["days_with_sales_set"])),
                "history_days": max(1, lookback_days),
                "city_sales_map": city_sales_map,
                "data_sources": list(item["data_sources"]),
                "planning_mode": item["planning_mode"],
                "data_quality_note": item["data_quality_note"],
            }
        )

    result.sort(key=lambda item: (-float(item["total_sales"]), item["sku"]))
    return result[:limit]


def _load_product_sales_from_db(
    skus: list[str] | None,
    lookback_days: int,
    limit: int,
) -> list[dict[str, Any]]:
    params: list[Any] = [lookback_days]
    sku_filter = ""
    if skus:
        sku_filter = "AND p.sku = ANY(%s)"
        params.append([str(sku) for sku in skus])
    params.append(limit)

    try:
        rows = execute_query(
            f"""
            SELECT
                p.sku,
                p.offer_id,
                p.name,
                COALESCE(SUM(s.quantity), 0) AS total_sales,
                COUNT(DISTINCT s.date) AS days_with_sales,
                ARRAY['products','sales'] AS data_sources,
                'Demand based on PostgreSQL sales history without city split.' AS data_quality_note
            FROM products p
            JOIN sales s ON s.product_id = p.id
            WHERE s.date >= CURRENT_DATE - (%s::int * INTERVAL '1 day')
              {sku_filter}
            GROUP BY p.id, p.sku, p.offer_id, p.name
            HAVING COALESCE(SUM(s.quantity), 0) > 0
            ORDER BY COALESCE(SUM(s.quantity), 0) DESC
            LIMIT %s
            """,
            tuple(params),
        )
    except Exception:
        return []

    allow_estimated = _allow_estimated_city_share()
    for row in rows:
        row["history_days"] = max(1, lookback_days)
        row["planning_mode"] = "sales_history_estimated"
        row["allow_estimated_city_share"] = allow_estimated
        if allow_estimated:
            row["data_quality_note"] = (
                "Demand is based on PostgreSQL sales history; city split is estimated from stock distribution."
            )
        else:
            row["data_quality_note"] = (
                "Sales history exists, but city split is unavailable. "
                "Estimated city allocation is disabled in production mode."
            )
    return rows


def _load_product_sales_from_files(
    skus: list[str] | None,
    lookback_days: int,
    limit: int,
) -> list[dict[str, Any]]:
    rows = _read_json_rows(ANALYTICS_DATA_PATH)
    if not rows:
        return []

    sku_filter = {str(sku) for sku in skus} if skus else None
    catalog = _load_product_catalog()
    allow_estimated = _allow_estimated_city_share()
    result: list[dict[str, Any]] = []

    for row in rows:
        sku = str(row.get("sku") or "").strip()
        if not sku or (sku_filter and sku not in sku_filter):
            continue

        total_sales = int(row.get("ordered_units") or row.get("orders") or row.get("quantity") or 0)
        if total_sales <= 0:
            continue

        product_info = catalog.get(sku, {})
        days_with_sales = _period_days(row.get("date_from"), row.get("date_to"), lookback_days)
        result.append(
            {
                "sku": sku,
                "offer_id": str(product_info.get("offer_id") or row.get("offer_id") or ""),
                "name": str(product_info.get("name") or row.get("product_name") or ""),
                "total_sales": total_sales,
                "days_with_sales": days_with_sales,
                "history_days": days_with_sales,
                "data_sources": ["analytics_data.json"],
                "planning_mode": "analytics_file_estimated",
                "allow_estimated_city_share": allow_estimated,
                "data_quality_note": (
                    "Demand is estimated from analytics_data.json period totals; "
                    "city allocation uses aggregated stock by city."
                    if allow_estimated
                    else "analytics_data.json exists, but file-based city estimation is disabled in production mode."
                ),
            }
        )

    result.sort(key=lambda item: (-float(item["total_sales"]), item["sku"]))
    return result[:limit]


def _load_stock_by_warehouse(skus: list[str]) -> list[dict[str, Any]]:
    if not skus:
        return []
    db_rows = _load_stock_by_warehouse_from_db(skus)
    if db_rows:
        return db_rows
    return _load_stock_by_warehouse_from_files(skus)


def _load_stock_by_warehouse_from_db(skus: list[str]) -> list[dict[str, Any]]:
    try:
        return execute_query(
            """
            WITH latest AS (
                SELECT
                    st.product_id,
                    COALESCE(st.warehouse, '') AS warehouse,
                    st.stock_total,
                    ROW_NUMBER() OVER (
                        PARTITION BY st.product_id, COALESCE(st.warehouse, '')
                        ORDER BY st.recorded_at DESC
                    ) AS rn
                FROM stocks st
            )
            SELECT
                p.sku,
                latest.warehouse AS warehouse_name,
                COALESCE(SUM(latest.stock_total), 0) AS current_stock
            FROM latest
            JOIN products p ON p.id = latest.product_id
            WHERE latest.rn = 1
              AND p.sku = ANY(%s)
            GROUP BY p.sku, latest.warehouse
            """,
            (skus,),
        )
    except Exception:
        return []


def _load_stock_by_warehouse_from_files(skus: list[str]) -> list[dict[str, Any]]:
    sku_filter = set(skus)
    rows = _read_json_rows(WAREHOUSE_STOCKS_PATH)
    if rows:
        result = []
        for row in rows:
            sku = str(row.get("sku") or "")
            if sku not in sku_filter:
                continue
            current_stock = int(row.get("free_to_sell") or 0)
            if current_stock < 0:
                continue
            result.append(
                {
                    "sku": sku,
                    "warehouse_name": str(row.get("warehouse_name") or ""),
                    "current_stock": current_stock,
                }
            )
        if result:
            return result

    rows = _read_json_rows(CURRENT_STOCKS_PATH)
    result = []
    for row in rows:
        sku = str(row.get("sku") or "")
        if sku not in sku_filter:
            continue
        result.append(
            {
                "sku": sku,
                "warehouse_name": "UNALLOCATED_FBO",
                "current_stock": int(row.get("fbo_present") or row.get("total_present") or 0),
            }
        )
    return result


def _load_product_catalog() -> dict[str, dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}
    try:
        for row in execute_query("SELECT sku, offer_id, name FROM products"):
            sku = str(row.get("sku") or "").strip()
            if sku:
                catalog[sku] = {
                    "offer_id": str(row.get("offer_id") or ""),
                    "name": str(row.get("name") or ""),
                }
    except Exception:
        pass

    for row in _read_json_rows(CURRENT_STOCKS_PATH):
        sku = str(row.get("sku") or "").strip()
        if sku and sku not in catalog:
            catalog[sku] = {
                "offer_id": str(row.get("offer_id") or ""),
                "name": str(row.get("product_name") or ""),
            }
    return catalog


def _read_json_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    rows = raw.get("rows") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _period_days(date_from: Any, date_to: Any, fallback_days: int) -> int:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if not start or not end:
        return max(1, min(30, fallback_days))
    return max(1, min(fallback_days, (end.date() - start.date()).days + 1))


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _index_stock_by_city(stock_rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    index: dict[tuple[str, str], int] = defaultdict(int)
    for row in stock_rows:
        sku = str(row.get("sku") or "")
        city_name = canonical_supply_city(row.get("warehouse_name"))
        index[(sku, city_name)] += int(row.get("current_stock") or 0)
    return dict(index)


def _city_targets(warehouses: list[Warehouse]) -> dict[str, Warehouse]:
    targets: dict[str, Warehouse] = {}
    for warehouse in warehouses:
        city_name = canonical_supply_city(warehouse.cluster_name, warehouse.name)
        current = targets.get(city_name)
        if current is None:
            targets[city_name] = warehouse
            continue
        if warehouse_priority(warehouse.name, warehouse.cluster_id) > warehouse_priority(current.name, current.cluster_id):
            targets[city_name] = warehouse
    return targets


def _resolve_city_shares(
    product: dict[str, Any],
    city_targets: dict[str, Warehouse],
    stock_index: dict[tuple[str, str], int],
) -> tuple[dict[str, float], str, dict[str, int]]:
    planning_mode = str(product.get("planning_mode") or "")
    city_sales_map = _normalized_city_sales_map(product.get("city_sales_map"))
    if city_sales_map:
        matched_sales = {
            city_name: int(city_sales_map.get(city_name, 0))
            for city_name in city_targets
            if int(city_sales_map.get(city_name, 0)) > 0
        }
        total_sales = sum(matched_sales.values())
        if total_sales > 0:
            shares = {city_name: qty / total_sales for city_name, qty in matched_sales.items()}
            return shares, planning_mode or "orders_city_history", matched_sales

    if not bool(product.get("allow_estimated_city_share")):
        return {}, planning_mode or "insufficient_city_signal", {}

    shares = _city_shares(str(product.get("sku") or ""), city_targets, stock_index)
    estimated_city_sales = {
        city_name: max(0, int(round(float(product.get("total_sales") or 0) * share)))
        for city_name, share in shares.items()
        if share > 0
    }
    return shares, planning_mode or "stock_weighted_estimate", estimated_city_sales


def _city_shares(
    sku: str,
    city_targets: dict[str, Warehouse],
    stock_index: dict[tuple[str, str], int],
) -> dict[str, float]:
    stocks = {
        city_name: stock_index.get((sku, city_name), 0)
        for city_name in city_targets
    }
    total_stock = sum(stocks.values())
    if total_stock > 0:
        return {city_name: stock / total_stock for city_name, stock in stocks.items()}

    equal_share = 1 / len(city_targets)
    return {city_name: equal_share for city_name in city_targets}


def _normalized_city_sales_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, int] = defaultdict(int)
    for raw_city, raw_qty in value.items():
        city_name = supply_city_from_order_destination(raw_city)
        qty = int(raw_qty or 0)
        if city_name and qty > 0:
            result[city_name] += qty
    return dict(result)


def _allow_estimated_city_share() -> bool:
    return os.getenv("FBO_ALLOW_ESTIMATED_CITY_SHARE", "").strip().lower() in {"1", "true", "yes"}


def _allow_file_fallback() -> bool:
    return os.getenv("FBO_ALLOW_FILE_FALLBACK", "").strip().lower() in {"1", "true", "yes"}


def _planning_note(planning_mode: str) -> str:
    if planning_mode == "orders_city_history":
        return (
            "Demand is based on real FBO order history by destination city; "
            "Ozon warehouse routing inside the city is selected automatically."
        )
    if planning_mode == "sales_history_estimated":
        return "Demand is based on sales history, but city split is estimated from stock distribution."
    if planning_mode == "analytics_file_estimated":
        return "Demand is estimated from analytics_data.json period totals and stock distribution."
    return "City demand signal is insufficient for a trusted recommendation."


def _normalize_warehouse_name(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).casefold()


def _confidence(days_with_sales: int, total_sales: float, cluster_share: float, planning_mode: str) -> float:
    history_score = min(0.7, days_with_sales / 90 * 0.7)
    volume_score = min(0.2, total_sales / 1000 * 0.2)
    share_score = 0.1 if cluster_share > 0 else 0.0
    mode_score = 0.1 if planning_mode == "orders_city_history" else 0.0
    return round(min(0.95, history_score + volume_score + share_score + mode_score), 2)




