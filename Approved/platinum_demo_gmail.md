---
type: approval_request
task: platinum_demo_gmail
source: gmail
priority: P0
sla_deadline: "2026-02-22 11:00"
sensitivity_score: 0.9
sensitivity_category: financial, external_communication
cross_domain: [gmail, odoo, ceo_briefing]
detected_by: cloud_agent
created: "2026-02-22 10:05"
status: awaiting_approval
---

# 🚨 P0 APPROVAL REQUIRED — Investor Email (Rs. 5,00,000)

> **Cloud Agent** detected this at 10:00 AM while local machine was offline.
> All drafts are ready. You only need to approve.

## Trigger
**investor@example.com** → *"We are interested in investing Rs. 5,00,000 in your company. Please send us your pitch deck and financial projections. We need a response by EOD tomorrow."*

| Field | Value |
|-------|-------|
| Priority | P0 — Critical |
| SLA | 2026-02-22 11:00 (1h from detection) |
| Sensitivity | 0.9 — financial + external_communication |
| Detected by | Cloud Agent (24/7 always-on) |
| Deadline | 2026-02-23 EOD |

---

## DRAFT 1 — Gmail Reply

**To:** investor@example.com
**Subject:** Re: Investment Inquiry — Rs. 5,00,000 funding

```
Dear Investor,

Thank you for reaching out and expressing interest in our company.
We are excited about the possibility of this collaboration.

We would be happy to share our pitch deck and financial projections.
Please allow us 24 hours to prepare a comprehensive package tailored
to your requirements.

In the meantime, could you kindly share:
1. Your preferred format (PDF / live presentation)?
2. Any specific metrics or KPIs you'd like us to highlight?
3. Your availability for a brief introductory call?

We look forward to exploring this opportunity with you.

Warm regards,
[Your Name]
Founder | [Company Name]
```

---

## DRAFT 2 — Odoo Lead (CRM)

```json
{
  "model": "crm.lead",
  "name": "Investment Inquiry — investor@example.com",
  "expected_revenue": 500000,
  "probability": 30,
  "description": "Investor interested in Rs. 5,00,000 investment. Requested pitch deck + financials. Deadline: 2026-02-23.",
  "priority": "2",
  "stage": "Qualification"
}
```
> Action: `POST http://localhost:3000/odoo` (draft only — not posted until HITL)

---

## DRAFT 3 — CEO Briefing Update

```markdown
## P0 Alert — Investor Contact (2026-02-22 10:00)
- **From:** investor@example.com
- **Interest:** Rs. 5,00,000 investment
- **Status:** Reply drafted, awaiting approval
- **Action Required:** Approve reply by 11:00 AM + prepare pitch deck
- **SLA:** Response due EOD 2026-02-23
```

---

## Manager Decision

- [ ] **APPROVE ALL** → Move to `/Approved/` — AI will send Gmail reply, create Odoo lead, update CEO Briefing
- [ ] **APPROVE REPLY ONLY** → Add note: "reply only"
- [ ] **REJECT** → Move to `/Rejected/` — investor will receive no reply (manual follow-up needed)

> ⏰ SLA breach in **55 minutes** (11:00 AM). Escalation auto-logged if no response.
> 🤖 Drafted by Cloud Agent | Approved by Local Agent | Platinum Tier
