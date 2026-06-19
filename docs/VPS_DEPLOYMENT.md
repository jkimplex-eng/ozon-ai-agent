# VPS Deployment Guide

## Prerequisites

- SSH key auth to VPS
- supervisor installed on VPS
- Python 3.11+ on VPS
- PostgreSQL accessible from VPS

## Deploy Commands

### Dry Run (Default)
```bash
ozon-agent deploy vps --target vps --branch main
```

### Execute Deploy
```bash
ozon-agent deploy vps --target vps --branch main --execute
```

### Rollback
```bash
ozon-agent deploy rollback --target vps
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
ssh vps 'supervisorctl status ozon-sheets-watch'
ssh vps 'grep -q "sheets watch --interval 30" /etc/supervisor/conf.d/ozon-sheets-watch.conf'
ssh vps 'tail -50 /root/ozon-ai-agent/logs/ozon-sheets-watch.log'
```
