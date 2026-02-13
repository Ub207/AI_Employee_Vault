"""
AI Employee Vault — Weekly Audit & CEO Briefing (Silver Tier)
Enhanced with SLA compliance metrics, priority breakdown, and approval response analysis.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

from config_loader import load_config, get_path

VAULT_PATH = Path(__file__).parent.resolve()


def read_logs_for_week(end_date: datetime) -> list[tuple[str, list[str]]]:
    logs_dir = get_path("logs")
    start_date = end_date - timedelta(days=6)
    entries: list[tuple[str, list[str]]] = []
    for i in range(7):
        day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        file = logs_dir / f"{day}.md"
        if not file.exists():
            continue
        with file.open("r", encoding="utf-8") as f:
            content = f.read()
        for block in re.split(r"\n(?=## )", content):
            if not block.strip().startswith("## "):
                continue
            lines = block.strip().splitlines()
            header = lines[0][3:].strip()
            details = [l.strip("- ").strip() for l in lines[1:]]
            entries.append((header, details))
    return entries


def summarize(entries: list[tuple[str, list[str]]]) -> dict:
    summary = {
        "total_actions": len(entries),
        "approvals_requested": 0,
        "approvals_granted": 0,
        "approvals_rejected": 0,
        "sensitive_flags": 0,
        "routine": 0,
        "errors": 0,
        "sla_reminders": 0,
        "sla_escalations": 0,
        "scheduled_tasks": 0,
        "priority_counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
    }
    for header, details in entries:
        text = " ".join([header] + details).lower()
        if "approval requested" in text or "request approval" in text:
            summary["approvals_requested"] += 1
        if "approved" in text or "approval granted" in text:
            summary["approvals_granted"] += 1
        if "rejected" in text:
            summary["approvals_rejected"] += 1
        if "sensitive" in text or "requires approval" in text:
            summary["sensitive_flags"] += 1
        if "routine" in text or "auto-processed" in text:
            summary["routine"] += 1
        if "error" in text or "failed" in text:
            summary["errors"] += 1
        if "sla reminder" in text:
            summary["sla_reminders"] += 1
        if "sla escalation" in text:
            summary["sla_escalations"] += 1
        if "scheduled task" in text:
            summary["scheduled_tasks"] += 1
        # Count priority mentions
        for detail in details:
            for p in ("P0", "P1", "P2", "P3"):
                if f"priority: {p}" in detail or f"Priority: {p}" in detail:
                    summary["priority_counts"][p] += 1
    return summary


def read_done_sla_data() -> dict:
    """Read SLA data from completed tasks."""
    done_dir = get_path("done")
    total = 0
    on_time = 0
    if not done_dir.exists():
        return {"total": 0, "on_time": 0, "compliance_pct": 100}
    for f in done_dir.iterdir():
        if not f.is_file() or f.name.startswith(".") or not f.name.endswith(".md"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
            has_sla = False
            completed_date = ""
            sla_deadline = ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("completed_date:"):
                    completed_date = stripped.split(":", 1)[1].strip()
                if stripped.startswith("sla_deadline:"):
                    sla_deadline = stripped.split(":", 1)[1].strip()
                    has_sla = True
            if has_sla and completed_date and sla_deadline and sla_deadline != "auto":
                total += 1
                if completed_date <= sla_deadline[:10]:
                    on_time += 1
        except Exception:
            pass
    pct = int(100 * on_time / total) if total > 0 else 100
    return {"total": total, "on_time": on_time, "compliance_pct": pct}


def generate_weekly_audit(entries: list[tuple[str, list[str]]], summary: dict, end_date: datetime) -> str:
    start_date = (end_date - timedelta(days=6)).strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    sla_data = read_done_sla_data()
    lines = []
    lines.append(f"# Weekly Audit ({start_date} \u2192 {end_str})")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for k in ["total_actions", "sensitive_flags", "approvals_requested", "approvals_granted",
              "approvals_rejected", "routine", "errors", "sla_reminders", "sla_escalations", "scheduled_tasks"]:
        label = k.replace("_", " ").title()
        lines.append(f"| {label} | {summary[k]} |")
    lines.append("")

    # SLA Compliance
    lines.append("## SLA Compliance")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Tasks with SLA tracking | {sla_data['total']} |")
    lines.append(f"| On-time completions | {sla_data['on_time']} |")
    lines.append(f"| Compliance rate | {sla_data['compliance_pct']}% |")
    lines.append("")

    # Priority Breakdown
    lines.append("## Priority Breakdown")
    lines.append("| Priority | Label | Count |")
    lines.append("|----------|-------|-------|")
    prio_labels = {"P0": "Critical", "P1": "High", "P2": "Medium", "P3": "Low"}
    for p in ("P0", "P1", "P2", "P3"):
        lines.append(f"| {p} | {prio_labels[p]} | {summary['priority_counts'][p]} |")
    lines.append("")

    # Activity Log
    lines.append("## Activity Log")
    for header, details in entries:
        lines.append(f"- {header}")
        for d in details:
            lines.append(f"  - {d}")
    return "\n".join(lines) + "\n"


def generate_ceo_briefing(summary: dict, end_date: datetime) -> str:
    start_date = (end_date - timedelta(days=6)).strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    sla_data = read_done_sla_data()
    cfg = load_config()
    autonomy = cfg.get("autonomy_level", "MEDIUM")

    lines = []
    lines.append(f"# CEO Briefing ({start_date} \u2192 {end_str})")
    lines.append("")

    lines.append("## System Status")
    lines.append(f"- **Tier:** Silver")
    lines.append(f"- **Autonomy Level:** {autonomy}")
    lines.append("")

    lines.append("## Highlights")
    lines.append(f"- Actions processed: {summary['total_actions']}")
    lines.append(f"- Sensitive flags: {summary['sensitive_flags']}")
    lines.append(f"- Approvals: {summary['approvals_granted']} granted, {summary['approvals_rejected']} rejected")
    lines.append(f"- Routine tasks: {summary['routine']}")
    lines.append(f"- Scheduled tasks created: {summary['scheduled_tasks']}")
    lines.append(f"- Errors: {summary['errors']}")
    lines.append("")

    lines.append("## SLA Performance")
    lines.append(f"- Compliance: **{sla_data['compliance_pct']}%** ({sla_data['on_time']}/{sla_data['total']} on-time)")
    lines.append(f"- SLA reminders sent: {summary['sla_reminders']}")
    lines.append(f"- SLA escalations: {summary['sla_escalations']}")
    lines.append("")

    lines.append("## Priority Summary")
    total_prio = sum(summary["priority_counts"].values())
    if total_prio > 0:
        lines.append(f"- Critical (P0): {summary['priority_counts']['P0']}")
        lines.append(f"- High (P1): {summary['priority_counts']['P1']}")
        lines.append(f"- Medium (P2): {summary['priority_counts']['P2']}")
        lines.append(f"- Low (P3): {summary['priority_counts']['P3']}")
    else:
        lines.append("- No priority-tagged tasks this period")
    lines.append("")

    lines.append("## Risks & Mitigations")
    if summary["errors"] > 0:
        lines.append(f"- {summary['errors']} error(s) detected — review logs for details.")
    else:
        lines.append("- No errors detected.")
    if summary["sla_escalations"] > 0:
        lines.append(f"- {summary['sla_escalations']} SLA escalation(s) — review pending approvals.")
    lines.append("- Continue approval-first policy for external communications and financial actions.")
    lines.append("")

    lines.append("## Next Week Goals")
    lines.append("- Maintain SLA compliance above 90%.")
    lines.append("- Clear all pending approvals within SLA windows.")
    lines.append("- Monitor scheduler for recurring task reliability.")
    lines.append("- Review and tune sensitivity thresholds if needed.")
    return "\n".join(lines) + "\n"


def main() -> None:
    now = datetime.now()
    entries = read_logs_for_week(now)
    summary = summarize(entries)
    weekly_audit = generate_weekly_audit(entries, summary, now)
    ceo_briefing = generate_ceo_briefing(summary, now)
    audit_file = VAULT_PATH / "Weekly_Audit.md"
    briefing_file = VAULT_PATH / "CEO_Briefing.md"
    audit_file.write_text(weekly_audit, encoding="utf-8")
    briefing_file.write_text(ceo_briefing, encoding="utf-8")
    print(f"Wrote {audit_file} and {briefing_file}")


if __name__ == "__main__":
    main()
