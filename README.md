# AI Employee Vault — Digital FTE (Hakathone-0)

> A markdown-based autonomous AI employee system built on Obsidian.
> The AI reads tasks, creates plans, follows company rules, requests approval for sensitive actions, and logs everything.

## What is a Digital FTE?

A **Digital Full-Time Equivalent** is an AI agent that operates like a real employee:
- It has a **workspace** (this Obsidian vault)
- It follows a **Company Handbook** with rules and autonomy levels
- It picks up tasks from an **inbox** (`/Needs_Action`)
- It **plans before acting** and **asks for approval** on sensitive items
- It **logs everything** it does for auditability
- It moves completed work to `/Done`

## Vault Structure

| Folder | Purpose |
|--------|---------|
| `/Needs_Action` | Inbox — drop tasks here for the AI to pick up |
| `/Tasks` | Active plans and work-in-progress |
| `/Plans` | Detailed execution plans |
| `/Pending_Approval` | Tasks waiting for manager sign-off |
| `/Approved` | Tasks approved and ready to execute |
| `/Rejected` | Tasks that were declined |
| `/Done` | Completed tasks (archived) |
| `/Logs` | Daily action logs — full audit trail |
| `/Notes` | Reference material, research, general notes |

## Key Files

| File | Purpose |
|------|---------|
| `Compony_Handbook.md` | Rules, policies, and autonomy level |
| `Dashboard.md` | Live status view of all queues |
| `README.md` | This file — project overview |

## How It Works

```
1. Drop a task into /Needs_Action
2. AI reads it and creates a plan in /Tasks
3. If sensitive → AI requests approval
4. AI executes and moves result to /Done
5. Everything is logged in /Logs
```

## Rules
1. Read and write only markdown files
2. Always create a plan before acting
3. Never take sensitive actions without approval
4. Move completed tasks to `/Done`
5. Log important actions in `/Logs`

## Autonomy Levels

| Level | Behavior |
|-------|----------|
| **LOW** | Ask before every action (current setting) |
| MEDIUM | Auto-handle routine tasks, ask for sensitive ones |
| HIGH | Fully autonomous, only flag critical decisions |

## Demo Workflow

This vault includes a completed demo cycle:
1. `test_task.md` was placed in `/Needs_Action` (client invoice request)
2. AI detected it, flagged as sensitive per Handbook, created a plan
3. AI requested approval and details from manager
4. After authorization, processed the task with demo data
5. Moved completed task to `/Done`, updated Dashboard and Logs

## Tech Stack
- **Obsidian** — Vault/workspace (markdown-native knowledge base)
- **Claude Code** — AI agent (reads, plans, executes, logs)
- **Git** — Version control (optional)
