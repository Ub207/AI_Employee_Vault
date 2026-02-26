---
type: plan
task: CLOUD_odoo_overdue_invoice_20260226
source: odoo
agent_origin: cloud
priority: P1
sla_deadline: 2026-02-26T11:00:00
sensitivity_score: 1.0
sensitivity_category: financial
requires_approval: true
created: 2026-02-26
---

# Plan: P1 — Odoo Overdue Invoice INV-2026-007 (Rs. 45,000, 2 days overdue)

## Platinum: Cloud Finance Watcher — 03:00 AM Scheduled Check

## Summary
Odoo finance_watcher ne 03:00 AM pe detect kiya ke INV-2026-007 (Rs. 45,000) 2 days overdue hai. Follow-up email draft karna hai.

## Source Channel
- Odoo (scheduled finance_watcher check at 03:00 AM — cloud agent)

## Priority & SLA
- Priority: **P1 (High)** — overdue receivable
- SLA Deadline: **2026-02-26 11:00** (4h — follow-up needed urgently)
- Financial impact: Rs. 45,000 outstanding

## Sensitivity Scoring
| Keyword | Weight |
|---------|--------|
| invoice | +0.80 |
| payment | +0.90 |
| email | +0.60 |
| **Total (capped)** | **1.0** |

- Score: **1.0 — MAXIMUM SENSITIVITY**
- Category: **financial**
- Requires Approval: **YES**

## Cross-Domain Dependencies
1. **Odoo**: Log follow-up action on INV-2026-007
2. **Gmail**: Draft polite overdue reminder email → approval required
3. **CEO Briefing**: Flag overdue receivable Rs. 45,000

## Draft Gmail — Overdue Reminder
**Subject:** Payment Reminder — Invoice INV-2026-007 (Overdue)

> Dear Client,
>
> I hope this message finds you well. I wanted to gently follow up on Invoice INV-2026-007 for Rs. 45,000, which was due on 2026-02-24 and appears to be outstanding.
>
> Could you please confirm the expected payment date? If you have already processed the payment, kindly disregard this reminder.
>
> Thank you for your continued partnership.
>
> Best regards,
> Ubaid ur Rahman
