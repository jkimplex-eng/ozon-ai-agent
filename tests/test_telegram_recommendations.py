"""Tests for Telegram recommendations bot."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from ozon_agent.approval.models import (
    RecommendationStatus,
    StoredRecommendation,
)
from ozon_agent.decision.models import ConfidenceLevel, RecommendationAction, RiskLevel
from ozon_agent.telegram.bot import format_rec_message, handle_message


def _sample_stored() -> StoredRecommendation:
    now = datetime.now(UTC)
    return StoredRecommendation(
        id="rec-test-1234-5678-9012",
        created_at=now,
        updated_at=now,
        sku="SKU-TEST",
        action=RecommendationAction.INCREASE_BUDGET,
        reason="Strong ROAS",
        confidence_score=0.85,
        confidence_level=ConfidenceLevel.HIGH,
        risk_score=0.2,
        risk_level=RiskLevel.LOW,
        expected_effect={"orders": {"delta_pct": 15.0}},
        supporting_metrics={"roas": 4.5},
        status=RecommendationStatus.PENDING,
    )


def test_format_rec_message() -> None:
    rec = _sample_stored()
    msg = format_rec_message(rec)
    assert "SKU-TEST" in msg
    assert "INCREASE_BUDGET" in msg
    assert "approve" in msg
    assert "reject" in msg


def test_handle_message_help() -> None:
    response = handle_message("unknown", "user")
    assert "Available commands" in response


def test_handle_message_pending_empty() -> None:
    with patch("ozon_agent.telegram.bot.list_recommendations", return_value=[]):
        response = handle_message("/recommendations", "user")
        assert "No pending" in response


def test_handle_message_pending_list() -> None:
    rec = _sample_stored()
    with patch("ozon_agent.telegram.bot.list_recommendations", return_value=[rec]):
        response = handle_message("/recommendations pending", "user")
        assert "SKU-TEST" in response


def test_handle_message_show_not_found() -> None:
    with patch("ozon_agent.telegram.bot.get_recommendation", return_value=None):
        with patch("ozon_agent.telegram.bot.list_recommendations", return_value=[]):
            response = handle_message("/recommendations show missing", "user")
            assert "not found" in response


def test_handle_message_approve() -> None:
    rec = _sample_stored()
    rec.status = RecommendationStatus.APPROVED
    with patch("ozon_agent.telegram.bot.approve_recommendation", return_value=rec):
        with patch("ozon_agent.telegram.bot.list_recommendations", return_value=[]):
            response = handle_message("/recommendations approve rec-123", "Pavel")
            assert "Approved" in response
            assert "Pavel" in response


def test_handle_message_reject() -> None:
    rec = _sample_stored()
    rec.status = RecommendationStatus.REJECTED
    with patch("ozon_agent.telegram.bot.reject_recommendation", return_value=rec):
        with patch("ozon_agent.telegram.bot.list_recommendations", return_value=[]):
            response = handle_message(
                "/recommendations reject rec-123 too risky", "Pavel"
            )
            assert "Rejected" in response


def test_telegram_no_execute_commands() -> None:
    with patch("ozon_agent.telegram.bot.list_recommendations", return_value=[]):
        response = handle_message("/recommendations", "user")
        assert "execute" not in response.lower() or "not" in response.lower()
