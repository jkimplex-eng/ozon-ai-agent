from __future__ import annotations

import csv
import io
import logging

from ozon_agent.performance.models import PerformanceStatsRow

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "День": "date",
    "sku": "sku",
    "Название товара": "product_name",
    "Цена товара, ₽": "unit_price",
    "Показы": "impressions",
    "Клики": "clicks",
    "CTR, %": "ctr",
    "Добавления в корзину": "add_to_cart",
    "Средняя стоимость клика, ₽": "cpc",
    "Расход, ₽, с НДС": "spend",
    "Продано товаров": "orders",
    "Продажи в продвижении, ₽": "revenue",
    "Продано товаров модели": "model_orders",
    "Продажи в продвижении с заказов модели, ₽": "model_revenue",
    "ДРР в продвижении, %": "drr",
    "Заказано на сумму, ₽": "ordered_amount",
    "ДРР (общий), %": "total_drr",
    "Дата добавления": "added_at",
}


def _safe_int(value: str) -> int:
    cleaned = value.replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return 0


def _safe_float(value: str) -> float:
    cleaned = value.replace("\xa0", "").replace(" ", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def parse_performance_csv(csv_text: str) -> list[PerformanceStatsRow]:
    if not csv_text or not csv_text.strip():
        return []

    lines = csv_text.strip().split("\n")
    header_idx = -1
    for i, line in enumerate(lines):
        if "sku" in line.lower() or "день" in line.lower():
            header_idx = i
            break

    if header_idx < 0:
        return []

    header_line = lines[header_idx]
    reader = csv.DictReader(
        io.StringIO(header_line + "\n" + "\n".join(lines[header_idx + 1:])),
        delimiter=";",
    )
    if reader.fieldnames is None:
        return []

    field_map: dict[str, str] = {}
    for col in reader.fieldnames:
        normalized = col.strip()
        if normalized in COLUMN_MAP:
            field_map[normalized] = COLUMN_MAP[normalized]

    rows: list[PerformanceStatsRow] = []
    for raw_row in reader:
        mapped: dict[str, str] = {}
        for raw_col, value in raw_row.items():
            if raw_col and raw_col.strip() in field_map:
                mapped[field_map[raw_col.strip()]] = str(value or "")

        row = PerformanceStatsRow(
            date=mapped.get("date", ""),
            campaign_id="",
            campaign_name="",
            sku=mapped.get("sku", ""),
            product_name=mapped.get("product_name", ""),
            impressions=_safe_int(mapped.get("impressions", "0")),
            clicks=_safe_int(mapped.get("clicks", "0")),
            ctr=_safe_float(mapped.get("ctr", "0")),
            add_to_cart=_safe_int(mapped.get("add_to_cart", "0")),
            cpc=_safe_float(mapped.get("cpc", "0")),
            spend=_safe_float(mapped.get("spend", "0")),
            orders=_safe_int(mapped.get("orders", "0")),
            revenue=_safe_float(mapped.get("revenue", "0")),
            model_orders=_safe_int(mapped.get("model_orders", "0")),
            model_revenue=_safe_float(mapped.get("model_revenue", "0")),
            drr=_safe_float(mapped.get("drr", "0")),
            ordered_amount=_safe_int(mapped.get("ordered_amount", "0")),
            total_drr=_safe_float(mapped.get("total_drr", "0")),
            added_at=mapped.get("added_at", ""),
        )
        rows.append(row)

    logger.info("Parsed %d rows from performance CSV", len(rows))
    return rows
