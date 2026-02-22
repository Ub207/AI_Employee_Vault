---
type: approval_request
task: gold_demo
source: whatsapp
priority: P2
sla_deadline: "2026-02-23 09:20"
sensitivity_score: 0.8
sensitivity_category: financial, external_communication
cross_domain: [odoo, twitter, linkedin, gmail]
created: "2026-02-22 09:20"
status: awaiting_approval
---

# ⚠️ APPROVAL REQUIRED — Cross-Domain Deal Win (4 Actions)

## Trigger Event
**Hamza Butt** (WhatsApp): *"Deal confirmed! Rs. 1,20,000 ka project start karte hain."*

## Why Approval Needed
Sensitivity score **0.8** — financial action + 3 external communications across 4 platforms.

---

## DRAFT 1 — Odoo Invoice

| Field | Value |
|-------|-------|
| Client | Hamza Butt |
| Amount | Rs. 1,20,000 |
| Description | Project Kickoff — Digital Services |
| Type | Draft Invoice (NOT posted until approval) |
| Due Date | 2026-03-08 (Net 14) |

> Action: `POST http://localhost:8010/tools/create_draft_invoice`
> Body: `{ "partner": "Hamza Butt", "amount": 120000, "description": "Project Kickoff - Digital Services", "due_date": "2026-03-08" }`

---

## DRAFT 2 — Twitter/X Tweet

```
🎉 New project confirmed!

Excited to announce we've kicked off a new collaboration.
Big things ahead. 🚀

#NewProject #DigitalServices #BusinessGrowth
```
*(280 chars max — current: 142 chars ✓)*

---

## DRAFT 3 — LinkedIn Post

```
Thrilled to announce a new project partnership! 🤝

We've officially kicked off a new digital services engagement.
This collaboration reflects our commitment to delivering measurable value for our clients.

Looking forward to the journey ahead — stay tuned for updates!

#BusinessDevelopment #NewProject #DigitalServices #Growth
```

---

## DRAFT 4 — Gmail Onboarding Email

**To:** Hamza Butt
**Subject:** Welcome! Your Project Kickoff — Next Steps

```
Dear Hamza,

Thank you for confirming the project! We're excited to get started.

Here's what happens next:
1. You'll receive your invoice (Rs. 1,20,000) within 24 hours
2. Our team will schedule the kickoff call within 48 hours
3. Project workspace access will be shared via email

Please don't hesitate to reach out for any questions.

Warm regards,
[Your Name]
Digital FTE — AI Employee
```

---

## Manager Decision

**Approve all 4 actions:**
- [ ] Move this file to `/Approved/` → AI will execute all 4 drafts

**Approve selectively (add notes below):**
- [ ] Odoo invoice only
- [ ] Social posts only (Twitter + LinkedIn)
- [ ] Gmail email only

**Reject:**
- [ ] Move this file to `/Rejected/` → All actions cancelled, client notified manually

> ⏰ SLA deadline: 2026-02-23 09:20 — escalation in 8h if no response
