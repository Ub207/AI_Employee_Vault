---
type: approval_request
task: oracle_cloud_vm_setup
priority: P1
sensitivity_score: 0.7
sensitivity_category: infrastructure, access_change
created: "2026-02-22 09:55"
status: awaiting_approval
---

# APPROVAL REQUIRED — Oracle Cloud Free VM Setup (Platinum Tier)

## Purpose
Deploy Cloud Agent (24/7 always-on) that handles email triage, social post drafts, and Odoo accounting drafts — even when your local machine is off.

## Steps Required (Human Must Do)

### Step 1 — Sign Up
- URL: https://cloud.oracle.com/free
- Use personal email
- Credit card required for verification (NOT charged for Always Free)
- Home region: Select closest available (Mumbai or Osaka if Karachi unavailable)

### Step 2 — Create VM
```
Shape: VM.Standard.A1.Flex (ARM — Always Free)
  OCPU: 4 | RAM: 24 GB
OS: Ubuntu 22.04 LTS (minimal)
Storage: 50 GB boot volume
SSH key: Generate new → save private key as D:/AI_Employee_Vault/Secrets/oracle_vm.pem
```

### Step 3 — SSH In
```bash
chmod 600 D:/AI_Employee_Vault/Secrets/oracle_vm.pem
ssh -i D:/AI_Employee_Vault/Secrets/oracle_vm.pem ubuntu@<VM_PUBLIC_IP>
```

### Step 4 — Install on VM
```bash
sudo apt update && sudo apt install -y python3 python3-pip nodejs npm git
pip3 install anthropic watchdog pyyaml
npm install -g pm2
```

### Step 5 — Clone Vault on VM
```bash
git clone https://github.com/<YOUR_USER>/ai-vault.git ~/vault
cd ~/vault
```

### Step 6 — Set Claude API Key on VM
```bash
echo "export ANTHROPIC_API_KEY=sk-ant-..." >> ~/.bashrc
source ~/.bashrc
```

### Step 7 — Start Cloud Agent on VM
```bash
cd ~/vault
# Cloud agent runs in read-only mode: drafts only, no sends
pm2 start watcher.py --interpreter python3 --name cloud-agent
pm2 start MCP/odoo_mcp.js --name odoo-mcp
pm2 save
pm2 startup
```

### Step 8 — Enable Vault Sync
On local machine:
```powershell
# Add to Windows Task Scheduler: run every 5 min
powershell -ExecutionPolicy Bypass -File D:/AI_Employee_Vault/scripts/sync_vault.ps1
```

### Step 9 — Configure config.yaml
```yaml
vault_sync:
  enabled: true
  interval_seconds: 300
  remote: "origin"
  branch: "main"
agent_role: local   # local machine
```
On VM: set `agent_role: cloud`

## Manager Decision
- [x] **APPROVE** — I will set up Oracle Cloud VM following steps above
- [ ] **SKIP** — Continue without cloud VM (local-only Platinum demo)

**Approved by:** Manager
**Approved at:** 2026-02-24
**Status:** In Progress

> The system is fully functional locally. Cloud VM adds 24/7 uptime when local is off.
