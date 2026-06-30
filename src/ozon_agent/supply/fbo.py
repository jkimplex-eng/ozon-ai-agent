"""FBO demand planning by cluster."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.db.connection import execute_query
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.models import Warehouse

DEFAULT_HORIZONS = (30, 60, 90)


@dataclass(frozen=True)
class FboDemandPlan:
    """Demand forecast and replenishment recommendation for one SKU in one cluster."""

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
    """Calculate FBO demand for 30/60/90 days across available clusters."""

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
    stock_index = _index_stock(stock_rows)
    cluster_targets = _cluster_targets(warehouses)
    if not cluster_targets:
        return []

    plans: list[FboDemandPlan] = []
    for product in product_rows:
        sku = str(product.get("sku") or "")
        total_sales = float(product.get("total_sales") or 0)
        days_with_sales = int(product.get("days_with_sales") or 0)
        if not sku or total_sales <= 0 or days_with_sales <= 0:
            continue

        avg_daily_sales = total_sales / days_with_sales
        shares = _cluster_shares(sku, cluster_targets, stock_index)
        for cluster_id, warehouse in cluster_targets.items():
            current_stock = stock_index.get((sku, warehouse.name.lower()), 0)
            share = shares.get(cluster_id, 0.0)
            plans.append(
                _build_one_plan(
                    product=product,
                    warehouse=warehouse,
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
    avg_daily_sales: float,
    cluster_share: float,
    current_stock: int,
    days_with_sales: int,
    total_sales: float,
) -> FboDemandPlan:
    cluster_daily_sales = avg_daily_sales * cluster_share
    demand = {horizon: ceil(cluster_daily_sales * horizon) for horizon in DEFAULT_HORIZONS}
    recommended = {horizon: max(0, demand[horizon] - current_stock) for horizon in DEFAULT_HORIZONS}
    stock_days = current_stock / cluster_daily_sales if cluster_daily_sales > 0 else None
    confidence = _confidence(days_with_sales, total_sales, cluster_share)

    return FboDemandPlan(
        sku=str(product.get("sku") or ""),
        offer_id=str(product.get("offer_id") or ""),
        product_name=str(product.get("name") or ""),
        cluster_id=warehouse.cluster_id or "unknown",
        cluster_name=warehouse.cluster_name or "Unknown",
        warehouse_id=warehouse.warehouse_id,
        warehouse_name=warehouse.name,
        avg_daily_sales=round(cluster_daily_sales, 2),
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
        data_sources=["products", "sales", "stocks", "supply_warehouses"],
        data_quality_note=(
            "Cluster demand is estimated from SKU sales and warehouse stock distribution; "
            "database has no direct cluster-level sales table."
        ),
    )


def _load_product_sales(skus: list[str] | None, lookback_days: int, limit: int) -> list[dict[str, Any]]:
    params: list[Any] = [lookback_days]
    sku_filter = ""
    if skus:
        sku_filter = "AND p.sku = ANY(%s)"
        params.append([str(sku) for sku in skus])
    params.append(limit)

    return execute_query(
        f"""
        SELECT
            p.sku,
            p.offer_id,
            p.name,
            COALESCE(SUM(s.quantity), 0) AS total_sales,
            COUNT(DISTINCT s.date) AS days_with_sales
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


def _load_stock_by_warehouse(skus: list[str]) -> list[dict[str, Any]]:
    if not skus:
        return []
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


def _index_stock(stock_rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    index: dict[tuple[str, str], int] = {}
    for row in stock_rows:
        sku = str(row.get("sku") or "")
        warehouse_name = str(row.get("warehouse_name") or "").lower()
        index[(sku, warehouse_name)] = int(row.get("current_stock") or 0)
    return index


def _cluster_targets(warehouses: list[Warehouse]) -> dict[str, Warehouse]:
    targets: dict[str, Warehouse] = {}
    for warehouse in warehouses:
        cluster_id = warehouse.cluster_id or f"warehouse:{warehouse.warehouse_id}"
        targets.setdefault(cluster_id, warehouse)
    return targets


def _cluster_shares(
    sku: str,
    cluster_targets: dict[str, Warehouse],
    stock_index: dict[tuple[str, str], int],
) -> dict[str, float]:
    stocks = {
        cluster_id: stock_index.get((sku, warehouse.name.lower()), 0)
        for cluster_id, warehouse in cluster_targets.items()
    }
    total_stock = sum(stocks.values())
    if total_stock > 0:
        return {cluster_id: stock / total_stock for cluster_id, stock in stocks.items()}

    equal_share = 1 / len(cluster_targets)
    return {cluster_id: equal_share for cluster_id in cluster_targets}


def _confidence(days_with_sales: int, total_sales: float, cluster_share: float) -> float:
    history_score = min(0.7, days_with_sales / 90 * 0.7)
    volume_score = min(0.2, total_sales / 1000 * 0.2)
    share_score = 0.1 if cluster_share > 0 else 0.0
    return round(min(0.95, history_score + volume_score + share_score), 2)
