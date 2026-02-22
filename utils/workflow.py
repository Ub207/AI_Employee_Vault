from datetime import datetime
from pathlib import Path

VAULT = Path(__file__).parent.parent.resolve()
PENDING = VAULT / "Pending_Approval"
DONE = VAULT / "Done"

def write_approval(stem: str, summary: str, category: str) -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    p = PENDING / f"approval_{stem}.md"
    lines = []
    lines.append(f"# Approval Request: {stem}")
    lines.append("")
    lines.append("## Why Sensitive")
    lines.append(f"- Category: {category}")
    lines.append("")
    lines.append("## Proposed Plan")
    lines.append("- Draft prepared")
    lines.append("- Await manager sign-off before sending/posting")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_done(stem: str, priority: str, category: str, body: str) -> None:
    DONE.mkdir(parents=True, exist_ok=True)
    p = DONE / f"{stem}.md"
    now = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append("---")
    lines.append("type: task")
    lines.append(f"priority: {priority}")
    lines.append("status: completed")
    lines.append(f"created: {now}")
    lines.append(f"completed_date: {now}")
    lines.append(f"sensitivity: {category}")
    lines.append("approval: not_required")
    lines.append("---")
    lines.append("")
    lines.append(body.strip() or f"# Completed: {stem}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
