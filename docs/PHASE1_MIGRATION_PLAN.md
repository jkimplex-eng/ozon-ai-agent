# Phase 1 Migration Plan

## Executive Summary

Phase 1 migrates 5 modules from ollama-bot (Node.js) to ozon-ai-agent (Python):

| Module | Complexity | Business Value | Dependencies | Recommendation |
|--------|-----------|---------------|-------------|----------------|
| **Performance API** | Medium | HIGH | Ozon API, sheets | **First migration** |
| **Daily P&L** | Medium | HIGH | Ozon API, sheets, COGS | Second migration |
| **Ads Diagnostics** | Medium | HIGH | Performance, finance, COGS | Third migration |
| **Alerts** | Low | MEDIUM | Products, performance | Fourth migration |
| **Telegram Bot** | High | CRITICAL | All services | Last (Phase 1C) |

**Recommended first migration: Performance API**

Reasoning:
- Foundation for Daily P&L and Ads Diagnostics (both depend on it)
- Well-isolated module (single API client + queue + CSV parsing)
- Clear data contracts (JSON files, Google Sheets tabs)
- Low coupling to other services
- Already has typed client infrastructure in ozon-ai-agent

---

## Performance API

### ollama-bot Location
- **File:** `services/performance.js` (1952 lines)
- **Entry:** `createPerformanceService(deps)` factory
- **Key functions:** 30+ methods including token auth, campaign listing, statistics reports (create/download/parse CSV), queue management

### Ozon Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/client/token` | POST | OAuth token (client_credentials) |
| `/api/client/campaign` | GET | Campaign listing (paginated) |
| `/api/client/campaign/:id/objects` | GET | Campaign objects |
| `/api/client/limits/list` | GET | Bid limits |
| `/api/client/min/sku` | POST | Min bid per SKU |
| `/api/client/statistics` | POST | Create stats report request |
| `/api/client/statistics/list` | GET | List remote reports |
| `/api/client/statistics/report?UUID=` | GET | Download CSV report |

### Data Produced
- **Performance campaigns:** campaignId, name, state, type, budget, bids
- **Performance stats:** date, campaignId, SKU, impressions, clicks, spend, orders, revenue
- **Queue state:** pending/claimed/completed/failed jobs
- **Google Sheets tabs:** `performance_campaigns`, `performance_stats`

### Dependencies
- Internal: `sheetsService` (for Sheet writes), `fs` (file-based queue/rows)
- External: `httpx` (already in ozon-ai-agent)
- Auth: `OZON_PERFORMANCE_CLIENT_ID`, `OZON_PERFORMANCE_CLIENT_SECRET`

### Migration Path
1. Create `src/ozon_agent/api/performance_client.py`
2. Port token caching, campaign listing, stats report lifecycle
3. Port CSV parser (`normalizeStatsFromCsv`, `parseSemicolonCsv`)
4. Port queue management (file-based → PostgreSQL or file-based)
5. Add `performance_campaigns` and `performance_stats` tabs to sheets module
6. Add Performance API endpoints to typed client registry

### Target Architecture
```
src/ozon_agent/api/
  performance_client.py    # New: Performance API client
  ozon_client.py           # Existing: Seller API client

src/ozon_agent/sheets/exporters/
  performance_campaigns.py  # New: campaign tab exporter
  performance_stats.py      # New: stats tab exporter
```

---

## Daily P&L

### ollama-bot Location
- **Files:** `services/dailySummary.js` (1057 lines), `dailyControl.js` (391 lines), `dailySync.js` (548 lines)
- **Entry:** `createDailySummaryService(deps)`, `createDailyControlService(deps)`, `createDailySyncService(deps)`

### Ozon Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/finance/transaction/list` | POST | Finance transactions |
| `/v3/posting/fbo/list` | POST | FBO postings |
| `/v3/posting/fbs/list` | POST | FBS postings |

### Data Produced
- **Daily P&L summary:** revenue, payout, commission, logistics, ad spend, COGS, profit, margin, DRR
- **Daily control row:** 15-column metrics with plan deviation and run-rate
- **Insights:** margin warnings, ad spend alerts, commission alerts
- **Google Sheets tabs:** `daily_summary`, `daily_sku`, `daily_history`, `finance_raw`, `orders_raw`, `pl_diagnostics`, `daily_control`

### Dependencies
- Internal: `ozonService`, `performanceService` (for stored rows), `sheetsService`, `cogsService`, `salesFactsService`, `financeFactsService`
- External: `httpx`, timezone handling (`pytz` or `zoneinfo`)

