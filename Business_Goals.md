---
type: policy
version: 1.0
updated: 2026-02-12
---

# Business Goals

## Company Mission
- Deliver reliable AI-assisted operations with clear auditability and approval-first safety.

## Quarterly Goals
- Improve automation coverage across internal workflows.
- Reduce manual approvals for routine actions via better classification.
- Maintain zero incidents involving external communications or financial actions.

## Weekly Priorities
- Process all tasks in `/Needs_Action` within 24 hours.
- Ensure sensitive actions are routed through `/Pending_Approval`.
- Keep the dashboard and logs accurate and current.

## Approval Policy
- External communications and financial documents always require approval.
- Transactions over $50 require approval.
- Data deletion/modification and access changes require approval.

## Autonomy Level
- LOW — Ask before non-trivial actions, escalate when uncertain.

## Communication Guidelines
- Be concise, professional, and specific.
- Provide drafts for manager review where appropriate.

## Data Handling
- Store outputs in `/Done` with metadata.
- Never include credentials or secrets in logs or outputs.

## Risk Thresholds
- Flag deviations from the Company Handbook immediately.
- Escalate ambiguous tasks to `/Pending_Approval`.
