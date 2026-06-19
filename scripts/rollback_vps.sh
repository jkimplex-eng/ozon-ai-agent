#!/usr/bin/env bash
set -euo pipefail

# VPS Rollback Script for ozon-ai-agent
# Usage: bash scripts/rollback_vps.sh [target] [commits_back]

TARGET="${1:-vps}"
COMMITS_BACK="${2:-1}"
DEPLOY_DIR="/root/ozon-ai-agent"
VENV="/root/ozon-ai-agent/.venv/bin/activate"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== OZON AI AGENT ROLLBACK ==="
log "Target: $TARGET"
log "Commits back: $COMMITS_BACK"
log ""

# Step 1: Current revision
log "Step 1: Current revision..."
CURRENT=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")
log "  Current: $CURRENT"

# Step 2: Revert
log "Step 2: Reverting $COMMITS_BACK commit(s)..."
ssh "$TARGET" "cd $DEPLOY_DIR && git reset --hard HEAD~$COMMITS_BACK" || {
    log "FAIL: git reset failed"
    exit 1
}
NEW_REV=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")
log "  Reverted to: $NEW_REV"

# Step 3: Reinstall
log "Step 3: Reinstalling dependencies..."
ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && pip install -e . 2>&1 | tail -3" || {
    log "FAIL: pip install failed"
    exit 1
}
log "  Dependencies installed."

# Step 4: Verify
log "Step 4: Verifying..."
ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && python -c 'import ozon_agent; print(\"OK:\", ozon_agent.__version__)'" \
    && log "  Import: OK ✓" \
    || log "  WARNING: Import check failed"

ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && ozon-agent --help >/dev/null 2>&1" \
    && log "  CLI: OK ✓" \
    || log "  WARNING: CLI check failed"

# Step 5: Supervisor
log "Step 5: Supervisor..."
if ssh "$TARGET" "command -v supervisorctl >/dev/null 2>&1"; then
    ssh "$TARGET" "mkdir -p $DEPLOY_DIR/logs"
    ssh "$TARGET" "cp $DEPLOY_DIR/deploy/supervisor/*.conf /etc/supervisor/conf.d/"
    ssh "$TARGET" "supervisorctl reread"
    ssh "$TARGET" "supervisorctl update"
    ssh "$TARGET" "supervisorctl restart ozon-sheets-watch 2>/dev/null || supervisorctl start ozon-sheets-watch"
    ssh "$TARGET" "supervisorctl status ozon-sheets-watch"
    log "  Supervisor: ozon-sheets-watch restarted."
else
    log "  WARNING: Supervisor not installed."
fi

log ""
log "=== ROLLBACK COMPLETE ==="
log "Rolled back from $CURRENT to $NEW_REV"
