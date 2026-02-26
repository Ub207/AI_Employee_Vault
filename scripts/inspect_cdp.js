/**
 * Inspect WhatsApp DOM via CDP using only Node.js built-ins (no ws module needed).
 * Uses HTTP upgrade to speak WebSocket manually.
 */
const http = require('http');
const net = require('net');
const crypto = require('crypto');

const CDP_HOST = 'localhost';
const CDP_PORT = 9222;
const WA_WS = process.argv[2]; // pass websocket URL as arg

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

// Minimal WebSocket client using net.Socket
function wsConnect(wsUrl) {
  return new Promise((resolve, reject) => {
    // Parse ws://host:port/path
    const m = wsUrl.match(/^ws:\/\/([^/:]+):(\d+)(\/.*)?$/);
    if (!m) return reject(new Error('Bad WS URL: ' + wsUrl));
    const [, host, port, path] = m;

    const key = crypto.randomBytes(16).toString('base64');
    const socket = net.createConnection(parseInt(port), host, () => {
      socket.write(
        `GET ${path || '/'} HTTP/1.1\r\n` +
        `Host: ${host}:${port}\r\n` +
        `Upgrade: websocket\r\n` +
        `Connection: Upgrade\r\n` +
        `Sec-WebSocket-Key: ${key}\r\n` +
        `Sec-WebSocket-Version: 13\r\n\r\n`
      );
    });

    let upgraded = false;
    let buf = Buffer.alloc(0);
    const handlers = [];

    socket.on('data', chunk => {
      buf = Buffer.concat([buf, chunk]);
      if (!upgraded) {
        const idx = buf.indexOf('\r\n\r\n');
        if (idx !== -1) {
          upgraded = true;
          buf = buf.slice(idx + 4);
        } else return;
      }
      // Parse WebSocket frames
      while (buf.length >= 2) {
        const fin  = (buf[0] & 0x80) !== 0;
        const opcode = buf[0] & 0x0f;
        let payLen = buf[1] & 0x7f;
        let offset = 2;
        if (payLen === 126) { payLen = buf.readUInt16BE(2); offset = 4; }
        else if (payLen === 127) { payLen = Number(buf.readBigUInt64BE(2)); offset = 10; }
        if (buf.length < offset + payLen) break;
        const payload = buf.slice(offset, offset + payLen);
        buf = buf.slice(offset + payLen);
        if (opcode === 1) { // text
          const msg = payload.toString('utf8');
          handlers.forEach(h => h(msg));
        }
      }
    });

    socket.on('error', reject);

    const ws = {
      send(msg) {
        const data = Buffer.from(msg, 'utf8');
        const len = data.length;
        const mask = crypto.randomBytes(4);
        let header;
        if (len < 126) header = Buffer.from([0x81, 0x80 | len]);
        else if (len < 65536) { header = Buffer.alloc(4); header[0]=0x81; header[1]=0xfe; header.writeUInt16BE(len,2); }
        else { header = Buffer.alloc(10); header[0]=0x81; header[1]=0xff; header.writeBigUInt64BE(BigInt(len),2); }
        const frame = Buffer.concat([header, mask]);
        const masked = Buffer.alloc(len);
        for (let i = 0; i < len; i++) masked[i] = data[i] ^ mask[i % 4];
        socket.write(Buffer.concat([frame, masked]));
      },
      on(ev, fn) { if (ev === 'message') handlers.push(fn); },
      off(ev, fn) {
        if (ev === 'message') {
          const i = handlers.indexOf(fn);
          if (i !== -1) handlers.splice(i, 1);
        }
      },
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
  const raw = await httpGet(`http://${CDP_HOST}:${CDP_PORT}/json`);
  const tabs = JSON.parse(raw);
  const wa = tabs.find(t => t.url && t.url.includes('whatsapp') && t.type === 'page');
  if (!wa) { console.error('WhatsApp tab not found'); process.exit(1); }
  console.log('Tab:', wa.title, wa.url);

  const ws = await wsConnect(wa.webSocketDebuggerUrl);
  await cdpSend(ws, 'Runtime.enable');

  const code = `JSON.stringify((function() {
    const res = {};
    res.ces = Array.from(document.querySelectorAll('[contenteditable="true"]')).map(e => ({
      tag: e.tagName, aria: e.getAttribute('aria-label')||'',
      testid: e.getAttribute('data-testid')||'', tab: e.getAttribute('data-tab')||'',
      role: e.getAttribute('role')||'', text: (e.innerText||'').slice(0,30)
    }));
    res.inputs = Array.from(document.querySelectorAll('input')).map(e => ({
      type: e.type, aria: e.getAttribute('aria-label')||'',
      testid: e.getAttribute('data-testid')||'', placeholder: e.placeholder||''
    }));
    const sels = [
      '[data-testid="search-input"]','[data-testid="search-container"]',
      '[aria-label="Search input textbox"]','[aria-label="Search or start new chat"]',
      'div[contenteditable="true"][data-tab="3"]',
      'div[contenteditable="true"][aria-label*="Search"]',
      '[role="textbox"][aria-label*="Search"]',
      '[data-testid="chat-list-search"]','[data-testid="search-bar-input"]',
      'p.selectable-text[data-tab="3"]',
    ];
    res.checks = {};
    sels.forEach(s => {
      const found = document.querySelectorAll(s);
      if (found.length) {
        const e = found[0];
        res.checks[s] = {count:found.length, tag:e.tagName,
          aria:e.getAttribute('aria-label')||'', testid:e.getAttribute('data-testid')||'',
          tab:e.getAttribute('data-tab')||''};
      } else res.checks[s] = null;
    });
    return res;
  })())`;

  const r = await cdpSend(ws, 'Runtime.evaluate', { expression: code, returnByValue: true });
  const data = JSON.parse(r.result.value);

  console.log('\n=== SELECTOR CHECKS ===');
  for (const [sel, info] of Object.entries(data.checks)) {
    if (info) console.log(`  FOUND(${info.count}): ${sel}\n    tag=${info.tag} aria='${info.aria}' testid='${info.testid}' tab='${info.tab}'`);
    else console.log(`  not found: ${sel}`);
  }

  console.log('\n=== ALL CONTENTEDITABLE ===');
  data.ces.forEach(e => console.log(`  ${e.tag} aria='${e.aria}' testid='${e.testid}' tab='${e.tab}' role='${e.role}' text='${e.text}'`));

  console.log('\n=== ALL INPUTS ===');
  data.inputs.forEach(e => console.log(`  input[${e.type}] aria='${e.aria}' testid='${e.testid}' ph='${e.placeholder}'`));

  ws.close();
}

main().catch(e => { console.error(e.message); process.exit(1); });
