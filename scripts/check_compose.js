/**
 * Navigate to a chat and check compose box selectors in WhatsApp Comet UI.
 * We click the FIRST chat in the list to open it, then inspect the compose area.
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

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const raw = await httpGet('http://localhost:9222/json');
  const tabs = JSON.parse(raw);
  const wa = tabs.find(t => t.url && t.url.includes('whatsapp') && t.type === 'page');
  if (!wa) { console.error('WhatsApp tab not found'); process.exit(1); }
  console.log('Tab:', wa.title);

  const ws = await wsConnect(wa.webSocketDebuggerUrl);
  await cdpSend(ws, 'Runtime.enable');

  // Click the first chat in the list to open it
  console.log('Opening first chat...');
  const clickResult = await cdpSend(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify((function() {
      // Try to find and click the first chat row
      const rows = document.querySelectorAll('[role="listitem"], [data-testid="cell-frame-container"], [role="row"]');
      let clicked = '';
      for (const r of rows) {
        if (r.offsetParent !== null) {  // visible
          r.click();
          clicked = r.getAttribute('aria-label') || r.innerText.slice(0, 30);
          break;
        }
      }
      return { clicked };
    })())`,
    returnByValue: true
  });
  console.log('Clicked:', clickResult.result.value);
  await sleep(2000);

  // Now check compose box selectors
  const code = `JSON.stringify((function() {
    function isVisible(el) {
      if (!el) return false;
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 &&
             style.display !== 'none' && style.visibility !== 'hidden';
    }

    const checks = [
      '[data-testid="conversation-compose-box-input"]',
      'div[contenteditable="true"][data-tab="10"]',
      'div[contenteditable="true"][title="Type a message"]',
      '[aria-label="Type a message"]',
      'div[contenteditable="true"][spellcheck="true"]',
      'div[contenteditable="true"][aria-label="Message"]',
      '[role="textbox"][aria-label="Type a message"]',
      '[role="textbox"][aria-label="Message"]',
      'div[contenteditable="true"][data-tab="6"]',
    ];

    const results = {};
    for (const sel of checks) {
      const els = document.querySelectorAll(sel);
      if (!els.length) { results[sel] = null; continue; }
      const e = els[0];
      results[sel] = {
        count: els.length,
        tag: e.tagName,
        aria: e.getAttribute('aria-label') || '',
        testid: e.getAttribute('data-testid') || '',
        tab: e.getAttribute('data-tab') || '',
        title: e.getAttribute('title') || '',
        spellcheck: e.getAttribute('spellcheck') || '',
        visible: isVisible(e),
        rect: (() => { const r = e.getBoundingClientRect(); return {w:Math.round(r.width),h:Math.round(r.height),top:Math.round(r.top)}; })(),
      };
    }

    // All contenteditable in the right panel
    const main = document.querySelector('#main') || document.querySelector('[data-testid="conversation-panel"]') || document.body;
    const ces = main ? Array.from(main.querySelectorAll('[contenteditable="true"]')) : [];
    const ceInfo = ces.map(e => ({
      tag: e.tagName,
      aria: e.getAttribute('aria-label') || '',
      testid: e.getAttribute('data-testid') || '',
      tab: e.getAttribute('data-tab') || '',
      title: e.getAttribute('title') || '',
      spellcheck: e.getAttribute('spellcheck') || '',
      visible: isVisible(e),
    }));

    return { checks: results, main_ces: ceInfo };
  })())`;

  const r = await cdpSend(ws, 'Runtime.evaluate', { expression: code, returnByValue: true });
  const data = JSON.parse(r.result.value);

  console.log('\n=== COMPOSE BOX CHECKS ===');
  for (const [sel, info] of Object.entries(data.checks)) {
    if (!info) { console.log(`  not found: ${sel}`); continue; }
    const v = info.visible ? 'VISIBLE' : 'HIDDEN';
    console.log(`  [${v}](${info.count}): ${sel}`);
    console.log(`    tag=${info.tag} aria='${info.aria}' testid='${info.testid}' tab='${info.tab}' title='${info.title}' spellcheck='${info.spellcheck}'`);
    console.log(`    rect: ${JSON.stringify(info.rect)}`);
  }

  console.log('\n=== ALL CONTENTEDITABLE IN MAIN PANEL ===');
  for (const e of data.main_ces) {
    const v = e.visible ? 'VISIBLE' : 'HIDDEN';
    console.log(`  [${v}] ${e.tag} aria='${e.aria}' testid='${e.testid}' tab='${e.tab}' title='${e.title}' spellcheck='${e.spellcheck}'`);
  }

  // Go back to main chat list (press Escape)
  await cdpSend(ws, 'Runtime.evaluate', {
    expression: `document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape',keyCode:27,bubbles:true}))`,
    returnByValue: true
  });

  ws.close();
}

main().catch(e => { console.error(e.message); process.exit(1); });
