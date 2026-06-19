#!/usr/bin/env bash
set -euo pipefail

# VPS Rollback Script for ozon-ai-agent
# Usage: bash scripts/rollback_vps.sh [target] [commits_back]

TARGET="${1:-vps}"
COMMITS_BACK="${2:-1}"
DEPLOY_DIR="/root/ozon-ai-agent"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== OZON AI AGENT ROLLBACK ==="
log "Target: $TARGET"
log "Commits back: $COMMITS_BACK"
log ""

# Step 1: Get current revision
log "Step 1: Current revision..."
CURRENT=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")
log "  Current: $CURRENT"

# Step 2: Revert
log "Step 2: Reverting $COMMITS_BACK commit(s)..."
ssh "$TARGET" "cd $DEPLOY_DIR && git checkout HEAD~$COMMITS_BACK" || {
    log "FAIL: git checkout failed"
    exit 1
}
NEW_REV=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")
log "  Reverted to: $NEW_REV"

# Step 3: Reinstall dependencies
log "Step 3: Reinstalling dependencies..."
ssh "$TARGET" "cd $DEPLOY_DIR && pip install -e . 2>&1 | tail -3" || {
    log "FAIL: pip install failed"
    exit 1
}
log "  Dependencies installed."

# Step 4: Restart services
log "Step 4: Restarting services..."
ssh "$TARGET" "pm2 restart ozon-sheets-watch 2>/dev/null || true"
ssh "$TARGET" "pm2 restart ozon-telegram-bot 2>/dev/null || true"
ssh "$TARGET" "pm2 save 2>/dev/null || true"
log "  Services restarted."

# Step 5: Health check
log "Step 5: Health check..."
ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import ozon_agent; print(\"OK:\", ozon_agent.__version__)'" \
    && log "  Import: OK ✓" \
    || log "  WARNING: Import check failed"

ssh "$TARGET" "cd $DEPLOY_DIR && ozon-agent --help >/dev/null 2>&1" \
    && log "  CLI: OK ✓" \
    || log "  WARNING: CLI check failed"

log ""
log "=== ROLLBACK COMPLETE ==="
log "Rolled back from $CURRENT to $NEW_REV"
log "If issues persist, rollback further: bash scripts/rollback_vps.sh $TARGET $((COMMITS_BACK + 1))"
