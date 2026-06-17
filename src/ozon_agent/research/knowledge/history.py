from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from ozon_agent.research.knowledge.models import (
    CompetitorHistoryRecord,
    MarketInsightRecord,
    MarketKnowledgeSnapshot,
    MarketTrend,
)
from ozon_agent.research.knowledge.repository import (
    competitor_key,
    history_record_from_observation,
)


def build_history(snapshots: list[MarketKnowledgeSnapshot]) -> list[CompetitorHistoryRecord]:
    records: list[CompetitorHistoryRecord] = []
    for snapshot in sorted(snapshots, key=lambda item: item.captured_at):
        records.extend(
            history_record_from_observation(snapshot.id, observation)
            for observation in snapshot.observations
        )
    return records


def compare_snapshots(
    previous: MarketKnowledgeSnapshot,
    current: MarketKnowledgeSnapshot,
) -> list[MarketInsightRecord]:
    return detect_changes(previous, current)


def detect_changes(
    previous: MarketKnowledgeSnapshot,
    current: MarketKnowledgeSnapshot,
) -> list[MarketInsightRecord]:
    previous_rows = {_observation_key(item): item for item in previous.observations}
    current_rows = {_observation_key(item): item for item in current.observations}
    insights: list[MarketInsightRecord] = []

    for key in sorted(set(current_rows) - set(previous_rows)):
        row = current_rows[key]
        insights.append(
            _insight(
                "NEW_COMPETITOR",
                current,
                row.sku,
                f"New competitor appeared: {_competitor_label(row.seller_name, row.source_url)}",
                "MEDIUM",
                previous_snapshot_id=previous.id,
                competitor_key=key,
            )
        )

    for key in sorted(set(previous_rows) - set(current_rows)):
        row = previous_rows[key]
        insights.append(
            _insight(
                "COMPETITOR_DISAPPEARED",
                current,
                row.sku,
                f"Competitor disappeared: {_competitor_label(row.seller_name, row.source_url)}",
                "MEDIUM",
                previous_snapshot_id=previous.id,
                competitor_key=key,
            )
        )

    for key in sorted(set(previous_rows) & set(current_rows)):
        insights.extend(
            _detect_row_changes(previous, current, key, previous_rows[key], current_rows[key])
        )

    return insights


def detect_trends(snapshots: list[MarketKnowledgeSnapshot]) -> list[MarketTrend]:
    return [
        *detect_price_trend(snapshots),
        *detect_rating_trend(snapshots),
        *detect_review_trend(snapshots),
    ]


def detect_price_trend(snapshots: list[MarketKnowledgeSnapshot]) -> list[MarketTrend]:
    return _detect_metric_trend(snapshots, "price")


def detect_rating_trend(snapshots: list[MarketKnowledgeSnapshot]) -> list[MarketTrend]:
    return _detect_metric_trend(snapshots, "rating")


def detect_review_trend(snapshots: list[MarketKnowledgeSnapshot]) -> list[MarketTrend]:
    return _detect_metric_trend(snapshots, "review_count")


def _detect_row_changes(
    previous_snapshot: MarketKnowledgeSnapshot,
    current_snapshot: MarketKnowledgeSnapshot,
    key: str,
    previous: object,
    current: object,
) -> list[MarketInsightRecord]:
    previous_price = getattr(previous, "price")
    current_price = getattr(current, "price")
    previous_rating = getattr(previous, "rating")
    current_rating = getattr(current, "rating")
    previous_reviews = getattr(previous, "review_count")
    current_reviews = getattr(current, "review_count")
    previous_available = getattr(previous, "available")
    current_available = getattr(current, "available")
    sku = str(getattr(current, "sku"))
    insights: list[MarketInsightRecord] = []
    insights.extend(
        _numeric_change(
            "PRICE_CHANGED",
            "price",
            previous_price,
            current_price,
            previous_snapshot,
            current_snapshot,
            sku,
            key,
        )
    )
    insights.extend(
        _numeric_change(
            "RATING_CHANGED",
            "rating",
            previous_rating,
            current_rating,
            previous_snapshot,
            current_snapshot,
            sku,
            key,
        )
    )
    insights.extend(
        _numeric_change(
            "REVIEWS_CHANGED",
            "review_count",
            previous_reviews,
            current_reviews,
            previous_snapshot,
            current_snapshot,
            sku,
            key,
        )
    )
    if previous_available is not None and current_available is not None:
        if previous_available != current_available:
            status = "available" if current_available else "unavailable"
            insights.append(
                _insight(
                    "AVAILABILITY_CHANGED",
                    current_snapshot,
                    sku,
                    f"Competitor availability changed to {status}",
                    "HIGH",
                    previous_snapshot_id=previous_snapshot.id,
                    competitor_key=key,
                    metrics={"previous": previous_available, "current": current_available},
                )
            )
    return insights


