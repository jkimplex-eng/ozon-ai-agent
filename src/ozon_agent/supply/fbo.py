"""FBO demand planning by city."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.db.connection import execute_query
from ozon_agent.supply.cities import canonical_supply_city, warehouse_priority
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
        if not sku or total_sales <= 0 or days_with_sales <= 0:
            continue

        avg_daily_sales = total_sales / days_with_sales
        shares = _city_shares(sku, city_targets, stock_index)
        for city_name, warehouse in city_targets.items():
            current_stock = stock_index.get((sku, city_name), 0)
            share = shares.get(city_name, 0.0)
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
) -> FboDemandPlan:
    city_daily_sales = avg_daily_sales * cluster_share
    demand = {horizon: ceil(city_daily_sales * horizon) for horizon in DEFAULT_HORIZONS}
    recommended = {horizon: max(0, demand[horizon] - current_stock) for horizon in DEFAULT_HORIZONS}
    stock_days = current_stock / city_daily_sales if city_daily_sales > 0 else None
    confidence = _confidence(days_with_sales, total_sales, cluster_share)
    note = str(product.get("data_quality_note") or "") or (
        "City demand is estimated from SKU sales and aggregated city stock; "
        "Ozon warehouse routing inside the city is selected automatically."
    )
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
        confidence=confidence,
        data_sources=sources,
        data_quality_note=note,
    )


def _load_product_sales(skus: list[str] | None, lookback_days: int, limit: int) -> list[dict[str, Any]]:
    db_rows = _load_product_sales_from_db(skus=skus, lookback_days=lookback_days, limit=limit)
    if db_rows:
        return db_rows
    return _load_product_sales_from_files(skus=skus, lookback_days=lookback_days, limit=limit)


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
        return execute_query(
            f"""
            SELECT
                p.sku,
                p.offer_id,
                p.name,
                COALESCE(SUM(s.quantity), 0) AS total_sales,
                COUNT(DISTINCT s.date) AS days_with_sales,
                ARRAY['products','sales'] AS data_sources,
                'Demand based on PostgreSQL sales history.' AS data_quality_note
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
                "data_sources": ["analytics_data.json"],
                "data_quality_note": (
                    "Demand is estimated from analytics_data.json period totals; "
                    "city allocation uses aggregated stock by city."
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


def _normalize_warehouse_name(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).casefold()


def _confidence(days_with_sales: int, total_sales: float, cluster_share: float) -> float:
    history_score = min(0.7, days_with_sales / 90 * 0.7)
    volume_score = min(0.2, total_sales / 1000 * 0.2)
    share_score = 0.1 if cluster_share > 0 else 0.0
    return round(min(0.95, history_score + volume_score + share_score), 2)
