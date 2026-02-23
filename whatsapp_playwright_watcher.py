"""
WhatsApp Playwright Watcher
----------------------------
Pehli baar: Browser khulega, QR code scan karo apne phone se.
Session save ho jaata hai — dobara scan ki zaroorat nahi.

Usage:
    python whatsapp_playwright_watcher.py           # normal run
    python whatsapp_playwright_watcher.py --setup   # QR scan mode (headless=False)
"""

import argparse
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows (handles Urdu/Arabic/emoji in messages)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_PATH    = Path(__file__).parent.resolve()
NEEDS_ACTION  = VAULT_PATH / "Needs_Action"
SESSION_PATH  = VAULT_PATH / ".whatsapp_session"   # browser profile saved here

# Keywords jo urgent messages identify karein
KEYWORDS = [
    "urgent", "asap", "invoice", "payment", "help",
    "price", "quote", "meeting", "call me", "important",
    "order", "refund", "complaint",
]

CHECK_INTERVAL = 30   # seconds between checks
MAX_RETRIES    = 3    # reconnect attempts on crash


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        safe = msg.encode("ascii", errors="replace").decode("ascii")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {safe}", flush=True)


def is_keyword_match(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)


def create_task_file(sender: str, message: str, chat_name: str) -> Path:
    """Create a Needs_Action task file for this WhatsApp message."""
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in chat_name)[:30]
    filepath = NEEDS_ACTION / f"WHATSAPP_{safe_name}_{timestamp}.md"

    content = f"""---
type: whatsapp_message
source: whatsapp
sender: {sender}
chat: {chat_name}
received: {datetime.now().isoformat()}
priority: P1
status: pending
sensitivity_score: 0.3
approval: not_required
---

## WhatsApp Message

**From:** {chat_name} ({sender})
**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Message Content
{message}

## Suggested Actions
- [ ] Review message and determine response
- [ ] Draft reply (requires approval before sending)
- [ ] Log outcome in /Logs/{datetime.now().strftime('%Y-%m-%d')}.md
"""
    with open(filepath, "w", encoding="utf-8", errors="replace", newline="\n") as fh:
        fh.write(content)
    log(f"Task created: {filepath.name}")
    return filepath


# ── Core Watcher ──────────────────────────────────────────────────────────────

