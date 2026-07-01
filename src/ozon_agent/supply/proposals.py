"""Supply Proposal Manager - handles proposal lifecycle."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any

from ozon_agent.api.ozon_client import OzonClient
from ozon_agent.supply.cities import canonical_supply_city, warehouse_priority
from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.models import DraftPayload, ProposalStatus, SupplyProposal
from ozon_agent.supply.repository import (
    create_proposal,
    get_proposal,
    list_proposals,
    update_proposal_fields,
    update_proposal_status,
)

logger = logging.getLogger(__name__)

_ACTIONABLE_DUPLICATE_STATUSES = {
    ProposalStatus.PROPOSED,
    ProposalStatus.OWNER_APPROVED,
    ProposalStatus.DRAFT_CREATED,
}


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
            city_name = canonical_supply_city(plan.get("target_cluster_name"), plan.get("target_warehouse_name"))
            existing = self._check_duplicate_proposal(
                sku=plan["sku"],
                city_name=city_name,
            )

            if existing:
                if existing.status == ProposalStatus.PROPOSED:
                    proposals.append(self._refresh_existing_proposal(existing, plan, city_name))
                else:
                    logger.info("Skipping duplicate actionable proposal for SKU %s in %s", plan["sku"], city_name)
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
                target_cluster_name=city_name,
                reason=plan["reason"],
                expected_prevented_loss=plan["expected_prevented_loss"],
                confidence=plan["confidence"],
                data_sources=plan["data_sources"],
                status=ProposalStatus.PROPOSED,
                draft_payload=draft_payload,
            )

            create_proposal(proposal)
            proposals.append(proposal)

            logger.info("Created proposal %s for SKU %s", proposal.proposal_id, proposal.sku)

        return proposals

    def _refresh_existing_proposal(
        self,
        proposal: SupplyProposal,
        plan: dict[str, Any],
        city_name: str,
    ) -> SupplyProposal:
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
        update_proposal_fields(
            proposal_id=str(proposal.proposal_id),
            quantity=plan["quantity"],
            target_warehouse_id=plan["target_warehouse_id"],
            target_warehouse_name=plan["target_warehouse_name"],
            target_cluster_id=str(plan["target_cluster_id"]),
            target_cluster_name=city_name,
            reason=plan["reason"],
            expected_prevented_loss=plan["expected_prevented_loss"],
            confidence=plan["confidence"],
            data_sources=plan["data_sources"],
            draft_payload=draft_payload,
            error_message=None,
        )
        refreshed = get_proposal(str(proposal.proposal_id))
        if refreshed is None:
            raise ValueError(f"Proposal not found after refresh: {proposal.proposal_id}")
        logger.info("Refreshed proposal %s for SKU %s in %s", refreshed.proposal_id, refreshed.sku, city_name)
        return refreshed

    def _check_duplicate_proposal(
        self,
        sku: int,
        city_name: str,
    ) -> SupplyProposal | None:
        """Check if actionable proposal already exists for this SKU and city."""
        existing = list_proposals(limit=1000)

        for proposal in existing:
            proposal_city = canonical_supply_city(proposal.target_cluster_name, proposal.target_warehouse_name)
            if proposal.sku == sku and proposal_city == city_name and proposal.status in _ACTIONABLE_DUPLICATE_STATUSES:
                return proposal

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

        logger.info("Proposal %s approved by %s", proposal_id, approved_by)
        return f"Proposal {proposal_id} approved by {approved_by}"

    def approve_batch(self, proposal_ids: list[str], approved_by: str) -> str:
        proposal_ids = list(dict.fromkeys(proposal_ids))
        approved = 0
        already_ready = 0
        for proposal_id in proposal_ids:
            proposal = get_proposal(proposal_id)
            if not proposal:
                continue
            if proposal.status == ProposalStatus.PROPOSED:
                self.approve_proposal(proposal_id, approved_by)
                approved += 1
            elif proposal.status in (ProposalStatus.OWNER_APPROVED, ProposalStatus.DRAFT_CREATED, ProposalStatus.SUPPLY_CREATED):
                already_ready += 1

        return f"Approved {approved} proposals; already ready: {already_ready}"

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

        logger.info("Proposal %s rejected by %s: %s", proposal_id, rejected_by, reason)
        return f"Proposal {proposal_id} rejected"

    def create_draft(self, proposal_id: str) -> str:
        """Create draft and supply order from approved proposal (MUTATION)."""
        proposal = get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")
        return self.create_draft_batch([proposal_id])

    def create_draft_batch(self, proposal_ids: list[str]) -> str:
        proposals = self._load_batch_proposals(proposal_ids)
        if not proposals:
            raise ValueError("No proposals selected for draft creation")

        for proposal in proposals:
            retry_failed = proposal.status == ProposalStatus.FAILED and proposal.approved_at is not None
            if proposal.status != ProposalStatus.OWNER_APPROVED and not retry_failed:
                raise ValueError(
                    f"Proposal must be approved first. Current status: {proposal.status.value}"
                )

        anchor = self._select_batch_anchor(proposals)
        cluster_id = self._resolve_cluster_id(anchor)
        payload = DraftPayload(
            warehouse_id=int(anchor.target_warehouse_id),
            cluster_id=cluster_id,
            items=[
                {"sku": int(proposal.sku), "quantity": int(proposal.quantity)}
                for proposal in proposals
            ],
        )

        try:
            draft_response = self._supply_client.create_draft(payload)
            draft_id = str(draft_response.get("draft_id") or draft_response.get("result", {}).get("draft_id") or "")
            if not draft_id:
                raise RuntimeError(f"No draft_id in response: {draft_response}")

            draft_info = self._wait_for_draft_ready(draft_id)
            actual_warehouse_id = int(draft_info.warehouse_id or anchor.target_warehouse_id)
            actual_warehouse_name = draft_info.warehouse_name or anchor.target_warehouse_name

            create_response = self._supply_client.create_supply_from_draft(
                draft_id=draft_id,
                cluster_id=cluster_id,
                warehouse_id=actual_warehouse_id,
            )
            error_reasons = create_response.get("error_reasons") or []
            if error_reasons:
                raise RuntimeError(f"Supply creation rejected: {error_reasons}")

            supply_id = self._wait_for_supply_order(draft_id)

            for proposal in proposals:
                update_proposal_status(
                    proposal_id=str(proposal.proposal_id),
                    status=ProposalStatus.DRAFT_CREATED,
                    draft_id=draft_id,
                    supply_id=supply_id,
                    draft_payload=payload.to_api_dict(),
                    target_warehouse_id=actual_warehouse_id,
                    target_warehouse_name=actual_warehouse_name,
                )

            logger.info(
                "Draft %s and supply order %s created for %s proposals",
                draft_id,
                supply_id,
                len(proposals),
            )
            return f"Draft created: {draft_id}; supply order created: {supply_id}; items: {len(proposals)}"

        except Exception as exc:
            for proposal in proposals:
                update_proposal_status(
                    proposal_id=str(proposal.proposal_id),
                    status=ProposalStatus.FAILED,
                    error_message=str(exc),
                )
            raise

    def create_supply(self, proposal_id: str, timeslot_id: str) -> str:
        """Reserve timeslot for already created supply order (MUTATION)."""
        proposal = get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")
        return self.create_supply_batch([proposal_id], timeslot_id)

    def create_supply_batch(self, proposal_ids: list[str], timeslot_id: str) -> str:
        proposals = self._load_batch_proposals(proposal_ids)
        if not proposals:
            raise ValueError("No proposals selected for slot booking")

        for proposal in proposals:
            if proposal.status != ProposalStatus.DRAFT_CREATED:
                raise ValueError(
                    f"Proposal must have draft created. Current status: {proposal.status.value}"
                )
            if not proposal.supply_id:
                raise ValueError("Proposal has no supply_id")

        supply_ids = {str(proposal.supply_id) for proposal in proposals if proposal.supply_id}
        if len(supply_ids) != 1:
            raise ValueError(f"Selected proposals belong to multiple supply orders: {sorted(supply_ids)}")
        supply_id = next(iter(supply_ids))

        try:
            response = self._supply_client.reserve_supply_timeslot(
                supply_order_id=supply_id,
                timeslot_id=timeslot_id,
            )
            operation_id = str(response.get("operation_id") or response.get("result", {}).get("operation_id") or "")
            if not operation_id:
                raise RuntimeError(f"No operation_id in response: {response}")

            self._wait_for_timeslot_status(operation_id)

            for proposal in proposals:
                update_proposal_status(
                    proposal_id=str(proposal.proposal_id),
                    status=ProposalStatus.SUPPLY_CREATED,
                    supply_id=supply_id,
                    timeslot_id=timeslot_id,
                )

            logger.info("Supply %s booked for %s proposals", supply_id, len(proposals))
            return f"Supply booked: {supply_id}"

        except Exception as exc:
            for proposal in proposals:
                update_proposal_status(
                    proposal_id=str(proposal.proposal_id),
                    status=ProposalStatus.FAILED,
                    error_message=str(exc),
                )
            raise

    def _load_batch_proposals(self, proposal_ids: list[str]) -> list[SupplyProposal]:
        proposals: list[SupplyProposal] = []
        for proposal_id in dict.fromkeys(proposal_ids):
            proposal = get_proposal(str(proposal_id))
            if proposal:
                proposals.append(proposal)
        proposals.sort(key=lambda proposal: (proposal.offer_id or str(proposal.sku), proposal.created_at))
        return proposals

    def _select_batch_anchor(self, proposals: list[SupplyProposal]) -> SupplyProposal:
        return max(
            proposals,
            key=lambda proposal: warehouse_priority(proposal.target_warehouse_name, proposal.target_cluster_id),
        )

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

    def _wait_for_draft_ready(self, draft_id: str, max_wait: int = 60):
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                draft_info = self._supply_client.get_draft_info(draft_id)
            except RuntimeError as exc:
                if "429 Too Many Requests" in str(exc):
                    time.sleep(2)
                    continue
                raise
            if draft_info.status == "SUCCESS":
                return draft_info
            if draft_info.status == "FAILED":
                raise RuntimeError(f"Draft creation failed for draft_id: {draft_id}")
            time.sleep(2)

        raise RuntimeError(f"Timeout waiting for draft readiness (draft_id: {draft_id})")

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
