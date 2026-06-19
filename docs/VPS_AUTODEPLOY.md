# VPS Auto-Deploy Pipeline

## Overview

Automated deployment pipeline for ozon-ai-agent to VPS with safety checks, health verification, and rollback support.

## Architecture

```
Local Machine                    VPS
┌─────────────────┐     ┌──────────────────────┐
│ scripts/         │ SSH │ /root/ozon-ai-agent/  │
│  deploy_vps.sh   │────▶│  pip install -e .     │
│  verify_vps.sh   │────▶│  pm2 restart ...      │
│  rollback_vps.sh │────▶│  sheets sync ...      │
└─────────────────┘     └──────────────────────┘
```

## Quick Start

### Deploy
```bash
bash scripts/deploy_vps.sh main vps
```

### Verify
```bash
bash scripts/verify_vps.sh vps
```

### Rollback
```bash
bash scripts/rollback_vps.sh vps 1
```

## CLI Commands

```bash
# Deploy with supervisor checks
ozon-agent deploy vps --target vps --branch main

# Deploy (execute mode)
ozon-agent deploy vps --target vps --execute

# Health check
ozon-agent deploy verify --target vps

# Rollback
ozon-agent deploy rollback --target vps --commits 1
```

## Scripts

### scripts/deploy_vps.sh

Full deployment pipeline:
1. Pre-flight: lint, mypy, tests
2. Push code to origin
3. Pull on VPS
4. Install dependencies
5. Run migrations
6. Restart services
7. Health checks (git rev, import, CLI, supervisor, sheets sync, env vars)

Safety:
- Blocks if `.env` contains service account keys
- Blocks if `secrets/` directory exists locally
- Never prints service account JSON

### scripts/verify_vps.sh

Comprehensive verification:
- Git revision match
- Python import
- CLI availability
- Dependencies (gspread, apscheduler, pandas, psycopg)
- Environment variables
- PM2 process status
- Google Sheets sync dry run
- File permissions

### scripts/rollback_vps.sh

Safe rollback:
- Reverts N commits
- Reinstalls dependencies
- Restarts services
- Health check

## Supervisor Configs

### deploy/supervisor/ozon-sheets-watch.conf

```ini
[program:ozon-sheets-watch]
command=python -m ozon_agent.cli sheets watch --interval 30
directory=/root/ozon-ai-agent
autostart=true
autorestart=true
```

Runs Google Sheets auto-sync every 30 minutes.

### deploy/supervisor/ozon-telegram-bot.conf

```ini
[program:ozon-telegram-bot]
command=python -m ozon_agent.cli telegram
directory=/root/ozon-ai-agent
autostart=true
autorestart=true
```

Runs Telegram bot for experiment management.

## Health Checks

| Check | What it verifies |
|-------|-----------------|
| git_revision | Remote matches local |
| python_import | `import ozon_agent` works |
| cli_available | `ozon-agent --help` works |
| dependencies | gspread, pandas, psycopg installed |
| env_vars | DATABASE_URL, GOOGLE_SHEETS_SPREADSHEET_ID set |
| sheets_sync | Dry run succeeds without FAILED tabs |
| pm2 | ozon processes are online |
| http | Health endpoint returns 200 |
| logs | No fatal errors in recent logs |

## Safety Rules

1. **Never commit secrets** — deploy script blocks if `secrets/` exists
2. **Never print service account JSON** — grep blocks it
3. **Fail fast on missing env** — health check catches it
4. **Rollback if smoke tests fail** — deploy script suggests rollback
5. **Dry-run first** — all scripts support dry-run mode

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://...
GOOGLE_SERVICE_ACCOUNT_JSON=/root/ozon-ai-agent/secrets/google-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=1Moaku...

# Optional
SHEETS_DATA_SOURCE=files
SHEETS_SYNC_DELAY_SECONDS=10
SHEETS_RETRY_ATTEMPTS=3
SHEETS_RETRY_BACKOFF_SECONDS=30
TELEGRAM_BOT_TOKEN=...
```

## VPS Setup

```bash
# On VPS
cd /root
git clone https://github.com/jkimplex-eng/ozon-ai-agent.git
cd ozon-ai-agent
pip install -e .

# Install supervisor configs
cp deploy/supervisor/*.conf /etc/supervisor/conf.d/
supervisorctl reread
supervisorctl update

# Set env vars in .env (not committed)
echo "DATABASE_URL=..." >> .env
echo "GOOGLE_SHEETS_SPREADSHEET_ID=..." >> .env

# Place secrets
mkdir -p secrets
# Upload service account JSON to secrets/google-service-account.json
```

## Troubleshooting

### Deploy fails at pip install
```bash
ssh vps "cd /root/ozon-ai-agent && pip install -e . --verbose"
```

### Sheets sync 429 errors
```bash
ssh vps "SHEETS_SYNC_DELAY_SECONDS=30 python -m ozon_agent.cli sheets sync --source files"
```

### PM2 processes not starting
```bash
ssh vps "pm2 logs ozon-sheets-watch --lines 50"
ssh vps "pm2 restart ozon-sheets-watch"
```

### Rollback needed
```bash
bash scripts/rollback_vps.sh vps 1
# or
ozon-agent deploy rollback --target vps
```
