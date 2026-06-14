from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from math import isnan
from typing import Any

import pandas as pd

from ozon_agent.decision.models import DecisionFeature


def build_decision_features(
    products_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    advertising_df: pd.DataFrame,
    forecasts_df: pd.DataFrame,
    stock_df: pd.DataFrame | None = None,
    ranking_df: pd.DataFrame | None = None,
    reviews_df: pd.DataFrame | None = None,
) -> list[DecisionFeature]:
    product_rows = _index_products(products_df)
    sales_rows = _aggregate_sales(sales_df)
    ad_rows = _aggregate_advertising(advertising_df)
    forecast_rows = _aggregate_forecasts(forecasts_df)
    stock_rows = _aggregate_stock(stock_df)
    ranking_rows = _aggregate_ranking(ranking_df)
    review_rows = _aggregate_reviews(reviews_df)

    all_skus = (
        set(product_rows)
        | set(sales_rows)
        | set(forecast_rows)
        | set(stock_rows)
        | set(ranking_rows)
    )
    all_skus |= set(review_rows)
    all_skus |= {sku for sku, _campaign_id in ad_rows}

    if not all_skus:
        return []

    features: list[DecisionFeature] = []
    for sku in sorted(all_skus):
        sku_key = _normalize_key(sku)
        product_info = product_rows.get(sku_key, {})
        sales_info = sales_rows.get(sku_key, {})
        forecast_info = forecast_rows.get(sku_key, {})
        stock_info = stock_rows.get(sku_key, {})
        ranking_info = ranking_rows.get(sku_key, {})
        review_info = review_rows.get(sku_key, {})
        sku_ad_rows = [
            (campaign_id, metrics)
            for (ad_sku, campaign_id), metrics in ad_rows.items()
            if ad_sku == sku_key
        ]

        if not sku_ad_rows:
            sku_ad_rows = [("", {})]

        for campaign_id, ad_info in sku_ad_rows:
            feature = DecisionFeature(
                sku=sku,
                offer_id=_string_value(
                    product_info, "offer_id", fallback=sales_info.get("offer_id", "")
                ),
                product_name=_string_value(
                    product_info,
                    "product_name",
                    fallback=_string_value(
                        ad_info, "product_name", fallback=sales_info.get("product_name", "")
                    ),
                ),
                campaign_id=campaign_id,
                date=_string_value(
                    ad_info, "latest_date", fallback=_string_value(sales_info, "latest_date")
                ),
                price=_resolve_price(product_info, sales_info, ad_info),
                sales_quantity=_float_value(sales_info, "quantity"),
                sales_revenue=_float_value(sales_info, "revenue"),
                sales_rows_matched=int(_float_value(sales_info, "rows_count")),
                sales_trend_pct=_float_value(sales_info, "sales_trend_pct"),
                sales_cv=_float_value(sales_info, "sales_cv"),
                ad_spend=_float_value(ad_info, "spend"),
                impressions=_float_value(ad_info, "impressions"),
                clicks=_float_value(ad_info, "clicks"),
                ctr=_float_value(ad_info, "ctr"),
                cpc=_float_value(ad_info, "cpc"),
                ad_orders=_float_value(ad_info, "orders"),
                ad_revenue=_float_value(ad_info, "revenue"),
                roas=_float_value(ad_info, "roas"),
                drr=_float_value(ad_info, "drr"),
                current_stock=_optional_float(stock_info, "current_stock"),
                stock_days=_optional_float(stock_info, "stock_days"),
                stockout_probability=_optional_float(
                    forecast_info,
                    "stockout_probability",
                    fallback=_optional_float(stock_info, "stockout_probability"),
                ),
                forecast_quantity=_optional_float(forecast_info, "forecast_quantity"),
                forecast_revenue=_optional_float(forecast_info, "forecast_revenue"),
                ranking_position=_optional_float(ranking_info, "ranking_position"),
                ranking_trend=_optional_float(ranking_info, "ranking_trend"),
                review_rating=_optional_float(review_info, "review_rating"),
                review_count=int(_float_value(review_info, "review_count")),
                priority_sku=_bool_value(
                    product_info,
                    "priority_sku",
                    fallback=_bool_value(forecast_info, "priority_sku"),
                ),
                external_traffic=_bool_value(
                    product_info,
                    "external_traffic",
                    fallback=_bool_value(forecast_info, "external_traffic"),
                ),
                data_freshness_days=_calculate_freshness_days(
                    _iter_dates(
                        ad_info.get("latest_date"),
                        sales_info.get("latest_date"),
                        forecast_info.get("latest_date"),
                    )
                ),
                sample_size=int(
                    _float_value(sales_info, "rows_count") + _float_value(ad_info, "rows_count")
                ),
                has_forecast=bool(forecast_info),
                has_stock=bool(stock_info),
                has_ranking=bool(ranking_info),
                has_reviews=bool(review_info),
            )
            feature.cogs_per_unit = _optional_float(
                product_info,
                "cogs_per_unit",
                fallback=_optional_float(sales_info, "cogs_per_unit"),
            )
            feature.gross_profit_estimate = _estimate_gross_profit(feature)
            feature.gross_margin_pct = _estimate_gross_margin(feature)
            feature.supporting_metrics = {
                "sales_rows_count": feature.sales_rows_matched,
                "ad_rows_count": int(_float_value(ad_info, "rows_count")),
                "forecast_source": _string_value(forecast_info, "source"),
                "stock_source": _string_value(stock_info, "source"),
                "ranking_source": _string_value(ranking_info, "source"),
                "reviews_source": _string_value(review_info, "source"),
            }
            features.append(feature)

    return features