class WhatsAppWatcher:
    def __init__(self, headless: bool = True, setup_mode: bool = False):
        self.headless = headless
        self.setup_mode = setup_mode
        self.seen_messages: set[str] = set()
        self.browser = None
        self.page = None

    def start(self, playwright):
        """Launch browser with saved session."""
        SESSION_PATH.mkdir(parents=True, exist_ok=True)
        log(f"Launching browser (headless={self.headless}) ...")

        # WhatsApp Web headless mode block karta hai — always visible run karo
        # Window minimize kar sakte ho taskbar se
        self.browser = playwright.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_PATH),
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-notifications",
            ],
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()

    def dismiss_use_here_dialog(self):
        """Click 'Use Here' if WhatsApp shows 'open in another window' dialog."""
        try:
            result = self.page.evaluate("""
                () => {
                    // Find any button whose text includes 'Use Here' or 'Use here'
                    const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
                    for (const btn of btns) {
                        if (/use here/i.test(btn.textContent)) {
                            btn.click();
                            return 'clicked: ' + btn.textContent.trim().substring(0, 30);
                        }
                    }
                    // Also check for dialog with 'open in another' and click OK/Continue
                    const dialog = document.querySelector('[role="dialog"]');
                    if (dialog && /another/i.test(dialog.textContent)) {
                        const btn = dialog.querySelector('button');
                        if (btn) { btn.click(); return 'dialog_btn: ' + btn.textContent.trim().substring(0,20); }
                    }
                    return null;
                }
            """)
            if result:
                log(f"Dismissed dialog: {result}")
                time.sleep(3)
        except Exception:
            pass

    def wait_for_login(self):
        """Navigate to WhatsApp Web and wait until logged in."""
        log("Opening web.whatsapp.com ...")
        self.page.goto("https://web.whatsapp.com", timeout=60_000)

        # Updated selectors for current WhatsApp Web UI (2025)
        LOGGED_IN_SELECTORS = [
            '#side',
            '#pane-side',
            '[data-testid="chat-list"]',
            'div[aria-label="Chat list"]',
            '[data-testid="chatlist-header"]',
            '[aria-label="Search input textbox"]',
            '[data-testid="search-input"]',
            '[data-testid="default-user"]',
            'div[tabindex="-1"][role="grid"]',
        ]

        def is_logged_in(total_timeout_ms=15_000) -> bool:
            # Divide total timeout evenly across selectors
            per_selector_ms = max(2_000, total_timeout_ms // len(LOGGED_IN_SELECTORS))
            for selector in LOGGED_IN_SELECTORS:
                try:
                    self.page.wait_for_selector(selector, timeout=per_selector_ms)
                    log(f"Logged in detected via: {selector}")
                    return True
                except Exception:
                    continue
            # JS fallback: QR canvas gone aur app loaded
            try:
                result = self.page.evaluate(
                    "() => !!document.getElementById('side') || "
                    "!!document.getElementById('pane-side') || "
                    "(!document.querySelector('canvas[aria-label]') && "
                    " !!document.querySelector('#app > div > div'))"
                )
                if result:
                    log("Logged in detected via JS check")
                    return True
            except Exception:
                pass
            return False

        # Check agar already logged in hai
        if is_logged_in(total_timeout_ms=15_000):
            log("Already logged in!")
            return

        # QR code wait — setup mode ya session expire hone pe
        if not self.setup_mode:
            log("Session expired ya login lost — setup mode mein chalaao:")
            log("  python whatsapp_playwright_watcher.py --setup")
            sys.exit(1)

        log("QR code scan karo apne phone se ...")
        log("Waiting for QR scan (5 minutes) ...")
        if is_logged_in(total_timeout_ms=300_000):
            log("Login successful! Session saved.")
        else:
            log("Login timeout — dobara try karo.")
            sys.exit(1)

    def get_unread_messages(self) -> list[dict]:
        """Chat list se unread messages fetch karo (JS-based, multi-selector fallback)."""
        messages = []
        try:
            result = self.page.evaluate("""
                () => {
                    const debug = [];
                    const msgs = [];

                    // Pane detection — try every known selector for old + new WhatsApp Web
                    const paneSelectors = [
                        '#pane-side',
                        '#side',
                        '[data-testid="chat-list"]',
                        'div[aria-label="Chat list"]',
                        'div[aria-label="Chats"]',
                        '[role="grid"]',
                        '[role="list"]',
                    ];
                    let pane = null;
                    for (const sel of paneSelectors) {
                        pane = document.querySelector(sel);
                        if (pane) { debug.push('PANE:' + sel); break; }
                    }
                    if (!pane) {
                        // Dump #app structure — aria-labels and roles of first 3 levels
                        const app = document.querySelector('#app');
                        const ariaEls = app
                            ? Array.from(app.querySelectorAll('[aria-label]'))
                                  .slice(0, 20)
                                  .map(e => e.tagName + '[' + e.getAttribute('aria-label').substring(0,30) + ']')
                                  .join('|')
                            : 'NO_APP';
                        const roleEls = app
                            ? Array.from(app.querySelectorAll('[role]'))
                                  .slice(0, 20)
                                  .map(e => e.tagName + '[role=' + e.getAttribute('role') + ']')
                                  .join('|')
                            : '';
                        debug.push('NO_PANE. aria=' + ariaEls);
                        debug.push('roles=' + roleEls);
                        return { msgs, debug };
                    }

                    // Try badge selectors in priority order
                    const badgeSelectors = [
                        '[data-testid="icon-unread-count"]',
                        '[data-icon="unread-count"]',
                        'span[aria-label*="unread"]',
                        'div[aria-label*="unread"]',
                    ];

                    let badges = [];
                    for (const sel of badgeSelectors) {
                        const found = pane.querySelectorAll(sel);
                        if (found.length > 0) {
                            badges = Array.from(found);
                            debug.push('BADGE_SEL:' + sel + ' count:' + found.length);
                            break;
                        }
                    }

                    if (badges.length === 0) {
                        // Dump aria-labels and roles inside pane for diagnosis
                        const ariaEls = Array.from(pane.querySelectorAll('[aria-label]'))
                            .slice(0, 20)
                            .map(e => e.tagName + '[' + e.getAttribute('aria-label').substring(0,40) + ']')
                            .join('|');
                        const roleEls = Array.from(pane.querySelectorAll('[role]'))
                            .slice(0, 10)
                            .map(e => e.getAttribute('role'))
                            .join('|');
                        // Also look for any spans with pure number content (unread count)
                        const numSpans = Array.from(pane.querySelectorAll('span'))
                            .filter(s => /^\d+$/.test(s.textContent.trim()))
                            .slice(0, 10)
                            .map(s => 'span[' + s.textContent.trim() + ']class=' + s.className.substring(0,30))
                            .join('|');
                        debug.push('NO_BADGES. aria=' + ariaEls);
                        debug.push('roles=' + roleEls);
                        if (numSpans) debug.push('numspans=' + numSpans);
                        return { msgs, debug };
                    }

                    // Strategy: find all role=row containers, check each for a badge
                    const rows = Array.from(pane.querySelectorAll('[role="row"]'));
                    debug.push('ROWS:' + rows.length);

                    const processedRows = new Set();
                    for (const badge of badges) {
                        // Walk up to find the enclosing row
                        let row = badge;
                        let found = false;
                        for (let i = 0; i < 15; i++) {
                            row = row.parentElement;
                            if (!row) break;
                            if (row.getAttribute('role') === 'row' ||
                                row.getAttribute('role') === 'listitem' ||
                                row.getAttribute('data-testid') === 'cell-frame-container') {
                                found = true;
                                break;
                            }
                        }
                        // Fallback: if no role=row found, go 6 levels up from badge
                        if (!found || !row) {
                            row = badge;
                            for (let i = 0; i < 6; i++) {
                                row = row.parentElement;
                                if (!row) break;
                            }
                        }
                        if (!row || processedRows.has(row)) continue;
                        processedRows.add(row);

                        // Chat name: first span with meaningful text
                        let name = 'Unknown';
                        const allSpans = Array.from(row.querySelectorAll('span'));
                        for (const sp of allSpans) {
                            const t = sp.textContent.trim();
                            // Skip empty, single chars, pure numbers (those are badges)
                            if (t.length > 1 && !/^\d+$/.test(t) && !sp.querySelector('span')) {
                                name = t;
                                break;
                            }
                        }

                        // Last message: second meaningful span
                        let message = '';
                        let nameFound = false;
                        for (const sp of allSpans) {
                            const t = sp.textContent.trim();
                            if (t.length > 1 && !/^\d+$/.test(t) && !sp.querySelector('span')) {
                                if (!nameFound) { nameFound = true; continue; }
                                message = t;
                                break;
                            }
                        }

                        debug.push('CHAT name=' + name.substring(0,20).replace(/[^\x20-\x7E]/g,'?') + ' msg=' + message.substring(0,20).replace(/[^\x20-\x7E]/g,'?'));
                        msgs.push({ name, message });
                    }

                    return { msgs, debug };
                }
            """)

            for d in result.get("debug", []):
                log(f"[DOM] {d}")

            for item in result.get("msgs", []):
                chat_name = item.get("name", "Unknown")
                message   = item.get("message", "")
                key       = f"{chat_name}:{message}"
                if key in self.seen_messages:
                    continue
                messages.append({
                    "chat_name": chat_name,
                    "sender":    chat_name,
                    "message":   message,
                    "key":       key,
                })

        except Exception as e:
            log(f"Error reading chats: {e}")

        return messages

    def wait_for_chat_list(self, timeout_s: int = 60) -> bool:
        """Block until #pane-side (chat list) is visible, or timeout."""
        log("Waiting for chat list pane to load ...")
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            # Dismiss "open in another window" popup each cycle
            self.dismiss_use_here_dialog()
            try:
                found = self.page.evaluate(
                    "() => !!(document.querySelector('#pane-side') || "
                    "document.querySelector('#side') || "
                    "document.querySelector('div[aria-label=\"Chat list\"]'))"
                )
                if found:
                    log("Chat list pane ready.")
                    return True
            except Exception:
                pass
            time.sleep(2)
        log("Chat list pane not found after timeout — proceeding anyway.")
        return False

    def run_loop(self):
        """Main polling loop."""
        log(f"WhatsApp Watcher active — checking every {CHECK_INTERVAL}s")
        self.wait_for_chat_list(timeout_s=60)

        while True:
            try:
                # Page alive check
                if self.page.is_closed():
                    log("Page closed — reconnecting ...")
                    self.wait_for_login()

                messages = self.get_unread_messages()

                for msg in messages:
                    try:
                        create_task_file(
                            sender=msg["sender"],
                            message=msg["message"],
                            chat_name=msg["chat_name"],
                        )
                        self.seen_messages.add(msg["key"])
                    except Exception as me:
                        log(f"Task create error: {me}")

                if not messages:
                    log("No new unread messages.")

            except Exception as e:
                log(f"Loop error: {e}")

            time.sleep(CHECK_INTERVAL)

    def close(self):
        if self.browser:
            self.browser.close()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WhatsApp Playwright Watcher")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Pehli baar QR scan ke liye visible browser open karo",
    )
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    retries = 0
    while retries < MAX_RETRIES:
        watcher = WhatsAppWatcher(headless=False, setup_mode=args.setup)
        try:
            with sync_playwright() as p:
                watcher.start(p)
                watcher.wait_for_login()

                if args.setup:
                    log("Setup complete! Session saved.")
                    log("Ab normal mode mein chalaao: python whatsapp_playwright_watcher.py")
                    watcher.close()
                    return

                watcher.run_loop()

        except KeyboardInterrupt:
            log("Watcher stopped by user.")
            watcher.close()
            return

        except Exception as e:
            log(f"Crash: {e}")
            retries += 1
            if retries < MAX_RETRIES:
                log(f"Restarting in 10s ... (attempt {retries}/{MAX_RETRIES})")
                time.sleep(10)
            else:
                log("Max retries reached. Watcher stopped.")
                watcher.close()
                sys.exit(1)


if __name__ == "__main__":
    main()
