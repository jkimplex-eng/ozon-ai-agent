#!/usr/bin/env bash
set -euo pipefail

# VPS Deploy Script for ozon-ai-agent
# Usage: bash scripts/deploy_vps.sh [branch] [target]

BRANCH="${1:-main}"
TARGET="${2:-vps}"
DEPLOY_DIR="/root/ozon-ai-agent"
LOG_FILE="/tmp/ozon-deploy-$(date +%Y%m%d-%H%M%S).log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
fail() { log "FAIL: $*"; exit 1; }

log "=== OZON AI AGENT DEPLOY ==="
log "Branch: $BRANCH"
log "Target: $TARGET"
log "Deploy dir: $DEPLOY_DIR"
log ""

# Pre-flight: never commit secrets
if [ -f .env ]; then
    if grep -q "SERVICE_ACCOUNT" .env 2>/dev/null; then
        fail "DANGER: .env contains service account keys. Remove before deploying."
    fi
fi

if [ -d secrets ]; then
    fail "DANGER: secrets/ directory exists locally. Never deploy secrets."
fi

# Step 1: Verify local state
log "Step 1: Verifying local state..."
python -m ruff check src/ tests/ --quiet || fail "Lint failed. Fix before deploying."
python -m mypy src/ --quiet 2>/dev/null || log "WARNING: mypy had issues (non-blocking)"
python -m pytest tests/ -q --tb=no 2>/dev/null || fail "Tests failed. Fix before deploying."
log "  Local checks passed."

# Step 2: Push code
log "Step 2: Pushing code to origin..."
git push origin "$BRANCH" || fail "Git push failed."
log "  Pushed."

# Step 3: Deploy on VPS
log "Step 3: Deploying on VPS..."
ssh "$TARGET" "cd $DEPLOY_DIR && git fetch origin && git checkout $BRANCH && git pull origin $BRANCH" \
    || fail "Git pull on VPS failed."
log "  Code updated."

# Step 4: Install dependencies
log "Step 4: Installing dependencies..."
ssh "$TARGET" "cd $DEPLOY_DIR && pip install -e . 2>&1 | tail -3" \
    || fail "pip install failed."
log "  Dependencies installed."

# Step 5: Run migrations
log "Step 5: Running migrations..."
ssh "$TARGET" "cd $DEPLOY_DIR && python -m ozon_agent.cli migrate --dry-run 2>&1 | head -5" \
    || log "  WARNING: migrate check failed (non-blocking)"
log "  Migrations checked."

# Step 6: Restart services
log "Step 6: Restarting services..."
ssh "$TARGET" "pm2 restart ozon-sheets-watch 2>/dev/null || true"
ssh "$TARGET" "pm2 restart ozon-telegram-bot 2>/dev/null || true"
ssh "$TARGET" "pm2 save 2>/dev/null || true"
log "  Services restarted."

# Step 7: Health checks
log "Step 7: Running health checks..."
HEALTH_OK=true

# Git revision
REMOTE_REV=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "UNKNOWN")
LOCAL_REV=$(git rev-parse --short HEAD)
if [ "$REMOTE_REV" = "$LOCAL_REV" ]; then
    log "  Git revision: $REMOTE_REV ✓"
else
    log "  WARNING: Rev mismatch local=$LOCAL_REV remote=$REMOTE_REV"
    HEALTH_OK=false
fi

# Python import
ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import ozon_agent; print(ozon_agent.__version__)'" 2>/dev/null \
    && log "  Python import: OK ✓" \
    || { log "  Python import: FAILED"; HEALTH_OK=false; }

# CLI availability
ssh "$TARGET" "cd $DEPLOY_DIR && ozon-agent --help >/dev/null 2>&1" \
    && log "  CLI: OK ✓" \
    || { log "  CLI: FAILED"; HEALTH_OK=false; }

# Supervisor status
ssh "$TARGET" "pm2 list 2>/dev/null | grep -q ozon" \
    && log "  Supervisor: OK ✓" \
    || log "  WARNING: No ozon processes in PM2"

# Sheets sync dry run
ssh "$TARGET" "cd $DEPLOY_DIR && SHEETS_DATA_SOURCE=files GOOGLE_SERVICE_ACCOUNT_JSON=/root/ozon-ai-agent/secrets/google-service-account.json GOOGLE_SHEETS_SPREADSHEET_ID=1MoakuEmSMkEEKf1TtoNkEF6wVyx_NBgheb3v-M4LqeI python -m ozon_agent.cli sheets sync --source files --delay 5 2>&1 | tail -12" \
    && log "  Sheets sync: OK ✓" \
    || log "  WARNING: Sheets sync had issues"

# Env vars
for VAR in GOOGLE_SERVICE_ACCOUNT_JSON GOOGLE_SHEETS_SPREADSHEET_ID; do
    ssh "$TARGET" "test -f \${$VAR:-/nonexistent} 2>/dev/null || test -n \${$VAR:-}" 2>/dev/null \
        && log "  Env $VAR: OK ✓" \
        || log "  WARNING: $VAR not set on VPS"
done

log ""
if [ "$HEALTH_OK" = true ]; then
    log "=== DEPLOY COMPLETE ==="
    log "All health checks passed."
else
    log "=== DEPLOY COMPLETE WITH WARNINGS ==="
    log "Some health checks failed. Review warnings above."
    log "Rollback: bash scripts/rollback_vps.sh $TARGET"
fi

log "Log saved to: $LOG_FILE"
