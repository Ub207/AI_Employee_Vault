#!/bin/bash
# ============================================================
# Vault Git Sync Script — Platinum Tier
# Runs on Cloud VM, syncs markdown/state files every 60s.
# Secrets (*.env, Secrets/, sessions) are NEVER committed.
# ============================================================

VAULT="${VAULT_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
SYNC_INTERVAL="${SYNC_INTERVAL:-60}"
AGENT="${AGENT_ROLE:-cloud}"
REMOTE="${GIT_REMOTE:-origin}"
BRANCH="${GIT_BRANCH:-main}"

cd "$VAULT" || exit 1

git config user.email "${AGENT}@ai-employee.local" 2>/dev/null
git config user.name "${AGENT^} AI Agent" 2>/dev/null

log() { echo "[$(date '+%H:%M:%S')] [$AGENT Sync] $*"; }

log "Starting vault sync loop (interval=${SYNC_INTERVAL}s, branch=${BRANCH})"

while true; do
    # ── Pull latest ──────────────────────────────────────────
    git pull --rebase "$REMOTE" "$BRANCH" 2>&1 | tail -2

    # ── Stage safe files only ────────────────────────────────
    # Use explicit patterns to avoid accidentally staging secrets
    git add -- \
        "Needs_Action" \
        "Tasks" \
        "Pending_Approval" \
        "Approved" \
        "Rejected" \
        "Done" \
        "Logs" \
        "In_Progress" \
        "Updates" \
        "Plans" \
        "Channels" \
        "config.yaml" \
        "SKILL.md" \
        "Business_Goals.md" \
        "Dashboard.md" \
        "Weekly_Audit.md" \
        "CEO_Briefing.md" \
        2>/dev/null

    # ── Commit if changed ────────────────────────────────────
    if ! git diff --cached --quiet; then
        CHANGED=$(git diff --cached --name-only | wc -l)
        git commit -m "${AGENT}: sync ${CHANGED} file(s) at $(date -Iseconds)" 2>&1

        git push "$REMOTE" "$BRANCH" 2>&1 | tail -2
        log "Pushed $CHANGED changed file(s) to $REMOTE/$BRANCH"
    fi

    sleep "$SYNC_INTERVAL"
done
