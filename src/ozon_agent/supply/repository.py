"""Repository for supply proposals."""
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from ozon_agent.db.connection import get_connection
from .models import ProposalStatus, SupplyProposal

logger = logging.getLogger(__name__)


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
    query = """
        SELECT 
            proposal_id, sku, offer_id, product_name, quantity,
            target_warehouse_id, target_warehouse_name,
            target_cluster_id, target_cluster_name,
            reason, expected_prevented_loss, confidence,
            data_sources, status, draft_id, supply_id, timeslot_id,
            draft_payload, created_at, approved_at, approved_by,
            rejected_reason, error_message
        FROM supply_proposals
        WHERE proposal_id = %s
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (proposal_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return SupplyProposal(
                proposal_id=row[0],
                sku=row[1],
                offer_id=row[2],
                product_name=row[3],
                quantity=row[4],
                target_warehouse_id=row[5],
                target_warehouse_name=row[6],
                target_cluster_id=row[7],
                target_cluster_name=row[8],
                reason=row[9],
                expected_prevented_loss=row[10],
                confidence=row[11],
                data_sources=row.get( data_sources, []) if isinstance(row.get(data_sources), list) else json.loads(row.get(data_sources, [])),
                status=ProposalStatus(row[13]),
                draft_id=row[14],
                supply_id=row[15],
                timeslot_id=row[16],
                draft_payload=row.get(draft_payload) if isinstance(row.get(draft_payload), (dict, list)) else json.loads(row.get(draft_payload, null)),
                created_at=row[18],
                approved_at=row[19],
                approved_by=row[20],
                rejected_reason=row[21],
                error_message=row[22],
            )


def list_proposals(
    status: ProposalStatus | None = None,
    limit: int = 50,
) -> list[SupplyProposal]:
    """List proposals with optional status filter."""
    query = """
        SELECT 
            proposal_id, sku, offer_id, product_name, quantity,
            target_warehouse_id, target_warehouse_name,
            target_cluster_id, target_cluster_name,
            reason, expected_prevented_loss, confidence,
            data_sources, status, draft_id, supply_id, timeslot_id,
            draft_payload, created_at, approved_at, approved_by,
            rejected_reason, error_message
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
            
            proposals = []
            for row in rows:
                proposals.append(
                    SupplyProposal(
                        proposal_id=row['proposal_id'],
                        sku=row['sku'],
                        offer_id=row['offer_id'],
                        product_name=row['product_name'],
                        quantity=row['quantity'],
                        target_warehouse_id=row['target_warehouse_id'],
                        target_warehouse_name=row['target_warehouse_name'],
                        target_cluster_id=row['target_cluster_id'],
                        target_cluster_name=row['target_cluster_name'],
                        reason=row['reason'],
                        expected_prevented_loss=row['expected_prevented_loss'],
                        confidence=row['confidence'],
                        data_sources=row["data_sources"] or [],
                        status=ProposalStatus(row['status']),
                        draft_id=row['draft_id'],
                        supply_id=row['supply_id'],
                        timeslot_id=row['timeslot_id'],
                        draft_payload=row["draft_payload"] or None,
                        created_at=row['created_at'],
                        approved_at=row['approved_at'],
                        approved_by=row['approved_by'],
                        rejected_reason=row['rejected_reason'],
                        error_message=row['error_message'],
                    )
                )
            
            return proposals


def update_proposal_status(
    proposal_id: str,
    status: ProposalStatus,
    **kwargs: Any,
) -> None:
    """Update proposal status and optional fields."""
    allowed_fields = {
        "draft_id", "supply_id", "timeslot_id", "draft_payload",
        "approved_at", "approved_by", "rejected_reason", "error_message",
    }
    
    set_clauses = ["status = %s"]
    params: list[Any] = [status.value]
    
    for field, value in kwargs.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = %s")
            if isinstance(value, (dict, list)):
                params.append(json.dumps(value))
            else:
                params.append(value)
    
    params.append(proposal_id)
    
    query = f"""
        UPDATE supply_proposals
        SET {', '.join(set_clauses)}
        WHERE proposal_id = %s
    """
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    
    logger.info(f"Updated proposal {proposal_id} to status {status.value}")
