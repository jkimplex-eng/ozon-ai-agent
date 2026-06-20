"""Tests for Performance API client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ozon_agent.performance.client import PerformanceClient, PerformanceCredentialsError
from ozon_agent.performance.models import (
    PerformanceCampaign,
    PerformanceCampaignsResult,
    PerformanceCredentials,
)


def test_credentials_error_on_empty():
    with pytest.raises(PerformanceCredentialsError):
        PerformanceClient(PerformanceCredentials(client_id="", client_secret=""))


def test_credentials_error_on_empty_secret():
    with pytest.raises(PerformanceCredentialsError):
        PerformanceClient(PerformanceCredentials(client_id="123", client_secret=""))


def test_from_env_missing(monkeypatch):
    monkeypatch.delenv("OZON_PERFORMANCE_CLIENT_ID", raising=False)
    monkeypatch.delenv("OZON_PERFORMANCE_CLIENT_SECRET", raising=False)
    with pytest.raises(PerformanceCredentialsError):
        PerformanceClient.from_env()


def test_auth_headers():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "test_token_123"}
    mock_response.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.post.return_value = mock_response

    client = PerformanceClient(
        PerformanceCredentials(client_id="id", client_secret="secret"),
        http_client=mock_http,
    )
    headers = client._auth_headers()
    assert headers["Authorization"] == "Bearer test_token_123"
    client.close()


def test_parse_campaigns_response():
    client = PerformanceClient(
        PerformanceCredentials(client_id="id", client_secret="secret"),
    )
    data = {
        "list": [
            {"id": 123, "title": "Test Campaign", "state": "ACTIVE", "advObjectType": "AUTO"},
        ],
        "pagination": {"page": 1, "totalPages": 2},
    }
    result = client.parse_campaigns_response(data)
    assert isinstance(result, PerformanceCampaignsResult)
    assert len(result.campaigns) == 1
    assert result.campaigns[0].id == 123
    assert result.campaigns[0].name == "Test Campaign"
    assert result.campaigns[0].status == "ACTIVE"
    assert result.total_pages == 2
    client.close()


def test_parse_campaigns_response_empty():
    client = PerformanceClient(
        PerformanceCredentials(client_id="id", client_secret="secret"),
    )
    data = {"list": [], "pagination": {"page": 1, "totalPages": 1}}
    result = client.parse_campaigns_response(data)
    assert len(result.campaigns) == 0
    client.close()


def test_parse_campaigns_response_missing_optional_fields():
    client = PerformanceClient(
        PerformanceCredentials(client_id="id", client_secret="secret"),
    )
    data = {"list": [{"id": 456}], "pagination": {}}
    result = client.parse_campaigns_response(data)
    assert len(result.campaigns) == 1
    assert result.campaigns[0].name == ""
    assert result.campaigns[0].status == ""
    assert result.total_pages == 1
    client.close()


def test_campaign_to_dict():
    c = PerformanceCampaign(id=1, name="C", status="ACTIVE")
    d = c.to_dict()
    assert d["id"] == 1
    assert d["name"] == "C"
    assert d["status"] == "ACTIVE"


@patch("ozon_agent.performance.client.time.sleep")
def test_get_retries_on_429(mock_sleep):
    mock_token_resp = MagicMock(spec=httpx.Response)
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "tok"}
    mock_token_resp.raise_for_status = MagicMock()

    response_429 = MagicMock(spec=httpx.Response)
    response_429.status_code = 429
    response_429.headers = {"Retry-After": "0.1"}

    response_ok = MagicMock(spec=httpx.Response)
    response_ok.status_code = 200
    response_ok.json.return_value = {"list": [], "pagination": {}}
    response_ok.raise_for_status = MagicMock()

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.post.return_value = mock_token_resp
    mock_http.get.side_effect = [response_429, response_ok]

    client = PerformanceClient(
        PerformanceCredentials(client_id="id", client_secret="secret"),
        http_client=mock_http,
    )
    result = client.get_campaigns_page(page=1)
    assert result == {"list": [], "pagination": {}}
    assert mock_http.get.call_count == 2
    client.close()
