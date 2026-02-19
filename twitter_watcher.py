"""
AI Employee Vault — Twitter/X Watcher
Monitors Channels/Twitter_Inbox for new JSON event files and converts them to
/Needs_Action tasks for the AI Employee to process.

Drop a JSON file like this to simulate an incoming event:
{
  "type": "mention",
  "from": "@johndoe",
  "message": "@mybusiness Can you help me with an order?",
  "tweet_id": "1234567890",
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
INBOX = VAULT_PATH / "Channels" / "Twitter_Inbox"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"


def twitter_event_to_task(json_path: Path) -> Path | None:
    """Convert a Twitter/X event JSON file into a /Needs_Action task."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[Twitter Watcher] Could not parse {json_path.name}: {e}")
        return None

    event_type = data.get("type", "mention")
    sender = data.get("from", "Unknown")
    message = data.get("message", "")
    tweet_id = data.get("tweet_id", "")
    timestamp = data.get("timestamp", datetime.now().isoformat())
    priority = data.get("priority", "P2")

    # Detect urgency keywords
    body_lower = message.lower()
    if any(kw in body_lower for kw in ("urgent", "help", "asap", "broken", "refund")):
        priority = "P1"

    task_name = f"TWITTER_{json_path.stem}"
    task_path = NEEDS_ACTION / f"{task_name}.md"

    tweet_url = f"https://twitter.com/i/web/status/{tweet_id}" if tweet_id else "N/A"

    content = f"""---
type: social_event
source: Twitter/X
event_type: {event_type}
from: {sender}
tweet_id: {tweet_id}
received: {timestamp}
priority: {priority}
status: pending
---

## Twitter/X {event_type.replace('_', ' ').title()} from {sender}

**Tweet URL:** {tweet_url}
**Message:**
> {message}

## Suggested Actions
- [ ] Review and craft a reply (max 280 chars)
- [ ] Route reply for approval (external communication)
- [ ] Like or retweet if appropriate
- [ ] Log to social media engagement report
"""
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content, encoding="utf-8")
    print(f"[Twitter Watcher] Created task: {task_path.name}")
    return task_path


class TwitterInboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".json"):
            return
        twitter_event_to_task(Path(event.src_path))


def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Twitter/X watcher online: {INBOX}")

    # Process existing files
    for json_file in INBOX.glob("*.json"):
        twitter_event_to_task(json_file)

    handler = TwitterInboxHandler()
    observer = Observer()
    observer.schedule(handler, str(INBOX), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    print("Twitter/X watcher offline.")


if __name__ == "__main__":
    main()
