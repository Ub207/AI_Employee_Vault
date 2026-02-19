# Cloud Deployment Guide — Platinum Tier

## Recommended Platform: Oracle Cloud Free Tier

Oracle Cloud's Always Free tier includes two ARM-based VMs (4 OCPUs, 24GB RAM) — more than enough for the cloud AI Employee.

**Sign up:** https://www.oracle.com/cloud/free/

---

## Step 1: Provision the VM

```bash
# Oracle Cloud CLI or Console:
# OS: Ubuntu 22.04 LTS (ARM)
# Shape: VM.Standard.A1.Flex (Always Free)
# OCPUs: 2 | RAM: 12GB | Storage: 50GB

# After provisioning, SSH in:
ssh ubuntu@<YOUR_VM_IP>
```

Alternatively, use **AWS EC2 Free Tier** (t2.micro) or any VPS provider.

---

## Step 2: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.13
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.13 python3.13-venv python3.13-pip git

# Install Node.js 24 LTS
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 (process manager)
sudo npm install -g pm2

# Verify
python3.13 --version
node --version
pm2 --version
```

---

## Step 3: Clone the Vault

```bash
# Generate SSH key for the cloud VM
ssh-keygen -t ed25519 -C "cloud-agent@ai-employee"
cat ~/.ssh/id_ed25519.pub
# Add this key to your GitHub repo (Settings → Deploy Keys)

# Clone
git clone git@github.com:YOUR_USERNAME/AI_Employee_Vault.git
cd AI_Employee_Vault
```

---

## Step 4: Configure the Cloud Agent

```bash
# Create cloud-specific .env (NEVER commit this)
cat > Secrets/.env << 'EOF'
# Cloud Agent configuration
AGENT_ROLE=cloud
AUTONOMY_LEVEL=MEDIUM
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
# NOTE: No WhatsApp session, no banking creds, no payment tokens
EOF

# Install Python dependencies
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install pyyaml croniter watchdog python-dotenv

# Backend database
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

---

## Step 5: Start Watchers with PM2

```bash
cd /home/ubuntu/AI_Employee_Vault

# Create PM2 ecosystem config
cat > pm2.cloud.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: "backend-api",
      script: "python3.13",
      args: "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      interpreter: "none",
      restart_delay: 5000,
      max_restarts: 10,
    },
    {
      name: "gmail-watcher",
      script: "python3.13",
      args: "gmail_watcher.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      interpreter: "none",
      restart_delay: 5000,
    },
    {
      name: "social-watcher",
      script: "python3.13",
      args: "social_watcher.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      interpreter: "none",
      restart_delay: 5000,
    },
    {
      name: "facebook-watcher",
      script: "python3.13",
      args: "facebook_watcher.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      interpreter: "none",
      restart_delay: 5000,
    },
    {
      name: "twitter-watcher",
      script: "python3.13",
      args: "twitter_watcher.py",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      interpreter: "none",
      restart_delay: 5000,
    },
    {
      name: "vault-sync",
      script: "bash",
      args: "scripts/sync_vault.sh",
      cwd: "/home/ubuntu/AI_Employee_Vault",
      interpreter: "none",
      restart_delay: 10000,
    },
  ]
};
EOF

# Start all processes
pm2 start pm2.cloud.config.js

# Persist across reboots
pm2 save
pm2 startup
# Follow the printed command (e.g., sudo env PATH=... pm2 startup systemd ...)
```

---

## Step 6: Git Sync Script

```bash
mkdir -p scripts
cat > scripts/sync_vault.sh << 'EOF'
#!/bin/bash
# Vault sync loop — pulls from and pushes to GitHub every 60 seconds
# Only syncs markdown and state files; secrets never leave the machine.

VAULT="/home/ubuntu/AI_Employee_Vault"
SYNC_INTERVAL=60
AGENT="cloud"

cd "$VAULT"
git config user.email "cloud-agent@ai-employee.local"
git config user.name "Cloud AI Agent"

echo "[$AGENT Sync] Starting vault sync loop..."

while true; do
    # Pull latest from remote
    git pull --rebase origin main 2>&1 | tail -3

    # Stage only safe files (no secrets)
    git add \
        "Needs_Action/*.md" \
        "Tasks/*.md" \
        "Pending_Approval/*.md" \
        "Approved/*.md" \
        "Rejected/*.md" \
        "Done/*.md" \
        "Logs/*.md" \
        "In_Progress/**/*.md" \
        "Updates/*.md" \
        "Plans/**/*.md" \
        "config.yaml" 2>/dev/null

    # Commit if there are changes
    if ! git diff --cached --quiet; then
        git commit -m "cloud: sync $(date -Iseconds)" 2>&1
        git push origin main 2>&1 | tail -2
        echo "[$AGENT Sync] Changes pushed at $(date)"
    fi

    sleep "$SYNC_INTERVAL"
done
EOF
chmod +x scripts/sync_vault.sh
```

---

## Step 7: Deploy Odoo Community on Cloud VM

```bash
# Install Docker
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu

# Create Odoo deployment
mkdir -p ~/odoo-deploy
cat > ~/odoo-deploy/docker-compose.yml << 'EOF'
version: "3.9"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: odoodb
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoopass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  odoo:
    image: odoo:17
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoopass
    volumes:
      - odoo_data:/var/lib/odoo

volumes:
  postgres_data:
  odoo_data:
EOF

cd ~/odoo-deploy
docker-compose up -d

# Set up HTTPS with nginx + certbot (recommended for production)
sudo apt install -y nginx certbot python3-certbot-nginx
# Configure your domain and run: sudo certbot --nginx -d yourdomain.com
```

---

## Step 8: Health Monitoring

```bash
# Install health check script
cat > scripts/health_check.sh << 'EOF'
#!/bin/bash
# Daily health check — PM2 status, disk space, API connectivity
echo "=== Health Check $(date) ==="
pm2 status
echo "--- Disk ---"
df -h / | tail -1
echo "--- Backend API ---"
curl -s http://localhost:8000/health | python3 -m json.tool
echo "--- Odoo ---"
curl -s http://localhost:8069/web/database/selector | head -5 && echo "OK" || echo "DOWN"
EOF
chmod +x scripts/health_check.sh

# Add to cron
(crontab -l 2>/dev/null; echo "0 8 * * * /home/ubuntu/AI_Employee_Vault/scripts/health_check.sh >> /home/ubuntu/logs/health.log 2>&1") | crontab -
```

---

## Security Checklist

- [ ] `.env` file is in `.gitignore` and never committed
- [ ] Oracle Cloud security group: open only ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- [ ] Use SSH key authentication only (disable password auth)
- [ ] Rotate all API credentials quarterly
- [ ] Odoo admin password changed from default
- [ ] Daily backups of Odoo PostgreSQL data
- [ ] Review `/Logs/` weekly for anomalies
