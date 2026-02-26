---
type: deployment_tracker
task: oracle_cloud_vm_setup
agent: local
priority: P1
started: "2026-02-24"
status: in_progress
repo: https://github.com/Ub207/AI_Employee_Vault.git
---

# Oracle Cloud VM — Deployment Tracker

## Progress

- [x] Approval given — 2026-02-24
- [x] PM2 cloud config created (ecosystem.cloud.config.js)
- [x] sync_vault.sh ready
- [ ] **STEP 1** — Oracle Cloud account sign up
- [ ] **STEP 2** — VM create karo (ARM, Always Free)
- [ ] **STEP 3** — SSH key save karo → Secrets/oracle_vm.pem
- [ ] **STEP 4** — VM par dependencies install
- [ ] **STEP 5** — GitHub repo clone on VM
- [ ] **STEP 6** — ANTHROPIC_API_KEY set
- [ ] **STEP 7** — PM2 start + save + startup
- [ ] **STEP 8** — Windows Task Scheduler: sync_vault.ps1 (har 5 min)
- [ ] **STEP 9** — Test: local machine band karo, cloud se task process ho

---

## STEP 1 — Sign Up (Tum Karo)

```
URL: https://cloud.oracle.com/free
Email: personal email use karo
Credit card: verification ke liye chahiye (charge NAHI hoga)
Home Region: Mumbai (ap-mumbai-1) — Pakistan ke qareeb
```

---

## STEP 2 — VM Create (Oracle Console)

```
Compute → Instances → Create Instance

Name: ai-employee-cloud
Image: Ubuntu 22.04 (Minimal)
Shape: VM.Standard.A1.Flex
  OCPU: 4
  RAM: 24 GB
Boot Volume: 50 GB

SSH Keys: Generate new pair
  → Private key download karo
  → Save as: D:/AI_Employee_Vault/Secrets/oracle_vm.pem
```

---

## STEP 3 — SSH Connect (MINGW/Git Bash)

VM IP milne ke baad (Oracle Console mein dikhega):

```bash
chmod 600 /d/AI_Employee_Vault/Secrets/oracle_vm.pem
ssh -i /d/AI_Employee_Vault/Secrets/oracle_vm.pem ubuntu@<VM_PUBLIC_IP>
```

---

## STEP 4 — VM Par Install (VM terminal mein)

```bash
# System update
sudo apt update && sudo apt upgrade -y

# Python
sudo apt install -y python3 python3-pip python3-venv git

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PM2
sudo npm install -g pm2

# Python packages
pip3 install anthropic watchdog pyyaml croniter python-dotenv
```

---

## STEP 5 — Repo Clone (VM par)

```bash
git clone https://github.com/Ub207/AI_Employee_Vault.git ~/AI_Employee_Vault
cd ~/AI_Employee_Vault
```

Agar repo private hai:
```bash
# Pehle SSH key generate karo VM par:
ssh-keygen -t ed25519 -C "cloud-agent"
cat ~/.ssh/id_ed25519.pub
# Yeh key GitHub → Settings → Deploy Keys mein add karo
```

---

## STEP 6 — API Key Set (VM par)

```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-APIKA_KEY_YAHaN_LIKHO' >> ~/.bashrc
echo 'export AGENT_ROLE=cloud' >> ~/.bashrc
source ~/.bashrc
```

---

## STEP 7 — PM2 Start (VM par)

```bash
cd ~/AI_Employee_Vault
pm2 start ecosystem.cloud.config.js
pm2 save
pm2 startup
# Jo command print ho usse copy karke run karo
```

---

## STEP 8 — Windows Task Scheduler (Local Machine)

PowerShell mein run karo (ek baar):
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"D:\AI_Employee_Vault\scripts\sync_vault.ps1`""
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "AI-Vault-Sync" -Action $action -Trigger $trigger -RunLevel Highest
```

---

## STEP 9 — Test

```
1. Koi file Needs_Action mein daalo (local se)
2. sync_vault.ps1 run karo (ya 5 min wait)
3. VM par check karo: git log --oneline -3
4. VM par check karo: pm2 logs file-watcher
5. Done folder mein file aa jaye → SUCCESS
```

---

## VM IP (Yahan Bharo Jab Mile)

```
VM_PUBLIC_IP: _______________
VM_USERNAME:  ubuntu
KEY_PATH:     D:/AI_Employee_Vault/Secrets/oracle_vm.pem
```
