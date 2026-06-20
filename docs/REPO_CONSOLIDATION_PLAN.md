# Repository Consolidation Plan: ollama-bot + ozon-ai-agent

## Status: Audit Complete — Plan Only, No Auto-Migration

---

## 1. Current State

### ollama-bot (Node.js)

| Aspect | Details |
|--------|---------|
| Language | Node.js (Express) |
| Lines of code | ~12,000+ service code |
| Services | 26 service files + 2 verification modules |
| Telegram | 150+ commands, primary UI |
| Google Sheets | Apps Script webhook (POST to webapp URL) |
| Ozon API | Seller API + Performance API (full) |
| Browser automation | CDP/Edge/Playwright capture system |
| Queue | Capture queue (FIFO, file-backed) |
| AI | Ollama integration (4 models) |
| Decision engine | Rule-based + AI prompts |
| Scheduler | setInterval jobs (products 30min, stocks 1hr) |
| PM2 | Process management |
| Tests | Integration assertions only (no framework) |
| Dependencies | 6 npm packages |

### ozon-ai-agent (Python)

| Aspect | Details |
|--------|---------|
| Language | Python 3.11+ |
| Lines of code | ~8,000+ src + 2,439 CLI |
| Modules | 20+ modules across src/ozon_agent/ |
| Telegram | 20 commands (approve/reject only) |
| Google Sheets | gspread direct API (8 tabs, throttled) |
| Ozon API | Seller API client + typed client layer |
| Browser automation | None |
| Queue | None |
| AI | Ollama (optional), ML models |
| Decision engine | ML-based (XGBoost, LightGBM, confidence/risk) |
| Scheduler | APScheduler (sheets watch) |
| Supervisor | SSH deploy, health checks |
| Tests | 392 tests, 59 test files |
| Dependencies | 23 runtime packages |

---

## 2. Component Map

### Unique to ollama-bot

| Component | Files | Why it matters |
|-----------|-------|----------------|
| **Telegram Bot (full)** | `services/telegram.js` (1665 lines) | 150+ commands, primary user interface |
| **Browser Automation** | `ozonBrowserCapture.js`, `ozon-ai-agent/` subdir | CDP/Edge/Playwright for Ozon Seller data capture |
| **Remote Capture Queue** | `ozonCaptureQueue.js` | FIFO job queue for distributed capture |
| **Ollama Integration** | `services/ollama.js` | Chat/coder/analytics model routing |
| **Daily P&L System** | `dailySummary.js`, `dailyControl.js`, `dailySync.js` | Full daily financial reporting |
| **Management Workbook** | `managementWorkbook.js` | Monthly Google Sheets tab management |
| **Ads Diagnostics** | `adsDiagnostics.js` (1277 lines) | Deep campaign/SKU analysis |
| **Ads Optimizer** | `adsOptimizer.js` | Rule-based budget recommendations |
| **Performance API Client** | `performance.js` (1952 lines) | Full Performance API with CSV parsing |
| **COGS Management** | `cogs.js` | SKU-to-cost mapping |
| **Replenishment** | `replenishment.js` | Stock forecasting + warehouse planning |
| **Alerts System** | `alerts.js` | Low stock, expensive campaigns, spend detection |
| **Background Jobs** | `jobs.js` | Periodic sync with retry |
| **SKU-Day Analysis** | `skuDay.js` | Granular per-SKU-per-day metrics |
| **Express Web UI** | `routes/api.js` | HTTP API + chat-stream + cron endpoints |
| **Data Verification** | `verification/` | Reconciliation + SKU-day validation |
| **Profile/Memory** | `routes/api.js` | Chat memory + user facts |

### Unique to ozon-ai-agent

