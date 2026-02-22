# Lessons Learned — AI Employee Hackathon-0

## Challenges and Solutions

### 1. Odoo Installation on Windows
- **Challenge**: Installing PostgreSQL and Odoo on Windows can be complex due to dependency conflicts (especially `psycopg2`).
- **Solution**: Use a Virtual Environment (`venv`) and prioritize the Odoo Community edition's `requirements.txt`. For Hackathon demos, a Mock MCP server is a viable fallback that preserves API structure without the infrastructure overhead.

### 2. Skills Indexing Issues
- **Challenge**: The AI agent occasionally fails to find custom skills if they aren't in the primary search path.
- **Solution**: Explicitly copy skill definitions to `.claude/commands/` or `.claude/skills/` and reference them in the main `SKILL.md`.

### 3. Cross-Platform Automation
- **Challenge**: WhatsApp and social media platforms are resistant to simple API automation.
- **Solution**: Used Playwright-based watchers that simulate real browser sessions, combined with session persistence to avoid frequent MFA prompts.

### 4. Cloud-Local Coordination
- **Challenge**: Synchronizing state between a cloud watcher and a local approval station.
- **Solution**: Implemented a "Claim-by-move" system synchronized via Git. The cloud creates the draft, the local human approves it, and the local agent executes it. This ensures "Local owns authority, Cloud owns attendance."

## Best Practices
- **Ralph Wiggum Mode**: Always log the "Next Steps" explicitly so the agent can resume if interrupted.
- **Safety First**: Never automate the *posting* of financial transactions or public social posts without a `Pending_Approval` step.
- **Structured Logging**: Use a dashboard-first logging approach for easy human monitoring.
