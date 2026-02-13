"""
AI Employee Vault — File Watcher (Silver Tier)
Monitors /Needs_Action for new task files and triggers Claude Code processing.
Features: config-driven, priority queue, SLA tracking, scheduler, approval monitor.
"""

import time
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config_loader import load_config, get_path, get_sla_deadline, log_event
from scheduler import check_due_tasks

# --- Configuration ---
VAULT_PATH = Path(__file__).parent.resolve()


def read_task_priority(filepath: Path) -> str:
    """Extract priority from task frontmatter, default from config."""
    cfg = load_config()
    default_prio = cfg.get("priority", {}).get("default", "P2")
    try:
        text = filepath.read_text(encoding="utf-8")
        if text.startswith("---"):
            fm_block = text.split("\n---", 1)[0].strip("-\n")
            for line in fm_block.splitlines():
                if line.strip().startswith("priority:"):
                    return line.split(":", 1)[1].strip()
        # Check for priority keywords in body
        from config_loader import get_priority_from_keywords
        detected = get_priority_from_keywords(text)
        if detected:
            return detected
    except Exception:
        pass
    return default_prio


def sort_by_priority(files: list[Path]) -> list[Path]:
    """Sort task files by priority (P0 first, P3 last)."""
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    def key_fn(f):
        prio = read_task_priority(f)
        return priority_order.get(prio, 2)
    return sorted(files, key=key_fn)


def check_approval_reminders() -> None:
    """Check pending approvals and log reminders if past SLA reminder threshold."""
    cfg = load_config()
    pending_dir = get_path("pending")
    reminder_hours = cfg.get("sla", {}).get("reminder_after_hours", 2)
    escalation_hours = cfg.get("sla", {}).get("escalation_after_hours", 8)
    now = datetime.now()

    if not pending_dir.exists():
        return

    for f in pending_dir.glob("*.md"):
        try:
            stat = f.stat()
            created = datetime.fromtimestamp(stat.st_ctime)
            hours_waiting = (now - created).total_seconds() / 3600

            if hours_waiting >= escalation_hours:
                log_event("SLA Escalation", [
                    f"Approval: {f.stem}",
                    f"Waiting: {hours_waiting:.1f} hours",
                    "Action: Escalation required",
                ])
            elif hours_waiting >= reminder_hours:
                log_event("SLA Reminder", [
                    f"Approval: {f.stem}",
                    f"Waiting: {hours_waiting:.1f} hours",
                    "Action: Reminder sent",
                ])
        except Exception:
            pass


