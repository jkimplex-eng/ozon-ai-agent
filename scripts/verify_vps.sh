#!/usr/bin/env bash
set -euo pipefail

# VPS Verify Script for ozon-ai-agent
# Usage: bash scripts/verify_vps.sh [target]

TARGET="${1:-vps}"
DEPLOY_DIR="/root/ozon-ai-agent"
VENV="/root/ozon-ai-agent/.venv/bin/activate"
EXIT_CODE=0

check() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  OK $name"
    else
        echo "  FAIL $name"
        EXIT_CODE=1
    fi
}

warn() { echo "  WARNING $1"; }

echo "=== OZON AI AGENT VPS VERIFICATION ==="
echo "Target: $TARGET"
echo ""

echo "1. Git Revision"
REMOTE_REV=$(ssh "$TARGET" "cd $DEPLOY_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "UNKNOWN")
LOCAL_REV=$(git rev-parse --short HEAD 2>/dev/null || echo "LOCAL-ONLY")
echo "  Remote: $REMOTE_REV"
echo "  Local:  $LOCAL_REV"
if [ "$REMOTE_REV" = "$LOCAL_REV" ]; then
    echo "  OK Revisions match"
else
    echo "  FAIL Revision mismatch"
    EXIT_CODE=1
fi
echo ""

echo "2. Python Environment"
check "Python version" ssh "$TARGET" "source $VENV && python3 --version"
check "ozon_agent importable" ssh "$TARGET" "source $VENV && python -c 'import ozon_agent'"
check "CLI available" ssh "$TARGET" "source $VENV && python -m ozon_agent.cli --help"
echo ""

echo "3. Dependencies"
check "gspread" ssh "$TARGET" "source $VENV && python -c 'import gspread'"
check "gspread_formatting" ssh "$TARGET" "source $VENV && python -c 'import gspread_formatting'"
check "APScheduler" ssh "$TARGET" "source $VENV && python -c 'import apscheduler'"
check "pandas" ssh "$TARGET" "source $VENV && python -c 'import pandas'"
check "psycopg" ssh "$TARGET" "source $VENV && python -c 'import psycopg'"
echo ""

echo "4. Environment & Secrets"
check ".env exists" ssh "$TARGET" "test -f $DEPLOY_DIR/.env"
check "secrets/google-service-account.json" ssh "$TARGET" "test -f $DEPLOY_DIR/secrets/google-service-account.json"
check "GOOGLE_SHEETS_SPREADSHEET_ID" ssh "$TARGET" "test -n \"\${GOOGLE_SHEETS_SPREADSHEET_ID:-}\""
check "DATABASE_URL" ssh "$TARGET" "test -n \"\${DATABASE_URL:-}\""
check "data/ directory" ssh "$TARGET" "test -d $DEPLOY_DIR/data"
echo ""

echo "5. CLI Commands"
check "sheets --help" ssh "$TARGET" "source $VENV && python -m ozon_agent.cli sheets --help"
check "recommendations --help" ssh "$TARGET" "source $VENV && python -m ozon_agent.cli recommendations --help"
check "ingest ozon datasets" ssh "$TARGET" "source $VENV && python -m ozon_agent.cli ingest ozon datasets --help"
echo ""

echo "6. Google Sheets Sync"
ssh "$TARGET" "cd $DEPLOY_DIR && source $VENV && SHEETS_DATA_SOURCE=files python -m ozon_agent.cli sheets sync --source files --delay 10 2>&1 | tail -12"
echo ""

echo "7. Supervisor"
if ssh "$TARGET" "command -v supervisorctl >/dev/null 2>&1"; then
    check "supervisorctl status" ssh "$TARGET" "supervisorctl status"
else
    warn "Supervisor not installed"
fi
echo ""

echo "=== RESULT ==="
if [ $EXIT_CODE -eq 0 ]; then
    echo "All checks passed."
else
    echo "Some checks failed."
fi
exit $EXIT_CODE
