import time
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from channel_event_to_task import event_to_task

VAULT_PATH = Path(__file__).parent.resolve()
INBOX = VAULT_PATH / "Channels" / "Social_Inbox"

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".json"):
            return
        p = Path(event.src_path)
        try:
            event_to_task(p)
        except Exception:
            pass

def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Social watcher online: {INBOX}")
    h = Handler()
    o = Observer()
    o.schedule(h, str(INBOX), recursive=False)
    o.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        o.stop()
    o.join()
    print("Social watcher offline")

if __name__ == "__main__":
    main()
