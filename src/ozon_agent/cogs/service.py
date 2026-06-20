"""COGS business logic service."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from ozon_agent.cogs.models import CogsCoverageReport, CogsRecord, create_cogs_record
from ozon_agent.cogs.repository import (
    get_record,
    list_records,
    save_record,
)

logger = logging.getLogger(__name__)


def get_cogs(sku: str) -> float | None:
    """Get unit cost for a SKU. Returns None if not found."""
    record = get_record(sku)
    if record is None:
        return None
    return record.unit_cost


def get_unit_cost(sku: str) -> Decimal | None:
    """Get unit cost as Decimal for precise calculations."""
    cost = get_cogs(sku)
    if cost is None:
        return None
    return Decimal(str(cost))


def set_cogs(
    sku: str,
    unit_cost: float | str,
    offer_id: str | None = None,
    product_name: str | None = None,
    logistics_cost: float = 0.0,
    packaging_cost: float = 0.0,
) -> CogsRecord:
    """Set COGS for a SKU. Validates cost is positive."""
    cost = _parse_cost(unit_cost)
    if cost <= 0:
        raise ValueError(f"Unit cost must be positive, got {cost}")

    existing = get_record(sku)
    if existing:
        existing.unit_cost = cost
        existing.logistics_cost = logistics_cost
        existing.packaging_cost = packaging_cost
        if offer_id:
            existing.offer_id = offer_id
        if product_name:
            existing.product_name = product_name
        existing.source = "manual"
        existing.updated_at = __import__("datetime").datetime.now(
            __import__("datetime").UTC
        )
        save_record(existing)
        return existing

    record = create_cogs_record(
        sku=sku,
        unit_cost=cost,
        offer_id=offer_id,
        product_name=product_name,
        logistics_cost=logistics_cost,
        packaging_cost=packaging_cost,
    )
    save_record(record)
    return record


def list_cogs() -> list[CogsRecord]:
    """List all COGS records."""
    return list_records()


def missing_cogs(products: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    """Find products without COGS."""
    if products is None:
        products = _load_products()

    existing = {r.sku for r in list_records()}
    missing = []
    for p in products:
        sku = p.get("sku", "")
        if sku and sku not in existing:
            missing.append({
                "sku": sku,
                "name": p.get("name", ""),
                "offer_id": p.get("offer_id", ""),
            })
    return missing


def coverage_report(products: list[dict[str, Any]] | None = None) -> CogsCoverageReport:
    """Calculate COGS coverage."""
    if products is None:
        products = _load_products()

    total = len(products)
    existing = {r.sku for r in list_records()}
    with_cogs = sum(1 for p in products if p.get("sku", "") in existing)
    without_cogs = total - with_cogs
    coverage_pct = (with_cogs / total * 100) if total > 0 else 0.0

    missing = [
        p.get("sku", "")
        for p in products
        if p.get("sku", "") and p.get("sku", "") not in existing
    ]

    return CogsCoverageReport(
        total_products=total,
        with_cogs=with_cogs,
        without_cogs=without_cogs,
        coverage_pct=round(coverage_pct, 1),
        missing_skus=missing[:20],
    )


def _parse_cost(value: float | str) -> float:
    """Parse cost value, validate it's a positive number."""
    try:
        cost = float(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid cost value: {value}") from e
    if cost < 0:
        raise ValueError(f"Cost cannot be negative: {cost}")
    return cost


def _load_products() -> list[dict[str, Any]]:
    """Load products from DB."""
    try:
        from ozon_agent.db.connection import execute_query
        return execute_query("SELECT sku, name, offer_id FROM products")
    except Exception:
        return []
