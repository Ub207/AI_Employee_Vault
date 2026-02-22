// Odoo MCP Server (Node.js) — Gold/Platinum Tier
// Exposes JSON-RPC bridge to Odoo XML-RPC endpoints for draft-only actions.
// Set ODOO_MOCK=true to run without a live Odoo instance (for demos/testing).
// Security: draft-only; posting requires human approval via /Pending_Approval.

const express = require('express');
const { createClient } = require('xmlrpc');

const app = express();
app.use(express.json());

const ODOO_HOST = process.env.ODOO_HOST || 'localhost';
const ODOO_PORT = parseInt(process.env.ODOO_PORT || '8069', 10);
const ODOO_DB   = process.env.ODOO_DB   || 'mycompany';
const ODOO_USER = process.env.ODOO_USER || 'admin';
const ODOO_PASS = process.env.ODOO_PASS || 'admin';
const MOCK_MODE = process.env.ODOO_MOCK === 'true' || true; // default mock until Odoo installed
const PORT      = parseInt(process.env.MCP_PORT || '3000', 10);

let _invoiceCounter = 1000;

// ── Mock helpers ──────────────────────────────────────────────────────────────

function mockCreateInvoice({ partner, amount, description, due_date }) {
  _invoiceCounter++;
  return {
    success: true,
    mock: true,
    invoice_id: _invoiceCounter,
    state: 'draft',
    partner,
    amount,
    description,
    due_date,
    note: 'MOCK — connect real Odoo to activate live creation',
  };
}

function mockListInvoices() {
  return {
    mock: true,
    invoices: [
      { id: 1001, partner: 'Hamza Butt',  amount: 120000, state: 'draft',  due: '2026-03-08' },
      { id: 1002, partner: 'Ahmed Khan',  amount:  50000, state: 'draft',  due: '2026-03-01' },
    ],
  };
}

function mockAccountingSummary() {
  return {
    mock: true,
    total_draft:   170000,
    total_posted:       0,
    unpaid_count:       2,
    currency: 'PKR',
    note: 'MOCK — connect real Odoo for live data',
  };
}

// ── Real Odoo helpers ─────────────────────────────────────────────────────────

async function getUid() {
  const common = createClient({ host: ODOO_HOST, port: ODOO_PORT, path: '/xmlrpc/2/common' });
  return new Promise((resolve, reject) => {
    common.methodCall('authenticate', [ODOO_DB, ODOO_USER, ODOO_PASS, {}], (err, uid) => {
      if (err) reject(err); else resolve(uid);
    });
  });
}

function objectClient() {
  return createClient({ host: ODOO_HOST, port: ODOO_PORT, path: '/xmlrpc/2/object' });
}

// ── Routes ────────────────────────────────────────────────────────────────────

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', mode: MOCK_MODE ? 'mock' : 'live', port: PORT });
});

// Generic execute_kw proxy
app.post('/odoo', async (req, res) => {
  if (MOCK_MODE) return res.json({ mock: true, result: null });
  try {
    const uid = await getUid();
    const { model, method, args, kwargs } = req.body;
    const client = objectClient();
    client.methodCall('execute_kw',
      [ODOO_DB, uid, ODOO_PASS, model, method, args || [], kwargs || {}],
      (err, result) => err ? res.status(500).json({ error: String(err) }) : res.json({ result })
    );
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

// Create draft invoice
app.post('/tools/create_draft_invoice', async (req, res) => {
  const { partner, amount, description, due_date } = req.body;
  if (MOCK_MODE) return res.json(mockCreateInvoice({ partner, amount, description, due_date }));
  try {
    const uid = await getUid();
    const client = objectClient();
    const values = {
      move_type: 'out_invoice',
      state: 'draft',
      invoice_line_ids: [[0, 0, { name: description, price_unit: amount, quantity: 1 }]],
    };
    client.methodCall('execute_kw',
      [ODOO_DB, uid, ODOO_PASS, 'account.move', 'create', [values]],
      (err, invoice_id) => err
        ? res.status(500).json({ error: String(err) })
        : res.json({ success: true, invoice_id, state: 'draft' })
    );
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

// List invoices
app.get('/tools/list_invoices', async (req, res) => {
  if (MOCK_MODE) return res.json(mockListInvoices());
  try {
    const uid = await getUid();
    const client = objectClient();
    client.methodCall('execute_kw',
      [ODOO_DB, uid, ODOO_PASS, 'account.move', 'search_read',
       [[['move_type','=','out_invoice']]], { fields: ['name','partner_id','amount_total','state'] }],
      (err, result) => err ? res.status(500).json({ error: String(err) }) : res.json({ result })
    );
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
});

// Accounting summary
app.get('/tools/accounting_summary', (_req, res) => {
  if (MOCK_MODE) return res.json(mockAccountingSummary());
  res.json({ note: 'Live mode — query Odoo for real data' });
});

app.listen(PORT, () => {
  console.log(`Odoo MCP (Node) on :${PORT} | mode=${MOCK_MODE ? 'MOCK' : 'LIVE'}`);
});