def _numeric_change(
    insight_type: str,
    metric: str,
    previous_value: float | int | None,
    current_value: float | int | None,
    previous_snapshot: MarketKnowledgeSnapshot,
    current_snapshot: MarketKnowledgeSnapshot,
    sku: str,
    key: str,
) -> list[MarketInsightRecord]:
    if previous_value is None or current_value is None or previous_value == current_value:
        return []
    delta = float(current_value) - float(previous_value)
    delta_percent = _delta_percent(float(previous_value), float(current_value))
    direction = "increased" if delta > 0 else "decreased"
    severity = "HIGH" if abs(delta_percent or 0) >= 10 else "MEDIUM"
    message = f"Competitor {metric} {direction} by {_format_delta(delta, delta_percent)}"
    return [
        _insight(
            insight_type,
            current_snapshot,
            sku,
            message,
            severity,
            previous_snapshot_id=previous_snapshot.id,
            competitor_key=key,
            metrics={
                "metric": metric,
                "previous": previous_value,
                "current": current_value,
                "delta": delta,
                "delta_percent": delta_percent,
            },
        )
    ]


def _detect_metric_trend(
    snapshots: list[MarketKnowledgeSnapshot],
    metric: str,
) -> list[MarketTrend]:
    values_by_key: dict[str, list[tuple[MarketKnowledgeSnapshot, float]]] = defaultdict(list)
    for snapshot in sorted(snapshots, key=lambda item: item.captured_at):
        for observation in snapshot.observations:
            value = getattr(observation, metric)
            if value is not None:
                values_by_key[_observation_key(observation)].append((snapshot, float(value)))

    trends: list[MarketTrend] = []
    for key, values in values_by_key.items():
        if len(values) < 2:
            continue
        first_snapshot, first_value = values[0]
        _, last_value = values[-1]
        delta = last_value - first_value
        if delta == 0:
            continue
        direction = "UP" if delta > 0 else "DOWN"
        sku = _sku_from_key(key, first_snapshot)
        trends.append(
            MarketTrend(
                sku=sku,
                competitor_key=key,
                metric=metric,
                direction=direction,
                first_value=first_value,
                last_value=last_value,
                delta=delta,
                delta_percent=_delta_percent(first_value, last_value),
                snapshot_count=len(values),
            )
        )
    return sorted(trends, key=lambda item: (item.sku, item.metric, item.competitor_key))


def _insight(
    insight_type: str,
    current_snapshot: MarketKnowledgeSnapshot,
    sku: str,
    message: str,
    severity: str,
    previous_snapshot_id: str | None = None,
    competitor_key: str | None = None,
    metrics: dict[str, object] | None = None,
) -> MarketInsightRecord:
    return MarketInsightRecord(
        id=f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
        insight_type=insight_type,
        sku=sku,
        message=message,
        severity=severity,
        snapshot_id=current_snapshot.id,
        previous_snapshot_id=previous_snapshot_id,
        current_snapshot_id=current_snapshot.id,
        competitor_key=competitor_key,
        metrics=dict(metrics or {}),
    )


def _observation_key(observation: object) -> str:
    return competitor_key(observation)  # type: ignore[arg-type]


def _competitor_label(seller_name: str, source_url: str) -> str:
    if seller_name and source_url:
        return f"{seller_name} ({source_url})"
    return seller_name or source_url or "unknown"


def _delta_percent(previous: float, current: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def _format_delta(delta: float, delta_percent: float | None) -> str:
    if delta_percent is None:
        return f"{delta:.2f}"
    return f"{delta:.2f} ({delta_percent:.1f}%)"


def _sku_from_key(key: str, snapshot: MarketKnowledgeSnapshot) -> str:
    for observation in snapshot.observations:
        if _observation_key(observation) == key:
            return observation.sku
    return key.split("|", maxsplit=1)[0]
