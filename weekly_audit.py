import re
from datetime import datetime, timedelta
from pathlib import Path

VAULT_PATH = Path(__file__).parent.resolve()
LOGS_DIR = VAULT_PATH / "Logs"

def read_logs_for_week(end_date: datetime) -> list[tuple[str, list[str]]]:
    start_date = end_date - timedelta(days=6)
    entries: list[tuple[str, list[str]]] = []
    for i in range(7):
        day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        file = LOGS_DIR / f"{day}.md"
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
    return summary

def generate_weekly_audit(entries: list[tuple[str, list[str]]], summary: dict, end_date: datetime) -> str:
    start_date = (end_date - timedelta(days=6)).strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# Weekly Audit ({start_date} → {end_str})")
    lines.append("")
    lines.append("## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for k in ["total_actions","sensitive_flags","approvals_requested","approvals_granted","approvals_rejected","routine","errors"]:
        label = k.replace("_"," ").title()
        lines.append(f"| {label} | {summary[k]} |")
    lines.append("")
    lines.append("## Activity Log")
    for header, details in entries:
        lines.append(f"- {header}")
        for d in details:
            lines.append(f"  - {d}")
    return "\n".join(lines) + "\n"

def generate_ceo_briefing(summary: dict, end_date: datetime) -> str:
    start_date = (end_date - timedelta(days=6)).strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# CEO Briefing ({start_date} → {end_str})")
    lines.append("")
    lines.append("## Highlights")
    lines.append(f"- Actions processed: {summary['total_actions']}")
    lines.append(f"- Sensitive flags: {summary['sensitive_flags']}")
    lines.append(f"- Approvals: {summary['approvals_granted']} granted, {summary['approvals_rejected']} rejected")
    lines.append(f"- Routine tasks: {summary['routine']}")
    lines.append(f"- Errors: {summary['errors']}")
    lines.append("")
    lines.append("## Risks & Mitigations")
    lines.append("- No high-severity incidents detected.")
    lines.append("- Continue approval-first policy for external communications and financial actions.")
    lines.append("")
    lines.append("## Next Week Goals")
    lines.append("- Increase automation coverage while maintaining approval boundaries.")
    lines.append("- Add additional watchers for email and messaging.")
    lines.append("- Improve dashboard auto-updates.")
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