| Component | Files | Why it matters |
|-----------|-------|----------------|
| **PostgreSQL Database** | `db/` | Persistent structured data storage |
| **ML Forecasting** | `forecast/` | Prophet, XGBoost, LightGBM |
| **Decision Engine (ML)** | `decision/` | Feature store, confidence/risk scoring |
| **Approval Workflow** | `approval/` | PENDING→APPROVED→EXECUTED→OBSERVED |
| **Experiments (DB-backed)** | `experiments/` | A/B testing with state machine |
| **Learning System** | `learning/` | Outcome learning, calibration, backtesting |
| **Recommendation Memory** | `memory/` | Persistent rec memory with similarity |
| **Knowledge Engine** | `knowledge/` | Expert rules (ads, pricing, ranking) |
| **Research System** | `research/` | Competitor snapshots, market insights |
| **Google Sheets (direct)** | `sheets/` | gspread API, 8 tabs, throttling |
| **ETL Pipeline** | `etl/` | Structured data sync to PostgreSQL |
| **Live Ingestion** | `ingestion/` | Read-only Ozon API with validation |
| **Typed API Clients** | `integrations/` | Swagger-derived typed clients |
| **Supervisor** | `supervisor/` | Git status, test results, risk detection |
| **Deploy System** | `deploy/` | SSH deploy, health checks, rollback |
| **CLI** | `cli.py` | 70+ commands via Click |
| **Skills Registry** | `skills/` | Extensible skill system |
| **MCP Discovery** | `mcp/` | Tool registry (execution disabled) |
| **A/B Experiment Tracking** | `experiments/` | DB-backed with event logging |
| **Confidence Calibration** | `learning/` | Historical calibration by action/SKU/risk |
| **Backtesting** | `learning/` | Historical recommendation evaluation |

### Duplicated / Overlapping

| Component | ollama-bot | ozon-ai-agent | Overlap level |
|-----------|-----------|---------------|---------------|
| **Google Sheets** | Apps Script webhook | gspread direct API | HIGH — different approach |
| **Ozon Seller API** | `ozon.js` (httpx) | `api/ozon_client.py` (httpx) | HIGH — same endpoints |
| **Ozon Performance API** | `performance.js` | None | UNIQUE to bot |
| **Recommendations** | `decisionEngine.js` (AI) | `decision/` (ML) | MEDIUM — different approach |
| **Decision Engine** | Rule-based + AI prompts | ML feature store | MEDIUM — complementary |
| **Daily P&L** | `dailySummary.js` | `analytics/` | HIGH — overlapping calculations |
| **AI/LLM** | Ollama (4 models) | Ollama (optional) | LOW — bot has full integration |
| **Scheduler** | setInterval | APScheduler | LOW — different mechanisms |
| **Alerts** | `alerts.js` | None | UNIQUE to bot |
| **Products/Stocks sync** | `jobs.js` | `etl/sync.py` | HIGH — same data flow |
| **COGS** | `cogs.js` | None | UNIQUE to bot |
| **Replenishment** | `replenishment.js` | None | UNIQUE to bot |

---

## 3. What to Migrate

### Priority 1: Core Features (must have)

| Feature | From | To | Complexity |
|---------|------|----|------------|
| **Telegram Bot (full)** | ollama-bot/services/telegram.js | ozon-ai-agent/telegram/ | HIGH — rewrite in Python |
| **Performance API Client** | ollama-bot/services/performance.js | ozon-ai-agent/api/ | MEDIUM — port to Python |
| **Daily P&L System** | ollama-bot/services/daily*.js | ozon-ai-agent/analytics/ | MEDIUM — merge with existing |
| **Ads Diagnostics** | ollama-bot/services/adsDiagnostics.js | ozon-ai-agent/analytics/ | MEDIUM — port logic |
| **Ads Optimizer** | ollama-bot/services/adsOptimizer.js | ozon-ai-agent/decision/ | LOW — enhance existing |
| **COGS Management** | ollama-bot/services/cogs.js | ozon-ai-agent/analytics/ | LOW — new module |
| **Alerts System** | ollama-bot/services/alerts.js | ozon-ai-agent/ (new) | LOW — new module |
| **Background Jobs** | ollama-bot/services/jobs.js | ozon-ai-agent/ (APScheduler) | LOW — use existing scheduler |

