# Performance API Sheets Export

The `Performance Stats` Google Sheets tab exports normalized, read-only Ozon Performance API report rows.

## Source

The exporter reads the latest JSON file from:

```text
data/performance/normalized/stats/
```

Expected file shape:

```json
{
  "rows": [
    {
      "date": "2026-06-17",
      "campaign_id": "29645639",
      "campaign_name": "",
      "sku": "4536601352",
      "product_name": "Product",
      "impressions": 591,
      "clicks": 13,
      "ctr": 2.2,
      "add_to_cart": 0,
      "cpc": 48.13,
      "spend": 625.65,
      "orders": 0,
      "revenue": 0,
      "model_orders": 0,
      "model_revenue": 0,
      "drr": 0,
      "ordered_amount": 0,
      "total_drr": 0,
      "added_at": "17.06.2026"
    }
  ]
}
```

The Sheets exporter does not call the Performance API. It only reads local normalized files.

## Tab Columns

```text
date
campaign_id
campaign_name
sku
product_name
impressions
clicks
ctr
add_to_cart
cpc
spend
orders
revenue
model_orders
model_revenue
drr_promo
ordered_amount
drr_total
raw_date_added
```

Field aliases:

```text
drr -> drr_promo
total_drr -> drr_total
added_at -> raw_date_added
```

Missing optional fields are exported as empty values. If no normalized stats file exists, the tab is still updated with headers and a `NO DATA` marker row.

## Command

```bash
python -m ozon_agent.cli sheets sync --source files --delay 30
```

For a single-tab smoke test:

```bash
python -m ozon_agent.cli sheets sync --tab "Performance Stats" --source files
```

## Safety

This export is read-only. It does not change campaigns, bids, budgets, products, stock, or prices.
