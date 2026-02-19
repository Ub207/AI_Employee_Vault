# Demo Video Script — AI Employee Vault (Digital FTE)
**Hackathon-0: Building Autonomous FTEs in 2026**
**Target length: 7–9 minutes | Tier: Platinum**

---

## PRE-RECORDING CHECKLIST

Before hitting record:
- [ ] Obsidian vault open and visible
- [ ] Terminal open at `/AI_Employee_Vault`
- [ ] VS Code or file explorer open for code walkthroughs
- [ ] GitHub repo open in browser: `github.com/Ub207/AI_Employee_Vault`
- [ ] `Dashboard.md` visible in Obsidian
- [ ] `/Needs_Action` folder empty (clean slate)
- [ ] Font size bumped up (terminal 16pt, Obsidian 18pt)
- [ ] Notifications OFF

---

## SECTION 1 — HOOK (0:00 – 0:45)

**[Screen: Black screen with text overlay]**

> *"A human employee works 2,000 hours a year. This one works 8,760."*

**[Cut to: Dashboard.md open in Obsidian — live system view]**

**NARRATION:**
> "This is the AI Employee Vault — a fully autonomous Digital FTE built for Hackathon-0.
> It doesn't wait for you to type. It watches your Gmail, WhatsApp, LinkedIn, Facebook,
> Instagram, Twitter, and Odoo accounting — and it works while you sleep.
> Let me show you how it works."

---

## SECTION 2 — THE CONCEPT (0:45 – 1:30)

**[Screen: README.md on GitHub — badges visible]**

**NARRATION:**
> "This project hits all four tiers of the hackathon — Bronze, Silver, Gold, and Platinum.
> It's built on three principles:
> local-first, approval-first, and agent-first."

**[Point to the table in README]**

> "A human FTE costs $5 per task and works 2,000 hours a year.
> This Digital FTE costs 50 cents per task and runs 8,760 hours a year.
> That's an 85% cost reduction — the number that gets a CEO's attention."

**[Screen: Architecture ASCII diagram from README]**

> "The architecture is: Watchers as senses, Obsidian as the brain's memory,
> Claude Code as the reasoning engine, and MCP servers as the hands."

---

## SECTION 3 — THE VAULT TOUR (1:30 – 2:30)

**[Screen: Obsidian vault — left sidebar showing folder structure]**

**NARRATION:**
> "Every file in this vault has a job."

**[Click through each folder briefly:]**

- `/Needs_Action` — *"This is the inbox. Drop anything here — the AI picks it up."*
- `/Tasks` — *"Before acting, the AI always writes a plan here first."*
- `/Pending_Approval` — *"Sensitive actions stop here. Nothing fires without your sign-off."*
- `/Approved` — *"You move a file here to say go."*
- `/Done` — *"12 completed tasks, each with full SLA metadata."*
- `/Logs` — *"Every action timestamped. Full audit trail."*
- `config.yaml` — *"One file controls everything — autonomy level, SLA windows, sensitivity thresholds."*
- `SKILL.md` — *"This is the AI's operating manual — its job description."*
- `Company_Handbook.md` — *"The rules. The AI reads this before every action."*

---

## SECTION 4 — LIVE DEMO: BRONZE/SILVER — FILE DROP (2:30 – 3:45)

**[Screen: Split — terminal on left, Obsidian on right]**

**NARRATION:**
> "Let's start the watcher and drop a task."

**[Terminal — type and run:]**
```bash
python watcher.py
```

> "The watcher is now watching `/Needs_Action` for new files."

**[Create a new file in `/Needs_Action/` — use Obsidian or terminal:]**

```bash
# Create a test task
cat > Needs_Action/client_invoice_request.md << 'EOF'
---
priority: P1
---

Client A just messaged asking for their January invoice.
Amount: $1,500. Send to client_a@email.com ASAP.
EOF
```

**[Watch the terminal react immediately:]**

> "The watcher detects it instantly. Classifies priority — P1, High, 4-hour SLA.
> Scores sensitivity — invoice + email + client = 0.9. That's sensitive.
> Claude creates a plan..."

**[Switch to Obsidian — show `/Tasks/plan_client_invoice_request.md` appear]**

> "There's the plan. And because it's sensitive..."

**[Show `/Pending_Approval/` — approval file appears]**

> "...it stops here and waits for me.
> The AI does not send the email. It never will, until I say so."

