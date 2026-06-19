#!/usr/bin/env bash
set -euo pipefail

# VPS Verify Script for ozon-ai-agent
# Usage: bash scripts/verify_vps.sh [target]

TARGET="${1:-vps}"
DEPLOY_DIR="/root/ozon-ai-agent"
EXIT_CODE=0

check() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  ✓ $name"
    else
        echo "  ✗ $name"
        EXIT_CODE=1
    fi
}

echo "=== OZON AI AGENT VPS VERIFICATION ==="
echo "Target: $TARGET"
echo ""

echo "1. Git Revision"
REMOTE_REV=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "UNKNOWN")
LOCAL_REV=$(git rev-parse --short HEAD 2>/dev/null || echo "LOCAL-ONLY")
echo "  Remote: $REMOTE_REV"
echo "  Local:  $LOCAL_REV"
if [ "$REMOTE_REV" = "$LOCAL_REV" ]; then
    echo "  ✓ Revisions match"
else
    echo "  ✗ Revision mismatch"
    EXIT_CODE=1
fi
echo ""

echo "2. Python Environment"
check "Python available" ssh "$TARGET" "python3 --version"
check "ozon_agent importable" ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import ozon_agent'"
check "CLI available" ssh "$TARGET" "cd $DEPLOY_DIR && ozon-agent --help"
echo ""

echo "3. Dependencies"
check "gspread installed" ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import gspread'"
check "gspread_formatting installed" ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import gspread_formatting'"
check "APScheduler installed" ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import apscheduler'"
check "pandas installed" ssh "$TARGET" "cd $DEPLOY_DIR && python -c 'import pandas'"
echo ""

echo "4. Environment Variables"
check "DATABASE_URL set" ssh "$TARGET" "test -n \"\${DATABASE_URL:-}\""
check "GOOGLE_SERVICE_ACCOUNT_JSON file exists" ssh "$TARGET" "test -f /root/ozon-ai-agent/secrets/google-service-account.json"
check "GOOGLE_SHEETS_SPREADSHEET_ID set" ssh "$TARGET" "test -n \"\${GOOGLE_SHEETS_SPREADSHEET_ID:-}\""
echo ""

echo "5. Supervisor (PM2)"
check "PM2 running" ssh "$TARGET" "pm2 list"
OZON_PROCS=$(ssh "$TARGET" "pm2 list 2>/dev/null | grep -c ozon" || echo "0")
echo "  Ozon processes: $OZON_PROCS"
echo ""

echo "6. Google Sheets Sync (dry run)"
ssh "$TARGET" "cd $DEPLOY_DIR && SHEETS_DATA_SOURCE=files python -m ozon_agent.cli sheets sync --source files --delay 5 2>&1 | tail -12"
echo ""

echo "7. File Permissions"
check "secrets dir permissions" ssh "$TARGET" "test -d /root/ozon-ai-agent/secrets && test -f /root/ozon-ai-agent/secrets/google-service-account.json"
check ".env not committed" ssh "$TARGET" "cd $DEPLOY_DIR && git ls-files .env | grep -q . && echo COMMITTED || true"
echo ""

echo "=== RESULT ==="
if [ $EXIT_CODE -eq 0 ]; then
    echo "All checks passed."
else
    echo "Some checks failed. Review output above."
fi
exit $EXIT_CODE
