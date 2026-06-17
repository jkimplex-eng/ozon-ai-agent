from __future__ import annotations

from typing import Any

from ozon_agent.ingestion.models import LiveOzonDataset


def extract_raw_rows(dataset: LiveOzonDataset, payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result", {})
    if dataset is LiveOzonDataset.PRODUCTS:
        return _dict_rows(result.get("items", []))
    if dataset is LiveOzonDataset.STOCKS:
        return _dict_rows(result.get("items", result.get("stocks", [])))
    if dataset in {LiveOzonDataset.ORDERS_FBO, LiveOzonDataset.ORDERS_FBS}:
        return _dict_rows(result.get("postings", []))
    if dataset is LiveOzonDataset.FINANCE_OPERATIONS:
        return _dict_rows(result.get("operations", []))
    return []


def normalize_rows(dataset: LiveOzonDataset, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = extract_raw_rows(dataset, payload)
    if dataset is LiveOzonDataset.PRODUCTS:
        return [_normalize_product(row) for row in rows]
    if dataset is LiveOzonDataset.STOCKS:
        return [_normalize_stock(row) for row in rows]
    if dataset in {LiveOzonDataset.ORDERS_FBO, LiveOzonDataset.ORDERS_FBS}:
        return [
            normalized
            for row in rows
            for normalized in _normalize_order(row, dataset)
        ]
    if dataset is LiveOzonDataset.FINANCE_OPERATIONS:
        return [_normalize_finance_operation(row) for row in rows]
    return rows


def _normalize_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": row.get("product_id") or row.get("id"),
        "offer_id": row.get("offer_id", ""),
        "sku": str(row.get("sku", "")),
        "name": row.get("name", ""),
        "visibility": row.get("visibility"),
        "raw": row,
    }


def _normalize_stock(row: dict[str, Any]) -> dict[str, Any]:
    stocks = row.get("stocks", [])
    stock_total = 0
    if isinstance(stocks, list):
        stock_total = sum(
            int(item.get("present", 0) or 0)
            for item in stocks
            if isinstance(item, dict)
        )
    return {
        "product_id": row.get("product_id"),
        "offer_id": row.get("offer_id", ""),
        "sku": str(row.get("sku", "")),
        "stock_total": stock_total,
        "raw": row,
    }


def _normalize_order(row: dict[str, Any], dataset: LiveOzonDataset) -> list[dict[str, Any]]:
    products = row.get("products", [])
    if not isinstance(products, list):
        products = []
    normalized: list[dict[str, Any]] = []
    for product in products:
        if not isinstance(product, dict):
            continue
        normalized.append(
            {
                "posting_number": row.get("posting_number", ""),
                "order_id": row.get("order_id", ""),
                "scheme": "FBO" if dataset is LiveOzonDataset.ORDERS_FBO else "FBS",
                "status": row.get("status", ""),
                "created_at": row.get("created_at"),
                "offer_id": product.get("offer_id", ""),
                "sku": str(product.get("sku", "")),
                "quantity": int(product.get("quantity", 0) or 0),
                "price": _float(product.get("price")),
                "raw": row,
            }
        )
    return normalized


def _normalize_finance_operation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_id": row.get("operation_id"),
        "operation_type": row.get("operation_type", ""),
        "operation_type_name": row.get("operation_type_name", ""),
        "operation_date": row.get("operation_date", ""),
        "amount": _float(row.get("amount")),
        "posting_number": row.get("posting", {}).get("posting_number", "")
        if isinstance(row.get("posting"), dict)
        else "",
        "raw": row,
    }


def _dict_rows(value: object) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _float(value: object) -> float:
    if not isinstance(value, int | float | str):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0