def _empty_frame(df: pd.DataFrame | None) -> pd.DataFrame:
    return df.copy() if df is not None else pd.DataFrame()


def _normalize_key(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_frame_keys(df: pd.DataFrame, key_columns: Iterable[str]) -> pd.DataFrame:
    normalized = df.copy()
    for column in key_columns:
        if column in normalized.columns:
            normalized[column] = normalized[column].fillna("").astype(str).str.strip()
    return normalized


def _index_products(products_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if products_df.empty:
        return {}

    normalized = _normalize_frame_keys(products_df, ["sku", "offer_id"])
    name_column = (
        "product_name"
        if "product_name" in normalized.columns
        else "name"
        if "name" in normalized.columns
        else ""
    )
    records: dict[str, dict[str, Any]] = {}
    for record in normalized.to_dict(orient="records"):
        sku = _normalize_key(record.get("sku"))
        if not sku:
            continue
        product_name = record.get(name_column, "") if name_column else ""
        records[sku] = {
            "offer_id": _normalize_key(record.get("offer_id")),
            "product_name": _normalize_key(product_name),
            "price": _safe_float(record.get("price")),
            "sales_price": _safe_float(record.get("sales_price")),
            "cogs_per_unit": _safe_optional_float(
                record.get("cost_price"), record.get("cogs_per_unit")
            ),
            "priority_sku": bool(record.get("priority_sku", False)),
            "external_traffic": bool(record.get("external_traffic", False)),
        }
    return records


def _aggregate_sales(sales_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if sales_df.empty:
        return {}

    normalized = _normalize_frame_keys(sales_df, ["sku", "offer_id"])
    if "sku" not in normalized.columns and "offer_id" not in normalized.columns:
        return {}

    grouping_column = "sku" if "sku" in normalized.columns else "offer_id"
    rows: dict[str, dict[str, Any]] = {}
    for key, group in normalized.groupby(grouping_column, dropna=False):
        normalized_key = _normalize_key(key)
        if not normalized_key:
            continue
        quantity_series = pd.to_numeric(
            group.get("quantity", pd.Series(dtype=float)), errors="coerce"
        ).fillna(0.0)
        revenue_series = pd.to_numeric(
            group.get("revenue", pd.Series(dtype=float)), errors="coerce"
        ).fillna(0.0)
        daily_sales = quantity_series.groupby(
            group.get("date", pd.Series(dtype=object)).astype(str)
        ).sum()
        sales_cv = 0.0
        if len(daily_sales) > 1 and daily_sales.mean() > 0:
            sales_cv = float(daily_sales.std(ddof=0) / daily_sales.mean())
        sales_trend_pct = 0.0
        if len(daily_sales) >= 2:
            first_value = float(daily_sales.iloc[0])
            last_value = float(daily_sales.iloc[-1])
            if first_value > 0:
                sales_trend_pct = ((last_value - first_value) / first_value) * 100.0
        rows[normalized_key] = {
            "quantity": float(quantity_series.sum()),
            "revenue": float(revenue_series.sum()),
            "rows_count": int(len(group)),
            "sales_trend_pct": sales_trend_pct,
            "sales_cv": sales_cv,
            "latest_date": _latest_date(group.get("date", pd.Series(dtype=object))),
            "offer_id": _first_nonempty(group.get("offer_id", pd.Series(dtype=object))),
            "product_name": _first_nonempty(
                group.get("product_name", group.get("name", pd.Series(dtype=object)))
            ),
            "cogs_per_unit": _safe_optional_float(
                _first_nonempty(group.get("cogs_per_unit", pd.Series(dtype=object)))
            ),
        }
    return rows


def _aggregate_advertising(advertising_df: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    if advertising_df.empty:
        return {}

    normalized = _normalize_frame_keys(advertising_df, ["sku", "campaign_id"])
    if "sku" not in normalized.columns:
        return {}

    if "campaign_id" not in normalized.columns:
        normalized["campaign_id"] = ""

    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for (sku, campaign_id), group in normalized.groupby(["sku", "campaign_id"], dropna=False):
        normalized_sku = _normalize_key(sku)
        if not normalized_sku:
            continue
        spend = (
            pd.to_numeric(group.get("spend", pd.Series(dtype=float)), errors="coerce")
            .fillna(0.0)
            .sum()
        )
        impressions = (
            pd.to_numeric(group.get("impressions", pd.Series(dtype=float)), errors="coerce")
            .fillna(0.0)
            .sum()
        )
        clicks = (
            pd.to_numeric(group.get("clicks", pd.Series(dtype=float)), errors="coerce")
            .fillna(0.0)
            .sum()
        )
        orders = (
            pd.to_numeric(group.get("orders", pd.Series(dtype=float)), errors="coerce")
            .fillna(0.0)
            .sum()
        )
        revenue = (
            pd.to_numeric(group.get("revenue", pd.Series(dtype=float)), errors="coerce")
            .fillna(0.0)
            .sum()
        )
        ctr = (clicks / impressions * 100.0) if impressions > 0 else 0.0
        cpc = (spend / clicks) if clicks > 0 else 0.0
        roas = (revenue / spend) if spend > 0 else 0.0
        drr = (spend / revenue * 100.0) if revenue > 0 else 0.0
        rows[(normalized_sku, _normalize_key(campaign_id))] = {
            "spend": float(spend),
            "impressions": float(impressions),
            "clicks": float(clicks),
            "orders": float(orders),
            "revenue": float(revenue),
            "ctr": ctr,
            "cpc": cpc,
            "roas": roas,
            "drr": drr,
            "rows_count": int(len(group)),
            "latest_date": _latest_date(group.get("date", pd.Series(dtype=object))),
            "product_name": _first_nonempty(
                group.get("product_name", group.get("name", pd.Series(dtype=object)))
            ),
            "price": _safe_float(_first_nonempty(group.get("price", pd.Series(dtype=object)))),
        }
    return rows


def _aggregate_forecasts(forecasts_df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if forecasts_df.empty:
        return {}

    normalized = _normalize_frame_keys(forecasts_df, ["sku"])
    if "sku" not in normalized.columns:
        return {}

    rows: dict[str, dict[str, Any]] = {}
    for sku, group in normalized.groupby("sku", dropna=False):
        normalized_sku = _normalize_key(sku)
        if not normalized_sku:
            continue
        rows[normalized_sku] = {
            "forecast_quantity": float(
                pd.to_numeric(
                    group.get("forecast_quantity", pd.Series(dtype=float)), errors="coerce"
                )
                .fillna(0.0)
                .sum()
            ),
            "forecast_revenue": float(
                pd.to_numeric(
                    group.get("forecast_revenue", pd.Series(dtype=float)), errors="coerce"
                )
                .fillna(0.0)
                .sum()
            ),
            "stockout_probability": _safe_optional_float(
                _first_nonempty(group.get("stockout_probability", pd.Series(dtype=object)))
            ),
            "priority_sku": bool(
                _first_nonempty(group.get("priority_sku", pd.Series(dtype=object)))
            ),
            "external_traffic": bool(
                _first_nonempty(group.get("external_traffic", pd.Series(dtype=object)))
            ),
            "latest_date": _latest_date(group.get("date", pd.Series(dtype=object))),
            "source": "forecast_df",
        }
    return rows


def _aggregate_stock(stock_df: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    normalized = _empty_frame(stock_df)
    if normalized.empty or "sku" not in normalized.columns:
        return {}

    normalized = _normalize_frame_keys(normalized, ["sku"])
    rows: dict[str, dict[str, Any]] = {}
    for sku, group in normalized.groupby("sku", dropna=False):
        normalized_sku = _normalize_key(sku)
        if not normalized_sku:
            continue
        current_stock = pd.to_numeric(
            group.get(
                "current_stock",
                group.get("available_stock", group.get("stock_total", pd.Series(dtype=float))),
            ),
            errors="coerce",
        ).fillna(0.0)
        stock_days = _safe_optional_float(
            _first_nonempty(group.get("stock_days", pd.Series(dtype=object)))
        )
        rows[normalized_sku] = {
            "current_stock": float(current_stock.iloc[-1]) if not current_stock.empty else 0.0,
            "stock_days": stock_days,
            "stockout_probability": _safe_optional_float(
                _first_nonempty(group.get("stockout_probability", pd.Series(dtype=object)))
            ),
            "source": "stock_df",
        }
    return rows


def _aggregate_ranking(ranking_df: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    normalized = _empty_frame(ranking_df)
    if normalized.empty or "sku" not in normalized.columns:
        return {}

    normalized = _normalize_frame_keys(normalized, ["sku"])
    rows: dict[str, dict[str, Any]] = {}
    for sku, group in normalized.groupby("sku", dropna=False):
        normalized_sku = _normalize_key(sku)
        if not normalized_sku:
            continue
        position_series = pd.to_numeric(
            group.get("ranking_position", group.get("position", pd.Series(dtype=float))),
            errors="coerce",
        ).dropna()
        if position_series.empty:
            continue
        latest_position = float(position_series.iloc[-1])
        trend = 0.0
        if len(position_series) >= 2:
            trend = float(position_series.iloc[-1] - position_series.iloc[0])
        rows[normalized_sku] = {
            "ranking_position": latest_position,
            "ranking_trend": trend,
            "source": "ranking_df",
        }
    return rows


def _aggregate_reviews(reviews_df: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    normalized = _empty_frame(reviews_df)
    if normalized.empty or "sku" not in normalized.columns:
        return {}

    normalized = _normalize_frame_keys(normalized, ["sku"])
    rows: dict[str, dict[str, Any]] = {}
    for sku, group in normalized.groupby("sku", dropna=False):
        normalized_sku = _normalize_key(sku)
        if not normalized_sku:
            continue
        rows[normalized_sku] = {
            "review_rating": _safe_optional_float(
                _first_nonempty(
                    group.get("review_rating", group.get("rating", pd.Series(dtype=object)))
                )
            ),
            "review_count": int(
                _safe_float(
                    _first_nonempty(
                        group.get(
                            "review_count", group.get("reviews_count", pd.Series(dtype=object))
                        )
                    )
                )
            ),
            "source": "reviews_df",
        }
    return rows


def _estimate_gross_profit(feature: DecisionFeature) -> float | None:
    if feature.cogs_per_unit is None:
        return None
    if feature.sales_quantity <= 0 and feature.ad_revenue <= 0:
        return None
    revenue = feature.sales_revenue if feature.sales_revenue > 0 else feature.ad_revenue
    quantity = feature.sales_quantity if feature.sales_quantity > 0 else feature.ad_orders
    return revenue - (feature.cogs_per_unit * quantity) - feature.ad_spend


def _estimate_gross_margin(feature: DecisionFeature) -> float | None:
    if feature.gross_profit_estimate is None:
        return None
    revenue = feature.sales_revenue if feature.sales_revenue > 0 else feature.ad_revenue
    if revenue <= 0:
        return None
    return feature.gross_profit_estimate / revenue * 100.0


def _resolve_price(
    product_info: dict[str, Any],
    sales_info: dict[str, Any],
    ad_info: dict[str, Any],
) -> float:
    price_candidates = (
        _safe_optional_float(product_info.get("price")),
        _safe_optional_float(product_info.get("sales_price")),
        _safe_optional_float(ad_info.get("price")),
    )
    for candidate in price_candidates:
        if candidate is not None and candidate > 0:
            return candidate
    quantity = _float_value(sales_info, "quantity")
    revenue = _float_value(sales_info, "revenue")
    if quantity > 0:
        return revenue / quantity
    return 0.0


def _float_value(values: dict[str, Any], key: str) -> float:
    return _safe_float(values.get(key))


def _optional_float(
    values: dict[str, Any], key: str, fallback: float | None = None
) -> float | None:
    value = _safe_optional_float(values.get(key))
    return fallback if value is None else value


def _string_value(values: dict[str, Any], key: str, fallback: str = "") -> str:
    value = values.get(key, fallback)
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _bool_value(values: dict[str, Any], key: str, fallback: bool = False) -> bool:
    value = values.get(key, fallback)
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _latest_date(series: pd.Series) -> str:
    if series.empty:
        return ""
    parsed_dates = pd.to_datetime(series, errors="coerce").dropna()
    if parsed_dates.empty:
        return ""
    return str(parsed_dates.max().date())


def _first_nonempty(series: pd.Series) -> Any:
    if series.empty:
        return ""
    for value in series.tolist():
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return value
    return ""


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if isnan(converted) else converted


def _safe_optional_float(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, pd.Series):
            value = _first_nonempty(value)
        if value is None or value == "":
            continue
        try:
            converted = float(value)
        except (TypeError, ValueError):
            continue
        if not isnan(converted):
            return converted
    return None


def _iter_dates(*values: Any) -> Iterable[str]:
    for value in values:
        text = _normalize_key(value)
        if text:
            yield text


def _calculate_freshness_days(values: Iterable[str]) -> float:
    parsed: list[date] = []
    for value in values:
        try:
            parsed.append(datetime.fromisoformat(value).date())
        except ValueError:
            continue
    if not parsed:
        return 999.0
    latest = max(parsed)
    return float((date.today() - latest).days)