class TaskHandler(FileSystemEventHandler):
    """Handles new files dropped into /Needs_Action."""

    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        filename = os.path.basename(event.src_path)
        if filename.startswith(".") or filename.startswith("~"):
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        priority = read_task_priority(Path(event.src_path))
        print(f"\n[{timestamp}] New task detected: {filename} [Priority: {priority}]")
        print(f"  Path: {event.src_path}")
        print(f"  Triggering AI Employee...")

        self.process_task(event.src_path, filename)

    def process_task(self, filepath, filename):
        """Trigger Claude Code to process the new task."""
        cfg = load_config()
        retry_cfg = cfg.get("retry", {})
        watcher_cfg = cfg.get("watcher", {})
        task_name = Path(filename).stem
        priority = read_task_priority(Path(filepath))
        detected_at = datetime.now()
        sla_deadline = get_sla_deadline(priority, detected_at)

        prompt = (
            f"A new task has arrived in /Needs_Action: {filename}\n"
            f"Priority: {priority} | SLA Deadline: {sla_deadline.strftime('%Y-%m-%d %H:%M')}\n"
            f"Detected at: {detected_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Read SKILL.md for your processing instructions, then:\n"
            f"1. Read the task at Needs_Action/{filename}\n"
            f"2. Check Company_Handbook.md for sensitivity\n"
            f"3. Create a plan in /Tasks/plan_{task_name}.md\n"
            f"4. If sensitive, create approval request in /Pending_Approval\n"
            f"5. If routine, execute immediately\n"
            f"6. Save result to /Done/{task_name}.md (include priority: {priority} and sla_deadline: {sla_deadline.strftime('%Y-%m-%d %H:%M')} in frontmatter)\n"
            f"7. Log action in /Logs\n"
            f"8. Update Dashboard.md\n"
            f"Process this task now."
        )

        timestamp = datetime.now().strftime("%H:%M:%S")
        log_event("New Task Detected", [
            f"File: {filename}",
            f"Priority: {priority}",
            f"SLA Deadline: {sla_deadline.strftime('%Y-%m-%d %H:%M')}",
            f"Path: {filepath}",
        ])

        attempts = 0
        max_attempts = retry_cfg.get("max_attempts", 3)
        backoff = retry_cfg.get("initial_backoff", 2)
        max_backoff = retry_cfg.get("max_backoff", 60)
        timeout = watcher_cfg.get("timeout", 120)

        while attempts < max_attempts:
            attempts += 1
            try:
                result = subprocess.run(
                    ["claude", "-p", prompt],
                    cwd=str(VAULT_PATH),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                print(f"[{timestamp}] Claude response:")
                print(result.stdout[:500] if result.stdout else "(no output)")
                if result.stderr:
                    print(f"  Errors: {result.stderr[:200]}")
                log_event(
                    "Task Processed",
                    [
                        f"Task: {task_name}",
                        f"Priority: {priority}",
                        f"Attempts: {attempts}",
                        "Result: processed by Claude",
                    ],
                )
                try:
                    subprocess.run([sys.executable, str(VAULT_PATH / "update_dashboard.py")], timeout=30)
                except Exception:
                    pass
                break
            except subprocess.TimeoutExpired:
                print(f"[{timestamp}] Claude timed out processing {filename}")
                log_event("Error: Timeout", [f"Task: {task_name}", f"Attempt: {attempts}"])
            except FileNotFoundError:
                print(f"[{timestamp}] ERROR: 'claude' CLI not found in PATH.")
                print("  Falling back to local reasoner...")
                log_event("Error: Missing Claude CLI", [f"Task: {task_name}"])
                try:
                    subprocess.run([sys.executable, str(VAULT_PATH / "local_reasoner.py")], timeout=60)
                    log_event("Fallback Local Reasoner Executed", [f"Task: {task_name}"])
                except Exception as e:
                    log_event("Error: Local Reasoner Failed", [str(e)])
                break
            except Exception as e:
                print(f"[{timestamp}] ERROR: {e}")
                log_event("Error: Unhandled", [f"Task: {task_name}", f"Exception: {e}"])

            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)


def main():
    cfg = load_config()
    inbox_path = get_path("inbox")
    logs_dir = get_path("logs")
    poll_interval = cfg.get("watcher", {}).get("poll_interval", 1)
    autonomy = cfg.get("autonomy_level", "MEDIUM")

    inbox_path.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  AI Employee Vault — File Watcher")
    print("  Silver Tier | Digital FTE | Hakathone-0")
    print(f"  Autonomy: {autonomy}")
    print("=" * 60)
    print(f"  Vault:    {VAULT_PATH}")
    print(f"  Watching: {inbox_path}")
    print(f"  Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("\nWaiting for new tasks in /Needs_Action ...")
    print("(Drop a .md file to trigger processing)")
    print("Press Ctrl+C to stop.\n")

    handler = TaskHandler()
    observer = Observer()
    observer.schedule(handler, str(inbox_path), recursive=False)
    observer.start()

    log_event("Watcher Started", [
        "Tier: Silver",
        f"Autonomy: {autonomy}",
        f"Poll interval: {poll_interval}s",
    ])

    try:
        # Process existing tasks sorted by priority
        existing = list(inbox_path.glob("*.md"))
        if existing:
            sorted_tasks = sort_by_priority(existing)
            print(f"Found {len(sorted_tasks)} existing task(s), processing by priority...")
            for task_file in sorted_tasks:
                handler.process_task(str(task_file), task_file.name)

        loop_count = 0
        while True:
            time.sleep(poll_interval)
            loop_count += 1

            # Every 60 iterations, run scheduler and approval checks
            if loop_count % 60 == 0:
                try:
                    created = check_due_tasks()
                    if created:
                        print(f"[Scheduler] Created tasks: {', '.join(created)}")
                except Exception as e:
                    log_event("Scheduler Error", [str(e)])

                try:
                    check_approval_reminders()
                except Exception as e:
                    log_event("Approval Monitor Error", [str(e)])

    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()

    observer.join()
    log_event("Watcher Stopped", ["Reason: KeyboardInterrupt"])
    print("Watcher stopped. AI Employee offline.")


if __name__ == "__main__":
    main()
