# Ozon AI Agent

Autonomous analytics agent for Ozon marketplace.

## Architecture

```
Ozon Seller API → ETL Pipeline → PostgreSQL Data Warehouse → ML Models → Decision Engine
```

## Data Warehouse Schema

Core entities with history:
- `products` - product catalog with price history
- `orders` - order details from FBO/FBS
- `sales` - daily aggregated sales per product
- `advertising` - campaign performance data
- `search_positions` - search ranking history
- `competitors` - competitor price tracking
- `reviews` - customer reviews
- `stocks` - inventory levels
- `finance` - daily P&L
- `experiments` - A/B test journal
- `decisions` - decision engine log

## Quick Start

```bash
# Start PostgreSQL
docker-compose up -d

# Install dependencies
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your Ozon API credentials

# Run initial sync
ozon-agent sync --days 30

# Check status
ozon-agent status
```

## Development

```bash
# Run tests
pytest

# Type check
mypy src/

# Lint
ruff check src/
```

## ETL Pipeline

```bash
# Full sync (products + orders + finance)
ozon-agent sync --days 7

# Individual sync
ozon-agent sync-products
ozon-agent sync-orders 2026-06-01 2026-06-13
ozon-agent sync-finance 2026-06-01 2026-06-13
```

## Roadmap

- [x] Phase 1: Data Warehouse schema + ETL
- [ ] Phase 2: Analytics & diagnostics
- [ ] Phase 3: Forecasting models
- [ ] Phase 4: Decision Engine
- [ ] Phase 5: Autonomous experiments
