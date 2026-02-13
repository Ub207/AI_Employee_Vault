# Company Handbook

## Core Rules
- Never send emails without approval
- Flag payments over $50
- Always be professional
- If confused, create an approval request
- All settings are defined in `config.yaml` — it is the source of truth

## Sensitive Actions (Require Approval)
- Financial documents (invoices, payments, refunds)
- External communications (emails, messages to clients)
- Data deletion or modification
- Access changes or permissions
- Any action over $50

## Task Processing Protocol
1. Check `/Needs_Action` for new tasks
2. Classify priority (P0-P3) from frontmatter or keyword detection
3. Score sensitivity using weighted keyword analysis
4. Read and understand each task
5. Create a plan in `/Tasks` before acting
6. If sensitive → request manager approval
7. Execute the plan
8. Move completed task to `/Done` with SLA metadata
9. Log the action in `/Logs`
10. Update `/Dashboard.md`

## Autonomy Levels

The system's autonomy level is set in `config.yaml` and controls decision boundaries:

### LOW — Ask Before Everything
- Request approval for **all** non-trivial tasks, even routine ones
- Maximum human oversight, minimum risk
- Best for: initial setup, compliance-heavy environments

### MEDIUM — Smart Autonomy (Default)
- **Routine tasks**: Auto-execute without asking
- **Sensitive tasks**: Always request approval
- Balanced approach — fast for safe work, careful for risky work
- Best for: standard operations, trusted AI employee

### HIGH — Full Autonomy
- Auto-execute both routine and sensitive tasks
- Sensitive actions are logged with warnings but not blocked
- Maximum speed, requires high trust in classification accuracy
- Best for: time-critical operations, well-tuned sensitivity settings

## Priority Definitions

All priority levels and SLA windows are defined in `config.yaml`:

| Priority | Label | SLA Window | When to Use |
|----------|-------|------------|-------------|
| **P0** | Critical | 1 hour | System outages, urgent client issues, blocking problems |
| **P1** | High | 4 hours | Important deadlines, client requests, time-sensitive work |
| **P2** | Medium | 24 hours | Standard tasks, regular work items (default) |
| **P3** | Low | 72 hours | Nice-to-haves, background work, improvements |

### Auto-Detection Keywords
Tasks without explicit priority are scanned for keywords:
- "urgent", "critical" → P0
- "asap", "deadline" → P1
- No match → P2 (default from config)

## Sensitivity Scoring

The sensitivity scorer uses **weighted keywords** from `config.yaml`:
- Each keyword has a weight (0.0 to 1.0)
- Context modifiers adjust scores (e.g., "email" + "client" = higher)
- If total score >= threshold (default 0.6) → task requires approval
- Categories: financial, external_communication, data_deletion, access_change

## Data Handling
- Store outputs in `/Done` with full metadata (priority, SLA, sensitivity score)
- Never include credentials or secrets in logs or outputs
- All config lives in `config.yaml` — no hardcoded values in scripts

## Risk Thresholds
- Flag deviations from this handbook immediately
- Escalate ambiguous tasks to `/Pending_Approval`
- SLA reminders trigger after 2 hours of pending approval
- SLA escalations trigger after 8 hours
