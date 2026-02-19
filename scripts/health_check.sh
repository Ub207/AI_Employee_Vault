#!/bin/bash
# ============================================================
# Health Check Script — Platinum Tier
# Run daily via cron to verify all services are operational.
# ============================================================

VAULT="${VAULT_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ODOO_URL="${ODOO_URL:-http://localhost:8069}"
LOG_FILE="$VAULT/Logs/$(date +%Y-%m-%d)_health.md"

pass() { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; FAILURES=$((FAILURES+1)); }
FAILURES=0

echo "# Health Check — $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "## System"

# Disk space
DISK_PCT=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
if [ "$DISK_PCT" -lt 80 ]; then
    pass "Disk usage: ${DISK_PCT}%"
else
    fail "Disk usage: ${DISK_PCT}% (> 80% threshold)"
fi

# Memory
FREE_MB=$(free -m | awk 'NR==2 {print $4}')
if [ "$FREE_MB" -gt 512 ]; then
    pass "Free memory: ${FREE_MB}MB"
else
    fail "Low memory: ${FREE_MB}MB free"
fi

echo ""
echo "## Processes (PM2)"
if command -v pm2 &>/dev/null; then
    for proc in backend-api gmail-watcher social-watcher facebook-watcher twitter-watcher vault-sync; do
        STATUS=$(pm2 jlist 2>/dev/null | python3 -c "
import json,sys
procs=json.load(sys.stdin)
p=[x for x in procs if x.get('name')=='$proc']
print(p[0]['pm2_env']['status'] if p else 'not_found')
" 2>/dev/null)
        if [ "$STATUS" = "online" ]; then
            pass "PM2 $proc: online"
        else
            fail "PM2 $proc: $STATUS"
        fi
    done
fi

echo ""
echo "## APIs"

# Backend health
if curl -sf "${BACKEND_URL}/health" -o /dev/null 2>/dev/null; then
    pass "Backend API: ${BACKEND_URL}/health OK"
else
    fail "Backend API: ${BACKEND_URL}/health UNREACHABLE"
fi

# Odoo health
if curl -sf "${ODOO_URL}/web/database/selector" -o /dev/null 2>/dev/null; then
    pass "Odoo: ${ODOO_URL} reachable"
else
    fail "Odoo: ${ODOO_URL} UNREACHABLE"
fi

# Odoo MCP
if curl -sf "http://localhost:8010/health" -o /dev/null 2>/dev/null; then
    pass "Odoo MCP: http://localhost:8010 OK"
else
    fail "Odoo MCP: http://localhost:8010 UNREACHABLE"
fi

echo ""
echo "## Vault Sync"
cd "$VAULT" || exit 1
LAST_COMMIT=$(git log -1 --format="%ar" 2>/dev/null)
PENDING=$(git status --porcelain 2>/dev/null | wc -l)
pass "Last commit: $LAST_COMMIT"
if [ "$PENDING" -gt 0 ]; then
    fail "Uncommitted changes: $PENDING files (sync may be stuck)"
else
    pass "Vault synced (no pending changes)"
fi

echo ""
echo "## Summary"
if [ "$FAILURES" -eq 0 ]; then
    echo "**All checks passed** ✅"
else
    echo "**$FAILURES check(s) FAILED** ❌ — review above"
fi

# Append to daily log
{
    echo ""
    echo "## $(date '+%H:%M') - Health Check"
    echo "- Failures: $FAILURES"
    echo "- Disk: ${DISK_PCT}%"
    echo "- Memory: ${FREE_MB}MB free"
} >> "$LOG_FILE"

exit $FAILURES
