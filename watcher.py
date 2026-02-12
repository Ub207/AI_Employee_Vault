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
            f"2. Check Compony_Handbook.md for sensitivity\n"
            f"3. Create a plan in /Tasks/plan_{task_name}.md\n"
            f"4. If sensitive, create approval request in /Pending_Approval\n"
            f"5. If routine, execute immediately\n"
            f"6. Save result to /Done/{task_name}.md\n"
            f"7. Log action in /Logs\n"
            f"8. Update Dashboard.md\n"
            f"Process this task now."
        )

        timestamp = datetime.now().strftime("%H:%M:%S")

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
        except subprocess.TimeoutExpired:
            print(f"[{timestamp}] Claude timed out processing {filename}")
        except FileNotFoundError:
            print(f"[{timestamp}] ERROR: 'claude' CLI not found in PATH.")
            print("  Make sure Claude Code is installed and accessible.")
        except Exception as e:
            print(f"[{timestamp}] ERROR: {e}")


def main():
    # Ensure inbox folder exists
    INBOX_PATH.mkdir(parents=True, exist_ok=True)

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
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()

    observer.join()
    print("Watcher stopped. AI Employee offline.")


if __name__ == "__main__":
    main()
