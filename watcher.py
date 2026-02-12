"""
AI Employee Vault — File Watcher (Bronze Tier)
Monitors /Needs_Action for new task files and triggers Claude Code processing.
Uses Python watchdog library.
"""

import time
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
VAULT_PATH = Path(__file__).parent.resolve()
INBOX_PATH = VAULT_PATH / "Needs_Action"
LOGS_DIR = VAULT_PATH / "Logs"

def log_event(title: str, details: list[str] | None = None) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"## {datetime.now().strftime('%H:%M')} - {title}\n")
        for d in (details or []):
            f.write(f"- {d}\n")

class TaskHandler(FileSystemEventHandler):
    """Handles new files dropped into /Needs_Action."""

    def on_created(self, event):
        # Ignore directories and non-markdown files
        if event.is_directory:
            return
        if not event.src_path.endswith(".md"):
            return
        # Ignore hidden/temp files
        filename = os.path.basename(event.src_path)
        if filename.startswith(".") or filename.startswith("~"):
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] New task detected: {filename}")
        print(f"  Path: {event.src_path}")
        print(f"  Triggering AI Employee...")

        self.process_task(event.src_path, filename)

    def process_task(self, filepath, filename):
        """Trigger Claude Code to process the new task."""
        task_name = Path(filename).stem

        prompt = (
            f"A new task has arrived in /Needs_Action: {filename}\n"
            f"Read SKILL.md for your processing instructions, then:\n"
            f"1. Read the task at Needs_Action/{filename}\n"
            f"2. Check Company_Handbook.md for sensitivity\n"
            f"3. Create a plan in /Tasks/plan_{task_name}.md\n"
            f"4. If sensitive, create approval request in /Pending_Approval\n"
            f"5. If routine, execute immediately\n"
            f"6. Save result to /Done/{task_name}.md\n"
            f"7. Log action in /Logs\n"
            f"8. Update Dashboard.md\n"
            f"Process this task now."
        )

        timestamp = datetime.now().strftime("%H:%M:%S")
        log_event("New Task Detected", [f"File: {filename}", f"Path: {filepath}"])

        attempts = 0
        max_attempts = 3
        backoff = 2
        while attempts < max_attempts:
            attempts += 1
            try:
                result = subprocess.run(
                    ["claude", "-p", prompt],
                    cwd=str(VAULT_PATH),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                print(f"[{timestamp}] Claude response:")
                print(result.stdout[:500] if result.stdout else "(no output)")
                if result.stderr:
                    print(f"  Errors: {result.stderr[:200]}")
                log_event(
                    "Task Processed",
                    [
                        f"Task: {task_name}",
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
                print("  Make sure Claude Code is installed and accessible.")
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
            backoff = min(backoff * 2, 60)


def main():
    # Ensure inbox folder exists
    INBOX_PATH.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print("  AI Employee Vault — File Watcher")
    print("  Bronze Tier | Digital FTE | Hakathone-0")
    print("=" * 55)
    print(f"  Vault:   {VAULT_PATH}")
    print(f"  Watching: {INBOX_PATH}")
    print(f"  Started:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print("\nWaiting for new tasks in /Needs_Action ...")
    print("(Drop a .md file to trigger processing)")
    print("Press Ctrl+C to stop.\n")

    handler = TaskHandler()
    observer = Observer()
    observer.schedule(handler, str(INBOX_PATH), recursive=False)
    observer.start()

    try:
        for existing in INBOX_PATH.glob("*.md"):
            handler.process_task(str(existing), os.path.basename(existing))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()

    observer.join()
    print("Watcher stopped. AI Employee offline.")


if __name__ == "__main__":
    main()
