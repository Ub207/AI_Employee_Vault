import subprocess
import sys
from pathlib import Path
from datetime import datetime

VAULT_PATH = Path(__file__).parent.resolve()

def main():
    procs = []
    scripts = [
        "whatsapp_watcher.py",
        "gmail_watcher.py",
        "social_watcher.py",
        "facebook_watcher.py",
        "twitter_watcher.py",
    ]
    for s in scripts:
        p = subprocess.Popen([sys.executable, str(VAULT_PATH / s)], cwd=str(VAULT_PATH))
        procs.append(p)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Multi-watcher manager online")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
    print("Multi-watcher manager offline")

if __name__ == "__main__":
    main()
