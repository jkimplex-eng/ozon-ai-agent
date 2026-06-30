"""Supply Proposal Manager - handles proposal lifecycle."""
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.models import DraftPayload, ProposalStatus, SupplyProposal
from ozon_agent.supply.repository import (
    create_proposal,
    get_proposal,
    list_proposals,
    update_proposal_status,
)

logger = logging.getLogger(__name__)


class ProposalManager:
    """Manage supply proposal lifecycle with approval gates."""

    def __init__(self, client: OzonClient) -> None:
        self._client = client
        self._supply_client = SupplyAPIClient(client)

    def create_proposals_from_plans(
        self,
        plans: list[dict[str, Any]],
    ) -> list[SupplyProposal]:
        """Create proposals from supply plans."""
        proposals = []

        for plan in plans:
            existing = self._check_duplicate_proposal(
                sku=plan["sku"],
                warehouse_id=plan["target_warehouse_id"],
            )

            if existing:
                logger.info(f"Skipping duplicate proposal for SKU {plan['sku']}")
                continue

            draft_payload = {
                "warehouse_id": plan["target_warehouse_id"],
                "cluster_id": str(plan["target_cluster_id"]),
                "items": [
                    {
                        "sku": plan["sku"],
                        "quantity": plan["quantity"],
                    }
                ],
            }

            proposal = SupplyProposal(
                proposal_id=str(uuid.uuid4()),
                sku=plan["sku"],
                offer_id=plan["offer_id"],
                product_name=plan["product_name"],
                quantity=plan["quantity"],
                target_warehouse_id=plan["target_warehouse_id"],
                target_warehouse_name=plan["target_warehouse_name"],
                target_cluster_id=str(plan["target_cluster_id"]),
                target_cluster_name=plan["target_cluster_name"],
                reason=plan["reason"],
                expected_prevented_loss=plan["expected_prevented_loss"],
                confidence=plan["confidence"],
                data_sources=plan["data_sources"],
                status=ProposalStatus.PROPOSED,
                draft_payload=draft_payload,
            )

            create_proposal(proposal)
            proposals.append(proposal)

            logger.info(f"Created proposal {proposal.proposal_id} for SKU {proposal.sku}")

        return proposals

    def _check_duplicate_proposal(
        self,
        sku: int,
        warehouse_id: int,
    ) -> SupplyProposal | None:
        """Check if proposal already exists for this SKU and warehouse."""
        existing = list_proposals(status=ProposalStatus.PROPOSED, limit=1000)

        for p in existing:
            if p.sku == sku and p.target_warehouse_id == warehouse_id:
                return p

        return None

    def approve_proposal(self, proposal_id: str, approved_by: str) -> str:
        """Approve proposal (required before mutation)."""
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.PROPOSED:
            raise ValueError(
                f"Proposal status is {proposal.status.value}, expected 'proposed'"
            )

        update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.OWNER_APPROVED,
            approved_at=datetime.now(),
            approved_by=approved_by,
        )

        logger.info(f"Proposal {proposal_id} approved by {approved_by}")
        return f"Proposal {proposal_id} approved by {approved_by}"

    def reject_proposal(self, proposal_id: str, reason: str, rejected_by: str) -> str:
        """Reject proposal."""
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status not in (ProposalStatus.PROPOSED, ProposalStatus.OWNER_APPROVED):
            raise ValueError(
                f"Cannot reject proposal with status {proposal.status.value}"
            )

        update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.REJECTED,
            rejected_reason=reason,
        )

        logger.info(f"Proposal {proposal_id} rejected by {rejected_by}: {reason}")
        return f"Proposal {proposal_id} rejected"

    def create_draft(self, proposal_id: str) -> str:
        """Create draft and supply order from approved proposal (MUTATION)."""
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.OWNER_APPROVED:
            raise ValueError(
                f"Proposal must be approved first. Current status: {proposal.status.value}"
            )

        cluster_id = self._resolve_cluster_id(proposal)
        payload = DraftPayload(
            warehouse_id=int(proposal.target_warehouse_id),
            cluster_id=cluster_id,
            items=[{"sku": int(proposal.sku), "quantity": int(proposal.quantity)}],
        )

        try:
            draft_response = self._supply_client.create_draft(payload)
            draft_id = str(draft_response.get("draft_id") or draft_response.get("result", {}).get("draft_id") or "")
            if not draft_id:
                raise RuntimeError(f"No draft_id in response: {draft_response}")

            self._supply_client.create_supply_from_draft(
                draft_id=draft_id,
                cluster_id=cluster_id,
                warehouse_id=int(proposal.target_warehouse_id),
            )
            supply_id = self._wait_for_supply_order(draft_id)

            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.DRAFT_CREATED,
                draft_id=draft_id,
                supply_id=supply_id,
                draft_payload=payload.to_api_dict(),
            )

            logger.info(
                "Draft %s and supply order %s created for proposal %s",
                draft_id,
                supply_id,
                proposal_id,
            )
            return f"Draft created: {draft_id}; supply order created: {supply_id}"

        except Exception as e:
            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.FAILED,
                error_message=str(e),
            )
            raise

    def create_supply(self, proposal_id: str, timeslot_id: str) -> str:
        """Reserve timeslot for already created supply order (MUTATION)."""
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.DRAFT_CREATED:
            raise ValueError(
                f"Proposal must have draft created. Current status: {proposal.status.value}"
            )

        if not proposal.supply_id:
            raise ValueError("Proposal has no supply_id")

        try:
            response = self._supply_client.reserve_supply_timeslot(
                supply_order_id=str(proposal.supply_id),
                timeslot_id=timeslot_id,
            )
            operation_id = str(response.get("operation_id") or response.get("result", {}).get("operation_id") or "")
            if not operation_id:
                raise RuntimeError(f"No operation_id in response: {response}")

            self._wait_for_timeslot_status(operation_id)

            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.SUPPLY_CREATED,
                supply_id=proposal.supply_id,
                timeslot_id=timeslot_id,
            )

            logger.info("Supply %s booked for proposal %s", proposal.supply_id, proposal_id)
            return f"Supply booked: {proposal.supply_id}"

        except Exception as e:
            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.FAILED,
                error_message=str(e),
            )
            raise

    def _resolve_cluster_id(self, proposal: SupplyProposal) -> str:
        try:
            return str(int(str(proposal.target_cluster_id)))
        except ValueError:
            resolved = self._supply_client.resolve_cluster_for_warehouse(int(proposal.target_warehouse_id))
            if not resolved:
                raise RuntimeError(
                    f"Could not resolve macrolocal cluster for warehouse {proposal.target_warehouse_id}"
                )
            return resolved[0]

    def _wait_for_supply_order(self, draft_id: str, max_wait: int = 60) -> str:
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = self._supply_client.get_supply_create_status(draft_id)
            status = str(status_response.get("status") or "")

            if status == "SUCCESS":
                order_id = status_response.get("order_id")
                if order_id:
                    return str(order_id)
                raise RuntimeError("Supply creation completed but no order_id")

            if status == "FAILED":
                reasons = status_response.get("error_reasons") or []
                raise RuntimeError(f"Supply creation failed: {reasons}")

            time.sleep(2)

        raise RuntimeError(f"Timeout waiting for supply creation (draft_id: {draft_id})")

    def _wait_for_timeslot_status(self, operation_id: str, max_wait: int = 60) -> None:
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = self._supply_client.get_supply_timeslot_status(operation_id)
            status = str(status_response.get("status") or "")

            if status == "STATUS_SUCCESS":
                return

            if status == "STATUS_FAILED":
                reasons = status_response.get("errors") or []
                raise RuntimeError(f"Timeslot reservation failed: {reasons}")

            time.sleep(2)

        raise RuntimeError(f"Timeout waiting for timeslot reservation (operation_id: {operation_id})")
