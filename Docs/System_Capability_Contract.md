---
type: system_contract
version: 1.0
tier: Silver
generated: 2026-02-15
author: AI Employee (Digital FTE)
---

# System Capability Contract — Hakathone-0 (Digital FTE)

This document defines what the AI Employee system **can do**, what it **cannot do**, and what **future upgrades** would enable. It reflects the actual implemented state of the codebase as of 2026-02-15.

---

## Section 1: Current Capabilities (Bronze/Silver Tier)

### 1.1 Task Intake and Processing

| Capability | Status | Details |
|------------|--------|---------|
| File-based task intake | Implemented | `.md` files dropped into `/Needs_Action` are detected and processed |
| Filesystem watcher | Implemented | `watcher.py` uses `watchdog` library for real-time file monitoring |
| Channel event ingestion | Implemented | `channel_event_to_task.py` converts JSON events from `/Channels/` (Gmail, WhatsApp, Social) into task files |
| Local fallback processor | Implemented | `local_reasoner.py` processes tasks when Claude CLI is unavailable |
| Process manager with restart | Implemented | `process_manager.py` auto-restarts the watcher with exponential backoff |

### 1.2 Priority Queue System

| Capability | Status | Details |
|------------|--------|---------|
| 4-level priority (P0-P3) | Implemented | P0=Critical/1h, P1=High/4h, P2=Medium/24h, P3=Low/72h |
| Frontmatter priority parsing | Implemented | Reads `priority:` from YAML frontmatter |
| Keyword auto-detection | Implemented | "urgent"/"critical" -> P0, "asap"/"deadline" -> P1, default P2 |
| Priority-sorted processing | Implemented | Existing tasks in inbox are sorted P0-first before processing |
| Configurable defaults | Implemented | All priority labels, SLA hours, and keywords defined in `config.yaml` |

### 1.3 Sensitivity Scoring and Approval Routing

| Capability | Status | Details |
|------------|--------|---------|
| Weighted keyword scoring | Implemented | Keywords scored 0.0-1.0 (e.g., `password: 1.0`, `client: 0.5`) |
| Context modifiers | Implemented | Word pairs boost or reduce score (e.g., "email"+"client" = +0.3) |
| Category classification | Implemented | `financial`, `external_communication`, `data_deletion`, `access_change` |
| Configurable threshold | Implemented | Default 0.6; score >= threshold triggers approval requirement |
| Approval request generation | Implemented | Creates structured approval files in `/Pending_Approval/` |
| Approval folder workflow | Implemented | Pending -> Approved or Rejected, with audit trail |

### 1.4 Autonomy Levels

| Level | Routine Tasks | Sensitive Tasks | Status |
|-------|--------------|-----------------|--------|
| LOW | Request approval | Request approval | Implemented |
| MEDIUM (current) | Auto-execute | Request approval | Implemented, active |
| HIGH | Auto-execute | Auto-execute (log warning) | Implemented |

Current setting: **MEDIUM** -- configurable via `config.yaml`.

### 1.5 SLA Tracking

| Capability | Status | Details |
|------------|--------|---------|
| SLA deadline calculation | Implemented | Computed from priority level + detection time |
| SLA metadata in completed tasks | Implemented | `sla_deadline` and `detected_at` stored in frontmatter |
| Approval wait reminders | Implemented | Logged after 2 hours (configurable) |
| Approval wait escalations | Implemented | Logged after 8 hours (configurable) |
| SLA compliance reporting | Implemented | Calculated in weekly audit and dashboard |

### 1.6 Scheduling

| Capability | Status | Details |
|------------|--------|---------|
| Cron-based recurring tasks | Implemented | Uses `croniter` library to evaluate cron expressions |
| Persistent state tracking | Implemented | `scheduler_state.json` stores last-run timestamps |
| Config-driven schedules | Implemented | Defined in `config.yaml` `scheduler:` section |
| Current schedules | Active | `weekly_report` (Fridays 09:00), `daily_standup` (Mon-Fri 08:00) |

### 1.7 Logging and Audit

| Capability | Status | Details |
|------------|--------|---------|
| Daily action logs | Implemented | Written to `/Logs/YYYY-MM-DD.md` |
| Weekly audit generation | Implemented | `weekly_audit.py` aggregates logs into summary report |
| CEO briefing generation | Implemented | Executive summary with SLA, priority, risk sections |
| Dashboard updates | Implemented | `Dashboard.md` tracks queue counts, SLA %, priority distribution |