### Migration Path
1. Port `buildFinanceSummary`, `buildOrdersSummary`, `buildSummary` calculations
2. Port `buildControlRow`, `buildDayMetrics` for daily control
3. Port `syncDaily` orchestration (fetch sales → fetch finance → build → write)
4. Port auto-sync timer (use APScheduler)
5. Add 7 new sheets tabs
6. Integrate with existing `analytics/` module (merge daily P&L logic)

### Target Architecture
```
src/ozon_agent/analytics/
  daily_pnl.py             # New: daily P&L calculations
  daily_control.py         # New: daily control row builder
  daily_sync.py            # New: sync orchestration

src/ozon_agent/sheets/exporters/
  daily_summary.py         # New
  daily_sku.py             # New
  daily_control.py         # New
  finance_raw.py           # New
  orders_raw.py            # New
  pl_diagnostics.py        # New
```

---

## Ads Diagnostics

### ollama-bot Location
- **File:** `services/adsDiagnostics.js` (1277 lines)
- **Entry:** `createAdsDiagnosticsService(deps)`

### Data Produced
- **Campaign summary:** per-campaign spend, CTR, CPC, DRR, warnings
- **SKU summary:** per-SKU ad metrics + organic sales + COGS
- **Factor analysis:** traffic quality, click cost, conversion, economics, stock risk, data quality, confidence
- **Reconciliation:** Performance API spend vs finance advertising
- **Coverage gaps:** uncovered ad spend with recommendations

### Dependencies
- Internal: `performanceService`, `financeFactsService`, `ozonService`, `salesFactsService`, `cogsService`, `prioritySkusService`, `externalTrafficPlanService`
- Data: performance rows, finance facts, sales facts, COGS, stock, products

### Migration Path
1. Port `aggregateByDate`, `aggregateCampaignSummary`, `aggregateSkuSummary`
2. Port classification functions (traffic quality, click cost, conversion, economics, stock risk, data quality, confidence)
3. Port reconciliation logic
4. Port coverage gap analysis
5. Integrate with existing `analytics/factors.py` (extend factor analysis)

### Target Architecture
```
src/ozon_agent/analytics/
  ads_diagnostics.py       # New: campaign + SKU + factor analysis
  reconciliation.py        # New: Performance vs finance reconciliation
```

---

## Alerts

### ollama-bot Location
- **File:** `services/alerts.js` (374 lines)
- **Entry:** `createAlertsService(deps)`

### Alerts Detected
| Alert | Severity | Condition |
|-------|----------|-----------|
| Low stock | HIGH | 0 < stock ≤ threshold (default 5) |
| Missing stock | MEDIUM | stock is null |
| Missing SKU/Offer | MEDIUM | no sku or offerId |
| Expensive campaigns | MEDIUM | spend > 3000 |
| Spend without orders | HIGH | spend > 0 AND orders = 0 |

### Dependencies
- Internal: `ozonService` (getProducts), `performanceService` (getCampaignStats)
- Deduplication: SHA-1 signature of significant alerts

### Migration Path
1. Create `src/ozon_agent/alerts/` module
2. Port alert detection logic
3. Port deduplication (SHA-1 signature)
4. Add Telegram notification channel
5. Add `alerts` Google Sheets tab
6. Integrate with APScheduler for periodic checks

### Target Architecture
```
src/ozon_agent/alerts/
  __init__.py
  models.py               # AlertRule, AlertEvent
  engine.py               # AlertEvaluator, deduplication
  rules.py                # Individual alert rules
```

---

## Telegram Bot Audit

### ollama-bot Telegram (4074 lines)
- 150+ commands across 15+ command groups
- Full analytics, reporting, configuration, sync, optimization commands
- Russian language support
- Message formatting with markdown tables
- Short ID resolution for UUIDs

### ozon-ai-agent Telegram (312 lines)
- 14 commands across 2 groups (recommendations + experiments)
- Approve/reject recommendations only
- Experiment state management only
- No analytics, reporting, sync, or configuration commands

### Command Comparison Table

