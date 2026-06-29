"""ETL pipeline for syncing Ozon data to PostgreSQL."""
import logging
from datetime import datetime, timedelta

from ..api.ozon_client import OzonClient, create_client
from ..db.connection import get_cursor

logger = logging.getLogger(__name__)


def log_etl(
    source: str,
    status: str,
    rows_fetched: int = 0,
    rows_inserted: int = 0,
    error_message: str | None = None,
) -> None:
    completed_at = datetime.now() if status != "running" else None
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO etl_log
               (source, status, rows_fetched, rows_inserted, error_message, completed_at)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (source, status, rows_fetched, rows_inserted, error_message, completed_at),
        )


def sync_products(client: OzonClient) -> int:
    source = "products"
    log_etl(source, "running")
    try:
        result = client.get_products(limit=1000)
        items = result.get("result", {}).get("items", [])
        rows_fetched = len(items)

        if not items:
            log_etl(source, "success", rows_fetched=0, rows_inserted=0)
            return 0

        product_ids = [item["product_id"] for item in items]
        info_result = client.get_product_info(product_ids)
        products = info_result.get("items", []) if "items" in info_result else info_result.get("result", {}).get("items", [])

        rows = []
        for p in products:
            rows.append((
                p.get("offer_id", ""),
                str(p.get("sku", "")),
                p.get("id"),
                p.get("name", ""),
                p.get("category_name", ""),
                p.get("brand", ""),
                float(p.get("price", 0)) / 100 if p.get("price") else None,
                float(p.get("old_price", 0)) / 100 if p.get("old_price") else None,
                None,
                p.get("weight_grams"),
                p.get("state", ""),
            ))

        with get_cursor() as cur:
            cur.executemany(
                """INSERT INTO products
                   (offer_id, sku, product_id, name, category, brand,
                    price, old_price, cost_price, weight_grams, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (offer_id, sku) DO UPDATE SET
                       name = EXCLUDED.name,
                       category = EXCLUDED.category,
                       brand = EXCLUDED.brand,
                       price = EXCLUDED.price,
                       old_price = EXCLUDED.old_price,
                       status = EXCLUDED.status,
                       updated_at = NOW()""",
                rows,
            )
            rows_inserted = cur.rowcount

        log_etl(source, "success", rows_fetched, rows_inserted)
        return rows_inserted
    except Exception as e:
        logger.exception(f"Failed to sync {source}")
        log_etl(source, "failed", error_message=str(e))
        raise


def sync_orders(client: OzonClient, date_from: datetime, date_to: datetime) -> int:
    source = "orders"
    log_etl(source, "running")
    total_inserted = 0

    try:
        for scheme in ["FBO", "FBS"]:
            offset = 0
            while True:
                result = client.get_orders(
                    date_from, date_to, limit=100, offset=offset, scheme=scheme
                )
                postings = result.get("postings", []) if "postings" in result else result.get("result", {}).get("postings", [])

                if not postings:
                    break

                rows = []
                for order in postings:
                    for product in order.get("products", []):
                        analytics = order.get("analytics_data", {})
                        rows.append((
                            order.get("order_id", ""),
                            order.get("posting_number", ""),
                            None,
                            product.get("offer_id", ""),
                            str(product.get("sku", "")),
                            product.get("quantity", 1),
                            float(product.get("price", {}).get("amount", 0)) if isinstance(product.get("price"), dict) else float(product.get("price", 0)),
                            float(product.get("price", {}).get("amount", 0)) if isinstance(product.get("price"), dict) else float(product.get("price", 0)),
                            order.get("status", ""),
                            scheme,
                            analytics.get("region", ""),
                            analytics.get("city", ""),
                            order.get("created_at"),
                            order.get("shipment_date"),
                            order.get("delivery_date"),
                        ))

                with get_cursor() as cur:
                    cur.executemany(
                        """INSERT INTO orders
                           (order_id, posting_number, product_id, offer_id, sku,
                            quantity, price, final_price, status, scheme,
                            region, city, created_at, shipped_at, delivered_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                  %s, %s, %s, %s, %s)
                           ON CONFLICT (order_id) DO UPDATE SET
                               status = EXCLUDED.status,
                               shipped_at = EXCLUDED.shipped_at,
                               delivered_at = EXCLUDED.delivered_at""",
                        rows,
                    )
                    total_inserted += cur.rowcount

                if len(postings) < 100:
                    break
                offset += 100

        log_etl(source, "success", total_inserted, total_inserted)
        return total_inserted
    except Exception as e:
        logger.exception(f"Failed to sync {source}")
        log_etl(source, "failed", error_message=str(e))
        raise


