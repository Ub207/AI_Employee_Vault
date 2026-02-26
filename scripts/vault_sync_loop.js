#!/usr/bin/env node
// Vault Sync Loop - Platinum Tier (Node.js, PM2-native)
// Runs git sync every 60 seconds. No subprocess chains - pure Node.js.

const { execSync, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const VAULT = path.resolve(__dirname, '..');
const INTERVAL_MS = parseInt(process.env.SYNC_INTERVAL || '60', 10) * 1000;

const PROTECTED = ['.env', '*.token', '.whatsapp_session', 'Secrets/', '*.key'];
const SAFE_PATTERNS = [
  'Needs_Action/*.md',
  'Tasks/*.md',
  'Approved/*.md',
  'Rejected/*.md',
  'Done/*.md',
  'Logs/*.md',
  'In_Progress/**/*.md',
  'Updates/*.md',
  'Dashboard.md',
  'CEO_Briefing.md',
  'config.yaml',
  'ecosystem.config.js',
  'scripts/vault_sync_loop.js',
  'scripts/vault_sync_loop.ps1',
  'scripts/sync_vault.ps1',
];

function ts() {
  return new Date().toISOString().replace('T', ' ').substring(0, 19);
}

function run(cmd, opts = {}) {
  try {
    return execSync(cmd, { cwd: VAULT, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], ...opts });
  } catch (e) {
    return e.stdout || '';
  }
}

function sync() {
  // Safety check: verify .gitignore covers protected patterns
  let gitignore = '';
  try { gitignore = fs.readFileSync(path.join(VAULT, '.gitignore'), 'utf8'); } catch (_) {}
  for (const p of PROTECTED) {
    if (!gitignore.includes(p.replace('*', ''))) {
      console.log(`[${ts()}] [WARN] '${p}' may not be in .gitignore - skipping sync!`);
      return;
    }
  }

  const status = run('git status --porcelain');
  if (!status.trim()) {
    console.log(`[${ts()}] Vault is clean - nothing to sync.`);
    return;
  }

  // Stage only safe patterns
  for (const pattern of SAFE_PATTERNS) {
    run(`git add "${pattern}"`);
  }

  const staged = run('git diff --cached --name-only');
  if (!staged.trim()) {
    console.log(`[${ts()}] No staged changes after filtering.`);
    return;
  }

  const msg = `Auto-sync ${ts()}`;
  const commitOut = run(`git commit -m "${msg}"`);
  const pushOut = run('git push origin main');

  console.log(`[${ts()}] Synced: ${msg}`);
  console.log(`Files:\n${staged.trim()}`);
}

console.log(`[${ts()}] [Vault Sync Loop] Started - interval: ${INTERVAL_MS / 1000}s - vault: ${VAULT}`);

// Run immediately, then every INTERVAL_MS
(async function loop() {
  while (true) {
    console.log(`[${ts()}] Running vault sync...`);
    sync();
    console.log(`[${ts()}] Sleeping ${INTERVAL_MS / 1000}s...`);
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
})();
