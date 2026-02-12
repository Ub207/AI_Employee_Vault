from datetime import datetime
from pathlib import Path

VAULT_PATH = Path(__file__).parent.resolve()

def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.is_file() and not p.name.startswith("."))

def list_files(path: Path, max_items: int = 10) -> list[str]:
    if not path.exists():
        return []
    items = [p.stem for p in path.iterdir() if p.is_file() and not p.name.startswith(".")]
    return items[:max_items]

def recent_activity(max_rows: int = 8) -> list[tuple[str, str, str]]:
    logs_dir = VAULT_PATH / "Logs"
    today = datetime.now().strftime("%Y-%m-%d")
    file = logs_dir / f"{today}.md"
    rows: list[tuple[str, str, str]] = []
    if file.exists():
        text = file.read_text(encoding="utf-8")
        blocks = [b for b in text.split("\n## ") if b.strip()]
        for b in blocks[-max_rows:]:
            header, *rest = b.splitlines()
            time_title = header.strip()
            action = rest[0].strip("- ").strip() if rest else ""
            details = rest[1].strip("- ").strip() if len(rest) > 1 else ""
            rows.append((time_title, action, details))
    return rows

def write_dashboard() -> None:
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    needs_action = VAULT_PATH / "Needs_Action"
    pending = VAULT_PATH / "Pending_Approval"
    approved = VAULT_PATH / "Approved"
    tasks = VAULT_PATH / "Tasks"
    done = VAULT_PATH / "Done"
    rejected = VAULT_PATH / "Rejected"

    lines = []
    lines.append("# AI Employee Dashboard")
    lines.append("")
    lines.append("## Status")
    lines.append(f"**Digital FTE Online** | Last active: {today_str}")
    lines.append("")
    lines.append("## Active Tasks")
    active = list_files(tasks, 10)
    if active:
        for a in active:
            lines.append(f"- {a}")
    else:
        lines.append("- None — all tasks processed")
    lines.append("")
    lines.append("## Pending Approvals")
    pend = list_files(pending, 10)
    if pend:
        for p in pend:
            lines.append(f"- {p}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append(f"## Completed Today ({today_str})")
    completed_today = [p.stem for p in done.iterdir()] if done.exists() else []
    for c in completed_today:
        lines.append(f"- [x] {c}")
    lines.append("")
    lines.append("## Recent Activity")
    lines.append("| Time | Action | Details |")
    lines.append("|------|--------|---------|")
    for t, a, d in recent_activity():
        lines.append(f"| {t} | {a} | {d} |")
    lines.append("")
    lines.append("## Queue Summary")
    lines.append("| Folder | Count | Status |")
    lines.append("|--------|-------|--------|")
    lines.append(f"| `/Needs_Action` | {count_files(needs_action)} | {'Empty' if count_files(needs_action)==0 else 'Pending'} |")
    lines.append(f"| `/Pending_Approval` | {count_files(pending)} | {'Empty' if count_files(pending)==0 else 'Awaiting sign-off'} |")
    lines.append(f"| `/Approved` | {count_files(approved)} | Records |")
    lines.append(f"| `/Tasks` | {count_files(tasks)} | Active plans |")
    lines.append(f"| `/Done` | {count_files(done)} | Completed |")
    lines.append(f"| `/Rejected` | {count_files(rejected)} | {'Empty' if count_files(rejected)==0 else 'Declined'} |")
    lines.append("")
    lines.append("## Lifetime Stats")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total tasks received | {count_files(needs_action) + count_files(done)} |")
    lines.append(f"| Tasks completed | {count_files(done)} |")
    lines.append(f"| Sensitive actions flagged | {count_files(pending)} |")
    lines.append(f"| Approvals requested | {count_files(pending)} |")
    lines.append(f"| Approvals granted | {count_files(approved)} |")
    lines.append(f"| Approvals rejected | {count_files(rejected)} |")
    lines.append(f"| Completion rate | {'0%' if count_files(needs_action)+count_files(done)==0 else str(int(100*count_files(done)/(count_files(needs_action)+count_files(done)))) + '%'} |")

    (VAULT_PATH / "Dashboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Dashboard updated.")

if __name__ == "__main__":
    write_dashboard()
