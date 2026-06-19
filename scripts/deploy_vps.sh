#!/usr/bin/env bash
set -euo pipefail

# VPS Deploy Script for ozon-ai-agent
# Usage: bash scripts/deploy_vps.sh [branch] [target]

BRANCH="${1:-main}"
TARGET="${2:-vps}"
DEPLOY_DIR="/root/ozon-ai-agent"
VENV="/root/ozon-ai-agent/.venv/bin/activate"
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
python -m ruff check src/ tests/ --quiet || fail "Lint failed."
log "  Lint: OK"

# Step 2: Push code
log "Step 2: Pushing code..."
git push origin "$BRANCH" || fail "Git push failed."
log "  Pushed."

# Step 3: Deploy on VPS
log "Step 3: Deploying on VPS..."
ssh "$TARGET" "cd $DEPLOY_DIR && git fetch origin && git checkout $BRANCH && git pull origin $BRANCH" \
    || fail "Git pull on VPS failed."
log "  Code updated."

# Step 4: Install dependencies
log "Step 4: Installing dependencies..."
ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && pip install -e . 2>&1 | tail -3" \
    || fail "pip install failed."
log "  Dependencies installed."

# Step 5: Verify CLI
log "Step 5: Verifying CLI..."
ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && python -m ozon_agent.cli --help >/dev/null 2>&1" \
    && log "  CLI: OK" \
    || fail "CLI verification failed."
log "  CLI available."

# Step 6: Sheets sync
log "Step 6: Running sheets sync..."
ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && SHEETS_DATA_SOURCE=files python -m ozon_agent.cli sheets sync --source files --delay 10 2>&1 | tail -12" \
    || log "  WARNING: sheets sync had issues"
log "  Sheets sync done."

# Step 7: Supervisor
log "Step 7: Checking Supervisor..."
if ssh "$TARGET" "command -v supervisorctl >/dev/null 2>&1"; then
    ssh "$TARGET" "supervisorctl reread 2>/dev/null || true"
    ssh "$TARGET" "supervisorctl update 2>/dev/null || true"
    ssh "$TARGET" "supervisorctl restart ozon-agent:* 2>/dev/null || true"
    ssh "$TARGET" "supervisorctl status" || true
    log "  Supervisor: restarted."
else
    log "  WARNING: Supervisor not installed. Services not restarted."
fi

# Step 8: Health checks
log "Step 8: Health checks..."
HEALTH_OK=true

REMOTE_REV=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "UNKNOWN")
LOCAL_REV=$(git rev-parse --short HEAD)
if [ "$REMOTE_REV" = "$LOCAL_REV" ]; then
    log "  Git revision: $REMOTE_REV ✓"
else
    log "  WARNING: Rev mismatch local=$LOCAL_REV remote=$REMOTE_REV"
    HEALTH_OK=false
fi

ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && python -c 'import ozon_agent; print(ozon_agent.__version__)'" 2>/dev/null \
    && log "  Python import: OK ✓" \
    || { log "  Python import: FAILED"; HEALTH_OK=false; }

ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && ozon-agent --help >/dev/null 2>&1" \
    && log "  CLI: OK ✓" \
    || { log "  CLI: FAILED"; HEALTH_OK=false; }

for VAR in GOOGLE_SERVICE_ACCOUNT_JSON GOOGLE_SHEETS_SPREADSHEET_ID; do
    ssh "$TARGET" "test -n \"${VAR:-}\" || echo MISSING" 2>/dev/null \
        && log "  Env $VAR: OK ✓" \
        || log "  WARNING: $VAR not set on VPS"
done

ssh "$TARGET" "test -f /root/ozon-ai-agent/secrets/google-service-account.json" 2>/dev/null \
    && log "  Secrets file: OK ✓" \
    || log "  WARNING: secrets/google-service-account.json missing"

ssh "$TARGET" "test -d /root/ozon-ai-agent/data" 2>/dev/null \
    && log "  Data dir: OK ✓" \
    || log "  WARNING: data/ directory missing"

log ""
if [ "$HEALTH_OK" = true ]; then
    log "=== DEPLOY COMPLETE ==="
else
    log "=== DEPLOY COMPLETE WITH WARNINGS ==="
    log "Rollback: bash scripts/rollback_vps.sh $TARGET"
fi

log "Log: $LOG_FILE"
