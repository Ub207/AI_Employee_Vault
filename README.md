<div align="center">

# AI Employee Vault

### Digital FTE (Full-Time Equivalent) — Hakathone-0

A markdown-based autonomous AI employee system built on Obsidian.

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai)
[![Obsidian](https://img.shields.io/badge/Platform-Obsidian-7C3AED)](https://obsidian.md)
[![Markdown](https://img.shields.io/badge/Format-Markdown-000000)](https://commonmark.org)
[![Tasks Completed](https://img.shields.io/badge/Tasks%20Completed-3-brightgreen)]()
[![Approval Pipeline](https://img.shields.io/badge/Approval%20Pipeline-Active-orange)]()

---

**Drop a task. AI plans it. Sensitive? It asks first. Then executes, logs, and reports.**

[Getting Started](#getting-started) · [How It Works](#how-it-works) · [Demo](#demo-workflow) · [Screenshots](#screenshots)

</div>

---

## What is a Digital FTE?

A **Digital Full-Time Equivalent** is an AI agent that operates like a real employee:

- Has a **workspace** (this Obsidian vault)
- Follows a **Company Handbook** with rules and autonomy levels
- Picks up tasks from an **inbox** (`/Needs_Action`)
- **Plans before acting** and **asks for approval** on sensitive items
- **Logs everything** it does for full auditability
- Moves completed work to `/Done`

> Think of it as an AI coworker with its own desk, rules, and a manager to report to.

---

## Architecture

```
                    ┌─────────────────┐
                    │  /Needs_Action   │  ◄── You drop tasks here
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  AI reads task   │
                    │  + checks rules  │
                    └────────┬────────┘
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
                    │         │  _Approval   │
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
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐ ┌───▼───┐ ┌───────▼───────┐
       │   /Done      │ │ /Logs │ │  /Dashboard   │
       │   (archive)  │ │ (audit│ │  (status)     │
       └─────────────┘ │ trail)│ └───────────────┘
                        └───────┘
```

---

## Vault Structure

```
AI_Employee_Vault/
├── Needs_Action/          # Inbox — drop tasks here
├── Tasks/                 # Active plans and work-in-progress
├── Plans/                 # Detailed execution plans
├── Pending_Approval/      # Tasks waiting for manager sign-off
├── Approved/              # Tasks approved and ready to execute
├── Rejected/              # Tasks that were declined
├── Done/                  # Completed tasks (archived)
├── Logs/                  # Daily action logs — full audit trail
├── Notes/                 # Reference material and research
├── Compony_Handbook.md    # Rules, policies, and autonomy level
├── Dashboard.md           # Live status view of all queues
└── README.md              # You are here
```

| Folder | Purpose |
|--------|---------|
| `/Needs_Action` | Inbox — drop tasks here for the AI to pick up |
| `/Tasks` | Active plans and work-in-progress |
| `/Pending_Approval` | Tasks awaiting manager sign-off |
| `/Approved` | Approved tasks (audit record) |
| `/Rejected` | Declined tasks with feedback |
| `/Done` | Completed and archived tasks |
| `/Logs` | Daily action logs — full audit trail |
| `/Notes` | Reference material, research, general notes |

---

## How It Works

### Task Lifecycle

```
1. Drop a task into /Needs_Action
2. AI reads it and creates a plan in /Tasks
3. AI checks Company Handbook for sensitivity flags
4. If sensitive → AI files an approval request in /Pending_Approval
5. If routine → AI executes immediately
6. Completed task moves to /Done
7. Action logged in /Logs
8. Dashboard updated
```

### Sensitivity Detection

The AI checks every task against the **Company Handbook** before acting:

| Sensitive Action | Example |
|-----------------|---------|
| Financial documents | Invoices, payments, refunds |
| External communications | Emails, messages to clients |
| Data deletion | Removing or modifying records |
| Access changes | Permissions, credentials |
| Transactions > $50 | Any monetary action over threshold |

If a match is found, the task is **blocked** until the manager explicitly approves.

### Autonomy Levels

| Level | Behavior |
|-------|----------|
| **LOW** | Ask before every action (current setting) |
| MEDIUM | Auto-handle routine tasks, ask for sensitive ones |
| HIGH | Fully autonomous, only flag critical decisions |

---

## Demo Workflow

This vault ships with **3 completed demo tasks** showing both workflow paths:

### Task 1: Client Invoice (Sensitive Path)
| Step | Action |
|------|--------|
| Detected | `test_task.md` — "Client asked for invoice" |
| Handbook check | MATCH: Financial document |
| Result | Blocked → Approval requested → Approved → Completed |

### Task 2: Weekly Report (Routine Path)
| Step | Action |
|------|--------|
| Detected | `weekly_report.md` — "Prepare weekly progress report" |
| Handbook check | No match — internal/routine |
| Result | Auto-processed → Completed |

### Task 3: Client Email (Sensitive Path)
| Step | Action |
|------|--------|
| Detected | `client_email.md` — "Send follow-up email to client" |
| Handbook check | MATCH: External communication + "Never send emails without approval" |
| Result | Blocked → Draft prepared → Approval requested → Approved → Completed |

### Final Stats

| Metric | Value |
|--------|-------|
| Total tasks processed | 3 |
| Sensitive actions flagged | 2 |
| Approvals requested | 2 |
| Approvals granted | 2 |
| Completion rate | 100% |

---

## Screenshots

> Open this vault in Obsidian to see the full experience.

### Dashboard View
<!-- Screenshot: Dashboard.md showing live task status, queues, and stats -->
`Dashboard.md` — Real-time view of all queues, recent activity, and lifetime stats.

![Dashboard](screenshots/dashboard.png)

### Task Detection
<!-- Screenshot: AI detecting a task in /Needs_Action and checking the handbook -->
AI reads the inbox, checks the Company Handbook, and decides whether to auto-process or request approval.

![Task Detection](screenshots/task-detection.png)

### Approval Pipeline
<!-- Screenshot: Pending_Approval folder with an approval request -->
Sensitive tasks are blocked with a full draft for manager review. Nothing executes without sign-off.

![Approval Pipeline](screenshots/approval-pipeline.png)

### Audit Log
<!-- Screenshot: Logs/2026-02-11.md showing timestamped entries -->
Every action is timestamped and logged. Full traceability from inbox to completion.

![Audit Log](screenshots/audit-log.png)

### Completed Tasks
<!-- Screenshot: Done folder with all 3 completed tasks -->
Archived tasks with full resolution details, including approval records.

![Completed Tasks](screenshots/completed-tasks.png)

> **Note:** To add your own screenshots, create a `screenshots/` folder and replace the image paths above with your actual images.

---

## Getting Started

### Prerequisites
- [Obsidian](https://obsidian.md) (free)
- [Claude Code](https://claude.ai) (AI agent)

### Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Ub207/AI_Employee_Vault.git
   ```

2. **Open in Obsidian**
   - Open Obsidian → "Open folder as vault" → select `AI_Employee_Vault`

3. **Drop a task**
   - Create a markdown file in `/Needs_Action` with your task description

4. **Run the AI Employee**
   - Open Claude Code in the vault directory
   - Tell it: *"Process everything in /Needs_Action"*

5. **Watch it work**
   - Check `/Tasks` for plans
   - Check `/Pending_Approval` if sensitive
   - Check `/Done` when complete
   - Check `/Logs` for the audit trail

---

## Tech Stack

| Tool | Role |
|------|------|
| **Obsidian** | Vault / workspace (markdown-native knowledge base) |
| **Claude Code** | AI agent (reads, plans, executes, logs) |
| **Git + GitHub** | Version control and collaboration |
| **Markdown** | Universal format for all files |

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

**Built with Claude Code** · Hakathone-0 · Digital FTE

*An AI that works like an employee — plans, asks, executes, and reports.*

</div>