### Priority 2: Nice to have

| Feature | From | To | Complexity |
|---------|------|----|------------|
| **Browser Automation** | ollama-bot/ozonBrowserCapture.js | ozon-ai-agent/ (new) | HIGH — needs Playwright |
| **Remote Capture Queue** | ollama-bot/ozonCaptureQueue.js | ozon-ai-agent/ (new) | MEDIUM — queue system |
| **Replenishment** | ollama-bot/services/replenishment.js | ozon-ai-agent/analytics/ | MEDIUM — port logic |
| **SKU-Day Analysis** | ollama-bot/services/skuDay.js | ozon-ai-agent/analytics/ | MEDIUM — port logic |
| **Ollama Integration** | ollama-bot/services/ollama.js | ozon-ai-agent/ (enhance) | LOW — already has Ollama |
| **Data Verification** | ollama-bot/services/verification/ | ozon-ai-agent/analytics/ | LOW — new module |
| **Management Workbook** | ollama-bot/services/managementWorkbook.js | ozon-ai-agent/sheets/ | LOW — enhance sheets |

### Priority 3: Defer

| Feature | From | To | Complexity |
|---------|------|----|------------|
| **Express Web UI** | ollama-bot/routes/api.js | ozon-ai-agent/ (FastAPI) | HIGH — different framework |
| **Chat Memory/Profile** | ollama-bot/routes/api.js | ozon-ai-agent/memory/ | LOW — already has memory |

---

## 4. What to Archive

| Component | Reason |
|-----------|--------|
| `services/calendar.js` | Empty stub (7 lines) |
| `node_modules/` | Not needed after migration |
| `ecosystem.config.js` | PM2 config, replace with supervisor |
| `routes/api.js` (Express) | Replace with FastAPI or remove |
| `exports/` | User-specific chat exports |
| `uploads/` | File upload staging |
| `data/salesRows.json` | Temporary data, move to DB |
| `data/financeRows.json` | Temporary data, move to DB |
| `data/cogsMapping.json` | Move to DB or file store |
| `data/alertsState.json` | Move to DB or file store |
| `data/performanceQueue.json` | Move to DB or file store |
| `data/captureQueue.json` | Move to DB or file store |

---

## 5. What Must Stay Separate

| Component | Reason |
|-----------|--------|
| **Google Apps Script** | External deployment, can't merge |
| **Edge Browser Profile** | Local machine, not portable |
| **Ollama Models** | External service, keep as-is |
| **PM2 (for ollama-bot)** | Until fully migrated |

---

## 6. Target Architecture

```
ozon-ai-agent (Python, single product)
├── src/ozon_agent/
│   ├── api/                  # Ozon Seller + Performance API
│   ├── db/                   # PostgreSQL
│   ├── etl/                  # Data sync
│   ├── analytics/            # Daily P&L, ads diagnostics, COGS, SKU-day
│   ├── forecast/             # ML forecasting
│   ├── decision/             # ML recommendations + rule-based optimizer
│   ├── approval/             # Approval workflow
│   ├── experiments/          # A/B experiments (DB-backed)
│   ├── learning/             # Outcome learning, calibration
│   ├── memory/               # Recommendation memory
│   ├── knowledge/            # Expert rules
│   ├── research/             # Market research
│   ├── sheets/               # Google Sheets (gspread)
│   ├── telegram/             # Full Telegram bot (150+ commands)
│   ├── alerts/               # Alert system
│   ├── ingestion/            # Live Ozon ingestion
│   ├── browser/              # CDP/Edge capture (new)
│   ├── queue/                # Job queue (new)
│   ├── supervisor/           # Audit
│   ├── deploy/               # VPS deploy
│   ├── integrations/         # Typed API clients
│   ├── skills/               # Skills registry
│   └── cli.py                # CLI entry point
├── scripts/
│   ├── deploy_vps.sh
│   ├── verify_vps.sh
│   └── rollback_vps.sh
├── deploy/supervisor/
├── tests/                    # All tests
└── docs/
```

