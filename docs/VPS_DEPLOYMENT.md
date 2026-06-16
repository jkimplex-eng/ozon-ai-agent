# VPS Deployment Guide

## Prerequisites

- SSH key auth to VPS
- pm2 installed on VPS
- Node.js 18+ on VPS
- PostgreSQL accessible from VPS

## Deploy Commands

### Dry Run (Default)
```bash
ozon-agent deploy --dry-run --target vps
```

### Execute Deploy
```bash
ozon-agent deploy --target vps --execute
```

### Rollback
```bash
ozon-agent rollback --target vps
```

## Migration

Before deploying, run migrations:
```bash
ozon-agent migrate --dry-run
ozon-agent migrate
```

### Migration Files
- `001_initial_schema.sql` — Core tables
- `002_recommendations_approval.sql` — Recommendations + outcomes
- `003_experiments.sql` — Experiment tracking

## Phase 5: Experiment Engine

**Status:** Implemented / Integrated

### Safety
- Control-plane only — no automatic Ozon actions
- No external API calls from experiments module
- Supervisor scans for forbidden keywords
- Telegram can only manage experiment state

### Commands
```bash
# Create experiment
ozon-agent experiments create --sku SKU-1 --hypothesis "Test bid increase" --action INCREASE_BUDGET

# List experiments
ozon-agent experiments list
ozon-agent experiments list --status RUNNING

# Lifecycle
ozon-agent experiments ready <id>
ozon-agent experiments start <id>
ozon-agent experiments pause <id>
ozon-agent experiments resume <id>
ozon-agent experiments complete <id>
ozon-agent experiments cancel <id> --reason "no longer needed"

# Metrics
ozon-agent experiments metrics <id> --baseline-orders 10 --current-orders 15

# Evaluation
ozon-agent experiments evaluate <id>
ozon-agent experiments report <id>

# Create from recommendation
ozon-agent experiments create-from-recommendation <recommendation_id>
```

### Telegram Commands
```
/experiments list
/experiments show <id>
/experiments ready <id>
/experiments start <id>
/experiments pause <id>
/experiments complete <id>
/experiments cancel <id> reason
/experiments report <id>
```

## Supervisor Audit
```bash
ozon-agent supervise --task-goal "Phase 5 experiment integration"
```

## Health Check
```bash
ssh vps 'pm2 list'
ssh vps 'pm2 logs ollama-bot --lines 10 --nostream'
ssh vps 'curl -s http://localhost:3000/health'
```
