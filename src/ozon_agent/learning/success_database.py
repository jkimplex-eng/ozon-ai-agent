"""Recommendation success database — stores outcomes and calculates success rates."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SUCCESS_DB_PATH = Path("data/recommendation_success")


@dataclass(frozen=True)
class SuccessRecord:
    recommendation_id: str
    sku: str
    action: str
    result: str
    success_score: float
    profit_delta: float | None
    revenue_delta: float | None
    recorded_at: str
    category: str = ""
    market: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionTypeStats:
    action: str
    total: int
    successes: int
    failures: int
    partial: int
    unknown: int
    success_rate: float
    average_score: float
    average_profit_delta: float | None
    average_revenue_delta: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkuStats:
    sku: str
    total: int
    successes: int
    failures: int
    success_rate: float
    average_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SuccessDatabase:
    total_records: int
    overall_success_rate: float
    overall_average_score: float
    by_action: dict[str, ActionTypeStats]
    by_sku: dict[str, SkuStats]
    records: list[SuccessRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_records": self.total_records,
            "overall_success_rate": self.overall_success_rate,
            "overall_average_score": self.overall_average_score,
            "by_action": {k: v.to_dict() for k, v in self.by_action.items()},
            "by_sku": {k: v.to_dict() for k, v in self.by_sku.items()},
            "record_count": len(self.records),
        }


def save_success_record(
    record: SuccessRecord,
    root: str | Path | None = None,
) -> Path:
    """Save a success record."""
    path = Path(root) if root else SUCCESS_DB_PATH
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / f"{record.recommendation_id}.json"
    file_path.write_text(
        json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return file_path


def load_success_records(
    root: str | Path | None = None,
) -> list[SuccessRecord]:
    """Load all success records."""
    path = Path(root) if root else SUCCESS_DB_PATH
    if not path.exists():
        return []

    records = []
    for file_path in sorted(path.glob("*.json")):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            records.append(SuccessRecord(**data))
        except Exception as e:
            logger.warning("Failed to load success record %s: %s", file_path, e)

    return records


def build_success_database(
    root: str | Path | None = None,
) -> SuccessDatabase:
    """Build the full success database from all records."""
    records = load_success_records(root)

    if not records:
        return SuccessDatabase(
            total_records=0,
            overall_success_rate=0.0,
            overall_average_score=0.0,
            by_action={},
            by_sku={},
            records=[],
        )

    total = len(records)
    successes = sum(1 for r in records if r.result == "SUCCESS")
    overall_rate = successes / total if total > 0 else 0.0
    overall_score = sum(r.success_score for r in records) / total if total > 0 else 0.0

    by_action: dict[str, list[SuccessRecord]] = defaultdict(list)
    by_sku: dict[str, list[SuccessRecord]] = defaultdict(list)

    for record in records:
        by_action[record.action].append(record)
        by_sku[record.sku].append(record)

    action_stats = {}
    for action, action_records in by_action.items():
        n = len(action_records)
        s = sum(1 for r in action_records if r.result == "SUCCESS")
        f = sum(1 for r in action_records if r.result == "FAILURE")
        p = sum(1 for r in action_records if r.result == "PARTIAL_SUCCESS")
        u = sum(1 for r in action_records if r.result == "UNKNOWN")
        avg_score = sum(r.success_score for r in action_records) / n if n > 0 else 0.0
        profit_deltas = [r.profit_delta for r in action_records if r.profit_delta is not None]
        revenue_deltas = [r.revenue_delta for r in action_records if r.revenue_delta is not None]
        action_stats[action] = ActionTypeStats(
            action=action,
            total=n,
            successes=s,
            failures=f,
            partial=p,
            unknown=u,
            success_rate=s / n if n > 0 else 0.0,
            average_score=avg_score,
            average_profit_delta=(
                sum(profit_deltas) / len(profit_deltas) if profit_deltas else None
            ),
            average_revenue_delta=(
                sum(revenue_deltas) / len(revenue_deltas) if revenue_deltas else None
            ),
        )

    sku_stats = {}
    for sku, sku_records in by_sku.items():
        n = len(sku_records)
        s = sum(1 for r in sku_records if r.result == "SUCCESS")
        f = sum(1 for r in sku_records if r.result == "FAILURE")
        avg_score = sum(r.success_score for r in sku_records) / n if n > 0 else 0.0
        sku_stats[sku] = SkuStats(
            sku=sku,
            total=n,
            successes=s,
            failures=f,
            success_rate=s / n if n > 0 else 0.0,
            average_score=avg_score,
        )

    return SuccessDatabase(
        total_records=total,
        overall_success_rate=overall_rate,
        overall_average_score=overall_score,
        by_action=action_stats,
        by_sku=sku_stats,
        records=records,
    )


def get_confidence_explanation(
    action: str,
    sku: str | None = None,
    root: str | Path | None = None,
) -> str:
    """Generate human-readable confidence explanation."""
    db = build_success_database(root)

    action_stats = db.by_action.get(action)
    if not action_stats or action_stats.total == 0:
        return f"Confidence: LOW (no historical data for action '{action}')"

    base_confidence = action_stats.success_rate * 100

    sku_stats = db.by_sku.get(sku) if sku else None
    if sku_stats and sku_stats.total >= 3:
        sku_modifier = (sku_stats.success_rate - action_stats.success_rate) * 20
        base_confidence = max(0, min(100, base_confidence + sku_modifier))

    confidence_pct = round(base_confidence, 1)

    parts = [f"Confidence: {confidence_pct}%"]
    parts.append("Based on:")
    parts.append(f"  - {action_stats.total} similar cases for action '{action}'")
    parts.append(f"  - Success rate: {action_stats.success_rate * 100:.1f}%")
    if action_stats.average_profit_delta is not None:
        parts.append(f"  - Average profit impact: {action_stats.average_profit_delta:+.1f}%")
    if sku_stats and sku_stats.total > 0:
        sku_rate = sku_stats.success_rate * 100
        parts.append(f"  - SKU-specific: {sku_stats.total} cases, {sku_rate:.1f}% success")

    return "\n".join(parts)


def save_database_report(
    db: SuccessDatabase,
    output_dir: str | Path = "data/recommendation_success",
) -> Path:
    """Save database summary report."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    report_path = path / "success_database_report.json"
    report_path.write_text(
        json.dumps(db.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path
