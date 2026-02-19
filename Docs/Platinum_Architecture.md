# Platinum Tier Architecture — Always-On Cloud + Local Executive

## Overview

The Platinum tier splits the AI Employee into two specialized agents communicating via a synced vault (Git or Syncthing). This enables 24/7 uptime even when your local machine is off.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PLATINUM TIER ARCHITECTURE                   │
│              "Always-On Cloud + Local Executive"                │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐    Git Sync    ┌──────────────────────────────┐
│         CLOUD AGENT          │◄──────────────►│         LOCAL AGENT           │
│   (Oracle Cloud / AWS VM)    │                │    (Your Laptop / Mini-PC)    │
│                              │                │                               │
│  Owns:                       │                │  Owns:                        │
│  ✅ Email triage             │                │  ✅ Approval decisions        │
│  ✅ Draft email replies      │                │  ✅ WhatsApp session          │
│  ✅ Social post drafts       │                │  ✅ Payments & banking        │
│  ✅ LinkedIn scheduling      │                │  ✅ Final send / post         │
│  ✅ Odoo accounting (draft)  │                │  ✅ Dashboard.md (sole writer)│
│  ❌ Never sends email        │                │  ✅ Approve/reject actions    │
│  ❌ Never posts live         │                │  ✅ Odoo: post invoices       │
│  ❌ Never holds secrets      │                │                               │
└──────────────────────────────┘                └──────────────────────────────┘
                │                                              │
                └──────────────────┬───────────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │   SHARED VAULT       │
                        │  (Git / Syncthing)   │
                        │                      │
                        │  /Needs_Action/      │
                        │  /Tasks/             │
                        │  /Pending_Approval/  │
                        │  /Approved/          │
                        │  /Done/              │
                        │  /Logs/              │
                        │  /In_Progress/<agent>│
                        │  /Updates/           │
                        │  /Plans/<domain>/    │
                        └──────────────────────┘
```

---

## Work-Zone Specialization

### Cloud Agent Responsibilities
| Capability | Action |
|-----------|--------|
| Email triage | Read Gmail, classify priority, create task in `/Needs_Action/` |
| Draft replies | Write reply drafts to `/Pending_Approval/` for Local approval |
| Social post drafts | Create LinkedIn/Facebook/Twitter post drafts in `/Pending_Approval/` |
| Accounting | Create draft invoices in Odoo (HITL—never posts) |
| Monitoring | 24/7 watcher uptime even when Local is offline |
| Reports | Generate CEO Briefing drafts in `/Updates/` |

### Local Agent Responsibilities
| Capability | Action |
|-----------|--------|
| Approvals | Monitor `/Pending_Approval/`, move to `/Approved/` or `/Rejected/` |
| Email send | Execute approved email sends via Gmail MCP |
| Social post | Execute approved social posts via platform MCPs |
| WhatsApp | Full WhatsApp Web session (never synced to cloud) |
| Payments | Banking portal interactions via Playwright |
| Dashboard | Sole writer of `Dashboard.md` (single-writer rule) |
| Odoo posting | Post approved invoices after reviewing cloud-created drafts |

---

## Claim-by-Move Rule (Preventing Double-Work)

Both agents watch `/Needs_Action/`. To prevent both from processing the same task:

1. First agent to atomically move a file from `/Needs_Action/` to `/In_Progress/<agent>/` owns it
2. Other agent **must skip** any file already in `/In_Progress/`
3. On completion → move from `/In_Progress/<agent>/` to `/Done/`

```
/Needs_Action/task.md         ← available
/In_Progress/cloud/task.md    ← cloud claimed it
/In_Progress/local/task.md    ← local claimed it (different task)
/Done/task.md                 ← completed
```

---

## Vault Sync Strategy (Git — Phase 1)

### What Syncs (Markdown/State Only)
```
/Needs_Action/*.md
/Tasks/*.md
/Pending_Approval/*.md
/Approved/*.md
/Rejected/*.md
/Done/*.md
/Logs/*.md
/In_Progress/**/*.md
/Updates/*.md
/Plans/**/*.md
config.yaml
SKILL.md
```

### What NEVER Syncs (Secrets Stay Local)
```
.env files
Secrets/
backend/vault.db
WhatsApp session files
Banking credentials
API tokens
```

### Git Sync Workflow
```bash
# Cloud agent sync loop (every 60 seconds)
while true; do
    git pull --rebase origin main
    # ... process tasks ...
    git add -A -- '*.md' config.yaml
    git commit -m "cloud: processed tasks $(date -Iseconds)"
    git push origin main
    sleep 60
done

# Local agent sync on wakeup
git pull --rebase origin main
# ... approve/execute ...
git add -A -- '*.md' config.yaml
git commit -m "local: approved actions $(date -Iseconds)"
git push origin main
```

### Conflict Resolution
- `Dashboard.md` → **Local always wins** (single-writer rule); Cloud writes updates to `/Updates/dashboard_delta.md`, Local merges
- Task files → last-writer-wins (Git merge)
- If conflict in `/In_Progress/` → both agents abort and log the conflict

---

## Platinum Demo Gate (Minimum Passing)

**Scenario:** Email arrives while Local is offline

```
1. Gmail arrives at Cloud Agent
   └─ Cloud creates: /Needs_Action/EMAIL_client_X.md

2. Cloud claims task
   └─ Moves to: /In_Progress/cloud/EMAIL_client_X.md

3. Cloud drafts reply
   └─ Creates: /Pending_Approval/REPLY_client_X.md
   └─ Cloud can NOT send — it writes and waits

4. Git push → Vault synced

5. Local comes online → git pull
   └─ Sees /Pending_Approval/REPLY_client_X.md
   └─ User reviews draft in Obsidian
   └─ Moves to /Approved/REPLY_client_X.md

6. Local Agent detects /Approved/ file
   └─ Calls Gmail MCP → sends email
   └─ Logs to /Logs/
   └─ Moves task to /Done/
   └─ Updates Dashboard.md
   └─ git push → Cloud sees completion
```

---

## Security Rules

| Rule | Enforcement |
|------|-------------|
| Secrets never sync | `.gitignore` covers all `.env`, `Secrets/`, session files |
| Cloud never holds WhatsApp session | WhatsApp runs only on Local |
| Cloud never holds banking creds | Banking MCP runs only on Local |
| Cloud never posts live | All posts require Local approval move |
| Dashboard single-writer | Only Local writes `Dashboard.md` directly |
| Audit trail | All actions logged in `/Logs/` (synced) |

---

## Optional Phase 2: A2A (Agent-to-Agent) Upgrade

Replace file-based handoffs with direct Agent-to-Agent messages while keeping the vault as the audit record:

```python
# Cloud agent sends A2A message to Local agent
await a2a_client.send_task(
    agent_url="http://local-agent:8020",
    task={
        "type": "approval_request",
        "file": "REPLY_client_X.md",
        "action": "send_email",
        "draft": "..."
    }
)
# Local agent responds, Cloud logs to vault
```

This is optional — the file-based vault approach (Phase 1) is reliable and simpler to debug.
