---
type: policy
version: 3.0
updated: 2026-02-19
tier: Gold
---

# Business Goals

## Company Mission
- Operate as a fully autonomous AI employee across personal and business domains.
- Deliver reliable, auditable, approval-first automation with 24/7 coverage capability.
- Integrate all major communication platforms and business systems into one intelligent system.

## Quarterly Goals (Gold Tier)
- Achieve 90%+ SLA compliance across all priority levels.
- Automate 70%+ of routine tasks without human intervention.
- Maintain zero incidents involving unauthorized external communications or financial actions.
- Generate weekly CEO Briefings with real accounting data from Odoo.
- Maintain full audit trail for all cross-domain actions (Email, WhatsApp, LinkedIn, Facebook, Instagram, Twitter, Odoo).

## Revenue & Accounting Targets
- Monthly revenue goal: $10,000
- Invoice payment rate: > 90%
- Unpaid invoices: Follow up after 7 days
- Software costs: < $500/month (flag subscriptions > $600/month)

## Key Metrics to Track
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Client response time | < 24 hours | > 48 hours |
| Invoice payment rate | > 90% | < 80% |
| Social engagement rate | > 2% | < 0.5% |
| System uptime | > 99% | < 95% |
| SLA compliance | > 90% | < 80% |

## Platform Integration Map
| Domain | Platform | Watcher | Post | Summarize |
|--------|----------|---------|------|-----------|
| Personal | Gmail | ✅ | Gmail MCP | Weekly Audit |
| Personal | WhatsApp | ✅ | Twilio MCP | Weekly Audit |
| Business | LinkedIn | ✅ | LinkedIn API | `/summary` |
| Business | Facebook | ✅ | Facebook Graph API | `/summary` |
| Business | Instagram | ✅ | Instagram Graph API | `/summary` |
| Business | Twitter/X | ✅ | Twitter API v2 | `/summary` |
| Business | Odoo | HITL | Odoo MCP (draft) | `accounting_summary` |

## Approval Policy (Gold Tier)
- External communications always require approval (all platforms)
- Financial transactions over $50 require approval
- All Odoo invoice postings require explicit human approval
- Data deletion/modification requires approval
- Autonomy threshold configurable in `config.yaml` (default: MEDIUM)

## Subscription Audit Rules
Flag subscriptions for review if:
- No usage in 30 days
- Cost increased > 20% month-over-month
- Duplicate functionality with another tool
- Cost > $100/month for single tool

## Weekly Priorities
- Process all tasks in `/Needs_Action` within SLA deadlines
- P0 (Critical) tasks within 1 hour
- P1 (High) tasks within 4 hours
- P2 (Medium, default) tasks within 24 hours
- P3 (Low) tasks within 72 hours
- Generate social media content for LinkedIn, Facebook, Twitter daily
- Run weekly Odoo accounting audit every Sunday night
- Generate CEO Briefing every Monday morning

## Cross-Domain Workflow Examples
1. **Client WhatsApp** → create Odoo draft invoice → notify client via email (all with HITL approval)
2. **New task completed** → auto-post achievement to LinkedIn + Twitter
3. **Late payment detected** → send follow-up email draft for approval + log in Odoo
4. **Competitor news** → research + draft LinkedIn thought-leadership post for approval

## Risk Thresholds
- Flag deviations from Company Handbook immediately
- Escalate ambiguous tasks to `/Pending_Approval`
- SLA reminders after 2 hours, escalations after 8 hours
- Never auto-approve: new payees, amounts > $100, bulk communications
