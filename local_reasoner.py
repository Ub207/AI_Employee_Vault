"""
AI Employee Vault — Local Reasoner (Silver Tier)
Fallback processor when Claude CLI is unavailable.
Uses config-driven settings, weighted sensitivity scoring, and SLA tracking.
"""

import re
import os
from datetime import datetime
from pathlib import Path

from config_loader import load_config, get_path, get_sla_deadline, get_priority_from_keywords, log_event
from sensitivity_scorer import score_sensitivity

VAULT = Path(__file__).parent.resolve()


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


def detect_priority(meta: dict, body: str) -> str:
    """Detect priority from frontmatter or keyword auto-detection."""
    cfg = load_config()
    default_prio = cfg.get("priority", {}).get("default", "P2")
    # Check frontmatter first
    fm_prio = meta.get("priority", "")
    if fm_prio.upper().startswith("P") and len(fm_prio) == 2:
        return fm_prio.upper()
    # Auto-detect from keywords
    detected = get_priority_from_keywords(body)
    if detected:
        return detected
    return default_prio


def write_plan(stem: str, summary: str, sensitivity_result: dict, priority: str) -> None:
    tasks_dir = get_path("tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)
    p = tasks_dir / f"plan_{stem}.md"
    lines = [
        f"# Plan: {stem}",
        "",
        "## Summary",
        f"- {summary.strip()}",
        "",
        "## Classification",
        f"- Priority: {priority}",
        f"- Sensitivity Score: {sensitivity_result['score']}",
        f"- Category: {sensitivity_result['category']}",
        f"- Signals: {', '.join(sensitivity_result['signals']) or 'none'}",
        f"- Requires Approval: {'Yes' if sensitivity_result['requires_approval'] else 'No'}",
        "",
        "## Steps",
        "- Draft deliverable",
        "- Route approvals if sensitive",
        "- Save to /Done and update dashboard",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_approval(stem: str, summary: str, sensitivity_result: dict, priority: str) -> None:
    pending_dir = get_path("pending")
    pending_dir.mkdir(parents=True, exist_ok=True)
    p = pending_dir / f"approval_{stem}.md"
    lines = [
        f"# Approval Request: {stem}",
        "",
        "## Why Sensitive",
        f"- Category: {sensitivity_result['category']}",
        f"- Score: {sensitivity_result['score']}",
        f"- Signals: {', '.join(sensitivity_result['signals'])}",
        "",
        f"## Priority: {priority}",
        "",
        "## Proposed Plan",
        "- Draft prepared per plan",
        "- Await manager sign-off before sending/posting",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_done(stem: str, priority: str, sensitivity_result: dict, body: str) -> None:
    done_dir = get_path("done")
    done_dir.mkdir(parents=True, exist_ok=True)
    p = done_dir / f"{stem}.md"
    now = datetime.now()
    sla_deadline = get_sla_deadline(priority, now)
    lines = [
        "---",
        "type: task",
        f"priority: {priority}",
        "status: completed",
        f"created: {now.strftime('%Y-%m-%d')}",
        f"completed_date: {now.strftime('%Y-%m-%d')}",
        f"detected_at: {now.strftime('%Y-%m-%d %H:%M')}",
        f"sla_deadline: {sla_deadline.strftime('%Y-%m-%d %H:%M')}",
        f"sensitivity: {sensitivity_result['category']}",
        f"sensitivity_score: {sensitivity_result['score']}",
        "approval: not_required",
        "---",
        "",
        body.strip() or f"# Completed: {stem}",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def process_task(path: Path) -> None:
    cfg = load_config()
    stem = path.stem
    meta, body = read_frontmatter(path)
    priority = detect_priority(meta, body)
    summary = meta.get("subject", meta.get("title", stem))

    # Use weighted sensitivity scorer
    full_text = f"{summary} {body}"
    sensitivity_result = score_sensitivity(full_text, cfg)

    write_plan(stem, summary, sensitivity_result, priority)

    if sensitivity_result["requires_approval"]:
        write_approval(stem, summary, sensitivity_result, priority)
        log_event("Approval Requested", [
            f"Task: {stem}",
            f"Priority: {priority}",
            f"Sensitivity: {sensitivity_result['category']} (score: {sensitivity_result['score']})",
        ])
    else:
        write_done(stem, priority, sensitivity_result, f"# {summary}\n\nDraft prepared and completed.")
        log_event("Task Completed", [
            f"Task: {stem}",
            f"Priority: {priority}",
            "Routine",
        ])

    # No longer unlinking here safely. 
    # In a real multi-agent scenario, the agent would either move to Done or keep it in In_Progress.
    # For local_reasoner, we assume it's completing the task or requesting approval.
    # If it requested approval, the file technically stays in Needs_Action/In_Progress?
    # Actually, the protocol says remove from Needs_Action. 
    # If it's in In_Progress, we can leave it there as an audit or delete it.
    # Let's delete it if it's done or approval requested, to match existing behavior of "clearing the inbox".
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
    inbox = get_path("inbox")
    in_progress = get_path("in_progress") / "local"
    inbox.mkdir(parents=True, exist_ok=True)
    in_progress.mkdir(parents=True, exist_ok=True)
    
    for md in inbox.glob("*.md"):
        # Claim file
        new_path = in_progress / md.name
        try:
            os.rename(md, new_path)
            process_task(new_path)
        except Exception as e:
            print(f"Error claiming {md.name}: {e}")


if __name__ == "__main__":
    main()
