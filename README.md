[![Hakathone-0](https://img.shields.io/badge/Hakathone--0-Digital%20FTE-black?style=for-the-badge)](https://github.com/Ub207/AI_Employee_Vault)
[![Tier](https://img.shields.io/badge/Tier-Platinum-E5E4E2?style=for-the-badge&logo=github)](https://github.com/Ub207/AI_Employee_Vault)
[![Engine](https://img.shields.io/badge/Engine-Config%20Driven-blue?style=for-the-badge)](https://github.com/Ub207/AI_Employee_Vault/blob/main/config.yaml)
[![Governance](https://img.shields.io/badge/Governance-Active-green?style=for-the-badge)](https://github.com/Ub207/AI_Employee_Vault/blob/main/Company_Handbook.md)
[![Platforms](https://img.shields.io/badge/Platforms-7%20Integrated-blueviolet?style=for-the-badge)](https://github.com/Ub207/AI_Employee_Vault/blob/main/README.md#integration-map-all-tiers)
[![Cloud](https://img.shields.io/badge/Cloud-Always--On-orange?style=for-the-badge)](https://github.com/Ub207/AI_Employee_Vault/blob/main/Docs/Cloud_Deployment.md)


<div align="center">

# AI Employee Vault

### Digital FTE (Full-Time Equivalent) — Hakathone-0

A markdown-based autonomous AI employee system built on Obsidian.

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Ub207/AI_Employee_Vault/blob/main/LICENSE)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai)
[![Obsidian](https://img.shields.io/badge/Platform-Obsidian-7C3AED)](https://obsidian.md)
[![Markdown](https://img.shields.io/badge/Format-Markdown-000000)](https://commonmark.org)
[![Tier](https://img.shields.io/badge/Tier-Platinum-E5E4E2)](https://github.com/Ub207/AI_Employee_Vault)
[![Tasks Completed](https://img.shields.io/badge/Tasks%20Completed-12-brightgreen)](https://github.com/Ub207/AI_Employee_Vault/tree/main/Done)
[![Approval Pipeline](https://img.shields.io/badge/Approval%20Pipeline-Active-orange)](https://github.com/Ub207/AI_Employee_Vault/blob/main/Docs/Approval_Workflow.md)
[![SLA Tracking](https://img.shields.io/badge/SLA%20Tracking-Enabled-blue)](https://github.com/Ub207/AI_Employee_Vault/blob/main/Docs/SLA_and_Priority_Model.md)

---

**Drop a task. AI prioritizes it. Sensitive? It asks first. Then executes within SLA, logs, and reports.**

[Getting Started](#getting-started) · [How It Works](#how-it-works) · [Integration Map](#integration-map-all-tiers) · [Demo](#demo-workflow) · [Docs](https://github.com/Ub207/AI_Employee_Vault/tree/main/Docs)

</div>

---

## What is a Digital FTE?

A **Digital Full-Time Equivalent** is an AI agent that operates like a real employee:

- Has a **workspace** (this Obsidian vault)
- Follows a **Company Handbook** with rules and autonomy levels
- Picks up tasks from an **inbox** (`/Needs_Action`)
- **Classifies priority** (P0-P3) and tracks **SLA deadlines**
- **Plans before acting** and **asks for approval** on sensitive items
- **Logs everything** it does for full auditability
- **Schedules recurring tasks** automatically via cron
- Moves completed work to `/Done`

> Think of it as an AI coworker with its own desk, rules, priority queue, and a manager to report to.

---

## Silver Tier Features

| Feature | Description |
|---------|-------------|
| **Config-Driven** | All settings in `config.yaml` — no hardcoded values |
| **Priority Queue** | P0-P3 classification with automatic keyword detection |
| **SLA Tracking** | Deadline stamps, compliance metrics, reminders, escalations |
| **Smart Sensitivity** | Weighted keyword scoring with context modifiers |
| **Scheduler** | Cron-based recurring tasks (weekly reports, daily standups) |
| **Approval Monitor** | Automatic reminders and escalation for pending approvals |
| **Enhanced Dashboard** | Priority distribution, SLA performance, overdue tracking |
| **Autonomy Levels** | LOW/MEDIUM/HIGH configurable behavior |

---

## Architecture

```
    ┌──────────────┐     ┌──────────────┐
    │  config.yaml │     │  scheduler   │
    │  (settings)  │     │  (cron jobs) │
    └──────┬───────┘     └──────┬───────┘
           │                    │
           ▼                    ▼
    ┌─────────────────────────────────────┐
    │         /Needs_Action               │  ◄── You drop tasks here
    │    (sorted by priority queue)       │      (or scheduler creates them)
    └────────────────┬────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────────┐
    │  AI reads task + scores sensitivity │
    │  Priority: P0-P3 | SLA deadline    │
    └────────────────┬────────────────────┘
                     │
            ┌────────┴────────┐
            │                 │
      ┌─────▼─────┐   ┌──────▼──────┐
      │  ROUTINE   │   │  SENSITIVE   │
      │  Auto-run  │   │  Needs OK    │
      └─────┬─────┘   └──────┬──────┘
            │                │
            │         ┌──────▼──────┐
            │         │  /Pending    │
            │         │  _Approval   │ ◄── Reminders + escalation
            │         └──────┬──────┘
            │                │
            │         ┌──────▼──────┐
            │         │  Manager     │
            │         │  Approves    │
            │         └──────┬──────┘
            │                │
            └───────┬────────┘
                    │
           ┌────────▼────────┐
           │   AI Executes    │
           │  (tracks SLA)    │
           └────────┬────────┘
                    │
      ┌─────────────┼─────────────┐
      │             │             │
┌─────▼──────┐ ┌───▼───┐ ┌───────▼───────┐
│   /Done     │ │ /Logs │ │  /Dashboard   │
│  (archive + │ │(audit)│ │  (SLA stats + │
│   SLA meta) │ │       │ │   priority)   │
└────────────┘ └───────┘ └───────────────┘
```

---

## Vault Structure

```
AI_Employee_Vault/
├── Needs_Action/          # Inbox — drop tasks here
├── Tasks/                 # Active plans and work-in-progress
├── Pending_Approval/      # Tasks waiting for manager sign-off
├── Approved/              # Tasks approved and ready to execute
├── Rejected/              # Tasks that were declined
├── Done/                  # Completed tasks (archived)
├── Logs/                  # Daily action logs — full audit trail
├── Notes/                 # Reference material and research
├── Channels/              # External communication inboxes
│   ├── Gmail_Inbox/       #   Email events (JSON)
│   ├── Social_Inbox/      #   Social media events (JSON)
│   └── WhatsApp_Inbox/    #   WhatsApp events (JSON)
├── config.yaml            # CENTRAL CONFIG — all system settings
├── config_loader.py       # Shared config utility module
├── sensitivity_scorer.py  # Weighted sensitivity scoring engine
├── scheduler.py           # Cron-based recurring task scheduler
├── scheduler_state.json   # Scheduler last-run timestamps
├── Company_Handbook.md    # Rules, policies, and autonomy levels
├── Business_Goals.md      # Company mission, goals, and SLA targets
├── SKILL.md               # AI Employee operating manual (Silver)
├── Dashboard.md           # Live status: SLA, priority, queues
├── CEO_Briefing.md        # Weekly executive summary with SLA data
├── Weekly_Audit.md        # Weekly audit with priority breakdown
├── watcher.py             # File watcher with priority queue + scheduler
├── local_reasoner.py      # Fallback processor with smart scoring
├── update_dashboard.py    # Dashboard generator with SLA sections
├── weekly_audit.py        # Audit generator with SLA compliance
└── README.md              # You are here
```

| Folder / File | Purpose |
|----------------|---------|
| `/Needs_Action` | Inbox — drop tasks here for the AI to pick up |
| `/Tasks` | Active plans and work-in-progress |
| `/Pending_Approval` | Tasks awaiting manager sign-off (with reminders) |
| `/Approved` | Approved tasks (audit record) |
| `/Rejected` | Declined tasks with feedback |
| `/Done` | Completed tasks with SLA metadata |
| `/Logs` | Daily action logs — full audit trail |
| `config.yaml` | Central config — priority, SLA, sensitivity, scheduler |
| `config_loader.py` | Shared utility for reading config + logging |
| `sensitivity_scorer.py` | Weighted keyword scoring with context awareness |
| `scheduler.py` | Cron-based recurring task creation |

---

## Documentation

Full system documentation lives in `/Docs/`:

| Document | Description |
|----------|-------------|
| [System Capability Contract](Docs/System_Capability_Contract.md) | What the system can do, cannot do, and future upgrade paths |
| [Architecture](Docs/Architecture.md) | Component inventory, data flow, technology stack, resilience model |
| [Governance Model](Docs/Governance_Model.md) | Autonomy levels, sensitivity classification, enforcement points, risk mitigation |
| [SLA and Priority Model](Docs/SLA_and_Priority_Model.md) | P0-P3 priority levels, SLA deadlines, compliance tracking, limitations |
| [Approval Workflow](Docs/Approval_Workflow.md) | Sensitivity scoring engine, approval routing logic, worked examples |
| [Observability and Audit](Docs/Observability_and_Audit.md) | Logging pipeline, dashboard, weekly audit, CEO briefing, gap analysis |
| [Upgrade Roadmap](Docs/Upgrade_Roadmap.md) | Bronze → Silver → Gold tier progression, phased upgrade plan |

---

## How It Works

### Task Lifecycle

```
1. Drop a task into /Needs_Action (or scheduler creates one)
2. AI classifies priority (P0-P3) and stamps SLA deadline
3. AI scores sensitivity with weighted keywords
4. AI creates a plan in /Tasks
5. If sensitive → approval request in /Pending_Approval (reminders/escalation)
6. If routine → AI executes immediately
7. Completed task moves to /Done with full SLA metadata
8. Action logged in /Logs with priority info
9. Dashboard updated with SLA performance
```

### Priority System

| Priority | Label | SLA Window | Auto-Detect Keywords |
|----------|-------|------------|---------------------|
| **P0** | Critical | 1 hour | "urgent", "critical" |
| **P1** | High | 4 hours | "asap", "deadline" |
| **P2** | Medium | 24 hours | (default) |
| **P3** | Low | 72 hours | — |

### Sensitivity Detection

Smart weighted scoring replaces simple keyword matching:

| Keyword | Weight | Category |
|---------|--------|----------|
| password | 1.0 | access_change |
| payment | 0.9 | financial |
| delete | 0.9 | data_deletion |
| invoice | 0.8 | financial |
| email | 0.6 | external_communication |
| client | 0.5 | external_communication |

Context modifiers adjust scores: "email" + "client" = higher score, "email" + "internal" = lower score. Threshold configurable in `config.yaml` (default: 0.6).

### Autonomy Levels

| Level | Routine Tasks | Sensitive Tasks |
|-------|--------------|-----------------|
| **LOW** | Ask for approval | Ask for approval |
| **MEDIUM** | Auto-execute | Ask for approval (current) |
| **HIGH** | Auto-execute | Auto-execute (log warning) |

---

## Demo Workflow

This vault ships with **8 completed tasks** showing both workflow paths:

### Task 1: Client Invoice (Sensitive Path)
| Step | Action |
|------|--------|
| Detected | `test_task.md` — "Client asked for invoice" |
| Priority | P2 (default) — SLA: 24 hours |
| Sensitivity | Score: 0.8 — Category: financial |
| Result | Blocked → Approval requested → Approved → Completed |

### Task 2: Weekly Report (Routine Path)
| Step | Action |
|------|--------|
| Detected | `weekly_report.md` — "Prepare weekly progress report" |
| Priority | P2 (default) — SLA: 24 hours |
| Sensitivity | Score: 0.0 — No signals |
| Result | Auto-processed → Completed within SLA |

### Task 3: Urgent Client Email (Priority + Sensitive)
| Step | Action |
|------|--------|
| Detected | `client_email.md` — "Send follow-up email to client ASAP" |
| Priority | P1 (auto-detected: "ASAP") — SLA: 4 hours |
| Sensitivity | Score: 1.1 — Category: external_communication |
| Result | Blocked → Draft prepared → Approval requested → Completed |

### Final Stats

| Metric | Value |
|--------|-------|
| Total tasks processed | 8 |
| Sensitive actions flagged | 3 |
| Approvals requested | 3 |
| Approvals granted | 2 |
| Completion rate | 100% |

---

## Screenshots

> Open this vault in Obsidian to see the full experience.

| View | Description |
|------|-------------|
| **Dashboard** | `Dashboard.md` — SLA performance, priority distribution, overdue tracking, queue stats |
| **Task Detection** | AI reads inbox, scores sensitivity, classifies priority, stamps SLA |
| **Approval Pipeline** | Sensitive tasks blocked with reminders and escalation tracking |
| **Audit Log** | Every action timestamped with priority and SLA info |
| **Completed Tasks** | Archived tasks with full SLA metadata |

> **Add screenshots:** Place images in `screenshots/` and reference them here:
> `![Dashboard](screenshots/dashboard.png)` etc.

---

## Getting Started

### Prerequisites
- [Obsidian](https://obsidian.md) (free)
- [Claude Code](https://claude.ai) (AI agent)
- Python 3.10+ with `pyyaml`, `croniter`, `watchdog`

### Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Ub207/AI_Employee_Vault.git
   ```

2. **Install dependencies**
   ```bash
   pip install pyyaml croniter watchdog
   ```

3. **Open in Obsidian**
   - Open Obsidian → "Open folder as vault" → select `AI_Employee_Vault`

4. **Configure (optional)**
   - Edit `config.yaml` to adjust autonomy level, SLA windows, sensitivity thresholds

5. **Drop a task**
   - Create a markdown file in `/Needs_Action` with your task description
   - Optional: add `priority: P0` in frontmatter for critical tasks

6. **Run the AI Employee**
   - Start the watcher: `python watcher.py`
   - Or run directly: tell Claude Code *"Process everything in /Needs_Action"*

7. **Watch it work**
   - Check `/Tasks` for plans
   - Check `/Pending_Approval` if sensitive
   - Check `/Done` when complete
   - Check `/Logs` for the audit trail
   - Check `Dashboard.md` for SLA stats

---

## Tech Stack

| Tool | Role |
|------|------|
| **Obsidian** | Vault / workspace (markdown-native knowledge base) |
| **Claude Code** | AI agent (reads, plans, executes, logs) |
| **Git + GitHub** | Version control and collaboration |
| **Markdown + YAML** | Universal format for tasks and configuration |
| **Python** | Watcher, scheduler, sensitivity scorer, dashboard |
| **croniter** | Cron expression parsing for scheduled tasks |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-task-type`)
3. Commit your changes
4. Push and open a PR

---

## License

This project is open source under the [MIT License](LICENSE).

---

<div align="center">

**Built with Claude Code** · Hakathone-0 · Silver Tier · Digital FTE

*An AI that works like an employee — prioritizes, plans, asks, executes, tracks SLA, and reports.*

</div> 

---

# Hakathone-0 Tier Certification

**Project:** Digital FTE (AI Employee Vault)
**Owner:** Ub207
**Current Tier:** Platinum (Always-On Cloud + Local Executive)
**Certification Date:** 2026-02-19

---

## Bronze Tier — COMPLETE

- File-based task intake (`/Needs_Action`)
- Structured task planning (`/Tasks`)
- Approval workflow (`/Pending_Approval`)
- Completed lifecycle tracking (`/Done`)
- Daily logging system (`/Logs`)
- Config-driven behavior (`config.yaml`)
- Dashboard metrics, SLA tracking, priority queue (P0-P3)
- Sensitivity detection, weekly audit, CEO briefing
- System Capability Contract
- All functionality implemented as Agent Skills (`SKILL.md`)

Status: **100% Complete**

---

## Silver Tier — COMPLETE

- Two+ watcher scripts: Gmail, WhatsApp, LinkedIn (Social)
- LinkedIn auto-posting for business sales generation
- Claude reasoning loop creating `Plan.md` files
- MCP server for external actions (`business-mcp/`)
- Human-in-the-loop approval workflow
- Cron-based scheduler for recurring tasks
- Config-driven autonomy levels (LOW/MEDIUM/HIGH)
- Audit-grade traceability and SLA compliance

Status: **100% Complete**

---

## Gold Tier — COMPLETE

- Full cross-domain integration (Personal + Business)
- Facebook & Instagram integration: watcher, service, API routes, posting, summaries
- Twitter/X integration: watcher, service, OAuth2 PKCE, posting, engagement summaries
- Odoo Community MCP server: draft invoices, partner management, accounting summary
- Human-in-the-Loop for all Odoo financial actions
- Multiple MCP servers: business-mcp (email/LinkedIn), odoo-mcp (accounting)
- Weekly Business Audit + CEO Briefing (with cross-domain data)
- Error recovery: retry logic, graceful degradation, fallback local reasoner
- Comprehensive audit logging in `/Logs/`
- Ralph Wiggum stop hook + loop orchestrator for autonomous multi-step tasks
- Architecture documentation in `/Docs/`
- Gold-tier SKILL.md with cross-domain integration map

Status: **100% Complete**

---

## Platinum Tier — COMPLETE

- Platinum architecture documented: Cloud Agent + Local Agent split
- Work-Zone Specialization: Cloud drafts, Local executes
- Delegation via synced vault: `/In_Progress/cloud/` and `/In_Progress/local/` claim-by-move rule
- Single-writer rule: Local owns `Dashboard.md`; Cloud writes to `/Updates/`
- Vault sync script: `scripts/sync_vault.sh` (Git-based, markdown only)
- Security: secrets never sync; `.gitignore` hardened
- Cloud deployment guide: Oracle Cloud Free VM, PM2, Docker Odoo
- Health monitoring script: `scripts/health_check.sh` with PM2 + API checks
- Platinum SKILL.md: `Docs/Platinum_SKILL.md` (Cloud Agent operating manual)
- Odoo Cloud deployment: Docker Compose with PostgreSQL + HTTPS

Status: **100% Complete**

---

## Integration Map (All Tiers)

| Platform | Watch | Post/Act | Summarize | Tier |
|----------|-------|----------|-----------|------|
| File System | `watcher.py` | Claude Code | Dashboard | Bronze |
| Gmail | `gmail_watcher.py` + backend | Gmail MCP | Weekly Audit | Silver/Gold |
| WhatsApp | `whatsapp_watcher.py` + Twilio | Twilio MCP | Weekly Audit | Silver/Gold |
| LinkedIn | `social_watcher.py` + backend | LinkedIn API | `/summary` | Silver/Gold |
| Facebook | `facebook_watcher.py` + backend | Facebook Graph | `/summary` | Gold |
| Instagram | `facebook_watcher.py` + backend | Instagram Graph | `/summary` | Gold |
| Twitter/X | `twitter_watcher.py` + backend | Twitter API v2 | `/summary` | Gold |
| Odoo | Approval watcher | Odoo MCP (HITL) | `accounting_summary` | Gold |
| Cloud VM | PM2 watchers | Git sync | Health monitor | Platinum |

---

**Digital FTE is a fully autonomous Platinum-tier AI Employee with 24/7 cloud uptime, cross-domain integration across 7 platforms, accounting automation, and human-in-the-loop safety on every sensitive action.**