### 1.8 Retry and Error Handling

| Capability | Status | Details |
|------------|--------|---------|
| Configurable retry | Implemented | Max 3 attempts, exponential backoff (2s initial, 60s max) |
| Timeout handling | Implemented | Watcher timeout at 120s per task |
| Fallback processing | Implemented | Falls back to `local_reasoner.py` if Claude CLI not found |

### 1.9 Task Lifecycle (Folder Workflow)

```
Needs_Action/ --> Tasks/ (plan created)
                    |
                    +--> [routine] --> Done/ (auto-executed)
                    |
                    +--> [sensitive] --> Pending_Approval/
                                            |
                                            +--> Approved/ --> Done/
                                            +--> Rejected/
```

All transitions are logged. Dashboard is updated after each action.

---

## Section 2: Current Limitations

### 2.1 API Integrations: ALL SIMULATED

| Integration | Reality | Details |
|-------------|---------|---------|
| Gmail | **Simulated** | `/Channels/Gmail_Inbox/` reads static JSON files. No OAuth, no IMAP, no Gmail API connection. Cannot send or receive real emails. |
| WhatsApp | **Simulated** | `/Channels/WhatsApp_Inbox/` reads static JSON files. No WhatsApp Business API connection. Cannot send or receive real messages. |
| Social Media | **Simulated** | `/Channels/Social_Inbox/` reads static JSON files. No Twitter/LinkedIn/Instagram API connection. Cannot post or read real content. |
| Calendar | **Not implemented** | No Google Calendar or Outlook integration. |
| Payments | **Not implemented** | No Stripe, PayPal, or banking API. Financial tasks produce text drafts only. |
| CRM | **Not implemented** | No Salesforce, HubSpot, or similar integration. |
| Notifications | **Not implemented** | No Slack, Teams, email, or push notifications to humans. SLA reminders and escalations are log entries only -- not delivered to anyone. |

**All channel watchers (`gmail_watcher.py`, `whatsapp_watcher.py`, `social_watcher.py`) poll local JSON files. No network calls are made.**

### 2.2 Approval Workflow Limitations

| Limitation | Details |
|------------|---------|
| No notification to approver | Approval requests sit in `/Pending_Approval/` as files. No alert is sent to any human. The manager must manually check the folder. |
| No in-app approval mechanism | Approval/rejection requires manually moving files between folders. No UI, no API, no webhook. |
| SLA escalation is log-only | Escalations are written to log files. No pager, no email, no Slack alert. Nobody is actually notified. |
| No approval audit signatures | No cryptographic signing or identity verification on approvals. Anyone with file access can move files. |

### 2.3 Execution Limitations

| Limitation | Details |
|------------|---------|
| Text-output only | The system produces markdown files as deliverables. It cannot execute real-world actions (send emails, make API calls, modify databases, deploy code). |
| No state persistence beyond files | No database. All state is flat files and JSON. No transaction safety, no rollback capability. |
| Single-machine operation | Runs on one machine only. No distributed processing, no cloud deployment, no horizontal scaling. |
| No concurrent task processing | Tasks are processed sequentially. The watcher handles one task at a time. |
| No user authentication | No login system. Whoever has filesystem access has full control. |
| No version control on tasks | Task files can be overwritten without history (git tracks the vault, but individual task edits are not versioned). |

### 2.4 Intelligence Limitations

| Limitation | Details |
|------------|---------|
| No learning/adaptation | Sensitivity weights are static in config. The system does not learn from past approvals or rejections. |
| No context memory across tasks | Each task is processed independently. No awareness of related tasks or ongoing projects. |
| No natural language understanding for routing | Priority and sensitivity use keyword matching only, not semantic understanding (in the local reasoner path). |
| No predictive capabilities | Cannot forecast workload, predict SLA breaches before they happen, or suggest schedule adjustments. |

### 2.5 Monitoring Limitations

| Limitation | Details |
|------------|---------|
| No real-time monitoring UI | Dashboard is a static markdown file, not a live web dashboard. |
| No alerting system | No PagerDuty, OpsGenie, or alerting integration. |
| No metrics/telemetry export | No Prometheus, Datadog, or similar observability platform. |
| No health checks | No endpoint to verify the system is running. Process manager restarts on crash but does not report status externally. |

---

## Section 3: Future Upgrade Paths (Gold Tier)

### 3.1 Real API Integrations

