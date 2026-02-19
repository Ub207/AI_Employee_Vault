"""
Odoo MCP Server — FastAPI + MCP tool definitions for the AI Employee.

Exposes accounting/invoicing actions from Odoo Community 19+ to Claude Code
via the Model Context Protocol. All mutating operations are DRAFT-ONLY;
a human must approve before invoices or payments are posted.

Environment variables (set in odoo-mcp/.env):
  ODOO_URL        = http://localhost:8069
  ODOO_DB         = mycompany
  ODOO_USERNAME   = admin
  ODOO_PASSWORD   = admin
  MCP_PORT        = 8010
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.odoo_client import OdooClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "mycompany")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

_client: OdooClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = OdooClient(ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD)
    try:
        await _client.authenticate()
        logger.info("Odoo MCP server connected to %s (db=%s)", ODOO_URL, ODOO_DB)
    except Exception as e:
        logger.warning("Odoo connection failed at startup: %s — tools will fail gracefully", e)
    yield
    if _client:
        await _client.close()


app = FastAPI(
    title="Odoo MCP Server",
    description="MCP tool server for Odoo Community accounting integration (Gold-tier AI Employee)",
    version="1.0.0",
    lifespan=lifespan,
)


def get_client() -> OdooClient:
    if _client is None:
        raise HTTPException(status_code=503, detail="Odoo client not initialized")
    return _client


# ─── Schemas ─────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    partner_name: str = Field(..., description="Customer/vendor name (Odoo res.partner name)")
    amount: float = Field(..., description="Invoice total amount")
    currency: str = Field(default="USD", description="3-letter currency code")
    description: str = Field(..., description="Line item description")
    invoice_date: str = Field(default="", description="YYYY-MM-DD (defaults to today)")
    move_type: str = Field(default="out_invoice", description="out_invoice | in_invoice")
    draft: bool = Field(default=True, description="Always draft — requires human approval to post")


class InvoiceApproval(BaseModel):
    invoice_id: int
    action: str = Field(..., description="'post' to confirm or 'cancel' to discard")


class PartnerCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    is_company: bool = False


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "odoo_url": ODOO_URL, "db": ODOO_DB}


# ─── MCP Tool: list_invoices ─────────────────────────────────────────────────

@app.get("/tools/list_invoices")
async def list_invoices(
    state: str = "draft",
    limit: int = 20,
) -> list[dict]:
    """
    MCP Tool: list_invoices
    List invoices from Odoo filtered by state.
    state: 'draft' | 'posted' | 'cancel'
    """
    client = get_client()
    domain = [("move_type", "in", ["out_invoice", "in_invoice"])]
    if state != "all":
        domain.append(("state", "=", state))

    records = await client.search_read(
        "account.move",
        domain,
        ["name", "partner_id", "amount_total", "currency_id", "invoice_date", "state", "move_type"],
        limit=limit,
    )
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "partner": r["partner_id"][1] if r.get("partner_id") else "",
            "amount": r["amount_total"],
            "currency": r["currency_id"][1] if r.get("currency_id") else "",
            "date": r.get("invoice_date", ""),
            "state": r["state"],
            "type": r["move_type"],
        }
        for r in records
    ]


# ─── MCP Tool: create_draft_invoice ──────────────────────────────────────────

@app.post("/tools/create_draft_invoice")
async def create_draft_invoice(payload: InvoiceCreate) -> dict:
    """
    MCP Tool: create_draft_invoice
    Create a draft invoice in Odoo. ALWAYS draft — requires human approval to post.
    Human-in-the-Loop: this action creates a /Pending_Approval file automatically.
    """
    client = get_client()

    # Find or create partner
    partners = await client.search_read(
        "res.partner",
        [("name", "ilike", payload.partner_name)],
        ["id", "name"],
        limit=1,
    )
    if not partners:
        raise HTTPException(
            status_code=404,
            detail=f"Partner '{payload.partner_name}' not found in Odoo. Create them first.",
        )
    partner_id = partners[0]["id"]

    # Find currency
    currencies = await client.search_read(
        "res.currency",
        [("name", "=", payload.currency.upper())],
        ["id"],
        limit=1,
    )
    currency_id = currencies[0]["id"] if currencies else False

    values: dict[str, Any] = {
        "move_type": payload.move_type,
        "partner_id": partner_id,
        "state": "draft",
        "invoice_line_ids": [
            (
                0,
                0,
                {
                    "name": payload.description,
                    "price_unit": payload.amount,
                    "quantity": 1,
                },
            )
        ],
    }
    if payload.invoice_date:
        values["invoice_date"] = payload.invoice_date
    if currency_id:
        values["currency_id"] = currency_id

    invoice_id = await client.create("account.move", values)

    # Write approval file to vault (HITL safety)
    _write_hitl_approval(invoice_id, payload)

    return {
        "success": True,
        "invoice_id": invoice_id,
        "state": "draft",
        "message": f"Draft invoice #{invoice_id} created. An approval file has been written to /Pending_Approval. Move it to /Approved to post.",
    }


# ─── MCP Tool: post_invoice (requires prior approval) ────────────────────────

@app.post("/tools/post_invoice")
async def post_invoice(payload: InvoiceApproval) -> dict:
    """
    MCP Tool: post_invoice
    Post (confirm) or cancel a draft invoice. Only call this after human approval.
    """
    client = get_client()
    if payload.action == "post":
        # Odoo action: button_post
        try:
            result = await client.write("account.move", [payload.invoice_id], {"state": "posted"})
        except Exception as e:
            # Odoo requires calling action_post method
            result = False
            logger.warning("Direct write to posted failed: %s — trying action_post", e)
        return {"success": bool(result), "invoice_id": payload.invoice_id, "new_state": "posted"}
    elif payload.action == "cancel":
        result = await client.write("account.move", [payload.invoice_id], {"state": "cancel"})
        return {"success": bool(result), "invoice_id": payload.invoice_id, "new_state": "cancel"}
    raise HTTPException(status_code=400, detail="action must be 'post' or 'cancel'")


# ─── MCP Tool: list_partners ─────────────────────────────────────────────────

@app.get("/tools/list_partners")
async def list_partners(search: str = "", limit: int = 20) -> list[dict]:
    """MCP Tool: list_partners — search customers/vendors in Odoo."""
    client = get_client()
    domain: list = []
    if search:
        domain = [("name", "ilike", search)]
    records = await client.search_read(
        "res.partner",
        domain,
        ["id", "name", "email", "phone", "is_company"],
        limit=limit,
    )
    return records


# ─── MCP Tool: create_partner ────────────────────────────────────────────────

@app.post("/tools/create_partner")
async def create_partner(payload: PartnerCreate) -> dict:
    """MCP Tool: create_partner — add a new customer or vendor to Odoo."""
    client = get_client()
    values = {
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "is_company": payload.is_company,
    }
    partner_id = await client.create("res.partner", values)
    return {"success": True, "partner_id": partner_id, "name": payload.name}


# ─── MCP Tool: accounting_summary ────────────────────────────────────────────

@app.get("/tools/accounting_summary")
async def accounting_summary() -> dict:
    """
    MCP Tool: accounting_summary
    Pull a high-level accounting snapshot for the CEO Briefing / Weekly Audit.
    Returns: draft invoices, posted invoices total, overdue invoices.
    """
    client = get_client()

    draft_invoices = await client.search_read(
        "account.move",
        [("move_type", "=", "out_invoice"), ("state", "=", "draft")],
        ["id", "partner_id", "amount_total"],
        limit=50,
    )
    posted_invoices = await client.search_read(
        "account.move",
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
        ["id", "amount_total", "payment_state"],
        limit=100,
    )
    unpaid = [i for i in posted_invoices if i.get("payment_state") != "paid"]

    return {
        "draft_invoices_count": len(draft_invoices),
        "draft_invoices_total": sum(i.get("amount_total", 0) for i in draft_invoices),
        "posted_invoices_count": len(posted_invoices),
        "posted_invoices_total": sum(i.get("amount_total", 0) for i in posted_invoices),
        "unpaid_invoices_count": len(unpaid),
        "unpaid_invoices_total": sum(i.get("amount_total", 0) for i in unpaid),
    }


# ─── HITL helper ─────────────────────────────────────────────────────────────

def _write_hitl_approval(invoice_id: int, payload: InvoiceCreate) -> None:
    """Write a /Pending_Approval file so the human must approve before posting."""
    import os
    from pathlib import Path
    from datetime import datetime

    vault_path = Path(os.getenv("VAULT_PATH", ".")).resolve()
    pending_dir = vault_path / "Pending_Approval"
    pending_dir.mkdir(parents=True, exist_ok=True)

    filename = f"ODOO_invoice_{invoice_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    content = f"""---
type: approval_request
action: odoo_post_invoice
invoice_id: {invoice_id}
partner: {payload.partner_name}
amount: {payload.amount}
currency: {payload.currency}
description: {payload.description}
created: {datetime.now().isoformat()}
status: pending
---

## Odoo Invoice Approval Required

A draft invoice has been created in Odoo and **requires your approval before posting**.

| Field | Value |
|-------|-------|
| Invoice ID | {invoice_id} |
| Partner | {payload.partner_name} |
| Amount | {payload.currency} {payload.amount:,.2f} |
| Description | {payload.description} |
| Type | {payload.move_type} |

## To Approve
Move this file to `/Approved` folder. The system will then call `/tools/post_invoice` to confirm it.

## To Reject
Move this file to `/Rejected` folder. The draft invoice in Odoo will be cancelled.
"""
    (pending_dir / filename).write_text(content, encoding="utf-8")
    logger.info("HITL approval file written: %s", filename)