---

## 7. Migration Plan (Phases)

### Phase 1: Telegram Bot (Week 1-2)
- [ ] Port `telegram.js` command router to Python
- [ ] Port all 150+ command handlers
- [ ] Port message formatting (markdown tables)
- [ ] Port short ID resolution
- [ ] Test all command groups
- **Risk**: High — largest single migration, must maintain all commands

### Phase 2: Performance API + Daily P&L (Week 2-3)
- [ ] Port `performance.js` to Python httpx client
- [ ] Port `dailySummary.js` calculations
- [ ] Port `dailyControl.js` (plan deviation, run-rate)
- [ ] Port `dailySync.js` orchestration
- [ ] Merge with existing `analytics/` module
- **Risk**: Medium — well-defined calculations, mostly porting

### Phase 3: Ads + COGS + Alerts (Week 3-4)
- [ ] Port `adsDiagnostics.js` analysis logic
- [ ] Port `adsOptimizer.js` rule engine
- [ ] Port `cogs.js` CRUD
- [ ] Port `alerts.js` detection logic
- [ ] Integrate with `decision/` module
- **Risk**: Low — isolated modules

### Phase 4: Browser Automation + Queue (Week 4-5)
- [ ] Port `ozonBrowserCapture.js` to Python Playwright
- [ ] Port `ozonCaptureQueue.js` to PostgreSQL or file store
- [ ] Port remote capture worker
- [ ] Test CDP connection
- **Risk**: Medium — browser automation is platform-sensitive

### Phase 5: Google Sheets Consolidation (Week 5)
- [ ] Merge `sheetsMap.js` column mappings into Python
- [ ] Add missing tabs from ollama-bot (16 → extend)
- [ ] Keep gspread approach (better than Apps Script webhook)
- [ ] Add Apps Script fallback option
- **Risk**: Low — already working in both

### Phase 6: Jobs + Scheduler (Week 6)
- [ ] Port `jobs.js` background sync to APScheduler
- [ ] Port `replenishment.js` logic
- [ ] Port `skuDay.js` analysis
- [ ] Port `verification/` modules
- **Risk**: Low — isolated modules

### Phase 7: Cleanup + Archive (Week 7)
- [ ] Archive ollama-bot repo
- [ ] Remove duplicate code
- [ ] Update documentation
- [ ] Final testing
- **Risk**: Low

---

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Telegram bot migration breaks commands | HIGH | Test each command group incrementally |
| Google Sheets column mismatch | MEDIUM | Validate column counts match |
| Performance API auth differences | LOW | Both use client_credentials, same flow |
| Browser automation platform issues | MEDIUM | Test on VPS + Windows separately |
| Data format incompatibilities | MEDIUM | Normalize on ingestion |
| Missing environment variables | LOW | Document all vars, check .env |
| Ollama model availability | LOW | Both use same Ollama endpoint |
| PostgreSQL schema conflicts | LOW | New tables for new features |

---

## 9. Effort Estimate

| Phase | Effort | Dependencies |
|-------|--------|-------------|
| Phase 1: Telegram | 2 weeks | None |
| Phase 2: Performance + P&L | 1 week | None |
| Phase 3: Ads + COGS + Alerts | 1 week | Phase 2 |
| Phase 4: Browser + Queue | 1 week | None |
| Phase 5: Sheets | 3 days | None |
| Phase 6: Jobs + Scheduler | 3 days | Phase 2 |
| Phase 7: Cleanup | 2 days | All above |
| **Total** | **~7 weeks** | |

---

## 10. Decision Points

1. **Keep both repos or archive ollama-bot?** → Archive after migration complete
2. **Keep Apps Script as fallback?** → Yes, for users who prefer it
3. **Port Express web UI?** → Defer — Telegram is primary, CLI is secondary
4. **Keep Ollama integration?** → Yes, already in ozon-ai-agent
5. **Browser automation priority?** → Phase 4 (nice to have, not critical)
