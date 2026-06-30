"""Data models for Supply API."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ProposalStatus(StrEnum):
    """Status lifecycle for supply proposals."""

    PROPOSED = "proposed"
    OWNER_APPROVED = "owner_approved"
    DRAFT_CREATED = "draft_created"
    SUPPLY_CREATED = "supply_created"
    REJECTED = "rejected"
    FAILED = "failed"


class DataSource(StrEnum):
    """Data truth classification."""

    REAL_DATA = "REAL_DATA"
    DERIVED_DATA = "DERIVED_DATA"
    ESTIMATED_DATA = "ESTIMATED_DATA"
    MOCK_DATA = "MOCK_DATA"


@dataclass
class Warehouse:
    """FBO Warehouse."""

    warehouse_id: int
    name: str
    cluster_id: str | None
    cluster_name: str | None
    is_active: bool
    data_source: DataSource = DataSource.REAL_DATA


@dataclass
class Cluster:
    """Supply Cluster."""

    cluster_id: str
    name: str
    cluster_type: str
    warehouses_count: int
    data_source: DataSource = DataSource.REAL_DATA


@dataclass
class SupplyOrder:
    """Supply Order."""

    supply_id: str
    status: str
    warehouse_id: int | None
    items_count: int
    created_at: str | None
    data_source: DataSource = DataSource.REAL_DATA


@dataclass
class DraftInfo:
    """Draft Information."""

    draft_id: str
    warehouse_id: int | None
    warehouse_name: str | None
    items: list[dict[str, Any]]
    status: str
    created_at: str | None
    data_source: DataSource = DataSource.REAL_DATA


@dataclass
class Timeslot:
    """Available Timeslot."""

    timeslot_id: str
    date: str | None
    time_from: str | None
    time_to: str | None
    data_source: DataSource = DataSource.REAL_DATA


@dataclass
class DraftPayload:
    """Payload for direct draft creation."""

    warehouse_id: int
    cluster_id: str
    items: list[dict[str, Any]]
    deletion_sku_mode: int = 1

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to Ozon direct-draft request format."""
        return {
            "deletion_sku_mode": self.deletion_sku_mode,
            "cluster_info": {
                "macrolocal_cluster_id": int(self.cluster_id),
                "items": self.items,
            },
        }


@dataclass
class SupplyProposal:
    """Internal supply proposal (before mutation)."""

    proposal_id: str
    sku: int
    offer_id: str
    product_name: str
    quantity: int
    target_warehouse_id: int
    target_warehouse_name: str
    target_cluster_id: str
    target_cluster_name: str
    reason: str
    expected_prevented_loss: float
    confidence: float
    data_sources: list[str]
    status: ProposalStatus = ProposalStatus.PROPOSED
    draft_id: str | None = None
    supply_id: str | None = None
    timeslot_id: str | None = None
    draft_payload: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejected_reason: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "proposal_id": self.proposal_id,
            "sku": self.sku,
            "offer_id": self.offer_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "target_warehouse_id": self.target_warehouse_id,
            "target_warehouse_name": self.target_warehouse_name,
            "target_cluster_id": self.target_cluster_id,
            "target_cluster_name": self.target_cluster_name,
            "reason": self.reason,
            "expected_prevented_loss": self.expected_prevented_loss,
            "confidence": self.confidence,
            "data_sources": self.data_sources,
            "status": self.status.value,
            "draft_id": self.draft_id,
            "supply_id": self.supply_id,
            "timeslot_id": self.timeslot_id,
            "draft_payload": self.draft_payload,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "rejected_reason": self.rejected_reason,
            "error_message": self.error_message,
        }
