"""Tests for Performance API CSV parser."""
from __future__ import annotations

from ozon_agent.performance.csv_parser import parse_performance_csv


def test_empty_csv():
    assert parse_performance_csv("") == []
    assert parse_performance_csv("   ") == []


def test_no_header():
    assert parse_performance_csv("a;b;c") == []


def test_simple_csv():
    csv_text = (
        "Дата;ID кампании;Название кампании;Артикул;Название товара;"
        "Показы;Клики;CTR;Добавления в корзину;CPC;Расход;"
        "Заказы;Выручка;Заказы (мод.);Выручка (мод.);ДРР;"
        "Заказанное кол-во;Общий ДРР;Добавлено\n"
        "17.06.2026;29645639;Test Campaign;4536601352;Product;"
        "591;13;2.2;0;48.13;625.65;"
        "0;0;0;0;0;0;0;17.06.2026\n"
    )
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    row = rows[0]
    assert row.date == "17.06.2026"
    assert row.campaign_id == "29645639"
    assert row.campaign_name == "Test Campaign"
    assert row.sku == "4536601352"
    assert row.product_name == "Product"
    assert row.impressions == 591
    assert row.clicks == 13
    assert row.ctr == 2.2
    assert row.add_to_cart == 0
    assert row.cpc == 48.13
    assert row.spend == 625.65
    assert row.orders == 0
    assert row.revenue == 0.0
    assert row.added_at == "17.06.2026"


def test_multiple_rows():
    csv_text = (
        "Дата;ID кампании;Показы;Клики\n"
        "01.06.2026;1;100;5\n"
        "02.06.2026;2;200;10\n"
    )
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 2
    assert rows[0].campaign_id == "1"
    assert rows[1].campaign_id == "2"


def test_missing_columns_become_defaults():
    csv_text = "Дата;ID кампании\n01.06.2026;99\n"
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].sku == ""
    assert rows[0].impressions == 0
    assert rows[0].spend == 0.0


def test_non_numeric_values_become_zero():
    csv_text = "Показы;Клики;CTR;Расход\nabc;xyz;not_a_number;also_not\n"
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].impressions == 0
    assert rows[0].clicks == 0
    assert rows[0].ctr == 0.0
    assert rows[0].spend == 0.0


def test_comma_decimal_separator():
    csv_text = "CTR;CPC;Расход\n2,5;48,13;625,65\n"
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].ctr == 2.5
    assert rows[0].cpc == 48.13
    assert rows[0].spend == 625.65


def test_row_to_dict():
    csv_text = (
        "Дата;ID кампании;Показы\n"
        "17.06.2026;123;591\n"
    )
    rows = parse_performance_csv(csv_text)
    d = rows[0].to_dict()
    assert d["date"] == "17.06.2026"
    assert d["campaign_id"] == "123"
    assert d["impressions"] == 591
