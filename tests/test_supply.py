"""Tests for Supply module."""
from datetime import datetime
from unittest.mock import MagicMock, patch

from ozon_agent.supply.client import SupplyAPIClient
from ozon_agent.supply.data_truth import DataTruthAuditor
from ozon_agent.supply.fbo import build_fbo_demand_plans
from ozon_agent.supply.models import (
    ProposalStatus,
    SupplyProposal,
    Warehouse,
)
from ozon_agent.supply.planning import SupplyPlanningEngine
from ozon_agent.supply.proposals import ProposalManager


class TestSupplyAPIClient:
    def test_list_fbo_warehouses(self):
        """Test warehouse listing."""
        client = MagicMock()
        client._post.return_value = {
            "result": {
                "warehouses": [
                    {
                        "warehouse_id": 1,
                        "name": "Test Warehouse",
                        "cluster_id": "test",
                        "cluster_name": "Test Cluster",
                        "is_active": True,
                    }
                ]
            }
        }

        supply_client = SupplyAPIClient(client)
        warehouses = supply_client.list_fbo_warehouses()

        assert len(warehouses) == 1
        assert warehouses[0].warehouse_id == 1
        assert warehouses[0].name == "Test Warehouse"

    def test_list_clusters(self):
        """Test cluster listing."""
        client = MagicMock()
        client._post.return_value = {
            "result": {
                "clusters": [
                    {
                        "cluster_id": "test",
                        "name": "Test Cluster",
                        "type": "central",
                        "warehouses_count": 5,
                    }
                ]
            }
        }

        supply_client = SupplyAPIClient(client)
        clusters = supply_client.list_clusters()

        assert len(clusters) == 1
        assert clusters[0].cluster_id == "test"


class TestSupplyPlanningEngine:
    def test_generate_plans_empty(self):
        """Test plan generation with no data."""
        client = MagicMock()
        engine = SupplyPlanningEngine(client)

        with patch.object(engine._supply_client, 'list_fbo_warehouses', return_value=[]):
            plans = engine.generate_plans()
            assert len(plans) == 0


class TestFboPlanning:
    def test_build_fbo_demand_for_30_60_90_by_cluster(self):
        products = [{
            "sku": "123",
            "offer_id": "offer-123",
            "name": "Test Product",
            "total_sales": 90,
            "days_with_sales": 30,
        }]
        stocks = [
            {"sku": "123", "warehouse_name": "Moscow WH", "current_stock": 15},
            {"sku": "123", "warehouse_name": "Kazan WH", "current_stock": 45},
        ]
        warehouses = [
            Warehouse(1, "Moscow WH", "msk", "Moscow", True),
            Warehouse(2, "Kazan WH", "kzn", "Kazan", True),
        ]

        plans = build_fbo_demand_plans(products, stocks, warehouses)

        assert len(plans) == 2
        by_cluster = {plan.cluster_id: plan for plan in plans}
        assert by_cluster["msk"].demand_30 == 23
        assert by_cluster["kzn"].demand_30 == 68
        assert by_cluster["msk"].recommended_60 == 30
        assert by_cluster["kzn"].recommended_90 == 158
        assert "estimated" in by_cluster["msk"].data_quality_note

    def test_build_fbo_demand_uses_equal_share_without_stock(self):
        products = [{
            "sku": "123",
            "offer_id": "offer-123",
            "name": "Test Product",
            "total_sales": 60,
            "days_with_sales": 30,
        }]
        warehouses = [
            Warehouse(1, "Moscow WH", "msk", "Moscow", True),
            Warehouse(2, "Kazan WH", "kzn", "Kazan", True),
        ]

        plans = build_fbo_demand_plans(products, [], warehouses)

        assert [plan.demand_30 for plan in plans] == [30, 30]
        assert [plan.recommended_30 for plan in plans] == [30, 30]


class TestProposalManager:
    def test_create_proposals_from_plans(self):
        """Test proposal creation from plans."""
        client = MagicMock()
        manager = ProposalManager(client)

        plans = [
            {
                "sku": 123,
                "offer_id": "test-offer",
                "product_name": "Test Product",
                "quantity": 100,
                "target_warehouse_id": 1,
                "target_warehouse_name": "Test Warehouse",
                "target_cluster_id": "test",
                "target_cluster_name": "Test Cluster",
                "reason": "Test reason",
                "expected_prevented_loss": 1000.0,
                "confidence": 0.85,
                "data_sources": ["sales", "stocks"],
            }
        ]

        with patch('ozon_agent.supply.proposals.create_proposal') as mock_create:
            with patch.object(manager, '_check_duplicate_proposal', return_value=None):
                proposals = manager.create_proposals_from_plans(plans)

                assert len(proposals) == 1
                assert proposals[0].sku == 123
                assert proposals[0].status == ProposalStatus.PROPOSED
                mock_create.assert_called_once()

    def test_approve_proposal(self):
        """Test proposal approval."""
        client = MagicMock()
        manager = ProposalManager(client)

        proposal = SupplyProposal(
            proposal_id="test-id",
            sku=123,
            offer_id="test",
            product_name="Test",
            quantity=100,
            target_warehouse_id=1,
            target_warehouse_name="Test",
            target_cluster_id="test",
            target_cluster_name="Test",
            reason="Test",
            expected_prevented_loss=100.0,
            confidence=0.8,
            data_sources=[],
            status=ProposalStatus.PROPOSED,
        )

        with patch('ozon_agent.supply.proposals.get_proposal', return_value=proposal):
            with patch('ozon_agent.supply.proposals.update_proposal_status') as mock_update:
                result = manager.approve_proposal("test-id", "test_user")

                assert "approved" in result
                mock_update.assert_called_once()


