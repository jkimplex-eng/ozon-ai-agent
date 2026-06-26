"""Tests for telegram/outcome_store.py."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ozon_agent.telegram.outcome_store import (
    get_outcome_stats,
    list_outcomes,
    load_success_patterns,
    record_outcome,
)


def test_record_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ozon_agent.telegram.outcome_store._OUTCOMES_DIR", tmp_path
    )
    monkeypatch.setattr(
        "ozon_agent.telegram.outcome_store._OUTCOMES_FILE", tmp_path / "outcomes.json"
    )
    rec = SimpleNamespace(
        id="rec-1234-5678-9012",
        sku="SKU-TEST",
        action=SimpleNamespace(value="INCREASE_BUDGET"),
    )
    record_outcome(
        recommendation_id=rec.id,
        sku=rec.sku,
        action=rec.action.value,
        result="SUCCESS",
        user="test_user",
    )
    outcomes = list_outcomes(limit=10)
    assert len(outcomes) == 1
    assert outcomes[0]["result"] == "SUCCESS"
    assert outcomes[0]["sku"] == "SKU-TEST"


def test_get_outcome_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ozon_agent.telegram.outcome_store._OUTCOMES_DIR", tmp_path
    )
    monkeypatch.setattr(
        "ozon_agent.telegram.outcome_store._OUTCOMES_FILE", tmp_path / "outcomes.json"
    )
    record_outcome("id1", "SKU1", "action1", "SUCCESS", "user")
    record_outcome("id2", "SKU2", "action2", "FAILURE", "user")
    record_outcome("id3", "SKU3", "action3", "OBSERVING", "user")

    stats = get_outcome_stats()
    assert stats["success"] == 1
    assert stats["failure"] == 1
    assert stats["observing"] == 1
    assert stats["total"] == 3
    assert stats["accuracy"] == 50


def test_load_success_patterns(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ozon_agent.telegram.outcome_store._OUTCOMES_DIR", tmp_path
    )
    monkeypatch.setattr(
        "ozon_agent.telegram.outcome_store._OUTCOMES_FILE", tmp_path / "outcomes.json"
    )
    record_outcome("id1", "SKU1", "pause_campaign", "SUCCESS", "user")
    record_outcome("id2", "SKU2", "pause_campaign", "SUCCESS", "user")
    record_outcome("id3", "SKU3", "pause_campaign", "FAILURE", "user")

    patterns = load_success_patterns()
    assert len(patterns) == 1
    assert patterns[0]["problem"] == "pause_campaign"
    assert patterns[0]["total_cases"] == 3
    assert abs(patterns[0]["success_rate"] - 66.7) < 1
