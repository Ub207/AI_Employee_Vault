---
type: approval_request
task: odoo19_install
priority: P2
sensitivity_score: 0.7
sensitivity_category: infrastructure
created: "2026-02-22 09:50"
status: awaiting_approval
---

# APPROVAL REQUIRED — Odoo 19 Community Install (Windows)

## Current State
Odoo MCP server is running in **MOCK mode** on port 3000.
All invoice endpoints work with simulated responses.
Real Odoo 19 requires full install — steps below need human execution.

## Why Human Required
- PostgreSQL install (system-level, needs admin)
- Odoo Git clone (2GB+ download)
- Database creation with credentials
- Windows service setup

## Step-by-Step Install Guide

### 1. Install PostgreSQL 15
```
Download: https://www.postgresql.org/download/windows/
- Default port: 5432
- Superuser password: odoo_pass
- Add to PATH
```

### 2. Create Odoo DB user
```bash
psql -U postgres -c "CREATE USER odoo WITH PASSWORD 'odoo_pass';"
psql -U postgres -c "CREATE DATABASE mycompany OWNER odoo;"
```

### 3. Clone Odoo 19
```bash
git clone https://github.com/odoo/odoo --depth 1 --branch 19.0 D:/odoo19
```

### 4. Create venv + install
```bash
python -m venv D:/odoo19/venv
D:/odoo19/venv/Scripts/activate
pip install -r D:/odoo19/requirements.txt
```

### 5. Create odoo.conf
```ini
[options]
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo_pass
addons_path = D:/odoo19/addons
http_port = 8069
```

### 6. Run
```bash
python D:/odoo19/odoo-bin -c D:/AI_Employee_Vault/odoo.conf
```

### 7. Switch MCP to live mode
In MCP/odoo_mcp.js, set: `const MOCK_MODE = false;`
Then `pm2 restart odoo-mcp`

## Manager Decision
- [ ] **APPROVE** — I will follow the steps above to install Odoo
- [ ] **SKIP** — Keep MCP in mock mode (sufficient for demo)

> Current mock mode is fully functional for Hackathon-0 demo purposes.
