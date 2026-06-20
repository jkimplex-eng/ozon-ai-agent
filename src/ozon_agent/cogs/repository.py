"""COGS data repository — DB + file fallback."""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ozon_agent.cogs.models import CogsRecord

logger = logging.getLogger(__name__)

DATA_DIR = Path("data") / "cogs"
FILE_PATH = DATA_DIR / "cogs.json"

ConnectionFactory = Any
_connection_factory: Any = None
_default_factory_loaded = False


def _get_connection_factory() -> Any:
    global _connection_factory, _default_factory_loaded
    if _connection_factory is not None:
        return _connection_factory
    if not _default_factory_loaded:
        from ozon_agent.db.connection import get_connection
        _connection_factory = get_connection
        _default_factory_loaded = True
    return _connection_factory


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_record(record: CogsRecord) -> None:
    """Save COGS record to DB or file fallback."""
    try:
        _save_to_db(record)
    except Exception as e:
        logger.warning("DB unavailable for COGS save, using file: %s", e)
        _save_to_file(record)


def get_record(sku: str) -> CogsRecord | None:
    """Load COGS record by SKU."""
    try:
        return _get_from_db(sku)
    except Exception as e:
        logger.debug("DB unavailable for COGS lookup, using file: %s", e)
        return _get_from_file(sku)


def list_records() -> list[CogsRecord]:
    """List all COGS records."""
    try:
        return _list_from_db()
    except Exception as e:
        logger.debug("DB unavailable for COGS list, using file: %s", e)
        return _list_from_file()


def delete_record(sku: str) -> bool:
    """Delete COGS record by SKU."""
    try:
        return _delete_from_db(sku)
    except Exception as e:
        logger.debug("DB unavailable for COGS delete, using file: %s", e)
        return _delete_from_file(sku)


def clear_all() -> int:
    """Clear all COGS records."""
    try:
        return _clear_db()
    except Exception as e:
        logger.debug("DB unavailable for COGS clear, using file: %s", e)
        return _clear_file()


# --- DB functions ---

def _execute_db(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    """Execute SQL using the connection factory."""
    factory = _get_connection_factory()
    with factory() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if cur.description else []
        conn.commit()
    return [dict(row) for row in rows]


def _save_to_db(record: CogsRecord) -> None:
    sql = """
        INSERT INTO cogs (id, sku, offer_id, product_name, unit_cost,
                          logistics_cost, packaging_cost, source, updated_at)
        VALUES (%(id)s, %(sku)s, %(offer_id)s, %(product_name)s, %(unit_cost)s,
                %(logistics_cost)s, %(packaging_cost)s, %(source)s, %(updated_at)s)
        ON CONFLICT (sku) DO UPDATE SET
            offer_id = EXCLUDED.offer_id,
            product_name = EXCLUDED.product_name,
            unit_cost = EXCLUDED.unit_cost,
            logistics_cost = EXCLUDED.logistics_cost,
            packaging_cost = EXCLUDED.packaging_cost,
            source = EXCLUDED.source,
            updated_at = EXCLUDED.updated_at
    """
    _execute_db(sql, {
        "id": record.id,
        "sku": record.sku,
        "offer_id": record.offer_id,
        "product_name": record.product_name,
        "unit_cost": record.unit_cost,
        "logistics_cost": record.logistics_cost,
        "packaging_cost": record.packaging_cost,
        "source": record.source,
        "updated_at": record.updated_at,
    })


def _get_from_db(sku: str) -> CogsRecord | None:
    rows = _execute_db("SELECT * FROM cogs WHERE sku = %(sku)s", {"sku": sku})
    if not rows:
        return None
    return _row_to_record(rows[0])


def _list_from_db() -> list[CogsRecord]:
    rows = _execute_db("SELECT * FROM cogs ORDER BY sku")
    return [_row_to_record(r) for r in rows]


def _delete_from_db(sku: str) -> bool:
    _execute_db("DELETE FROM cogs WHERE sku = %(sku)s", {"sku": sku})
    return True


def _clear_db() -> int:
    rows = _execute_db("SELECT id FROM cogs")
    count = len(rows)
    _execute_db("DELETE FROM cogs")
    return count


# --- File functions ---

def _save_to_file(record: CogsRecord) -> None:
    _ensure_data_dir()
    records = _list_from_file()
    records = [r for r in records if r.sku != record.sku]
    records.append(record)
    _write_file(records)


def _get_from_file(sku: str) -> CogsRecord | None:
    records = _list_from_file()
    for r in records:
        if r.sku == sku:
            return r
    return None


def _list_from_file() -> list[CogsRecord]:
    if not FILE_PATH.exists():
        return []
    try:
        data = json.loads(FILE_PATH.read_text(encoding="utf-8"))
        return [_json_to_record(item) for item in data]
    except Exception:
        return []


def _delete_from_file(sku: str) -> bool:
    records = _list_from_file()
    before = len(records)
    records = [r for r in records if r.sku != sku]
    if len(records) < before:
        _write_file(records)
        return True
    return False


def _clear_file() -> int:
    if FILE_PATH.exists():
        count = len(_list_from_file())
        _write_file([])
        return count
    return 0


def _write_file(records: list[CogsRecord]) -> None:
    _ensure_data_dir()
    data = [_record_to_json(r) for r in records]
    FILE_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _record_to_json(record: CogsRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "sku": record.sku,
        "offer_id": record.offer_id,
        "product_name": record.product_name,
        "unit_cost": record.unit_cost,
        "logistics_cost": record.logistics_cost,
        "packaging_cost": record.packaging_cost,
        "source": record.source,
        "updated_at": record.updated_at.isoformat(),
    }


def _json_to_record(data: dict[str, Any]) -> CogsRecord:
    return CogsRecord(
        id=data.get("id", str(uuid4())),
        sku=data["sku"],
        offer_id=data.get("offer_id"),
        product_name=data.get("product_name"),
        unit_cost=float(data.get("unit_cost", 0)),
        logistics_cost=float(data.get("logistics_cost", 0)),
        packaging_cost=float(data.get("packaging_cost", 0)),
        source=data.get("source", "manual"),
        updated_at=(
            datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.now(UTC)
        ),
    )


def _row_to_record(row: dict[str, Any]) -> CogsRecord:
    return CogsRecord(
        id=str(row["id"]),
        sku=str(row["sku"]),
        offer_id=row.get("offer_id"),
        product_name=row.get("product_name"),
        unit_cost=float(row["unit_cost"]),
        logistics_cost=float(row.get("logistics_cost", 0)),
        packaging_cost=float(row.get("packaging_cost", 0)),
        source=row.get("source", "manual"),
        updated_at=(
            row["updated_at"]
            if isinstance(row["updated_at"], datetime)
            else datetime.now(UTC)
        ),
    )


@contextmanager
def override_connection_factory(factory: ConnectionFactory) -> Any:
    """Override the connection factory for testing."""
    global _connection_factory, _default_factory_loaded
    previous = _connection_factory
    _connection_factory = factory
    _default_factory_loaded = True
    try:
        yield
    finally:
        _connection_factory = previous
        _default_factory_loaded = False
