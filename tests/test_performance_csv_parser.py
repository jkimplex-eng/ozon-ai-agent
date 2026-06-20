"""Tests for Performance API CSV parser."""
from __future__ import annotations

from ozon_agent.performance.csv_parser import parse_performance_csv

REAL_CSV_HEADER = (
    ";Кампания по продвижению товаров № 29645639, "
    "период 16.06.2026-19.06.2026\n"
    "День;sku;Название товара;Цена товара, ₽;Показы;Клики;"
    "CTR, %;Добавления в корзину;Средняя стоимость клика, ₽;"
    "Расход, ₽, с НДС;Продано товаров;Продажи в продвижении, ₽;"
    "Продано товаров модели;Продажи в продвижении с заказов модели, ₽;"
    "ДРР в продвижении, %;Заказано на сумму, ₽;"
    "ДРР (общий), %;Дата добавления"
)


def test_empty_csv():
    assert parse_performance_csv("") == []
    assert parse_performance_csv("   ") == []


def test_no_header():
    assert parse_performance_csv("a;b;c") == []


def test_simple_csv():
    csv_text = (
        f"{REAL_CSV_HEADER}\n"
        "17.06.2026;4536601352;Product;12626,00;591;13;"
        "2,20;0;48,13;625,65;"
        "0;0,00;0;0,00;0,0;0,00;0,0;17.06.2026\n"
    )
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    row = rows[0]
    assert row.date == "17.06.2026"
    assert row.sku == "4536601352"
    assert row.product_name == "Product"
    assert row.impressions == 591
    assert row.clicks == 13
    assert row.ctr == 2.20
    assert row.add_to_cart == 0
    assert row.cpc == 48.13
    assert row.spend == 625.65
    assert row.orders == 0
    assert row.revenue == 0.0
    assert row.added_at == "17.06.2026"


def test_multiple_rows():
    csv_text = (
        f"{REAL_CSV_HEADER}\n"
        "01.06.2026;111;P1;1000;100;5;5,0;0;20,0;100,0;1;500,0;0;0,0;0,5;300,0;0,3;01.06.2026\n"
        "02.06.2026;222;P2;2000;200;10;5,0;0;15,0;150,0;2;1000,0;0;0,0;0,3;600,0;0,3;02.06.2026\n"
    )
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 2
    assert rows[0].sku == "111"
    assert rows[1].sku == "222"


def test_missing_columns_become_defaults():
    csv_text = f"{REAL_CSV_HEADER}\n01.06.2026;99;;;;;;;;;;;;\n"
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].sku == "99"
    assert rows[0].impressions == 0
    assert rows[0].spend == 0.0


def test_non_numeric_values_become_zero():
    csv_text = (
        f"{REAL_CSV_HEADER}\n"
        "01.06.2026;abc;P;0;abc;xyz;not_a_number;0;0;0;0;0;0;0;0;0;0;01.06.2026\n"
    )
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].impressions == 0
    assert rows[0].clicks == 0
    assert rows[0].ctr == 0.0
    assert rows[0].spend == 0.0


def test_comma_decimal_separator():
    csv_text = (
        f"{REAL_CSV_HEADER}\n"
        "01.06.2026;1;P;0;0;0;2,50;0;48,13;625,65;0;0;0;0;0;0;0;01.06.2026\n"
    )
    rows = parse_performance_csv(csv_text)
    assert len(rows) == 1
    assert rows[0].ctr == 2.50
    assert rows[0].cpc == 48.13
    assert rows[0].spend == 625.65


def test_row_to_dict():
    csv_text = (
        f"{REAL_CSV_HEADER}\n"
        "17.06.2026;123;P;0;591;0;0;0;0;0;0;0;0;0;0;0;0;17.06.2026\n"
    )
    rows = parse_performance_csv(csv_text)
    d = rows[0].to_dict()
    assert d["date"] == "17.06.2026"
    assert d["sku"] == "123"
    assert d["impressions"] == 591
