---
type: plan
task: platinum_demo_gmail
source: gmail
priority: P0
sla_deadline: "2026-02-22 11:00"
sensitivity_score: 0.9
sensitivity_category: financial, external_communication
autonomy: MEDIUM
cross_domain: [gmail, odoo, ceo_briefing]
detected_by: cloud_agent
created: "2026-02-22 10:05"
status: pending_approval
---

# Plan: Platinum Demo — Investor Email (P0)

## Summary
Investor at investor@example.com expressing interest in Rs. 5,00,000 investment.
Detected by Cloud Agent at 10:00 AM. Local Agent must approve reply before send.

## Platinum Tier Flow
```
[investor@example.com] → Gmail
        ↓ (Cloud Agent detects at 10:00 AM — local machine was offline)
[Needs_Action/platinum_demo_gmail.md] created by Cloud Agent
        ↓ (Local Agent wakes up, reads inbox)
[Pending_Approval] ← ALL drafts prepared
        ↓ (Human approves)
[Gmail reply sent] + [Odoo lead logged] + [CEO Briefing updated]
        ↓
[Done/] + [Logs/] + [Dashboard/]
```

## Cross-Domain Dependencies
| Platform | Action | Risk |
|----------|--------|------|
| Gmail | Draft professional reply | HIGH — external investor |
| Odoo | Log as CRM lead / opportunity | MEDIUM — financial pipeline |
| CEO Briefing | Flag P0 investor contact | LOW — internal only |

## Checklist
- [x] Read task (Cloud Agent source: gmail)
- [x] Priority: P0 | SLA: 2026-02-22 11:00
- [x] Sensitivity: 0.9 — financial + external_communication
- [x] All drafts prepared in approval file
- [ ] AWAITING LOCAL AGENT APPROVAL
- [ ] Send Gmail reply
- [ ] Create Odoo lead
- [ ] Update CEO Briefing
- [ ] Move to Done/
