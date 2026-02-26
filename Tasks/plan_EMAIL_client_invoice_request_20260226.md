---
type: plan
task: EMAIL_client_invoice_request_20260226
source: gmail
priority: P1
sla_deadline: 2026-02-26T13:15:00
sensitivity_score: 1.0
sensitivity_category: financial
requires_approval: true
created: 2026-02-26
---

# Plan: Gmail — Client Invoice Request (Rs. 75,000)

## Summary
Client (client@acmecorp.com) ne web development project ka invoice aur bank transfer details maange hain. Amount: Rs. 75,000. Cross-domain: Gmail reply + Odoo draft invoice.

## Source Channel
- Gmail (client@acmecorp.com)

## Priority & SLA
- Priority: **P1 (High)**
- SLA Deadline: **2026-02-26 13:15** (4 hours from receipt)

## Sensitivity Scoring
| Keyword  | Weight |
|----------|--------|
| invoice  | +0.80  |
| email    | +0.60  |
| client   | +0.50  |
| payment  | +0.90  |
| bank     | +0.90  |
| transfer | +0.85  |
| **Total (capped)** | **1.0** |

- Score: **1.0** — MAXIMUM SENSITIVITY
- Category: **financial + external_communication**
- Requires Approval: **YES (mandatory)**

## Cross-Domain Dependencies
1. **Odoo MCP**: Draft invoice → Rs. 75,000 → web development project
2. **Gmail**: Reply email with invoice link + bank details → approval required
3. **Financial flag**: Amount exceeds large_payment_threshold (Rs. 50,000)

## Execution Checklist
- [x] Read and identify task
- [x] Classify priority: P1
- [x] Score sensitivity: 1.0 → SENSITIVE (financial)
- [x] Create plan
- [ ] Create /Pending_Approval/approval_EMAIL_client_invoice_request_20260226.md
- [ ] STOP — await manager approval
- [ ] On approval: Create Odoo draft invoice (Rs. 75,000)
- [ ] On approval: Send Gmail reply with invoice details
- [ ] Move to /Done
- [ ] Log and update Dashboard

## Proposed Email Draft
**To:** client@acmecorp.com
**Subject:** Re: Invoice Request — Web Development Project
**Body:**
> Dear Client,
>
> Thank you for your message. Please find the invoice details below:
>
> **Invoice:** WEB-2026-001
> **Project:** Web Development Project
> **Amount:** Rs. 75,000
> **Due Date:** 3 business days from today
>
> Bank transfer details will be shared upon invoice confirmation.
>
> Best regards,
> Ubaid ur Rahman

## Odoo Invoice Fields
- Partner: Acme Corp (client@acmecorp.com)
- Product: Web Development Services
- Quantity: 1
- Unit Price: 75,000 PKR
- Invoice Date: 2026-02-26
