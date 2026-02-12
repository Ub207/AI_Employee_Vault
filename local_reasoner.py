import re
import shutil
from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).parent.resolve()
INBOX = VAULT / "Needs_Action"
TASKS = VAULT / "Tasks"
PENDING = VAULT / "Pending_Approval"
APPROVED = VAULT / "Approved"
DONE = VAULT / "Done"
LOGS = VAULT / "Logs"

def read_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("\n---", 1)
        fm_block = parts[0].strip("-\n") if len(parts) > 1 else ""
        body = parts[1] if len(parts) > 1 else text
    else:
        fm_block = ""
        body = text
    meta: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body

def classify_sensitivity(meta: dict, body: str) -> str:
    if "sensitivity" in meta and meta["sensitivity"] not in ("", "none"):
        return meta["sensitivity"]
    b = body.lower()
    if any(w in b for w in ["invoice", "payment", "refund", "$", "usd"]):
        return "financial"
    if any(w in b for w in ["email", "gmail", "whatsapp", "message", "client", "linkedin", "twitter", "facebook", "instagram"]):
        return "external_communication"
    if any(w in b for w in ["delete", "remove", "erase", "drop table"]):
        return "data_deletion"
    if any(w in b for w in ["permission", "access", "role", "credential"]):
        return "access_change"
    return "none"

def write_log(title: str, details: list[str]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    f = LOGS / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"## {datetime.now().strftime('%H:%M')} - {title}\n")
        for d in details:
            fh.write(f"- {d}\n")

def write_plan(stem: str, summary: str, sensitivity: str) -> None:
    TASKS.mkdir(parents=True, exist_ok=True)
    p = TASKS / f"plan_{stem}.md"
    lines = []
    lines.append(f"# Plan: {stem}")
    lines.append("")
    lines.append(f"## Summary")
    lines.append(f"- {summary.strip()}")
    lines.append("")
    lines.append("## Classification")
    lines.append(f"- Sensitivity: {sensitivity}")
    lines.append("")
    lines.append("## Steps")
    lines.append("- Draft deliverable")
    lines.append("- Route approvals if sensitive")
    lines.append("- Save to /Done and update dashboard")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_approval(stem: str, summary: str, sensitivity: str) -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    p = PENDING / f"approval_{stem}.md"
    lines = []
    lines.append(f"# Approval Request: {stem}")
    lines.append("")
    lines.append("## Why Sensitive")
    lines.append(f"- Category: {sensitivity}")
    lines.append("")
    lines.append("## Proposed Plan")
    lines.append("- Draft prepared per plan")
    lines.append("- Await manager sign-off before sending/posting")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_done(stem: str, priority: str, sensitivity: str, body: str) -> None:
    DONE.mkdir(parents=True, exist_ok=True)
    p = DONE / f"{stem}.md"
    lines = []
    lines.append("---")
    lines.append("type: task")
    lines.append(f"priority: {priority}")
    lines.append("status: completed")
    lines.append(f"created: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"completed_date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"sensitivity: {sensitivity}")
    lines.append("approval: not_required")
    lines.append("---")
    lines.append("")
    lines.append(body.strip() or f"# Completed: {stem}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

def process_task(path: Path) -> None:
    stem = path.stem
    meta, body = read_frontmatter(path)
    priority = meta.get("priority", "medium")
    summary = meta.get("subject", meta.get("title", stem))
    sensitivity = classify_sensitivity(meta, body)
    write_plan(stem, summary, sensitivity)
    if sensitivity != "none":
        write_approval(stem, summary, sensitivity)
        write_log("Approval Requested", [f"Task: {stem}", f"Sensitivity: {sensitivity}"])
    else:
        write_done(stem, priority, sensitivity, f"# {summary}\n\nDraft prepared and completed.")
        write_log("Task Completed", [f"Task: {stem}", "Routine"])
    try:
        path.unlink()
    except Exception:
        pass
    try:
        from update_dashboard import write_dashboard
        write_dashboard()
    except Exception:
        pass

def main() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    for md in INBOX.glob("*.md"):
        process_task(md)

if __name__ == "__main__":
    main()
