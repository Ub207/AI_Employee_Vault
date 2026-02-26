/**
 * Take a CDP screenshot and dump ALL interactive elements to find compose box.
 */
const http = require('http');
const net = require('net');
const crypto = require('crypto');
const fs = require('fs');

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
          (h => { h[0]=0x81; h[1]=0xfe; h.writeUInt16BE(len,2); return h; })(Buffer.alloc(4));
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

  const ws = await wsConnect(wa.webSocketDebuggerUrl);
  await cdpSend(ws, 'Runtime.enable');

  // First press Escape to go back to chat list
  await cdpSend(ws, 'Runtime.evaluate', {
    expression: `document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape',keyCode:27,bubbles:true}))`,
    returnByValue: true
  });
  await sleep(500);

  // Click the search box and search for a specific contact (first non-group chat)
  // First let's find what chats are listed
  const listResult = await cdpSend(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify((function() {
      // Find all chat list items
      const items = document.querySelectorAll('[role="listitem"], [data-testid="cell-frame-container"]');
      const chats = [];
      for (const item of items) {
        if (!item.offsetParent) continue;
        // Check if it's a group (has group icon or ":" in last message)
        const groupIcon = item.querySelector('[data-icon="group"],[data-icon="groups"],[data-icon="community"],[data-icon="default-group"]');
        const spans = Array.from(item.querySelectorAll('span'));
        const nameSpan = spans.find(s => s.textContent.trim().length > 1 && !s.querySelector('span'));
        const name = nameSpan ? nameSpan.textContent.trim() : '';
        chats.push({ name: name.substring(0, 40), isGroup: !!groupIcon });
        if (chats.length >= 10) break;
      }
      return chats;
    })())`,
    returnByValue: true
  });
  const chats = JSON.parse(listResult.result.value);
  console.log('Available chats:');
  chats.forEach((c, i) => console.log(`  ${i}: ${c.isGroup ? '[GROUP]' : '[1-on-1]'} ${c.name}`));

  // Find the first non-group (1-on-1) chat
  const target = chats.findIndex(c => !c.isGroup);
  console.log(`\nClicking chat ${target}: ${chats[target] ? chats[target].name : 'none'}`);

  if (target === -1) {
    console.log('No 1-on-1 chat found — using first available chat');
  }

  // Click the target chat item
  const clickResult = await cdpSend(ws, 'Runtime.evaluate', {
    expression: `JSON.stringify((function() {
      const items = document.querySelectorAll('[role="listitem"], [data-testid="cell-frame-container"]');
      let count = 0, target = ${target === -1 ? 0 : target};
      for (const item of items) {
        if (!item.offsetParent) continue;
        if (count === target) {
          item.click();
          return { clicked: true, idx: count };
        }
        count++;
      }
      return { clicked: false };
    })())`,
    returnByValue: true
  });
  console.log('Click result:', clickResult.result.value);
  await sleep(2500);

  // Now take a screenshot to see the current state
  const shot = await cdpSend(ws, 'Page.captureScreenshot', { format: 'png', quality: 80 });
  const shotPath = 'D:\\AI_Employee_Vault\\screenshots\\compose_inspect.png';
  fs.writeFileSync(shotPath, Buffer.from(shot.data, 'base64'));
  console.log('Screenshot saved:', shotPath);

  // Comprehensive DOM dump to find compose box
  const code = `JSON.stringify((function() {
    // ALL contenteditable elements on the page
    const allCE = Array.from(document.querySelectorAll('[contenteditable]')).map(e => {
      const rect = e.getBoundingClientRect();
      return {
        tag: e.tagName,
        ce: e.getAttribute('contenteditable'),
        aria: e.getAttribute('aria-label') || '',
        testid: e.getAttribute('data-testid') || '',
        tab: e.getAttribute('data-tab') || '',
        title: e.getAttribute('title') || '',
        role: e.getAttribute('role') || '',
        spellcheck: e.getAttribute('spellcheck') || '',
        placeholder: e.getAttribute('placeholder') || '',
        classname: (e.className || '').substring(0,60),
        text: (e.innerText||'').substring(0,30),
        rect: {w:Math.round(rect.width), h:Math.round(rect.height), top:Math.round(rect.top), left:Math.round(rect.left)},
        visible: rect.width > 0 && rect.height > 0,
      };
    });

    // Look for footer area (compose box container)
    const footerSels = [
      'footer', '[data-testid="conversation-footer"]',
      '[data-testid="compose-box-input-container"]',
      '#main footer', '[role="region"][aria-label*="message"]',
      'div[tabindex="10"]', 'div[tabindex="-1"] > div[contenteditable]',
    ];
    const footerInfo = {};
    for (const sel of footerSels) {
      const el = document.querySelector(sel);
      footerInfo[sel] = el ? {
        found: true,
        tag: el.tagName,
        aria: el.getAttribute('aria-label') || '',
        testid: el.getAttribute('data-testid') || '',
        children_count: el.children.length,
      } : null;
    }

    // #main children structure
    const main = document.querySelector('#main');
    const mainChildren = main ? Array.from(main.children).map(c => ({
      tag: c.tagName, id: c.id, role: c.getAttribute('role') || '',
      aria: (c.getAttribute('aria-label') || '').substring(0,30),
      testid: c.getAttribute('data-testid') || '',
      classname: (c.className||'').substring(0,40),
    })) : [];

    return { allCE, footerInfo, mainChildren };
  })())`;

  const r = await cdpSend(ws, 'Runtime.evaluate', { expression: code, returnByValue: true });
  const data = JSON.parse(r.result.value);

  console.log('\n=== ALL CONTENTEDITABLE ELEMENTS ===');
  data.allCE.forEach(e => {
    const v = e.visible ? 'VISIBLE' : 'hidden';
    console.log(`  [${v}] ${e.tag}[ce=${e.ce}] aria='${e.aria}' testid='${e.testid}' tab='${e.tab}' title='${e.title}' role='${e.role}' spellcheck='${e.spellcheck}'`);
    console.log(`    rect=${JSON.stringify(e.rect)} text='${e.text}'`);
  });

  console.log('\n=== FOOTER / COMPOSE CONTAINER ===');
  for (const [sel, info] of Object.entries(data.footerInfo)) {
    if (info) console.log(`  FOUND: ${sel} → ${info.tag} aria='${info.aria}' testid='${info.testid}' children=${info.children_count}`);
    else console.log(`  not found: ${sel}`);
  }

  console.log('\n=== #MAIN CHILDREN ===');
  data.mainChildren.forEach(c => console.log(`  ${c.tag}#${c.id} role='${c.role}' aria='${c.aria}' testid='${c.testid}' class='${c.classname}'`));

  ws.close();
}

main().catch(e => { console.error(e.message); process.exit(1); });
