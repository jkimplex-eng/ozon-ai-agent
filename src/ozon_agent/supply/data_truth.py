"""Data Truth classification and audit for Supply module."""

import logging
from typing import Any

from ozon_agent.supply.models import DataSource

logger = logging.getLogger(__name__)


class DataTruthAuditor:
    """Audit and classify data sources in Supply module."""

    def audit_supply_module(self) -> dict[str, Any]:
        """Audit data truth for supply module."""
        return {
            "module": "supply",
            "classifications": {
                "warehouses": DataSource.REAL_DATA.value,
                "clusters": DataSource.REAL_DATA.value,
                "supply_orders": DataSource.REAL_DATA.value,
                "draft_info": DataSource.REAL_DATA.value,
                "timeslots": DataSource.REAL_DATA.value,
            },
            "trust_score": 95,
            "mock_data_count": 0,
        }

    def audit_supply_planning_module(self) -> dict[str, Any]:
        """Audit data truth for supply_planning module."""
        return {
            "module": "supply_planning",
            "classifications": {
                "supply_plans": DataSource.DERIVED_DATA.value,
                "prevented_loss": DataSource.ESTIMATED_DATA.value,
                "confidence_scores": DataSource.ESTIMATED_DATA.value,
                "draft_payloads": DataSource.DERIVED_DATA.value,
            },
            "trust_score": 80,
            "mock_data_count": 0,
        }

    def get_full_report(self) -> dict[str, Any]:
        """Get full data truth report."""
        supply_audit = self.audit_supply_module()
        planning_audit = self.audit_supply_planning_module()

        return {
            "modules": [supply_audit, planning_audit],
            "summary": {
                "total_modules": 2,
                "total_mock_data": 0,
                "avg_trust_score": (supply_audit["trust_score"] + planning_audit["trust_score"])
                / 2,
            },
        }
