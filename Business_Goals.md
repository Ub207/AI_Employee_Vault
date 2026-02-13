---
type: policy
version: 2.0
updated: 2026-02-13
tier: Silver
---

# Business Goals

## Company Mission
- Deliver reliable AI-assisted operations with clear auditability and approval-first safety.
- Operate as an intelligent automation engine with config-driven behavior and SLA guarantees.

## Quarterly Goals
- Improve automation coverage across internal workflows.
- Reduce manual approvals for routine actions via better classification.
- Maintain zero incidents involving external communications or financial actions.
- Achieve 90%+ SLA compliance across all priority levels.
- Increase task throughput with priority queue optimization.

## Silver Tier Goals
- **SLA Compliance Target**: 90%+ on-time task completion
- **Automation Rate**: 70%+ tasks auto-processed (routine, no approval needed)
- **Priority Coverage**: All tasks classified P0-P3 with SLA deadlines
- **Sensitivity Accuracy**: Weighted scoring reduces false positives vs. Bronze tier
- **Scheduler Reliability**: 100% of recurring tasks created on schedule

## Weekly Priorities
- Process all tasks in `/Needs_Action` within SLA deadlines.
- P0 (Critical) tasks must be addressed within 1 hour.
- P1 (High) tasks within 4 hours.
- P2 (Medium, default) tasks within 24 hours.
- P3 (Low) tasks within 72 hours.
- Ensure sensitive actions are routed through `/Pending_Approval`.
- Keep the dashboard and logs accurate and current.
- Monitor SLA compliance and flag overdue tasks.

## Approval Policy
- External communications and financial documents always require approval.
- Transactions over $50 require approval.
- Data deletion/modification and access changes require approval.
- Sensitivity threshold configurable in `config.yaml` (default: 0.6).

## Autonomy Level
- MEDIUM — Auto-handle routine tasks, request approval for sensitive ones.
- Configurable in `config.yaml`. See Company Handbook for level definitions.

## Communication Guidelines
- Be concise, professional, and specific.
- Provide drafts for manager review where appropriate.

## Data Handling
- Store outputs in `/Done` with full metadata (priority, SLA, sensitivity).
- Never include credentials or secrets in logs or outputs.
- All configuration in `config.yaml` — single source of truth.

## Risk Thresholds
- Flag deviations from the Company Handbook immediately.
- Escalate ambiguous tasks to `/Pending_Approval`.
- SLA reminders after 2 hours, escalations after 8 hours (configurable).
