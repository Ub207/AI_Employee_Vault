---
type: plan
task: WHATSAPP_client_proposal_20260226
source: whatsapp
priority: P1
sla_deadline: 2026-02-26T15:00:00
sensitivity_score: 0.5
sensitivity_category: external_communication
requires_approval: true
rule_override: "SKILL.md — WhatsApp outgoing always approval-gated"
created: 2026-02-26
---

# Plan: WhatsApp — Client A Proposal Request

## Summary
Client A ne WhatsApp pe latest proposal maangi hai — deadline kal tak. Acknowledgment reply + proposal document prepare karna hoga.

## Source Channel
- WhatsApp (Channels/WhatsApp_Inbox/msg_demo.json)

## Priority & SLA
- Priority: **P1 (High)** — "high" keyword in source
- SLA Deadline: **2026-02-26 15:00** (4 hours — P1)

## Sensitivity Scoring
| Keyword | Weight |
|---------|--------|
| client  | +0.50  |
| **Total** | **0.50** |

- Score: **0.50** — below threshold but WhatsApp = always approval-gated
- Category: **external_communication (client)**
- Requires Approval: **YES (always-gated)**

## Cross-Domain Dependencies
- WhatsApp reply (primary)
- Proposal document → prep for delivery
- If deal closes → Odoo invoice will follow (separate task)

## Execution Checklist
- [x] Read and identify
- [x] Priority: P1
- [x] Sensitivity: 0.5 + always-gated → approval required
- [x] Create plan
- [ ] Create approval file → STOP
- [ ] On approval: Write to /Outbox/WhatsApp/WHATSAPP_client_proposal_20260226.json
- [ ] Prepare proposal document
- [ ] Move to /Done, log, update dashboard

## Draft WhatsApp Reply
> Assalam o Alaikum! Ji zaroor, main aaj hi latest proposal tayyar karke aap ko bhejta hoon. Kal tak ap ke paas pahunch jaegi. Koi specific requirements hain toh please batayein! 🙏

## Proposed Outbox JSON
```json
{
  "chat_name": "Client A",
  "message": "Assalam o Alaikum! Ji zaroor, main aaj hi latest proposal tayyar karke aap ko bhejta hoon. Kal tak ap ke paas pahunch jaegi. Koi specific requirements hain toh please batayein! 🙏",
  "task_ref": "WHATSAPP_client_proposal_20260226.md",
  "created_at": "2026-02-26T11:00:00"
}
```