| Upgrade | What It Enables | Implementation Approach |
|---------|----------------|------------------------|
| Gmail API (OAuth 2.0) | Send/receive real emails, auto-draft replies, attach files | Google API client with token refresh, scoped permissions |
| WhatsApp Business API | Send/receive real messages, template messages, media | Meta Cloud API or BSP integration with webhook receiver |
| Slack/Teams integration | Real-time notifications, approval buttons, status updates | Bot framework with interactive message components |
| Calendar sync | Read/create meetings, check availability, send invites | Google Calendar API or Microsoft Graph API |
| CRM integration | Read/update contacts, log interactions, track deals | REST API connector for Salesforce/HubSpot |
| Payment gateway | Process invoices, verify payments, issue refunds | Stripe/PayPal API with strict approval gates |

### 3.2 Enhanced Approval Workflow

| Upgrade | What It Enables |
|---------|----------------|
| Slack approval buttons | Manager clicks "Approve" or "Reject" in Slack; system continues automatically |
| Email-based approvals | Reply-to-approve via unique approval links |
| Mobile push notifications | Alert managers on their phone for P0/P1 approvals |
| Multi-level approval chains | P0 tasks require two approvers; financial tasks require finance + manager |
| Approval SLA enforcement | Auto-escalate to backup approver if primary does not respond within SLA |
| Audit signatures | Cryptographic or identity-verified approval records |

### 3.3 Increased Autonomy

| Upgrade | What It Enables |
|---------|----------------|
| Adaptive sensitivity tuning | System learns from approval/rejection history to adjust keyword weights |
| Confidence-based routing | High-confidence routine tasks skip planning step; low-confidence tasks get extra review |
| Cross-task context awareness | System remembers related tasks, ongoing projects, and client history |
| Predictive SLA management | Forecast workload spikes and suggest priority adjustments before breaches occur |
| Autonomous multi-step workflows | Chain tasks together (e.g., receive invoice -> verify amount -> draft payment -> request approval -> send confirmation) |

### 3.4 Infrastructure Upgrades

| Upgrade | What It Enables |
|---------|----------------|
| Database backend (SQLite/PostgreSQL) | Transaction-safe state, queryable task history, rollback capability |
| Web dashboard | Live status page with real-time updates, charts, and filtering |
| REST API layer | External systems can submit tasks, check status, and receive webhooks |
| Concurrent task processing | Worker pool for parallel task execution with priority preemption |
| Cloud deployment | Run as a service (Docker/K8s) with auto-scaling and high availability |
| Observability stack | Prometheus metrics, structured logging, distributed tracing |

### 3.5 Sensitive Action Handling Upgrades

| Upgrade | What It Enables |
|---------|----------------|
| Sandbox execution | Sensitive actions execute in isolated environment before committing to production |
| Dry-run mode | Generate full output of what would happen without actually executing |
| Rollback capability | Undo completed actions if post-execution review finds issues |
| Rate limiting | Prevent runaway execution (e.g., max 5 external emails per hour) |
| Sensitive data vault | Encrypted storage for credentials, API keys, and PII with access logging |

---

## Summary Matrix

| Dimension | Bronze | Silver (Current) | Gold (Future) |
|-----------|--------|-------------------|---------------|
| **Automation** | Manual trigger | File watcher + scheduler + auto-retry | Event-driven + API webhooks + worker pool |
| **Priority** | None | P0-P3 with SLA tracking | Predictive SLA + dynamic re-prioritization |
| **Sensitivity** | Simple keyword list | Weighted scoring + context modifiers | Adaptive ML-tuned thresholds |
| **Approval** | All manual | Config-driven routing (folder-based) | Interactive (Slack/email) + multi-level chains |
| **Integrations** | None | Simulated channels (local JSON) | Real APIs (Gmail, Slack, CRM, payments) |
| **Autonomy** | LOW only | LOW / MEDIUM / HIGH (configurable) | Confidence-based adaptive autonomy |
| **Notifications** | None | Log-only reminders/escalations | Push/Slack/email alerts to real humans |
| **Dashboard** | None | Static markdown | Live web UI with charts and filtering |
| **Data Store** | Flat files | Flat files + JSON state | Database with transactions and history |
| **Deployment** | Local script | Local with process manager | Cloud service with HA and scaling |

---

*This contract is a living document. It will be updated as capabilities change.*
*Generated by AI Employee (Digital FTE) on 2026-02-15.*
