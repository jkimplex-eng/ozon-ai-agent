# Live Ozon Data Ingestion

Live Ozon Data Ingestion is a read-only collection layer for Ozon Seller API data.
It fetches allowlisted Ozon endpoints, saves raw payloads, normalizes rows, and
keeps the result in local file storage for later ETL or diagnostics.

## Safety

The layer only permits explicit read-oriented datasets:

- `products`
- `stocks`
- `orders_fbo`
- `orders_fbs`
- `finance_operations`

Paths containing mutation markers such as import, update, delete, price, campaign,
bid, or budget are rejected before an HTTP call is made.

## Credentials

Live calls require:

```text
OZON_CLIENT_ID
OZON_API_KEY
```

Dry-run mode does not require credentials and does not call Ozon.

## Storage

Default storage:

```text
data/live_ozon/
  raw/
  normalized/
```

Override with:

```text
OZON_AGENT_LIVE_OZON_ROOT
```

## CLI

List datasets:

```bash
ozon-agent ingest ozon datasets
```

Dry-run a request:

```bash
ozon-agent ingest ozon run products --dry-run
```

Run a live read-only request:

```bash
ozon-agent ingest ozon run orders_fbo --date-from 2026-06-01 --date-to 2026-06-07
```

## Current Limitations

- The service fetches the first page only.
- It stores file snapshots and does not write to PostgreSQL yet.
- Ads Performance API ingestion remains separate from Seller API ingestion.
