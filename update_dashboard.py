"""
AI Employee Vault — Dashboard Generator (Silver Tier)
Enhanced with SLA performance, priority distribution, overdue tasks, and system config.
"""

from datetime import datetime
from pathlib import Path

from config_loader import load_config, get_path

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
    logs_dir = get_path("logs")
    today = datetime.now().strftime("%Y-%m-%d")
    file = logs_dir / f"{today}.md"
    rows: list[tuple[str, str, str]] = []
    if file.exists():
        text = file.read_text(encoding="utf-8")
        blocks = [b for b in text.split("\n## ") if b.strip()]
        for b in blocks[-max_rows:]:
            header, *rest = b.splitlines()
            time_title = header.strip().lstrip("# ").strip()
            action = rest[0].strip("- ").strip() if rest else ""
            details = rest[1].strip("- ").strip() if len(rest) > 1 else ""
            rows.append((time_title, action, details))
    return rows


def read_done_metadata() -> list[dict]:
    """Read frontmatter from all completed tasks for SLA/priority analysis."""
    done_dir = get_path("done")
    results = []
    if not done_dir.exists():
        return results
    for f in done_dir.iterdir():
        if not f.is_file() or f.name.startswith(".") or not f.name.endswith(".md"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
            meta = {}
            if text.startswith("---"):
                parts = text.split("\n---", 1)
                fm_block = parts[0].strip("-\n") if len(parts) > 1 else ""
                for line in fm_block.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
            meta["_name"] = f.stem
            results.append(meta)
        except Exception:
            pass
    return results


def get_priority_distribution(tasks: list[dict]) -> dict[str, int]:
    """Count tasks per priority level."""
    dist: dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for t in tasks:
        prio = t.get("priority", "P2").upper()
        if prio in dist:
            dist[prio] += 1
        else:
            dist["P2"] += 1
    return dist


def get_overdue_tasks() -> list[tuple[str, str]]:
    """Find tasks past their SLA deadline in pending/inbox."""
    overdue = []
    now = datetime.now()
    for folder_key in ("inbox", "pending"):
        folder = get_path(folder_key)
        if not folder.exists():
            continue
        for f in folder.iterdir():
            if not f.is_file() or f.name.startswith("."):
                continue
            try:
                text = f.read_text(encoding="utf-8")
                if "sla_deadline:" in text:
                    for line in text.splitlines():
                        if line.strip().startswith("sla_deadline:"):
                            deadline_str = line.split(":", 1)[1].strip()
                            if deadline_str and deadline_str != "auto":
                                deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
                                if now > deadline:
                                    overdue.append((f.stem, deadline_str))
                            break
            except Exception:
                pass
    return overdue


def compute_sla_stats(tasks: list[dict]) -> dict:
    """Compute SLA compliance from completed task metadata."""
    on_time = 0
    total_with_sla = 0
    for t in tasks:
        if "sla_deadline" in t and "detected_at" in t and "completed_date" in t:
            total_with_sla += 1
            # Simplified: if completed_date <= sla_deadline date, it's on time
            try:
                completed = t["completed_date"]
                deadline = t["sla_deadline"]
                if completed <= deadline[:10]:
                    on_time += 1
            except Exception:
                pass
    pct = int(100 * on_time / total_with_sla) if total_with_sla > 0 else 100
    return {"on_time": on_time, "total_with_sla": total_with_sla, "compliance_pct": pct}


def write_dashboard() -> None:
    cfg = load_config()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    needs_action = get_path("inbox")
    pending = get_path("pending")
    approved = get_path("approved")
    tasks = get_path("tasks")
    done = get_path("done")
    rejected = get_path("rejected")

    autonomy = cfg.get("autonomy_level", "MEDIUM")
    done_meta = read_done_metadata()
    prio_dist = get_priority_distribution(done_meta)
    sla_stats = compute_sla_stats(done_meta)
    overdue = get_overdue_tasks()

    lines = []
    lines.append("# AI Employee Dashboard")
    lines.append("")
    lines.append("## Status")
    lines.append(f"**Digital FTE Online** | Silver Tier | Autonomy: {autonomy} | Last active: {today_str}")
    lines.append("")

    # --- Priority Distribution ---
    lines.append("## Priority Distribution")
    max_count = max(prio_dist.values()) if any(prio_dist.values()) else 1
    prio_labels = {"P0": "Critical", "P1": "High", "P2": "Medium", "P3": "Low"}
    for prio in ("P0", "P1", "P2", "P3"):
        count = prio_dist[prio]
        bar_len = int(10 * count / max_count) if max_count > 0 else 0
        bar = "\u2588" * bar_len
        lines.append(f"- {prio} ({prio_labels[prio]}): {bar} {count}")
    lines.append("")

    # --- SLA Performance ---
    lines.append("## SLA Performance")
    lines.append(f"- Compliance: **{sla_stats['compliance_pct']}%** ({sla_stats['on_time']}/{sla_stats['total_with_sla']} on-time)")
    lines.append("")

    # --- Overdue Tasks ---
    lines.append("## Overdue Tasks")
    if overdue:
        for name, deadline in overdue:
            lines.append(f"- **{name}** — deadline was {deadline}")
    else:
        lines.append("- None — all tasks within SLA")
    lines.append("")

    # --- Active Tasks ---
    lines.append("## Active Tasks")
    done_names = {t["_name"] for t in done_meta}
    active = [name for name in list_files(tasks, 20)
              if name.replace("plan_", "", 1) not in done_names]
    if active:
        for a in active:
            lines.append(f"- {a}")
    else:
        lines.append("- None — all tasks processed")
    lines.append("")

    # --- Pending Approvals ---
    lines.append("## Pending Approvals")
    pend = list_files(pending, 10)
    if pend:
        for p in pend:
            lines.append(f"- {p}")
    else:
        lines.append("- None")
    lines.append("")

    # --- Completed Today ---
    lines.append(f"## Completed Today ({today_str})")
    completed_today = [t["_name"] for t in done_meta if t.get("completed_date", "") == today_str]
    if completed_today:
        for c in completed_today:
            lines.append(f"- [x] {c}")
    else:
        lines.append("- None")
    lines.append("")

    # --- Recent Activity ---
    lines.append("## Recent Activity")
    lines.append("| Time | Action | Details |")
    lines.append("|------|--------|---------|")
    for t, a, d in recent_activity():
        lines.append(f"| {t} | {a} | {d} |")
    lines.append("")

    # --- Queue Summary ---
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

    # --- Lifetime Stats ---
    lines.append("## Lifetime Stats")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    total_received = count_files(needs_action) + count_files(done) + count_files(pending)
    done_count = count_files(done)
    sensitive_count = sum(1 for t in done_meta if t.get("sensitivity", "none") not in ("none", ""))
    sensitive_count += count_files(pending)  # currently pending are also sensitive
    approvals_requested = sum(1 for t in done_meta if t.get("approval", "") == "granted") + count_files(pending)
    lines.append(f"| Total tasks received | {total_received} |")
    lines.append(f"| Tasks completed | {done_count} |")
    lines.append(f"| Sensitive actions flagged | {sensitive_count} |")
    lines.append(f"| Approvals requested | {approvals_requested} |")
    lines.append(f"| Approvals granted | {count_files(approved)} |")
    lines.append(f"| Approvals rejected | {count_files(rejected)} |")
    rate = "0%" if total_received == 0 else f"{int(100 * done_count / total_received)}%"
    lines.append(f"| Completion rate | {rate} |")
    lines.append(f"| SLA compliance | {sla_stats['compliance_pct']}% |")
    lines.append("")

    # --- System Config ---
    lines.append("## System Config")
    lines.append("| Setting | Value |")
    lines.append("|---------|-------|")
    lines.append(f"| Tier | Silver |")
    lines.append(f"| Autonomy Level | {autonomy} |")
    prio_cfg = cfg.get("priority", {})
    for p in ("P0", "P1", "P2", "P3"):
        if isinstance(prio_cfg.get(p), dict):
            lines.append(f"| SLA {p} ({prio_cfg[p].get('label', '')}) | {prio_cfg[p].get('sla_hours', '?')}h |")
    lines.append(f"| Default Priority | {prio_cfg.get('default', 'P2')} |")

    (VAULT_PATH / "Dashboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Dashboard updated.")


if __name__ == "__main__":
    write_dashboard()
