"""
WhatsApp Playwright Watcher — extends BaseWatcher
--------------------------------------------------
Pehli baar: Browser khulega, QR code scan karo apne phone se.
Session save ho jaata hai — dobara scan ki zaroorat nahi.

Usage:
    python whatsapp_playwright_watcher.py           # normal run
    python whatsapp_playwright_watcher.py --setup   # QR scan mode

BaseWatcher mapping:
    run()               → sync_playwright() context wrap karta hai, phir super().run()
    connect()           → _launch_browser() + wait_for_login()
    disconnect()        → browser close
    before_loop()       → wait_for_chat_list()
    check_new_events()  → page-alive + pane recovery + _get_unread_messages()
                          + blacklist/group filtering + check_outbox()
    process_event()     → _create_task_file()
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from base_watcher import BaseWatcher
from config_loader import load_config, log_event

# ── Constants ─────────────────────────────────────────────────────────────────

VAULT_PATH   = Path(__file__).parent.resolve()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
SESSION_PATH = VAULT_PATH / ".whatsapp_session"
OUTBOX       = VAULT_PATH / "Outbox" / "WhatsApp"
OUTBOX_SENT  = VAULT_PATH / "Outbox" / "WhatsApp_Sent"

KEYWORDS = [
    "urgent", "asap", "invoice", "payment", "help",
    "price", "quote", "meeting", "call me", "important",
    "order", "refund", "complaint",
]

GROUP_NAME_KEYWORDS = [
    "Group", "Grp", "Team", "Community", "Channel",
    "Discussion", "Slot", "Batch", "Class", "Squad",
    "Members", "Family", "Friends",
]

# ── Module-level helpers ───────────────────────────────────────────────────────

def ensure_single_instance() -> None:
    """Allow only one watcher instance using a Windows named mutex (atomic)."""
    import ctypes
    MUTEX_NAME = "Global\\AIEmployeeWhatsAppWatcher"
    ERROR_ALREADY_EXISTS = 183
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    err = ctypes.windll.kernel32.GetLastError()
    if err == ERROR_ALREADY_EXISTS:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Another WhatsApp watcher is already running. Exiting.")
        sys.exit(0)
    ensure_single_instance._mutex = mutex  # keep handle alive for process lifetime


def load_whatsapp_config() -> dict:
    """config.yaml se WhatsApp channel settings load karo."""
    try:
        cfg = load_config()
        return cfg.get("channels", {}).get("whatsapp", {})
    except Exception:
        return {}


def should_process_group(chat_name: str, message: str) -> tuple[bool, str]:
    """
    Decide karo ke group message process karein ya nahi.
    Returns (process: bool, reason: str)
    """
    wa_cfg       = load_whatsapp_config()
    group_mode   = wa_cfg.get("group_mode", "mention_only")
    my_name      = wa_cfg.get("my_name", "")
    aliases      = wa_cfg.get("my_name_aliases", [])
    trigger_kws  = wa_cfg.get("group_trigger_keywords", [])
    blacklist    = wa_cfg.get("group_blacklist", [])

    chat_upper = chat_name.upper()
    for bl in blacklist:
        if bl.upper() in chat_upper:
            return False, f"blacklisted ({bl})"

    if group_mode == "disabled":
        return False, "group_mode=disabled"
    if group_mode == "all":
        return True, "group_mode=all"

    # mention_only (default)
    msg_lower = message.lower()
    for name in [my_name] + aliases:
        if name.lower() in msg_lower:
            return True, f"mentioned ({name})"
    for kw in trigger_kws:
        if kw.lower() in msg_lower:
            return True, f"trigger keyword ({kw})"

    return False, "group: no mention/trigger"


# ── Core Watcher ──────────────────────────────────────────────────────────────

class WhatsAppWatcher(BaseWatcher):
    check_interval = 30       # seconds between polls
    watcher_name   = "WhatsAppWatcher"

    def __init__(self, setup_mode: bool = False):
        super().__init__()
        self.setup_mode       = setup_mode
        self.browser          = None
        self.page             = None
        self.seen_messages:   set[str] = set()
        self._playwright      = None   # set by run() before connect() is called
        self._no_pane_streak  = 0      # consecutive cycles where chat pane was missing

    # ── run() override ────────────────────────────────────────────────────────

    def run(self, max_restarts: int = 3) -> None:
        """
        Wrap BaseWatcher.run() inside sync_playwright() so the Playwright
        instance stays alive across reconnects inside the retry loop.
        """
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            self._playwright = p
            super().run(max_restarts=max_restarts)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Launch browser with saved session and wait for WhatsApp login."""
        self._launch_browser()
        self.wait_for_login()

        if self.setup_mode:
            self.log("Setup complete! Session saved.")
            self.log("Ab normal mode mein chalaao: python whatsapp_playwright_watcher.py")
            # Signal run_loop() to exit cleanly without entering the poll loop
            self.running = False

    def disconnect(self) -> None:
        """Close the Playwright browser context."""
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
            self.page    = None
            self.log("Browser closed.")

    def before_loop(self) -> None:
        """Called once after connect() — wait for chat list pane to be ready."""
        if self.setup_mode:
            return
        self.log(f"WhatsApp Watcher active — checking every {self.check_interval}s")
        self.log(f"Outbox: {OUTBOX}")
        self.wait_for_chat_list(timeout_s=60)
        self._no_pane_streak = 0

    # ── BaseWatcher interface ─────────────────────────────────────────────────

    def check_new_events(self) -> list[dict]:
        """
        One full poll cycle:
          1. Page-alive check → reconnect if page was closed
          2. Pane recovery   → dismiss "Use Here" dialog if chat list disappeared
          3. Fetch unread messages from DOM
          4. Blacklist + group-mode filtering
          5. check_outbox()  → send any pending outgoing replies
        Returns only messages that passed all filters.
        """

        # ── 1. Page alive ────────────────────────────────────────────────────
        if self.page.is_closed():
            self.log("Page closed — reconnecting ...")
            self.wait_for_login()
            self._no_pane_streak = 0

        # ── 2. Pane recovery ─────────────────────────────────────────────────
        try:
            pane_visible = self.page.evaluate(
                "() => !!(document.querySelector('#pane-side') || "
                "document.querySelector('#side') || "
                "document.querySelector('[data-testid=\"chat-list\"]'))"
            )
        except Exception:
            pane_visible = False

        if not pane_visible:
            self._no_pane_streak += 1
            if self._no_pane_streak >= 2:
                self.log("Chat pane not visible — reclaiming session ...")
                self.dismiss_use_here_dialog()
                self.wait_for_chat_list(timeout_s=30)
                self._no_pane_streak = 0
        else:
            self._no_pane_streak = 0

        # ── 3. Fetch raw unread messages from DOM ─────────────────────────────
        raw = self._get_unread_messages()

        # ── 4. Blacklist + group-mode filtering ───────────────────────────────
        wa_cfg    = load_whatsapp_config()
        blacklist = wa_cfg.get("group_blacklist", [])
        processable: list[dict] = []

        for msg in raw:
            chat_name = msg["chat_name"]
            key       = msg["key"]

            # Blacklist check applies to ALL chats (group JS detection can fail)
            self.log(f"Checking blacklist for: '{chat_name[:40]}' (len={len(chat_name)})")
            chat_upper  = chat_name.upper()
            blacklisted = False
            for bl in blacklist:
                if bl.upper() in chat_upper:
                    self.log(f"BLACKLISTED [{chat_name[:30]}]: matched '{bl}'")
                    blacklisted = True
                    break

            if blacklisted:
                self.seen_messages.add(key)
                continue

            # Name-based group heuristics (JS detection can miss some)
            is_group = msg.get("is_group", False)
            if not is_group:
                is_group = any(kw.lower() in chat_name.lower() for kw in GROUP_NAME_KEYWORDS)
            msg["is_group"] = is_group

            if is_group:
                process, reason = should_process_group(chat_name, msg["message"])
                if not process:
                    self.log(f"Group SKIPPED [{chat_name[:25]}]: {reason}")
                    self.seen_messages.add(key)
                    continue
                self.log(f"Group PROCESSING [{chat_name[:25]}]: {reason}")

            processable.append(msg)

        if not raw:
            self.log("No new unread messages.")

        # ── 5. Outbox: send pending replies ───────────────────────────────────
        self.check_outbox()

        return processable

    def process_event(self, event: dict) -> None:
        """Create a Needs_Action task file and mark message as seen."""
        self._create_task_file(
            sender    = event["sender"],
            message   = event["message"],
            chat_name = event["chat_name"],
            is_group  = event.get("is_group", False),
        )
        self.seen_messages.add(event["key"])

    # ── Browser / login ───────────────────────────────────────────────────────

    def _launch_browser(self) -> None:
        """Launch Chromium with a persistent session profile."""
        SESSION_PATH.mkdir(parents=True, exist_ok=True)

        # Remove stale Chrome lock files left behind by crashes
        for lock_file in [
            SESSION_PATH / "Default" / "LOCK",
            SESSION_PATH / "SingletonLock",
            SESSION_PATH / "SingletonCookie",
        ]:
            if lock_file.exists():
                try:
                    lock_file.unlink()
                    self.log(f"Removed stale lock: {lock_file.name}")
                except Exception as ex:
                    self.log(f"Could not remove lock {lock_file.name}: {ex}")

        self.log("Launching browser ...")
        # WhatsApp Web blocks headless mode — always run visible
        self.browser = self._playwright.chromium.launch_persistent_context(
            user_data_dir   = str(SESSION_PATH),
            headless        = False,
            args            = [
                "--no-sandbox",
                "--disable-notifications",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args = ["--enable-automation"],
        )
        self.page = self.browser.pages[0] if self.browser.pages else self.browser.new_page()
        try:
            self.browser.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception:
            pass

    def wait_for_login(self) -> None:
        """Navigate to WhatsApp Web and block until logged in."""
        self.log("Opening web.whatsapp.com ...")
        self.page.goto("https://web.whatsapp.com", timeout=60_000)

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

        def is_logged_in(total_timeout_ms: int = 15_000) -> bool:
            end_time = time.time() + total_timeout_ms / 1000
            while time.time() < end_time:
                for selector in LOGGED_IN_SELECTORS:
                    try:
                        if self.page.query_selector(selector):
                            self.log(f"Logged in detected via: {selector}")
                            return True
                    except Exception:
                        continue
                try:
                    if self.page.evaluate(
                        "() => !!document.getElementById('side') || "
                        "!!document.getElementById('pane-side') || "
                        "(!document.querySelector('canvas[aria-label]') && "
                        " document.querySelector('[data-testid]') !== null && "
                        " !!document.querySelector('#app > div > div'))"
                    ):
                        self.log("Logged in detected via JS check")
                        return True
                except Exception:
                    pass
                time.sleep(2)
            return False

        self.log("Checking login status (up to 120s) ...")
        if is_logged_in(total_timeout_ms=120_000):
            self.log("Already logged in!")
            return

        # Session expired or first run — auto-switch to QR mode
        if not self.setup_mode:
            self.log("Login nahi mila — QR scan mode mein switch ho raha hai ...")
            self.log("  python whatsapp_playwright_watcher.py --setup")
            self.setup_mode = True

        self.log("QR code scan karo apne phone se ...")
        self.log("Waiting for QR scan (5 minutes) ...")
        if is_logged_in(total_timeout_ms=300_000):
            self.log("Login successful! Session saved.")
        else:
            self.log("Login timeout — dobara try karo.")
            raise RuntimeError("QR scan timeout — please restart and scan again.")

    # ── DOM helpers ───────────────────────────────────────────────────────────

    def dismiss_use_here_dialog(self) -> None:
        """Click 'Use Here' if WhatsApp shows the 'open in another window' dialog."""
        try:
            result = self.page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
                    for (const btn of btns) {
                        if (/use here/i.test(btn.textContent)) {
                            btn.click();
                            return 'clicked: ' + btn.textContent.trim().substring(0, 30);
                        }
                    }
                    const dialog = document.querySelector('[role="dialog"]');
                    if (dialog && /another/i.test(dialog.textContent)) {
                        const btn = dialog.querySelector('button');
                        if (btn) { btn.click(); return 'dialog_btn: ' + btn.textContent.trim().substring(0,20); }
                    }
                    return null;
                }
            """)
            if result:
                self.log(f"Dismissed dialog: {result}")
                time.sleep(3)
        except Exception:
            pass

    def wait_for_chat_list(self, timeout_s: int = 60) -> bool:
        """Block until the chat list pane is visible, or timeout."""
        self.log("Waiting for chat list pane to load ...")
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            self.dismiss_use_here_dialog()
            try:
                if self.page.evaluate(
                    "() => !!(document.querySelector('#pane-side') || "
                    "document.querySelector('#side') || "
                    "document.querySelector('div[aria-label=\"Chat list\"]'))"
                ):
                    self.log("Chat list pane ready.")
                    return True
            except Exception:
                pass
            time.sleep(2)
        self.log("Chat list pane not found after timeout — proceeding anyway.")
        return False

    def _get_unread_messages(self) -> list[dict]:
        """Fetch unread chats from the DOM (JS-based, multi-selector fallback)."""
        messages: list[dict] = []
        try:
            result = self.page.evaluate("""
                () => {
                    const debug = [];
                    const msgs  = [];

                    const paneSelectors = [
                        '#pane-side', '#side',
                        '[data-testid="chat-list"]',
                        'div[aria-label="Chat list"]',
                        'div[aria-label="Chats"]',
                        '[role="grid"]', '[role="list"]',
                    ];
                    let pane = null;
                    for (const sel of paneSelectors) {
                        pane = document.querySelector(sel);
                        if (pane) { debug.push('PANE:' + sel); break; }
                    }
                    if (!pane) {
                        const app = document.querySelector('#app');
                        const ariaEls = app
                            ? Array.from(app.querySelectorAll('[aria-label]'))
                                  .slice(0,20)
                                  .map(e => e.tagName+'['+e.getAttribute('aria-label').substring(0,30)+']')
                                  .join('|')
                            : 'NO_APP';
                        const roleEls = app
                            ? Array.from(app.querySelectorAll('[role]'))
                                  .slice(0,20)
                                  .map(e => e.tagName+'[role='+e.getAttribute('role')+']')
                                  .join('|')
                            : '';
                        debug.push('NO_PANE. aria=' + ariaEls);
                        debug.push('roles=' + roleEls);
                        return { msgs, debug };
                    }

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
                        const ariaEls = Array.from(pane.querySelectorAll('[aria-label]'))
                            .slice(0,20)
                            .map(e => e.tagName+'['+e.getAttribute('aria-label').substring(0,40)+']')
                            .join('|');
                        const roleEls = Array.from(pane.querySelectorAll('[role]'))
                            .slice(0,10).map(e => e.getAttribute('role')).join('|');
                        const numSpans = Array.from(pane.querySelectorAll('span'))
                            .filter(s => /^\d+$/.test(s.textContent.trim()))
                            .slice(0,10)
                            .map(s => 'span['+s.textContent.trim()+']class='+s.className.substring(0,30))
                            .join('|');
                        debug.push('NO_BADGES. aria=' + ariaEls);
                        debug.push('roles=' + roleEls);
                        if (numSpans) debug.push('numspans=' + numSpans);
                        return { msgs, debug };
                    }

                    const processedRows = new Set();
                    for (const badge of badges) {
                        let row   = badge;
                        let found = false;
                        for (let i = 0; i < 15; i++) {
                            row = row.parentElement;
                            if (!row) break;
                            if (row.getAttribute('role') === 'row' ||
                                row.getAttribute('role') === 'listitem' ||
                                row.getAttribute('data-testid') === 'cell-frame-container') {
                                found = true; break;
                            }
                        }
                        if (!found || !row) {
                            row = badge;
                            for (let i = 0; i < 6; i++) { row = row.parentElement; if (!row) break; }
                        }
                        if (!row || processedRows.has(row)) continue;
                        processedRows.add(row);

                        let name = 'Unknown';
                        const allSpans = Array.from(row.querySelectorAll('span'));
                        for (const sp of allSpans) {
                            const t = sp.textContent.trim();
                            if (t.length > 1 && !/^\d+$/.test(t) && !sp.querySelector('span')) {
                                name = t; break;
                            }
                        }

                        let message  = '';
                        let nameFound = false;
                        for (const sp of allSpans) {
                            const t = sp.textContent.trim();
                            if (t.length > 1 && !/^\d+$/.test(t) && !sp.querySelector('span')) {
                                if (!nameFound) { nameFound = true; continue; }
                                message = t; break;
                            }
                        }

                        const groupIcon    = row.querySelector('[data-icon="group"],[data-icon="groups"],[data-icon="community"]');
                        const hasGroupPrefix = /^[^:]{1,40}:\s.+/.test(message) && message.includes(':');
                        const ariaLabel    = row.getAttribute('aria-label') || '';
                        const isGroupByAria = /group/i.test(ariaLabel);
                        const isGroup      = !!(groupIcon || isGroupByAria || hasGroupPrefix);

                        debug.push('CHAT name=' + name.substring(0,20).replace(/[^\x20-\x7E]/g,'?')
                            + ' msg=' + message.substring(0,20).replace(/[^\x20-\x7E]/g,'?')
                            + ' group=' + isGroup);
                        msgs.push({ name, message, isGroup });
                    }

                    return { msgs, debug };
                }
            """)

            for d in result.get("debug", []):
                self.log(f"[DOM] {d}")

            for item in result.get("msgs", []):
                chat_name = item.get("name",    "Unknown")
                message   = item.get("message", "")
                key       = f"{chat_name}:{message}"
                if key in self.seen_messages:
                    continue
                messages.append({
                    "chat_name": chat_name,
                    "sender":    chat_name,
                    "message":   message,
                    "is_group":  item.get("isGroup", False),
                    "key":       key,
                })

        except Exception as e:
            self.log(f"Error reading chats: {e}")

        return messages

    # ── Task file creation ────────────────────────────────────────────────────

    def _create_task_file(
        self, sender: str, message: str, chat_name: str, is_group: bool = False
    ) -> Path:
        """Write a Needs_Action task file for this WhatsApp message."""
        NEEDS_ACTION.mkdir(parents=True, exist_ok=True)

        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name  = "".join(c if c.isalnum() else "_" for c in chat_name)[:30]
        prefix     = "WHATSAPP_GROUP" if is_group else "WHATSAPP"
        filepath   = NEEDS_ACTION / f"{prefix}_{safe_name}_{timestamp}.md"
        chat_type  = "group" if is_group else "individual"
        reply_note = (
            "- [ ] Group message — reply sirf agar relevant ho\n"
            "- [ ] Individual message ha ya mention — reply draft karo\n"
            if is_group else
            "- [ ] Draft reply and write to Outbox/WhatsApp/<task>.json\n"
            "- [ ] Individual DM — reply zaroor karo\n"
        )

        content = (
            f"---\n"
            f"type: whatsapp_message\n"
            f"source: whatsapp\n"
            f"chat_type: {chat_type}\n"
            f"sender: {sender}\n"
            f"chat: {chat_name}\n"
            f"received: {datetime.now().isoformat()}\n"
            f"priority: {'P2' if is_group else 'P1'}\n"
            f"status: pending\n"
            f"sensitivity_score: {'0.2' if is_group else '0.3'}\n"
            f"approval: not_required\n"
            f"---\n\n"
            f"## WhatsApp {'Group' if is_group else 'Direct'} Message\n\n"
            f"**From:** {chat_name} ({sender})\n"
            f"**Type:** {'Group Chat' if is_group else 'Individual DM'}\n"
            f"**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"### Message Content\n{message}\n\n"
            f"## Suggested Actions\n"
            f"{reply_note}"
            f"- [ ] Log outcome in /Logs/{datetime.now().strftime('%Y-%m-%d')}.md\n"
        )
        with open(filepath, "w", encoding="utf-8", errors="replace", newline="\n") as fh:
            fh.write(content)
        self.log(f"Task created: {filepath.name}")
        log_event("WhatsAppWatcher Task Created", [
            f"Chat: {chat_name}",
            f"Type: {chat_type}",
            f"File: {filepath.name}",
        ])
        return filepath

    # ── Outbox: send pending replies ──────────────────────────────────────────

    def send_reply(self, chat_name: str, message: str) -> bool:
        """Send a message to a WhatsApp chat (search → click → type → Enter)."""
        try:
            self.log(f"Sending reply to: {chat_name}")

            # Step 1: Search box
            search_selectors = [
                '[data-testid="search-input"]',
                '[aria-label="Search input textbox"]',
                'div[contenteditable="true"][data-tab="3"]',
            ]
            search_box = None
            for sel in search_selectors:
                try:
                    self.page.wait_for_selector(sel, timeout=5_000)
                    search_box = self.page.query_selector(sel)
                    if search_box:
                        break
                except Exception:
                    continue

            if not search_box:
                self.log("ERROR: Search box nahi mila — reply nahi bheji ja saki")
                return False

            search_box.click()
            time.sleep(0.5)
            search_box.fill("")
            search_box.type(chat_name, delay=60)
            time.sleep(2)

            # Step 2: First search result
            result_selectors = [
                '[data-testid="cell-frame-container"]',
                '[role="row"]',
                '[data-testid="list-item-title"]',
            ]
            chat_row = None
            for sel in result_selectors:
                chat_row = self.page.query_selector(sel)
                if chat_row:
                    break

            if not chat_row:
                self.log(f"ERROR: Chat '{chat_name}' search results mein nahi mila")
                try:
                    self.page.keyboard.press("Escape")
                except Exception:
                    pass
                return False

            chat_row.click()
            time.sleep(1)

            # Step 3: Compose box
            compose_selectors = [
                '[data-testid="conversation-compose-box-input"]',
                'div[contenteditable="true"][data-tab="10"]',
                'div[contenteditable="true"][title="Type a message"]',
                '[aria-label="Type a message"]',
                'div[contenteditable="true"][spellcheck="true"]',
            ]
            compose_box = None
            for sel in compose_selectors:
                try:
                    self.page.wait_for_selector(sel, timeout=5_000)
                    compose_box = self.page.query_selector(sel)
                    if compose_box:
                        break
                except Exception:
                    continue

            if not compose_box:
                self.log("ERROR: Message input box nahi mila")
                return False

            compose_box.click()
            time.sleep(0.3)
            compose_box.type(message, delay=30)
            time.sleep(0.5)
            self.page.keyboard.press("Enter")
            time.sleep(1)

            self.log(f"Reply sent to '{chat_name}': {message[:60]}...")
            return True

        except Exception as e:
            self.log(f"send_reply error: {e}")
            return False

    def check_outbox(self) -> None:
        """Process pending outgoing replies from Outbox/WhatsApp/."""
        OUTBOX.mkdir(parents=True, exist_ok=True)
        OUTBOX_SENT.mkdir(parents=True, exist_ok=True)

        pending = list(OUTBOX.glob("*.json"))
        if not pending:
            return

        self.log(f"Outbox: {len(pending)} pending reply(ies) found")
        for outfile in pending:
            try:
                data      = json.loads(outfile.read_text(encoding="utf-8"))
                chat_name = data.get("chat_name", "").strip()
                message   = data.get("message",   "").strip()
                task_ref  = data.get("task_ref",   outfile.stem)

                if not chat_name or not message:
                    self.log(f"Outbox file invalid (missing chat_name or message): {outfile.name}")
                    outfile.rename(OUTBOX_SENT / f"INVALID_{outfile.name}")
                    continue

                success = self.send_reply(chat_name, message)

                log_path = VAULT_PATH / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
                try:
                    with open(log_path, "a", encoding="utf-8") as lf:
                        status = "SENT" if success else "FAILED"
                        lf.write(
                            f"\n## {datetime.now().strftime('%H:%M')} - WhatsApp Reply {status}\n"
                            f"- Chat: {chat_name}\n"
                            f"- Task: {task_ref}\n"
                            f"- Message: {message[:100]}\n"
                        )
                except Exception:
                    pass

                dest_name = f"{'SENT' if success else 'FAILED'}_{outfile.name}"
                outfile.rename(OUTBOX_SENT / dest_name)

            except Exception as e:
                self.log(f"Outbox processing error ({outfile.name}): {e}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="WhatsApp Playwright Watcher")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Pehli baar QR scan ke liye visible browser open karo",
    )
    args = parser.parse_args()

    # Single-instance guard (skip in --setup mode so QR scan can run alongside)
    if not args.setup:
        ensure_single_instance()

    WhatsAppWatcher(setup_mode=args.setup).run()


if __name__ == "__main__":
    main()
