"""COGS data importer — CSV and plain text."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

from ozon_agent.cogs.service import set_cogs

logger = logging.getLogger(__name__)


def import_csv(text: str) -> int:
    """Import COGS from CSV text.

    Expected format: SKU,UnitCost[,LogisticsCost[,PackagingCost[,ProductName]]]
    First row can be header (skipped if first cell is 'SKU' or 'sku').
    """
    reader = csv.reader(io.StringIO(text))
    count = 0

    for row in reader:
        if not row or len(row) < 2:
            continue
        sku = row[0].strip()
        if sku.lower() in ("sku", ""):
            continue

        try:
            unit_cost = float(row[1].strip())
        except (ValueError, IndexError):
            logger.warning("Skipping invalid row: %s", row)
            continue

        logistics = float(row[2].strip()) if len(row) > 2 and row[2].strip() else 0.0
        packaging = float(row[3].strip()) if len(row) > 3 and row[3].strip() else 0.0
        name = row[4].strip() if len(row) > 4 else None

        set_cogs(
            sku=sku,
            unit_cost=unit_cost,
            logistics_cost=logistics,
            packaging_cost=packaging,
            product_name=name,
        )
        count += 1

    return count


def import_text(text: str) -> int:
    """Import COGS from plain text.

    Expected format (one per line):
    SKU UNIT_COST [LOGISTICS_COST] [PACKAGING_COST] [PRODUCT_NAME]

    Examples:
    12345 550
    12345 550 50
    12345 550 50 10 Крем X
    """
    count = 0

    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        sku = parts[0]
        try:
            unit_cost = float(parts[1])
        except ValueError:
            logger.warning("Skipping invalid line: %s", line)
            continue

        logistics = float(parts[2]) if len(parts) > 2 else 0.0
        packaging = float(parts[3]) if len(parts) > 3 else 0.0
        name = " ".join(parts[4:]) if len(parts) > 4 else None

        set_cogs(
            sku=sku,
            unit_cost=unit_cost,
            logistics_cost=logistics,
            packaging_cost=packaging,
            product_name=name,
        )
        count += 1

    return count


def import_rows(rows: list[dict[str, Any]]) -> int:
    """Import COGS from list of dicts (e.g., Google Sheets rows)."""
    count = 0
    for row in rows:
        sku = str(row.get("sku", row.get("SKU", ""))).strip()
        if not sku:
            continue

        try:
            unit_cost = float(row.get("unit_cost", row.get("Unit Cost", 0)))
        except (ValueError, TypeError):
            continue

        if unit_cost <= 0:
            continue

        logistics = float(row.get("logistics_cost", row.get("Logistics Cost", 0)) or 0)
        packaging = float(row.get("packaging_cost", row.get("Packaging Cost", 0)) or 0)
        name = row.get("product_name", row.get("Product Name"))

        set_cogs(
            sku=sku,
            unit_cost=unit_cost,
            logistics_cost=logistics,
            packaging_cost=packaging,
            product_name=name,
        )
        count += 1

    return count