def sync_finance(client: OzonClient, date_from: datetime, date_to: datetime) -> int:
    source = "finance"
    log_etl(source, "running")
    try:
        all_operations = []
        current_start = date_from
        while current_start < date_to:
            current_end = min(current_start + timedelta(days=30), date_to)
            result = client.get_finance_operations(current_start, current_end)
            all_operations.extend(result.get("result", {}).get("operations", []))
            current_start = current_end + timedelta(days=1)
        operations = all_operations

        daily_totals = {}
        for op in operations:
            op_date = op.get("operation_date", "")[:10]
            if not op_date:
                continue

            if op_date not in daily_totals:
                daily_totals[op_date] = {
                    "sales": 0.0, "returns": 0.0, "commission": 0.0,
                    "logistics": 0.0, "partner_services": 0.0, "fbo_services": 0.0,
                    "other_services": 0.0, "advertising": 0.0, "accrued": 0.0,
                }

            amount = float(op.get("amount", 0))
            op_type = op.get("operation_type", "")
            services = op.get("services", [])

            if "DeliveredToCustomer" in op_type or "Продажи" in op_type or "sale" in op_type.lower():
                daily_totals[op_date]["sales"] += amount
            elif "Return" in op_type or "Возврат" in op_type:
                daily_totals[op_date]["returns"] += abs(amount)
            elif "Commission" in op_type or "Комиссия" in op_type:
                daily_totals[op_date]["commission"] += abs(amount)
            elif "Logistic" in op_type or "Логистика" in op_type or "Packaging" in op_type:
                daily_totals[op_date]["logistics"] += abs(amount)

            for svc in services:
                svc_name = svc.get("name", "")
                svc_amount = float(svc.get("amount", 0))
                if "реклам" in svc_name.lower() or "продвиж" in svc_name.lower():
                    daily_totals[op_date]["advertising"] += abs(svc_amount)
                elif "партнёр" in svc_name.lower():
                    daily_totals[op_date]["partner_services"] += abs(svc_amount)
                elif "fbo" in svc_name.lower():
                    daily_totals[op_date]["fbo_services"] += abs(svc_amount)

            daily_totals[op_date]["accrued"] += amount

        rows = []
        for op_date, totals in daily_totals.items():
            rows.append((
                op_date, totals["sales"], totals["returns"], totals["commission"],
                totals["logistics"], totals["partner_services"], totals["fbo_services"],
                totals["other_services"], totals["advertising"], totals["accrued"],
            ))

        with get_cursor() as cur:
            cur.executemany(
                """INSERT INTO finance
                   (date, sales, returns, ozon_commission, logistics,
                    partner_services, fbo_services, other_services,
                    advertising, accrued_total)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (date) DO UPDATE SET
                       sales = EXCLUDED.sales,
                       returns = EXCLUDED.returns,
                       ozon_commission = EXCLUDED.ozon_commission,
                       logistics = EXCLUDED.logistics,
                       partner_services = EXCLUDED.partner_services,
                       fbo_services = EXCLUDED.fbo_services,
                       other_services = EXCLUDED.other_services,
                       advertising = EXCLUDED.advertising,
                       accrued_total = EXCLUDED.accrued_total,
                       synced_at = NOW()""",
                rows,
            )
            rows_inserted = cur.rowcount

        log_etl(source, "success", len(operations), rows_inserted)
        return rows_inserted
    except Exception as e:
        logger.exception(f"Failed to sync {source}")
        log_etl(source, "failed", error_message=str(e))
        raise


def sync_all(date_from: datetime | None = None, date_to: datetime | None = None) -> None:
    client = create_client()
    try:
        if date_to is None:
            date_to = datetime.now()
        if date_from is None:
            date_from = date_to - timedelta(days=7)

        logger.info(f"Starting full sync: {date_from.date()} to {date_to.date()}")

        sync_products(client)
        sync_orders(client, date_from, date_to)
        sync_finance(client, date_from, date_to)

        logger.info("Full sync completed")
    finally:
        client.close()