**[Move the approval file to `/Approved/`]**

> "I approve it — just move the file. The AI continues, executes, and..."

**[Show `/Done/client_invoice_request.md` — open it]**

> "Done. SLA met. Full metadata. Logged."

**[Flash to `/Logs/` — show the entry]**

> "And the audit trail is right here."

---

## SECTION 5 — LIVE DEMO: SILVER — MULTI-CHANNEL WATCHERS (3:45 – 4:30)

**[Screen: Terminal — run multi-watcher manager]**

```bash
python multi_watcher_manager.py
```

**NARRATION:**
> "Silver tier adds five simultaneous watchers — Gmail, WhatsApp, LinkedIn,
> Facebook, and Twitter — all running in parallel."

**[Drop a JSON file into `/Channels/WhatsApp_Inbox/`:]**

```bash
cat > Channels/WhatsApp_Inbox/client_msg.json << 'EOF'
{
  "type": "message",
  "from": "+1234567890",
  "message": "Hey, urgent — need a quote for 50 units ASAP",
  "timestamp": "2026-02-19T10:00:00Z"
}
EOF
```

> "A WhatsApp message drops in. The watcher converts it to a task automatically."

**[Switch to Obsidian — show the task appear in `/Needs_Action/`]**

> "P1 — keyword 'urgent' detected. Sensitivity flagged — external communication.
> Plan created. Approval requested."

**[Drop a JSON into `/Channels/Social_Inbox/`:]**

```bash
cat > Channels/Social_Inbox/linkedin_comment.json << 'EOF'
{
  "type": "comment",
  "from": "Jane Smith",
  "message": "Loved your last post! What services do you offer?",
  "platform": "linkedin"
}
EOF
```

> "At the same time, a LinkedIn comment arrives. Different channel, same system.
> Each one is classified, planned, and routed — independently, in parallel."

---

## SECTION 6 — LIVE DEMO: GOLD — FACEBOOK + TWITTER + ODOO (4:30 – 6:00)

**[Screen: VS Code — open `backend/integrations/facebook.py` briefly]**

**NARRATION:**
> "Gold tier is where it gets serious. We add Facebook, Instagram, Twitter,
> and Odoo accounting."

**[Screen: Show `facebook_watcher.py` running, drop demo JSON]**

```bash
# Facebook comment arrives
cat Channels/Facebook_Inbox/demo_comment.json
```

> "A Facebook comment — auto-converted to a task, sensitivity scored,
> draft reply queued for approval."

**[Screen: Show `twitter_watcher.py`, drop demo JSON]**

```bash
cat Channels/Twitter_Inbox/demo_mention.json
```

> "A Twitter mention. Same pipeline. Draft reply, 280 chars, approval required."

**[Screen: Terminal — show Odoo MCP server]**

```bash
# Show the Odoo MCP server
cat odoo-mcp/README.md
```

> "And here's the Odoo MCP server. When a client asks for an invoice,
> the AI calls this to create a draft in Odoo."

**[Screen: Show `odoo-mcp/app/main.py` — highlight `create_draft_invoice` and `_write_hitl_approval`]**

> "Draft invoice created. But look — it automatically writes an approval file.
> The invoice stays as a draft in Odoo until you approve.
> The AI cannot post a financial transaction. That's by design."

**[Screen: Show the CEO Briefing file]**

```bash
python weekly_audit.py
cat CEO_Briefing.md
```

> "And every Monday, it generates this — the CEO Briefing.
> SLA compliance, approvals, errors, priority breakdown.
> All from the logs. No manual reporting."

---

## SECTION 7 — LIVE DEMO: GOLD — RALPH WIGGUM LOOP (6:00 – 6:45)

**[Screen: Terminal — show `ralph_loop.py`]**

**NARRATION:**
> "The 'Ralph Wiggum' loop solves the lazy agent problem.
> Claude Code normally exits when it thinks it's done.
> This stop hook intercepts the exit."

**[Show `.claude/hooks/stop.py` briefly]**

> "If the task isn't in `/Done` yet — Claude gets sent back to work.
> It keeps iterating until the job is actually finished, up to a configurable limit.
> This turns Claude from a one-shot responder into a persistent worker."

**[Show `ralph_loop.py` usage]**

```bash
python ralph_loop.py "my_task.md" "Process everything in /Needs_Action" --max-iterations 10
```

