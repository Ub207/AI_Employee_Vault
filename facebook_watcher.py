"""
AI Employee Vault — Facebook & Instagram Watcher
Monitors Channels/Facebook_Inbox for new JSON event files and converts them to
/Needs_Action tasks for the AI Employee to process.

Drop a JSON file like this to simulate an incoming event:
{
  "type": "comment",
  "from": "Jane Doe",
  "message": "Love your product! Where can I buy?",
  "page": "My Business Page",
  "timestamp": "2026-02-19T10:00:00Z"
}
"""

import json
import time
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

VAULT_PATH = Path(__file__).parent.resolve()
INBOX = VAULT_PATH / "Channels" / "Facebook_Inbox"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"


def facebook_event_to_task(json_path: Path) -> Path | None:
    """Convert a Facebook/Instagram event JSON file into a /Needs_Action task."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Facebook Watcher] Could not parse {json_path.name}: {e}")
        return None

    event_type = data.get("type", "unknown")
    sender = data.get("from", "Unknown")
    message = data.get("message", "")
    page = data.get("page", "")
    platform = data.get("platform", "facebook").capitalize()
    timestamp = data.get("timestamp", datetime.now().isoformat())
    priority = data.get("priority", "P2")

    # Detect urgency keywords
    body_lower = message.lower()
    if any(kw in body_lower for kw in ("urgent", "critical", "asap", "help")):
        priority = "P1"

    task_name = f"FACEBOOK_{json_path.stem}"
    task_path = NEEDS_ACTION / f"{task_name}.md"

    content = f"""---
type: social_event
source: {platform}
event_type: {event_type}
from: {sender}
page: {page}
received: {timestamp}
priority: {priority}
status: pending
---

## {platform} {event_type.replace('_', ' ').title()} from {sender}

**Page/Account:** {page}
**Message:**
> {message}

## Suggested Actions
- [ ] Review and respond to {event_type}
- [ ] Draft a reply for approval (if external communication)
- [ ] Log engagement metrics
- [ ] Update social media activity report
"""
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content, encoding="utf-8")
    print(f"[Facebook Watcher] Created task: {task_path.name}")
    return task_path


class FacebookInboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".json"):
            return
        facebook_event_to_task(Path(event.src_path))


def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Facebook/Instagram watcher online: {INBOX}")

    # Process existing files
    for json_file in INBOX.glob("*.json"):
        facebook_event_to_task(json_file)

    handler = FacebookInboxHandler()
    observer = Observer()
    observer.schedule(handler, str(INBOX), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    print("Facebook/Instagram watcher offline.")


if __name__ == "__main__":
    main()
