import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

VAULT_PATH = Path(__file__).parent.resolve()
WATCHER_PATH = VAULT_PATH / "watcher.py"

def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    logs_dir = VAULT_PATH / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"## {datetime.now().strftime('%H:%M')} - Process Manager\n")
        f.write(f"- {msg}\n")

def main() -> None:
    if not WATCHER_PATH.exists():
        log("ERROR: watcher.py not found")
        sys.exit(1)

    backoff_seconds = 2
    max_backoff = 60

    log("Starting process manager for watcher.py")
    while True:
        try:
            proc = subprocess.Popen(
                [sys.executable, str(WATCHER_PATH)],
                cwd=str(VAULT_PATH),
            )
            ret = proc.wait()
            if ret == 0:
                log("Watcher exited cleanly, restarting")
            else:
                log(f"Watcher exited with code {ret}, restarting")
        except Exception as e:
            log(f"ERROR starting watcher: {e}")

        log(f"Sleeping {backoff_seconds}s before restart")
        time.sleep(backoff_seconds)
        backoff_seconds = min(backoff_seconds * 2, max_backoff)

if __name__ == "__main__":
    main()
