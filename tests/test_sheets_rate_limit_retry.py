"""Tests for Google Sheets rate limit retry and throttling."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from gspread.exceptions import APIError

from ozon_agent.sheets.client import (
    _get_retry_config,
    _is_rate_limit_error,
    retry_on_rate_limit,
)
from ozon_agent.sheets.sync import _get_delay, _sync_one_tab


def test_is_rate_limit_error_true() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 429
    exc = APIError(mock_response)
    assert _is_rate_limit_error(exc) is True


def test_is_rate_limit_error_false_403() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 403
    exc = APIError(mock_response)
    assert _is_rate_limit_error(exc) is False


def test_is_rate_limit_error_non_api() -> None:
    assert _is_rate_limit_error(ValueError("test")) is False


def test_get_retry_config_defaults() -> None:
    attempts, backoff = _get_retry_config()
    assert attempts == 3
    assert backoff == 30


def test_get_retry_config_from_env() -> None:
    import os
    os.environ["SHEETS_RETRY_ATTEMPTS"] = "5"
    os.environ["SHEETS_RETRY_BACKOFF_SECONDS"] = "60"
    try:
        attempts, backoff = _get_retry_config()
        assert attempts == 5
        assert backoff == 60
    finally:
        del os.environ["SHEETS_RETRY_ATTEMPTS"]
        del os.environ["SHEETS_RETRY_BACKOFF_SECONDS"]


def test_retry_on_rate_limit_success() -> None:
    func = MagicMock(return_value=42)
    result = retry_on_rate_limit(func)
    assert result == 42
    func.assert_called_once()


def test_retry_on_rate_limit_retries_on_429() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 429
    rate_limit_exc = APIError(mock_response)

    func = MagicMock(side_effect=[rate_limit_exc, rate_limit_exc, 7])
    with patch("ozon_agent.sheets.client.time.sleep"):
        result = retry_on_rate_limit(func)
    assert result == 7
    assert func.call_count == 3


def test_retry_on_rate_limit_exhausts_retries() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 429
    rate_limit_exc = APIError(mock_response)

    func = MagicMock(side_effect=rate_limit_exc)
    with patch("ozon_agent.sheets.client.time.sleep"):
        with pytest.raises(APIError):
            retry_on_rate_limit(func)
    assert func.call_count == 3


def test_retry_on_rate_limit_non_429_raises_immediately() -> None:
    func = MagicMock(side_effect=ValueError("other error"))
    with pytest.raises(ValueError, match="other error"):
        retry_on_rate_limit(func)
    func.assert_called_once()


def test_retry_on_rate_limit_passes_args() -> None:
    func = MagicMock(return_value=10)
    result = retry_on_rate_limit(func, "a", "b", key="val")
    assert result == 10
    func.assert_called_once_with("a", "b", key="val")


def test_get_delay_default() -> None:
    assert _get_delay(None) == 10


def test_get_delay_explicit() -> None:
    assert _get_delay(5) == 5


def test_get_delay_from_env() -> None:
    import os
    os.environ["SHEETS_SYNC_DELAY_SECONDS"] = "20"
    try:
        assert _get_delay(None) == 20
    finally:
        del os.environ["SHEETS_SYNC_DELAY_SECONDS"]


def test_sync_one_tab_success_with_delay() -> None:
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    exporter = MagicMock(return_value=5)

    with patch("ozon_agent.sheets.sync.time.sleep") as mock_sleep:
        count = _sync_one_tab(
            "Test Tab", exporter, True, mock_spreadsheet, 10, is_last=False,
        )
        assert count == 5
        mock_sleep.assert_called_once_with(10)


def test_sync_one_tab_no_delay_when_last() -> None:
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    exporter = MagicMock(return_value=3)

    with patch("ozon_agent.sheets.sync.time.sleep") as mock_sleep:
        count = _sync_one_tab(
            "Test Tab", exporter, True, mock_spreadsheet, 10, is_last=True,
        )
        assert count == 3
        mock_sleep.assert_not_called()


def test_sync_one_tab_failure_returns_negative() -> None:
    mock_spreadsheet = MagicMock()
    exporter = MagicMock(side_effect=Exception("write failed"))

    count = _sync_one_tab(
        "Test Tab", exporter, True, mock_spreadsheet, 10, is_last=False,
    )
    assert count == -1


def test_sync_one_tab_rate_limit_retries() -> None:
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    mock_response = MagicMock()
    mock_response.status_code = 429
    rate_limit_exc = APIError(mock_response)

    exporter = MagicMock(side_effect=[rate_limit_exc, 42])

    with patch("ozon_agent.sheets.sync.time.sleep"):
        count = _sync_one_tab(
            "Test Tab", exporter, True, mock_spreadsheet, 10, is_last=False,
        )
        assert count == 42