class TestDataTruthAuditor:
    def test_audit_supply_module(self):
        """Test supply module audit."""
        auditor = DataTruthAuditor()
        audit = auditor.audit_supply_module()

        assert audit["module"] == "supply"
        assert audit["trust_score"] == 95
        assert audit["mock_data_count"] == 0

    def test_audit_supply_planning_module(self):
        """Test supply_planning module audit."""
        auditor = DataTruthAuditor()
        audit = auditor.audit_supply_planning_module()

        assert audit["module"] == "supply_planning"
        assert audit["trust_score"] == 80
        assert audit["mock_data_count"] == 0

    def test_audit_fbo_planning_module(self):
        """Test fbo_planning module audit."""
        auditor = DataTruthAuditor()
        audit = auditor.audit_fbo_planning_module()

        assert audit["module"] == "fbo_planning"
        assert audit["mock_data_count"] == 0



    def test_create_draft_uses_full_available_warehouse_from_draft_info(self):
        client = MagicMock()
        manager = ProposalManager(client)

        proposal = SupplyProposal(
            proposal_id="test-id",
            sku=123,
            offer_id="test",
            product_name="Test",
            quantity=100,
            target_warehouse_id=111,
            target_warehouse_name="Planned Warehouse",
            target_cluster_id="4067",
            target_cluster_name="Novosibirsk",
            reason="Test",
            expected_prevented_loss=100.0,
            confidence=0.8,
            data_sources=[],
            status=ProposalStatus.OWNER_APPROVED,
        )

        draft_info = MagicMock()
        draft_info.warehouse_id = 222
        draft_info.warehouse_name = "Actual Ozon Warehouse"

        with patch('ozon_agent.supply.proposals.get_proposal', return_value=proposal):
            with patch('ozon_agent.supply.proposals.update_proposal_status') as mock_update:
                with patch.object(manager, '_wait_for_draft_ready', return_value=draft_info):
                    with patch.object(manager, '_wait_for_supply_order', return_value='supply-1'):
                        with patch.object(manager._supply_client, 'create_draft', return_value={'draft_id': 'draft-1'}):
                            with patch.object(manager._supply_client, 'create_supply_from_draft', return_value={} ) as mock_create_supply:
                                    result = manager.create_draft('test-id')

        assert 'draft-1' in result
        mock_create_supply.assert_called_once_with(
            draft_id='draft-1',
            cluster_id='4067',
            warehouse_id=222,
        )
        assert mock_update.call_args_list[0].kwargs['target_warehouse_id'] == 222
        assert mock_update.call_args_list[0].kwargs['target_warehouse_name'] == 'Actual Ozon Warehouse'


    def test_create_draft_allows_retry_for_failed_approved_proposal(self):
        client = MagicMock()
        manager = ProposalManager(client)

        proposal = SupplyProposal(
            proposal_id="retry-id",
            sku=123,
            offer_id="test",
            product_name="Test",
            quantity=100,
            target_warehouse_id=111,
            target_warehouse_name="Planned Warehouse",
            target_cluster_id="4067",
            target_cluster_name="Novosibirsk",
            reason="Test",
            expected_prevented_loss=100.0,
            confidence=0.8,
            data_sources=[],
            status=ProposalStatus.FAILED,
            approved_at=datetime.now(),
        )

        draft_info = MagicMock()
        draft_info.warehouse_id = 222
        draft_info.warehouse_name = "Actual Ozon Warehouse"

        with patch('ozon_agent.supply.proposals.get_proposal', return_value=proposal):
            with patch('ozon_agent.supply.proposals.update_proposal_status'):
                with patch.object(manager, '_wait_for_draft_ready', return_value=draft_info):
                    with patch.object(manager, '_wait_for_supply_order', return_value='supply-1'):
                        with patch.object(manager._supply_client, 'create_draft', return_value={'draft_id': 'draft-1'}):
                            with patch.object(manager._supply_client, 'create_supply_from_draft', return_value={}):
                                result = manager.create_draft('retry-id')

        assert 'draft-1' in result

