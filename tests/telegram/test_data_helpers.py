"""Tests for telegram/data_helpers.py."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ozon_agent.telegram.data_helpers import (
    count_payload_rows,
    count_unique_skus,
    data_freshness,
    format_dt,
    last_update_time,
    load_json_dict,
    load_payload,
)


def test_load_json_dict(tmp_path):
    p = tmp_path / "test.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    assert load_json_dict(p) == {"key": "value"}


def test_load_json_dict_missing(tmp_path):
    assert load_json_dict(tmp_path / "missing.json") == {}


def test_load_json_dict_invalid(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    assert load_json_dict(p) == {}


def test_load_json_dict_list(tmp_path):
    p = tmp_path / "list.json"
    p.write_text('[1, 2, 3]', encoding="utf-8")
    assert load_json_dict(p) == {}


def test_load_payload(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"rows": [{"a": 1}, {"b": 2}]}), encoding="utf-8")
    assert load_payload(p) == [{"a": 1}, {"b": 2}]


def test_load_payload_bare_list(tmp_path):
    p = tmp_path / "list.json"
    p.write_text(json.dumps([{"a": 1}]), encoding="utf-8")
    assert load_payload(p) == [{"a": 1}]


def test_load_payload_missing(tmp_path):
    assert load_payload(tmp_path / "missing.json") == []


def test_count_payload_rows_with_record_count(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"record_count": 42, "rows": []}), encoding="utf-8")
    assert count_payload_rows(p) == 42


def test_count_payload_rows_with_rows(tmp_path):
    p = tmp_path / "data.json"
    p.write_text(json.dumps({"rows": [{"a": 1}, {"b": 2}]}), encoding="utf-8")
    assert count_payload_rows(p) == 2


def test_count_unique_skus(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data" / "analytics"
    data_dir.mkdir(parents=True)
    (data_dir / "sku_history.json").write_text(
        json.dumps({"rows": [{"sku": "SKU-1"}, {"sku": "SKU-2"}]}),
        encoding="utf-8",
    )
    assert count_unique_skus() == 2


def test_last_update_time(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data" / "signals"
    data_dir.mkdir(parents=True)
    (data_dir / "signals.json").write_text("{}", encoding="utf-8")
    result = last_update_time()
    assert result is not None
    assert isinstance(result, datetime)


def test_last_update_time_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert last_update_time() is None


def test_data_freshness_empty():
    assert data_freshness(None, {}) == "неизвестно"


def test_data_freshness_with_date_to():
    result = data_freshness(None, {"date_to": "2026-06-25"})
    assert "2026-06-25" in result


def test_format_dt_none():
    assert format_dt(None) == "неизвестно"


def test_format_dt_value():
    dt = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    result = format_dt(dt)
    assert "2026-06-25" in result
    assert "12:00" in result