| Telegram Command | ollama-bot | ozon-ai-agent | Action |
|-----------------|-----------|---------------|--------|
| `/daily` | ✓ full | — | Migrate |
| `/daily в таблицу` | ✓ | — | Migrate |
| `/daily control` | ✓ | — | Migrate |
| `/management` | ✓ | — | Migrate |
| `/performance` | ✓ 20+ sub | — | Migrate |
| `/ads` | ✓ 13+ sub | — | Migrate |
| `/analytics` | ✓ | — | Migrate |
| `/report` | ✓ | — | Migrate |
| `/cogs` | ✓ | — | Migrate |
| `/sales` | ✓ | — | Migrate |
| `/finance` | ✓ | — | Migrate |
| `/alerts` | ✓ | — | Migrate |
| `/ai` | ✓ 6 modes | — | Migrate (enhance) |
| `/ozon товары` | ✓ | — | Migrate |
| `/ozon capture` | ✓ | — | Phase 2 |
| `/replenishment` | ✓ | — | Phase 2 |
| `/priority sku` | ✓ | — | Migrate |
| `/traffic plan` | ✓ | — | Migrate |
| `/warehouse mapping` | ✓ | — | Migrate |
| `/recommendations` | — | ✓ 4 cmds | Keep |
| `/recommendations approve` | — | ✓ | Keep |
| `/recommendations reject` | — | ✓ | Keep |
| `/experiments` | — | ✓ 8 cmds | Keep |
| `/experiments start` | — | ✓ | Keep |
| `/experiments report` | — | ✓ | Keep |
| `/sheet` | ✓ | — | Migrate |
| `/models` | ✓ | — | Migrate |
| `/health` | ✓ | ✓ deploy health | Merge |
| `/start` | ✓ | ✓ | Keep |
| `/chatid` | ✓ | — | Migrate |
| Free text (Ollama) | ✓ | — | Phase 2 |
| `/код\|/code` | ✓ | — | Phase 2 |

### Commands Already Migrated
- `/recommendations` (list, show, approve, reject)
- `/experiments` (list, show, ready, start, pause, complete, cancel, report)

### Commands Missing (need migration)
- `/daily` group (7 commands)
- `/daily control` (2 commands)
- `/management` (7 commands)
- `/performance` (20+ commands)
- `/ads` (13+ commands)
- `/analytics` (5 commands)
- `/report` (4 commands)
- `/cogs` (7 commands)
- `/sales` (3 commands)
- `/finance` (5 commands)
- `/alerts` (6 commands)
- `/ai` (6 commands)
- `/ozon товары` (1 command)
- `/priority sku` (4 commands)
- `/traffic plan` (3 commands)
- `/warehouse mapping` (3 commands)
- `/sheet` (1 command)
- `/models` (1 command)
- `/chatid` (1 command)

### Commands Obsolete
- `/ozon capture` → Phase 2 (browser automation)
- `/replenishment` → Phase 2
- Free text Ollama → Phase 2
- `/код|/code` → Phase 2

---

## Migration Order

| Phase | Module | Effort | Depends On |
|-------|--------|--------|-----------|
| **1A** | Performance API | 1 week | None |
| **1B** | Daily P&L | 1 week | 1A |
| **1B** | Ads Diagnostics | 1 week | 1A |
| **1C** | Alerts | 3 days | 1A |
| **1D** | Telegram Bot (commands) | 2 weeks | 1A, 1B, 1C |

**Total Phase 1: ~5-6 weeks**

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Performance API auth differences | LOW | Both use client_credentials, same flow |
| CSV parsing edge cases | MEDIUM | Test with real Ozon CSV output |
| Daily P&L calculation accuracy | MEDIUM | Port unit tests, compare outputs |
| Ads Diagnostics factor thresholds | LOW | Port configurable thresholds |
| Telegram command count (150+) | HIGH | Migrate incrementally, test each group |
| Google Sheets tab count (8→22+) | MEDIUM | Throttling already handles rate limits |
| Missing COGS data | MEDIUM | COGS module must be migrated first |

---

## Recommended First Migration

**Performance API** should be first because:

1. **Foundation dependency** — Daily P&L and Ads Diagnostics both consume Performance API data
2. **Isolated module** — Single API client with clear boundaries
3. **Clear contracts** — Token auth, campaign listing, CSV stats, queue management
4. **Existing infrastructure** — ozon-ai-agent already has httpx, typed clients, file-based storage
5. **Low risk** — Read-only API, no mutations, no side effects
6. **High value** — Enables all advertising analytics and optimization

**Implementation effort:** ~1 week
- Day 1-2: Performance API client (token, campaigns, stats)
- Day 3-4: CSV parser + queue management
- Day 5: Sheets integration (2 new tabs)
- Day 6-7: Tests + documentation
