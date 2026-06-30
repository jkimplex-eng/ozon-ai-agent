"""Repository for supply proposals."""
from __future__ import annotations

import json
import logging
from typing import Any

from ozon_agent.db.connection import get_connection

from .models import ProposalStatus, SupplyProposal

logger = logging.getLogger(__name__)

PROPOSAL_COLUMNS = [
    "proposal_id",
    "sku",
    "offer_id",
    "product_name",
    "quantity",
    "target_warehouse_id",
    "target_warehouse_name",
    "target_cluster_id",
    "target_cluster_name",
    "reason",
    "expected_prevented_loss",
    "confidence",
    "data_sources",
    "status",
    "draft_id",
    "supply_id",
    "timeslot_id",
    "draft_payload",
    "created_at",
    "approved_at",
    "approved_by",
    "rejected_reason",
    "error_message",
]


def _row_value(row: Any, key: str) -> Any:
    if hasattr(row, "keys"):
        return row[key]
    return row[PROPOSAL_COLUMNS.index(key)]


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _proposal_from_row(row: Any) -> SupplyProposal:
    return SupplyProposal(
        proposal_id=_row_value(row, "proposal_id"),
        sku=_row_value(row, "sku"),
        offer_id=_row_value(row, "offer_id"),
        product_name=_row_value(row, "product_name"),
        quantity=_row_value(row, "quantity"),
        target_warehouse_id=_row_value(row, "target_warehouse_id"),
        target_warehouse_name=_row_value(row, "target_warehouse_name"),
        target_cluster_id=_row_value(row, "target_cluster_id"),
        target_cluster_name=_row_value(row, "target_cluster_name"),
        reason=_row_value(row, "reason"),
        expected_prevented_loss=_row_value(row, "expected_prevented_loss"),
        confidence=_row_value(row, "confidence"),
        data_sources=_json_value(_row_value(row, "data_sources"), []),
        status=ProposalStatus(_row_value(row, "status")),
        draft_id=_row_value(row, "draft_id"),
        supply_id=_row_value(row, "supply_id"),
        timeslot_id=_row_value(row, "timeslot_id"),
        draft_payload=_json_value(_row_value(row, "draft_payload"), None),
        created_at=_row_value(row, "created_at"),
        approved_at=_row_value(row, "approved_at"),
        approved_by=_row_value(row, "approved_by"),
        rejected_reason=_row_value(row, "rejected_reason"),
        error_message=_row_value(row, "error_message"),
    )


def create_proposal(proposal: SupplyProposal) -> str:
    """Create new supply proposal in database."""
    query = """
        INSERT INTO supply_proposals (
            proposal_id, sku, offer_id, product_name, quantity,
            target_warehouse_id, target_warehouse_name,
            target_cluster_id, target_cluster_name,
            reason, expected_prevented_loss, confidence,
            data_sources, status, draft_payload, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING proposal_id
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    proposal.proposal_id,
                    proposal.sku,
                    proposal.offer_id,
                    proposal.product_name,
                    proposal.quantity,
                    proposal.target_warehouse_id,
                    proposal.target_warehouse_name,
                    proposal.target_cluster_id,
                    proposal.target_cluster_name,
                    proposal.reason,
                    proposal.expected_prevented_loss,
                    proposal.confidence,
                    json.dumps(proposal.data_sources),
                    proposal.status.value,
                    json.dumps(proposal.draft_payload) if proposal.draft_payload else None,
                    proposal.created_at,
                ),
            )
            conn.commit()
            return proposal.proposal_id


def get_proposal(proposal_id: str) -> SupplyProposal | None:
    """Get proposal by ID."""
    query = f"""
        SELECT {", ".join(PROPOSAL_COLUMNS)}
        FROM supply_proposals
        WHERE proposal_id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (proposal_id,))
            row = cur.fetchone()
            return _proposal_from_row(row) if row else None


def list_proposals(
    status: ProposalStatus | None = None,
    limit: int = 50,
) -> list[SupplyProposal]:
    """List proposals with optional status filter."""
    query = f"""
        SELECT {", ".join(PROPOSAL_COLUMNS)}
        FROM supply_proposals
    """
    params: list[Any] = []

    if status:
        query += " WHERE status = %s"
        params.append(status.value)

    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [_proposal_from_row(row) for row in rows]


def update_proposal_status(
    proposal_id: str,
    status: ProposalStatus,
    **kwargs: Any,
) -> None:
    """Update proposal status and optional fields."""
    allowed_fields = {
        "draft_id",
        "supply_id",
        "timeslot_id",
        "draft_payload",
        "approved_at",
        "approved_by",
        "rejected_reason",
        "error_message",
    }

    set_clauses = ["status = %s"]
    params: list[Any] = [status.value]

    for field, value in kwargs.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = %s")
            params.append(json.dumps(value) if isinstance(value, (dict, list)) else value)

    params.append(proposal_id)

    query = f"""
        UPDATE supply_proposals
        SET {", ".join(set_clauses)}
        WHERE proposal_id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()

    logger.info("Updated proposal %s to status %s", proposal_id, status.value)
