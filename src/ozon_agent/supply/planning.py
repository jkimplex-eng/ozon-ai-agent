"""Supply Planning Engine - generates plans from real data."""

import logging
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.db.connection import get_connection
from ozon_agent.supply.client import SupplyAPIClient

logger = logging.getLogger(__name__)


class SupplyPlanningEngine:
    """Generate supply plans from real stocks and sales data."""

    def __init__(self, client: OzonClient) -> None:
        self._client = client
        self._supply_client = SupplyAPIClient(client)

    def generate_plans(
        self,
        skus: list[int] | None = None,
        max_plans: int = 10,
        min_stock_days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Generate supply plans based on real data.

        Args:
            skus: Specific SKUs to plan (None = auto-select)
            max_plans: Maximum plans to generate
            min_stock_days: Minimum stock days threshold

        Returns:
            List of plan dictionaries
        """
        logger.info(f"Generating supply plans (max={max_plans})")

        # Load warehouses
        warehouses = self._supply_client.list_fbo_warehouses()
        if not warehouses:
            logger.warning("No warehouses available")
            return []

        # Get SKUs needing replenishment
        if skus is None:
            skus = self._get_skus_needing_replenishment(min_stock_days, limit=50)

        if not skus:
            logger.info("No SKUs need replenishment")
            return []

        plans = []

        for sku in skus:
            if len(plans) >= max_plans:
                break

            # Get product info
            product_info = self._get_product_info(sku)
            if not product_info:
                continue

            # Analyze demand by warehouse
            for warehouse in warehouses:
                if not warehouse.is_active:
                    continue

                plan = self._create_plan_for_warehouse(
                    sku=sku,
                    product_info=product_info,
                    warehouse=warehouse,
                )

                if plan:
                    plans.append(plan)

                    if len(plans) >= max_plans:
                        break

        logger.info(f"Generated {len(plans)} supply plans")
        return plans

    def _get_skus_needing_replenishment(
        self,
        min_stock_days: int,
        limit: int = 50,
    ) -> list[int]:
        """Get SKUs with low stock relative to sales velocity."""
        query = """
            WITH sku_metrics AS (
                SELECT
                    s.product_id,
                    AVG(s.quantity) as avg_daily_sales,
                    COALESCE(SUM(st.stock_total), 0) as total_stock,
                    CASE
                        WHEN AVG(s.quantity) > 0
                        THEN COALESCE(SUM(st.stock_total), 0) / AVG(s.quantity)
                        ELSE 999
                    END as days_of_stock
                FROM sales s
                LEFT JOIN stocks st ON s.product_id = st.product_id
                WHERE s.date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY s.product_id
            )
            SELECT p.sku
            FROM sku_metrics sm
            JOIN products p ON sm.product_id = p.id
            WHERE sm.days_of_stock < %s
              AND sm.avg_daily_sales > 0
            ORDER BY sm.days_of_stock ASC
            LIMIT %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (min_stock_days, limit))
                rows = cur.fetchall()
                return [int(row[0]) for row in rows]

    def _get_product_info(self, sku: int) -> dict[str, Any] | None:
        """Get product information from database."""
        query = """
            SELECT sku, offer_id, name, price
            FROM products
            WHERE sku = %s
            LIMIT 1
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (sku,))
                row = cur.fetchone()

                if not row:
                    return None

                return {
                    "sku": row[0],
                    "offer_id": row[1],
                    "name": row[2],
                    "price": float(row[3]) if row[3] else 0.0,
                }

    def _create_plan_for_warehouse(
        self,
        sku: int,
        product_info: dict[str, Any],
        warehouse: Any,
    ) -> dict[str, Any] | None:
        """Create supply plan for specific SKU and warehouse."""
        # Get sales and stock for this warehouse
        query = """
            SELECT
                COALESCE(SUM(s.quantity), 0) as total_sales,
                COUNT(DISTINCT s.date) as days_with_sales,
                COALESCE(st.stock, 0) as current_stock
            FROM (
                SELECT sku, quantity, date
                FROM sales
                WHERE sku = %s
                  AND date >= CURRENT_DATE - INTERVAL '30 days'
            ) s
            LEFT JOIN (
                SELECT sku, quantity as stock
                FROM stocks
                WHERE sku = %s
            ) st ON s.product_id = st.product_id
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (sku, sku))
                row = cur.fetchone()

                if not row:
                    return None

                total_sales = float(row[0])
                days_with_sales = int(row[1])
                current_stock = int(row[2])

        if days_with_sales == 0:
            return None

        avg_daily_sales = total_sales / days_with_sales

        # Calculate recommended quantity (30 days supply)
        target_stock = int(avg_daily_sales * 30)
        recommended_quantity = max(0, target_stock - current_stock)

        if recommended_quantity < 10:  # Minimum threshold
            return None

        # Calculate expected prevented loss
        days_until_stockout = int(current_stock / avg_daily_sales) if avg_daily_sales > 0 else 999
        prevented_loss = self._calculate_prevented_loss(
            days_until_stockout=days_until_stockout,
            avg_daily_sales=avg_daily_sales,
            price=product_info["price"],
            replenishment_days=7,
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            days_with_sales=days_with_sales,
            total_sales=total_sales,
        )

        # Determine reason
        if days_until_stockout <= 3:
            reason = "Critical stock level - immediate replenishment needed"
        elif days_until_stockout <= 7:
            reason = "Low stock - replenishment recommended within 7 days"
        else:
            reason = "Preventive replenishment to maintain optimal stock level"

        return {
            "sku": sku,
            "offer_id": product_info["offer_id"],
            "product_name": product_info["name"],
            "quantity": recommended_quantity,
            "target_warehouse_id": warehouse.warehouse_id,
            "target_warehouse_name": warehouse.name,
            "target_cluster_id": warehouse.cluster_id or "unknown",
            "target_cluster_name": warehouse.cluster_name or "Unknown",
            "reason": reason,
            "expected_prevented_loss": prevented_loss,
            "confidence": confidence,
            "data_sources": ["sales", "stocks", "products"],
            "avg_daily_sales": avg_daily_sales,
            "current_stock": current_stock,
            "days_until_stockout": days_until_stockout,
        }

    def _calculate_prevented_loss(
        self,
        days_until_stockout: int,
        avg_daily_sales: float,
        price: float,
        replenishment_days: int,
    ) -> float:
        """Calculate expected prevented loss from stockout."""
        if days_until_stockout >= replenishment_days:
            return 0.0

        stockout_days = replenishment_days - days_until_stockout
        lost_units = avg_daily_sales * stockout_days
        return lost_units * price

    def _calculate_confidence(
        self,
        days_with_sales: int,
        total_sales: float,
    ) -> float:
        """Calculate confidence score based on data quality."""
        base_confidence = min(1.0, days_with_sales / 30.0)
        volume_boost = min(0.2, total_sales / 1000.0)
        return min(1.0, base_confidence + volume_boost)
