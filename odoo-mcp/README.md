# Odoo MCP Server — Gold Tier

This MCP (Model Context Protocol) server connects the AI Employee to **Odoo Community 19+** for accounting and invoice management.

## Setup

1. Install Odoo Community (self-hosted or via Docker):
   ```bash
   docker run -d -p 8069:8069 --name odoo odoo:19
   ```

2. Configure the MCP server:
   ```bash
   cd odoo-mcp
   cp .env.example .env
   # Edit .env with your Odoo URL, database, and credentials
   pip install -r requirements.txt
   ```

3. Start the server:
   ```bash
   python run.py
   ```

4. Register in Claude Code MCP config (`~/.claude/mcp.json`):
   ```json
   {
     "servers": [
       {
         "name": "odoo",
         "command": "python",
         "args": ["/path/to/AI_Employee_Vault/odoo-mcp/run.py"]
       }
     ]
   }
   ```

## Available MCP Tools

| Tool | Method | Description |
|------|--------|-------------|
| `list_invoices` | GET | List invoices by state (draft/posted/cancel) |
| `create_draft_invoice` | POST | Create a draft invoice (HITL — requires approval to post) |
| `post_invoice` | POST | Post or cancel a draft invoice (after human approval) |
| `list_partners` | GET | Search customers/vendors |
| `create_partner` | POST | Add a new customer or vendor |
| `accounting_summary` | GET | High-level accounting snapshot for CEO briefing |

## Human-in-the-Loop Safety

`create_draft_invoice` automatically writes an approval file to `/Pending_Approval/`. The invoice stays as a draft in Odoo until you:
- Move the file to `/Approved/` → the agent calls `post_invoice` to confirm
- Move the file to `/Rejected/` → the agent cancels the draft

**Payments are NEVER auto-approved.** This follows the Gold-tier security rule: _all financial mutations require human sign-off._

## API Reference

Interactive API docs available at: `http://localhost:8010/docs`
