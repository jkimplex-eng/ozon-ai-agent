"""Supply Proposal Manager - handles proposal lifecycle."""
import logging
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
                target_cluster_id=plan["target_cluster_id"],
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
        """Create draft from approved proposal (MUTATION)."""
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.OWNER_APPROVED:
            raise ValueError(
                f"Proposal must be approved first. Current status: {proposal.status.value}"
            )

        if not proposal.draft_payload:
            raise ValueError("Proposal has no draft payload")

        payload = DraftPayload(
            warehouse_id=proposal.draft_payload["warehouse_id"],
            items=proposal.draft_payload["items"],
        )

        try:
            response = self._supply_client.create_draft(payload)
            draft_id = response.get("result", {}).get("draft_id")

            if not draft_id:
                raise RuntimeError(f"No draft_id in response: {response}")

            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.DRAFT_CREATED,
                draft_id=draft_id,
            )

            logger.info(f"Draft created: {draft_id} for proposal {proposal_id}")
            return f"Draft created: {draft_id}"

        except Exception as e:
            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.FAILED,
                error_message=str(e),
            )
            raise

    def create_supply(self, proposal_id: str, timeslot_id: str) -> str:
        """Create supply from draft with selected timeslot (MUTATION)."""
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.DRAFT_CREATED:
            raise ValueError(
                f"Proposal must have draft created. Current status: {proposal.status.value}"
            )

        if not proposal.draft_id:
            raise ValueError("Proposal has no draft_id")

        try:
            response = self._supply_client.create_supply_from_draft(
                draft_id=proposal.draft_id,
                timeslot_id=timeslot_id,
            )

            task_id = response.get("result", {}).get("task_id")
            if not task_id:
                raise RuntimeError(f"No task_id in response: {response}")

            supply_id = self._wait_for_supply(task_id)

            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.SUPPLY_CREATED,
                supply_id=supply_id,
                timeslot_id=timeslot_id,
            )

            logger.info(f"Supply created: {supply_id} for proposal {proposal_id}")
            return f"Supply created: {supply_id}"

        except Exception as e:
            update_proposal_status(
                proposal_id=proposal_id,
                status=ProposalStatus.FAILED,
                error_message=str(e),
            )
            raise

    def _wait_for_supply(self, task_id: str, max_wait: int = 60) -> str:
        """Wait for supply creation to complete."""
        import time

        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = self._client._post(
                "/v1/draft/supply/create/status",
                {"task_id": task_id},
            )

            status = status_response.get("result", {}).get("status")

            if status == "completed":
                supply_id = status_response.get("result", {}).get("supply_id")
                if supply_id:
                    return supply_id
                raise RuntimeError("Supply creation completed but no supply_id")

            elif status == "failed":
                error = status_response.get("result", {}).get("error", "Unknown")
                raise RuntimeError(f"Supply creation failed: {error}")

            time.sleep(2)

        raise RuntimeError(f"Timeout waiting for supply creation (task_id: {task_id})")
