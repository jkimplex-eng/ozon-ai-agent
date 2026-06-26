"""Tests for telegram/format.py."""
from __future__ import annotations

from ozon_agent.telegram.format import (
    divider,
    no_data_message,
    pct,
    problem_business,
    retro_action_business,
    rub,
    safe_str,
    severity_emoji,
    signal_cause,
    signal_checklist,
    signal_type_business,
)


def test_rub_basic():
    assert rub(1000) == "1 000 ₽"
    assert rub(0) == "0 ₽"
    assert rub(-500) == "-500 ₽"


def test_rub_none():
    assert rub(None) == "0 ₽"


def test_rub_float():
    assert rub(1234.5) == "1 234 ₽"  # banker's rounding


def test_pct_basic():
    assert pct(50.0) == "50.0%"
    assert pct(0) == "0.0%"
    assert pct(33.33) == "33.3%"


def test_pct_none():
    assert pct(None) == "0.0%"


def test_divider():
    assert len(divider()) > 0
    assert "━" in divider()


def test_no_data_message():
    assert "Нет данных" in no_data_message()
    assert "Нет данных" in no_data_message("section")


def test_safe_str():
    assert safe_str("hello") == "hello"
    assert safe_str(None) == "—"
    assert safe_str("") == "—"
    assert safe_str(None, "fallback") == "fallback"


def test_severity_emoji():
    assert severity_emoji("HIGH") == "🔴"
    assert severity_emoji("CRITICAL") == "🔴"
    assert severity_emoji("MEDIUM") == "🟡"
    assert severity_emoji("LOW") == "🟢"
    assert severity_emoji("INFO") == "🟢"
    assert severity_emoji("UNKNOWN") == "⚪"


def test_signal_type_business():
    assert signal_type_business("MARGIN_DECLINE") == "Падение маржи"
    assert signal_type_business("STOCK_LOW") == "Мало остатков"
    assert signal_type_business("UNKNOWN") == "UNKNOWN"


def test_signal_cause():
    assert "себестоимость" in signal_cause("MARGIN_DECLINE").lower()
    assert "требуется анализ" in signal_cause("UNKNOWN")


def test_signal_checklist():
    steps = signal_checklist("MARGIN_DECLINE")
    assert len(steps) > 0
    assert isinstance(steps, list)


def test_problem_business():
    assert problem_business("low_margin") == "Низкая маржа"
    assert problem_business("high_drr") == "Высокий ДРР"
    assert problem_business("custom_problem") == "custom_problem"


def test_retro_action_business():
    assert retro_action_business("pause_campaign") == "Остановить кампанию"
    assert retro_action_business("unknown") == "unknown"
