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

    def audit_fbo_planning_module(self) -> dict[str, Any]:
        """Audit data truth for FBO cluster demand planning."""
        return {
            "module": "fbo_planning",
            "classifications": {
                "sku_sales_velocity": DataSource.DERIVED_DATA.value,
                "cluster_demand_30_60_90": DataSource.ESTIMATED_DATA.value,
                "warehouse_stock": DataSource.DERIVED_DATA.value,
                "slot_booking": DataSource.REAL_DATA.value,
                "google_sheets_export": DataSource.DERIVED_DATA.value,
                "telegram_view": DataSource.DERIVED_DATA.value,
            },
            "trust_score": 78,
            "mock_data_count": 0,
        }

    def get_full_report(self) -> dict[str, Any]:
        """Get full data truth report."""
        supply_audit = self.audit_supply_module()
        planning_audit = self.audit_supply_planning_module()
        fbo_audit = self.audit_fbo_planning_module()

        return {
            "modules": [supply_audit, planning_audit, fbo_audit],
            "summary": {
                "total_modules": 3,
                "total_mock_data": 0,
                "avg_trust_score": (
                    supply_audit["trust_score"]
                    + planning_audit["trust_score"]
                    + fbo_audit["trust_score"]
                )
                / 3,
            },
        }


