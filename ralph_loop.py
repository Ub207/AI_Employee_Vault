"""
Ralph Wiggum Loop Orchestrator — Gold Tier
===========================================
Creates the state file that activates the Stop hook and launches Claude Code
with a task prompt. Claude will keep running until the task is moved to /Done.

Usage:
  python ralph_loop.py "task_name.md" "Process this task" --max-iterations 10

Or from Claude Code as a skill:
  /ralph-loop "Process all files in /Needs_Action" --max-iterations 5
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

STATE_FILE = Path("/tmp/ralph_task.json")
VAULT_PATH = Path(__file__).parent.resolve()


def start_ralph_loop(task_file: str, prompt: str, max_iterations: int = 10) -> None:
    """Activate the Ralph Wiggum stop hook and launch Claude Code."""
    state = {
        "task_file": task_file,
        "prompt": prompt,
        "iterations": 0,
        "max_iterations": max_iterations,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"[Ralph Wiggum] Starting loop for '{task_file}' (max {max_iterations} iterations)")
    print(f"[Ralph Wiggum] State file: {STATE_FILE}")
    print(f"[Ralph Wiggum] Launching Claude Code...")

    from dotenv import load_dotenv
    load_dotenv(VAULT_PATH / "Secrets" / ".env")
    llm_cmd = os.getenv("CLAUDE_CMD", "").strip()
    cmd = (llm_cmd.split() + ["-p", prompt]) if llm_cmd else ["claude", "-p", prompt]

    try:
        result = subprocess.run(cmd, cwd=str(VAULT_PATH))
        if result.returncode == 0:
            print("[Ralph Wiggum] Claude exited normally. Check /Done for completed task.")
        else:
            print(f"[Ralph Wiggum] Claude exited with code {result.returncode}")
    except FileNotFoundError:
        print("[Ralph Wiggum] ERROR: 'claude' CLI not found. Is Claude Code installed?")
        sys.exit(1)
    finally:
        # Cleanup state file if it still exists
        STATE_FILE.unlink(missing_ok=True)
        print("[Ralph Wiggum] Loop ended. State file cleaned up.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ralph Wiggum Loop Orchestrator")
    parser.add_argument("task_file", help="Name of the task file (e.g. 'my_task.md')")
    parser.add_argument("prompt", help="Prompt to send to Claude Code")
    parser.add_argument("--max-iterations", type=int, default=10,
                        help="Maximum loop iterations before forced exit (default: 10)")
    args = parser.parse_args()
    start_ralph_loop(args.task_file, args.prompt, args.max_iterations)


if __name__ == "__main__":
    main()
