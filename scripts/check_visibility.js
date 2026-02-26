/**
 * Check if WhatsApp search/compose elements are visible and interactable.
 */
const http = require('http');
const net = require('net');
const crypto = require('crypto');

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(d));
      res.on('error', reject);
    }).on('error', reject);
  });
}

function wsConnect(wsUrl) {
  return new Promise((resolve, reject) => {
    const m = wsUrl.match(/^ws:\/\/([^/:]+):(\d+)(\/.*)?$/);
    if (!m) return reject(new Error('Bad WS URL'));
    const [, host, port, path] = m;
    const key = crypto.randomBytes(16).toString('base64');
    const socket = net.createConnection(parseInt(port), host, () => {
      socket.write(`GET ${path||'/'} HTTP/1.1\r\nHost: ${host}:${port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    });
    let upgraded = false, buf = Buffer.alloc(0);
    const handlers = [];
    socket.on('data', chunk => {
      buf = Buffer.concat([buf, chunk]);
      if (!upgraded) {
        const idx = buf.indexOf('\r\n\r\n');
        if (idx !== -1) { upgraded = true; buf = buf.slice(idx + 4); } else return;
      }
      while (buf.length >= 2) {
        const opcode = buf[0] & 0x0f;
        let payLen = buf[1] & 0x7f, offset = 2;
        if (payLen === 126) { payLen = buf.readUInt16BE(2); offset = 4; }
        if (buf.length < offset + payLen) break;
        const payload = buf.slice(offset, offset + payLen);
        buf = buf.slice(offset + payLen);
        if (opcode === 1) { const msg = payload.toString('utf8'); handlers.forEach(h => h(msg)); }
      }
    });
    socket.on('error', reject);
    const ws = {
      send(msg) {
        const data = Buffer.from(msg, 'utf8'), len = data.length;
        const mask = crypto.randomBytes(4);
        let header = len < 126 ? Buffer.from([0x81, 0x80 | len]) :
          (len < 65536 ? (h => { h[0]=0x81; h[1]=0xfe; h.writeUInt16BE(len,2); return h; })(Buffer.alloc(4)) : null);
        if (!header) return;
        const masked = Buffer.alloc(len);
        for (let i = 0; i < len; i++) masked[i] = data[i] ^ mask[i % 4];
        socket.write(Buffer.concat([header, mask, masked]));
      },
      on(ev, fn) { if (ev === 'message') handlers.push(fn); },
      off(ev, fn) { if (ev === 'message') { const i = handlers.indexOf(fn); if (i !== -1) handlers.splice(i, 1); } },
      close() { socket.destroy(); },
    };
    setTimeout(() => resolve(ws), 200);
  });
}

function cdpSend(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1e8);
    const handler = (data) => {
      try {
        const resp = JSON.parse(data);
        if (resp.id === id) {
          ws.off('message', handler);
          if (resp.error) reject(new Error(resp.error.message));
          else resolve(resp.result);
        }
      } catch(e) {}
    };
    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { ws.off('message', handler); reject(new Error('timeout ' + method)); }, 10000);
  });
}

async function main() {
  const raw = await httpGet('http://localhost:9222/json');
  const tabs = JSON.parse(raw);
  const wa = tabs.find(t => t.url && t.url.includes('whatsapp') && t.type === 'page');
  if (!wa) { console.error('WhatsApp tab not found'); process.exit(1); }
  console.log('Tab:', wa.title);

  const ws = await wsConnect(wa.webSocketDebuggerUrl);
  await cdpSend(ws, 'Runtime.enable');

  const code = `JSON.stringify((function() {
    function isVisible(el) {
      if (!el) return false;
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 &&
             style.display !== 'none' &&
             style.visibility !== 'hidden' &&
             style.opacity !== '0' &&
             rect.top < window.innerHeight &&
             rect.left < window.innerWidth;
    }

    const checks = [
      '[data-testid="search-input"]',
      '[aria-label="Search input textbox"]',
      'div[contenteditable="true"][data-tab="3"]',
      'div[contenteditable="true"][aria-label="Search"]',
      '[role="textbox"][aria-label="Search"]',
      '[role="textbox"][aria-label="Search input textbox"]',
    ];

    const results = {};
    for (const sel of checks) {
      const els = document.querySelectorAll(sel);
      if (els.length === 0) { results[sel] = 'NOT_IN_DOM'; continue; }
      const info = Array.from(els).map((e, i) => ({
        index: i,
        visible: isVisible(e),
        aria: e.getAttribute('aria-label') || '',
        tab: e.getAttribute('data-tab') || '',
        rect: (() => { const r = e.getBoundingClientRect(); return {w:Math.round(r.width),h:Math.round(r.height),top:Math.round(r.top),left:Math.round(r.left)}; })(),
        display: window.getComputedStyle(e).display,
        opacity: window.getComputedStyle(e).opacity,
      }));
      results[sel] = info;
    }

    return { window: {w: window.innerWidth, h: window.innerHeight}, checks: results };
  })())`;

  const r = await cdpSend(ws, 'Runtime.evaluate', { expression: code, returnByValue: true });
  const data = JSON.parse(r.result.value);

  console.log(`Window size: ${data.window.w}x${data.window.h}`);
  console.log('\n=== VISIBILITY CHECKS ===');
  for (const [sel, info] of Object.entries(data.checks)) {
    if (info === 'NOT_IN_DOM') {
      console.log(`  NOT IN DOM: ${sel}`);
    } else {
      for (const el of info) {
        const v = el.visible ? 'VISIBLE' : 'HIDDEN';
        console.log(`  [${v}] ${sel} (${el.index})`);
        console.log(`    aria='${el.aria}' tab='${el.tab}' rect=${JSON.stringify(el.rect)} display=${el.display} opacity=${el.opacity}`);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error(e.message); process.exit(1); });