> "Start a loop — max 10 iterations. Claude works, checks /Done, works again if needed.
> That's the difference between a chatbot and an employee."

---

## SECTION 8 — PLATINUM ARCHITECTURE (6:45 – 7:45)

**[Screen: `Docs/Platinum_Architecture.md` in Obsidian — show the ASCII diagram]**

**NARRATION:**
> "Platinum tier adds 24/7 cloud uptime. The system splits into two agents."

**[Point to the diagram]**

> "The Cloud Agent runs on Oracle Cloud's Always Free VM — it never sleeps.
> It handles email triage, drafts social posts, creates Odoo invoices.
> But it can never send, never post, never pay.
>
> The Local Agent — your laptop — wakes up, pulls the vault via Git,
> reviews what the Cloud drafted overnight, and approves with a file move.
> The Cloud executes. The vault syncs back."

**[Show `scripts/sync_vault.sh`]**

> "Vault sync is just Git. Markdown files only.
> Secrets, sessions, databases — never touch the repo.
> That's the security model."

**[Show `Docs/Cloud_Deployment.md` briefly]**

> "Full deployment guide is here — Oracle Cloud, PM2, Docker Odoo, HTTPS.
> The whole thing."

---

## SECTION 9 — CLOSE (7:45 – 8:15)

**[Screen: GitHub repo — github.com/Ub207/AI_Employee_Vault]**

**NARRATION:**
> "Let me recap what we built:
>
> Bronze — a working vault with approval pipeline and audit logs.
> Silver — five simultaneous channel watchers and a cron scheduler.
> Gold — Facebook, Instagram, Twitter, Odoo accounting, and the Ralph Wiggum loop.
> Platinum — Cloud plus Local, always-on, vault-synced, work-zone specialized.
>
> Seven platforms integrated. One approval rule: the AI drafts, you decide.
> Full audit trail. 24/7 uptime. 85% cheaper than a human FTE.
>
> This is a Digital FTE."

**[Screen: Final shot of Dashboard.md in Obsidian — full tier table visible]**

> "The code is open source. Link in the description."

**[Fade out]**

---

## RECORDING TIPS

| Tip | Detail |
|-----|--------|
| **Resolution** | 1920×1080 minimum |
| **Font sizes** | Terminal 16pt+, Obsidian 18pt+, VS Code 16pt+ |
| **Pace** | Speak slowly on demos — let the file system changes be visible |
| **Pauses** | 1-second pause after each file appears in Obsidian |
| **Terminal** | Use a dark theme (e.g. One Dark, Dracula) for contrast |
| **Split screen** | Terminal left 40%, Obsidian right 60% during live demos |
| **Highlights** | Use a screen highlighter tool to point at key lines in code |
| **Cuts** | Cut between sections; no need to show full Claude processing time |

## TIMESTAMPS (for YouTube description)

```
0:00 - Introduction & Hook
0:45 - What is a Digital FTE?
1:30 - Vault Tour (Obsidian structure)
2:30 - Live Demo: Bronze/Silver — File drop & approval pipeline
3:45 - Live Demo: Silver — Multi-channel watchers (WhatsApp, LinkedIn)
4:30 - Live Demo: Gold — Facebook, Twitter & Odoo accounting
6:00 - Live Demo: Gold — Ralph Wiggum persistence loop
6:45 - Platinum Architecture: Cloud + Local always-on
7:45 - Closing & GitHub link
```

## DESCRIPTION TEMPLATE (YouTube / Submission)

```
AI Employee Vault — Digital FTE | Hackathon-0

A fully autonomous AI employee built on Claude Code + Obsidian.
Monitors Gmail, WhatsApp, LinkedIn, Facebook, Instagram, Twitter, and Odoo —
24/7, with human-in-the-loop approval on every sensitive action.

Tiers completed: Bronze → Silver → Gold → Platinum

Key features:
• 5 simultaneous channel watchers
• Sensitivity scoring + P0–P3 priority queue with SLA tracking
• Human-in-the-loop approval via file-move (zero code to approve)
• Odoo accounting MCP server (draft-only, HITL)
• Ralph Wiggum persistence loop (autonomous multi-step tasks)
• Platinum: Cloud Agent (drafts) + Local Agent (approves + executes)
• Git-based vault sync — secrets never leave your machine

GitHub: https://github.com/Ub207/AI_Employee_Vault

Built with: Claude Code · Obsidian · Python · FastAPI · Odoo Community
```
