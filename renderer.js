/**
 * The KAKASHI Recon V 1.1 — Renderer Process
 * Handles UI interactions, ANSI parsing, result rendering, and scan lifecycle.
 */

'use strict';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const domainInput    = document.getElementById('domainInput');
const outputInput    = document.getElementById('outputInput');
const startBtn       = document.getElementById('startBtn');
const stopBtn        = document.getElementById('stopBtn');
const clearBtn       = document.getElementById('clearBtn');
const openDirBtn     = document.getElementById('openDirBtn');
const browseBtn      = document.getElementById('browseBtn');
const terminalBody   = document.getElementById('terminalBody');
const statusDot      = document.getElementById('statusDot');
const statusText     = document.getElementById('statusText');
const timerDisplay   = document.getElementById('timerDisplay');
const moduleProgress = document.getElementById('moduleProgress');
const selectAllBtn   = document.getElementById('selectAllBtn');
const selectNoneBtn  = document.getElementById('selectNoneBtn');
const selectQuickBtn = document.getElementById('selectQuickBtn');

// ── State ─────────────────────────────────────────────────────────────────────
let scanning      = false;
let timerInterval = null;
let elapsedSecs   = 0;
let lastDomain    = '';
let lastOutput    = '';
let lastReport    = null; // cached after scan for downloads

// ── ANSI → HTML Parser ────────────────────────────────────────────────────────
const ANSI_MAP = {
  '\x1b[0m':    '</span>',
  '\x1b[1m':    '<span class="b">',
  '\x1b[92m':   '<span class="green">',
  '\x1b[94m':   '<span class="blue">',
  '\x1b[93m':   '<span class="yellow">',
  '\x1b[91m':   '<span class="red">',
  '\x1b[90m':   '<span class="gray">',
  '\x1b[33m':   '<span class="yellow">',
  '\x1b[32m':   '<span class="green">',
  '\x1b[31m':   '<span class="red">',
  '\x1b[1;36m': '<span class="cyan b">',
  '\x1b[1;35m': '<span class="magenta b">',
  '\x1b[1;33m': '<span class="yellow b">',
  '\x1b[1;31m': '<span class="red b">',
  '\x1b[1;32m': '<span class="green b">',
};

function ansiToHtml(raw) {
  // Escape HTML entities first
  let str = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Apply known ANSI → HTML mappings
  for (const [code, html] of Object.entries(ANSI_MAP)) {
    // Escape regex metacharacters in the ANSI code
    const escaped = code.replace(/[\[\]\\^$.*+?(){}|]/g, '\\$&');
    str = str.replace(new RegExp(escaped, 'g'), html);
  }

  // Strip any remaining unknown ANSI codes
  str = str.replace(/\x1b\[[0-9;]*m/g, '');

  return str;
}

// ── Terminal Append ───────────────────────────────────────────────────────────
function appendToTerminal(rawText) {
  // Remove welcome message on first output
  const welcome = terminalBody.querySelector('.welcome-msg');
  if (welcome) welcome.remove();

  const html = ansiToHtml(rawText);
  const span = document.createElement('span');
  span.innerHTML = html;
  terminalBody.appendChild(span);

  // Auto-scroll
  terminalBody.scrollTop = terminalBody.scrollHeight;

  // Update module progress indicator
  const sectionMatch = rawText.match(/MODULE\s+(\d+)\s*[│|]\s*(.+)/);
  if (sectionMatch) {
    moduleProgress.textContent = `▸ ${sectionMatch[2].trim()}`;
  }
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function startTimer() {
  elapsedSecs = 0;
  timerDisplay.textContent = '00:00';
  timerInterval = setInterval(() => {
    elapsedSecs++;
    const m = String(Math.floor(elapsedSecs / 60)).padStart(2, '0');
    const s = String(elapsedSecs % 60).padStart(2, '0');
    timerDisplay.textContent = `${m}:${s}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
}

// ── Status ────────────────────────────────────────────────────────────────────
function setStatus(state) {
  statusDot.className  = `status-dot ${state}`;
  statusText.textContent = {
    idle:     'IDLE',
    scanning: 'SCANNING',
    done:     'COMPLETE',
    error:    'ERROR',
    stopped:  'STOPPED',
  }[state] || state.toUpperCase();
}

// ── Module checkbox helpers ───────────────────────────────────────────────────
function getCheckedModules() {
  const checked = [...document.querySelectorAll('.mod-cb:checked')];
  return checked.map(cb => cb.value).join(',') || 'all';
}

function setAllModules(val) {
  document.querySelectorAll('.mod-cb').forEach(cb => { cb.checked = val; });
}

// Quick preset: subdomains + s3 + tech + quick (fast & useful)
function setQuickPreset() {
  setAllModules(false);
  ['subdomains', 'tech', 'quick', 'dns', 'tls', 'cors', 'api'].forEach(m => {
    const cb = document.querySelector(`.mod-cb[value="${m}"]`);
    if (cb) cb.checked = true;
  });
}

// ── Button state helpers ──────────────────────────────────────────────────────
function setScanningState(active) {
  scanning = active;
  startBtn.disabled = active;
  stopBtn.disabled  = !active;
  domainInput.disabled = active;
}

// ── Tab switching ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove('hidden');
  });
});

// ── Results Rendering ─────────────────────────────────────────────────────────

function renderSummary(data) {
  const el = document.getElementById('tab-summary');
  const tech = Object.entries(data.technologies || {})
    .map(([k, v]) => `<span class="badge badge-blue">${k}: ${v}</span>`)
    .join('');

  const criticalWins = (data.quick_wins || []).filter(w => w.critical);

  el.innerHTML = `
    <div class="summary-grid">
      <div class="sum-card">
        <div class="sum-num green">${(data.subdomains || []).length}</div>
        <div class="sum-lbl">Live Subdomains</div>
      </div>
      <div class="sum-card">
        <div class="sum-num ${(data.s3_buckets || []).length > 0 ? 'yellow' : 'gray'}">${(data.s3_buckets || []).length}</div>
        <div class="sum-lbl">S3 Buckets Found</div>
      </div>
      <div class="sum-card">
        <div class="sum-num ${(data.quick_wins || []).length > 0 ? 'red' : 'gray'}">${(data.quick_wins || []).length}</div>
        <div class="sum-lbl">Quick Wins</div>
      </div>
      <div class="sum-card">
        <div class="sum-num ${criticalWins.length > 0 ? 'red b' : 'gray'}">${criticalWins.length}</div>
        <div class="sum-lbl">⚠ Critical Findings</div>
      </div>
      <div class="sum-card">
        <div class="sum-num blue">${(data.js_endpoints || []).length}</div>
        <div class="sum-lbl">JS Endpoints</div>
      </div>
      <div class="sum-card">
        <div class="sum-num">${(data.wayback_urls || []).length}</div>
        <div class="sum-lbl">Wayback URLs</div>
      </div>
    </div>
    <div class="sum-tech">
      <div class="sum-tech-label">TECHNOLOGY STACK</div>
      <div>${tech || '<span class="gray">Not detected</span>'}</div>
    </div>
    ${criticalWins.length > 0 ? `
      <div class="critical-banner">
        ⚠ ${criticalWins.length} CRITICAL FINDING(S) — CHECK QUICK WINS TAB
        <ul>
          ${criticalWins.map(w => `<li><a class="crit-link">${w.url}</a> — ${w.label} [${w.status}]</li>`).join('')}
        </ul>
      </div>` : ''}
  `;
}

function renderSubdomains(data) {
  const el   = document.getElementById('tab-subdomains');
  const subs = data.subdomains || [];
  if (!subs.length) { el.innerHTML = '<div class="empty-tab">No subdomains found.</div>'; return; }

  el.innerHTML = `
    <div class="result-header">
      Found <strong class="green">${subs.length}</strong> live subdomain(s)
    </div>
    <table class="result-table">
      <thead><tr><th>#</th><th>Host</th><th>IP Address</th></tr></thead>
      <tbody>
        ${subs.map((s, i) => `
          <tr>
            <td class="gray">${i + 1}</td>
            <td class="green mono">${escHtml(s.host)}</td>
            <td class="blue mono">${escHtml(s.ip)}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderS3(data) {
  const el  = document.getElementById('tab-s3');
  const bks = data.s3_buckets || [];
  if (!bks.length) { el.innerHTML = '<div class="empty-tab">No S3 buckets found.</div>'; return; }

  el.innerHTML = `
    <div class="result-header">
      Found <strong class="yellow">${bks.length}</strong> bucket(s)
    </div>
    <table class="result-table">
      <thead><tr><th>#</th><th>Bucket</th><th>URL</th><th>Status</th></tr></thead>
      <tbody>
        ${bks.map((b, i) => {
          const isPublic = b.status.includes('PUBLIC');
          return `
          <tr class="${isPublic ? 'row-critical' : ''}">
            <td class="gray">${i + 1}</td>
            <td class="yellow mono">${escHtml(b.bucket)}</td>
            <td class="blue mono">${escHtml(b.url)}</td>
            <td class="${isPublic ? 'red b' : 'yellow'}">${escHtml(b.status)}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

function renderTech(data) {
  const el   = document.getElementById('tab-tech');
  const tech = data.technologies || {};
  const keys = Object.keys(tech);
  if (!keys.length) { el.innerHTML = '<div class="empty-tab">No technology data.</div>'; return; }

  el.innerHTML = `
    <div class="result-header">
      Detected <strong class="blue">${keys.length}</strong> technology/ies
    </div>
    <table class="result-table">
      <thead><tr><th>Category</th><th>Value</th></tr></thead>
      <tbody>
        ${keys.map(k => `
          <tr>
            <td class="yellow">${escHtml(k)}</td>
            <td class="green">${escHtml(tech[k])}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderQuickWins(data) {
  const el  = document.getElementById('tab-quickwins');
  const wins = data.quick_wins || [];
  if (!wins.length) { el.innerHTML = '<div class="empty-tab">No accessible paths found.</div>'; return; }

  el.innerHTML = `
    <div class="result-header">
      Found <strong class="red">${wins.length}</strong> accessible path(s) — review each one!
    </div>
    <table class="result-table">
      <thead><tr><th>#</th><th>Label</th><th>URL</th><th>Status</th><th>Size</th><th>Critical</th></tr></thead>
      <tbody>
        ${wins.map((w, i) => `
          <tr class="${w.critical ? 'row-critical' : ''}">
            <td class="gray">${i + 1}</td>
            <td class="${w.critical ? 'red b' : 'green'}">${escHtml(w.label)}</td>
            <td class="blue mono">${escHtml(w.url)}</td>
            <td>${escHtml(String(w.status))}</td>
            <td class="gray">${w.size}b</td>
            <td>${w.critical ? '<span class="badge badge-red">⚠ YES</span>' : '<span class="badge">—</span>'}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderDns(data) {
  const el      = document.getElementById('tab-dns');
  const records = data.dns_records || {};
  const types   = Object.keys(records);
  if (!types.length) { el.innerHTML = '<div class="empty-tab">No DNS records collected.</div>'; return; }
  el.innerHTML = `
    <div class="result-header">DNS records for <strong class="green">${data.target}</strong></div>
    <table class="result-table">
      <thead><tr><th>Type</th><th>Records</th></tr></thead>
      <tbody>
        ${types.map(t => `
          <tr>
            <td class="yellow b">${escHtml(t)}</td>
            <td class="mono" style="white-space:pre-wrap">${records[t].map(v => escHtml(v)).join('\n')}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderTls(data) {
  const el  = document.getElementById('tab-tls');
  const tls = data.tls || {};
  if (tls.error) {
    el.innerHTML = `<div class="empty-tab red">TLS error: ${escHtml(tls.error)}</div>`;
    return;
  }
  if (!tls.cn) { el.innerHTML = '<div class="empty-tab">No TLS data collected.</div>'; return; }
  const daysClass = tls.days_left < 0 ? 'red b' : tls.days_left < 30 ? 'yellow' : 'green';
  el.innerHTML = `
    <table class="result-table">
      <thead><tr><th>Field</th><th>Value</th></tr></thead>
      <tbody>
        <tr><td class="yellow">Common Name</td><td class="green mono">${escHtml(tls.cn)}</td></tr>
        <tr><td class="yellow">Issuer</td><td>${escHtml(tls.issuer)}</td></tr>
        <tr><td class="yellow">TLS Version</td><td class="blue">${escHtml(tls.tls_version)}</td></tr>
        <tr><td class="yellow">Cipher</td><td class="mono">${escHtml(tls.cipher)}</td></tr>
        <tr><td class="yellow">Expires</td><td class="${daysClass}">${escHtml(tls.expires?.split('T')[0] || '?')} (${tls.days_left} days)</td></tr>
        <tr><td class="yellow">SANs</td><td class="mono">${(tls.sans || []).map(s => escHtml(s)).join(', ') || '—'}</td></tr>
      </tbody>
    </table>`;
}

function renderCors(data) {
  const el   = document.getElementById('tab-cors');
  const cors = data.cors || [];
  if (!cors.length) { el.innerHTML = '<div class="empty-tab green">✔ No CORS misconfigurations detected.</div>'; return; }
  el.innerHTML = `
    <div class="result-header">Found <strong class="red">${cors.length}</strong> CORS issue(s)</div>
    <table class="result-table">
      <thead><tr><th>Severity</th><th>Origin Tested</th><th>ACAO</th><th>Credentials</th></tr></thead>
      <tbody>
        ${cors.map(c => `
          <tr class="${c.severity === 'high' ? 'row-critical' : ''}">
            <td><span class="badge ${c.severity === 'high' ? 'badge-red' : 'badge-blue'}">${escHtml(c.severity.toUpperCase())}</span></td>
            <td class="mono">${escHtml(c.origin)}</td>
            <td class="yellow mono">${escHtml(c.acao)}</td>
            <td class="${c.credentials === 'true' ? 'red b' : 'gray'}">${escHtml(c.credentials || '—')}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderSecrets(data) {
  const el      = document.getElementById('tab-secrets');
  const secrets = data.js_secrets || [];
  if (!secrets.length) { el.innerHTML = '<div class="empty-tab green">✔ No secrets found in JS files.</div>'; return; }
  el.innerHTML = `
    <div class="result-header">Found <strong class="red">${secrets.length}</strong> potential secret(s) — verify manually!</div>
    <table class="result-table">
      <thead><tr><th>#</th><th>Type</th><th>Match</th><th>File</th></tr></thead>
      <tbody>
        ${secrets.map((s, i) => `
          <tr class="row-critical">
            <td class="gray">${i + 1}</td>
            <td><span class="badge badge-red">${escHtml(s.type)}</span></td>
            <td class="yellow mono">${escHtml(s.match)}</td>
            <td class="blue mono" style="font-size:10px;word-break:break-all">${escHtml(s.file)}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderApi(data) {
  const el  = document.getElementById('tab-api');
  const eps = data.api_endpoints || [];
  if (!eps.length) { el.innerHTML = '<div class="empty-tab">No API endpoints found.</div>'; return; }
  el.innerHTML = `
    <div class="result-header">Found <strong class="blue">${eps.length}</strong> API endpoint(s)</div>
    <table class="result-table">
      <thead><tr><th>#</th><th>Type</th><th>URL</th><th>Size</th></tr></thead>
      <tbody>
        ${eps.map((e, i) => `
          <tr class="${e.type === 'graphql-introspection' || e.type === 'swagger/openapi' ? 'row-critical' : ''}">
            <td class="gray">${i + 1}</td>
            <td><span class="badge ${e.type.includes('swagger') || e.type.includes('graphql') ? 'badge-red' : 'badge-blue'}">${escHtml(e.type)}</span></td>
            <td class="blue mono">${escHtml(e.url)}</td>
            <td class="gray">${e.size || 0}b</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderJson(data) {
  document.getElementById('jsonView').textContent = JSON.stringify(data, null, 2);
}

function updateStats(data) {
  document.getElementById('statSubs').textContent = (data.subdomains  || []).length;
  document.getElementById('statS3').textContent   = (data.s3_buckets || []).length;
  document.getElementById('statQW').textContent   = (data.quick_wins || []).length;
  document.getElementById('statJS').textContent   = (data.js_endpoints || []).length;
  document.getElementById('statWB').textContent   = (data.wayback_urls || []).length;
  const techCount = Object.keys(data.technologies || {}).length;
  document.getElementById('statTech').textContent = techCount;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Toast notification ────────────────────────────────────────────────────────
function showToast(msg, isError = false) {
  const t = document.createElement('div');
  t.className = 'toast' + (isError ? ' error' : '');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── Report generators ─────────────────────────────────────────────────────────

function generateCsv(data) {
  const esc  = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const rows = [];

  rows.push('=== KAKASHI RECON REPORT ===');
  rows.push(`Target,${esc(data.target)}`);
  rows.push(`Scan Time,${esc(data.scan_time || '')}`);
  rows.push('');

  rows.push('--- SUBDOMAINS ---');
  rows.push('Host,IP');
  (data.subdomains || []).forEach(s => rows.push(`${esc(s.host)},${esc(s.ip)}`));
  rows.push('');

  rows.push('--- S3 BUCKETS ---');
  rows.push('Bucket,URL,Status');
  (data.s3_buckets || []).forEach(b => rows.push(`${esc(b.bucket)},${esc(b.url)},${esc(b.status)}`));
  rows.push('');

  rows.push('--- TECHNOLOGIES ---');
  rows.push('Category,Value');
  Object.entries(data.technologies || {}).forEach(([k, v]) => rows.push(`${esc(k)},${esc(v)}`));
  rows.push('');

  rows.push('--- QUICK WINS ---');
  rows.push('Label,URL,Status,Size (bytes),Critical');
  (data.quick_wins || []).forEach(w =>
    rows.push(`${esc(w.label)},${esc(w.url)},${esc(w.status)},${esc(w.size)},${esc(w.critical ? 'YES' : 'NO')}`)
  );
  rows.push('');

  rows.push('--- DNS RECORDS ---');
  rows.push('Type,Value');
  Object.entries(data.dns_records || {}).forEach(([type, vals]) =>
    (vals || []).forEach(v => rows.push(`${esc(type)},${esc(v)}`))
  );
  rows.push('');

  rows.push('--- TLS / SSL ---');
  const tls = data.tls || {};
  if (tls.cn) {
    rows.push(`Common Name,${esc(tls.cn)}`);
    rows.push(`Issuer,${esc(tls.issuer)}`);
    rows.push(`TLS Version,${esc(tls.tls_version)}`);
    rows.push(`Cipher,${esc(tls.cipher)}`);
    rows.push(`Expires,${esc(tls.expires)}`);
    rows.push(`Days Left,${esc(tls.days_left)}`);
  }
  rows.push('');

  rows.push('--- CORS ISSUES ---');
  rows.push('Severity,Origin,ACAO,Credentials');
  (data.cors || []).forEach(c =>
    rows.push(`${esc(c.severity)},${esc(c.origin)},${esc(c.acao)},${esc(c.credentials || '')}`)
  );
  rows.push('');

  rows.push('--- JS SECRETS ---');
  rows.push('Type,Match,File');
  (data.js_secrets || []).forEach(s =>
    rows.push(`${esc(s.type)},${esc(s.match)},${esc(s.file)}`)
  );
  rows.push('');

  rows.push('--- API ENDPOINTS ---');
  rows.push('Type,URL,Size (bytes)');
  (data.api_endpoints || []).forEach(e =>
    rows.push(`${esc(e.type)},${esc(e.url)},${esc(e.size || 0)}`)
  );

  return rows.join('\r\n');
}

function generateHtml(data) {
  const target  = escHtml(data.target || 'Unknown');
  const scanned = escHtml(data.scan_time || new Date().toISOString());
  const subs    = data.subdomains    || [];
  const buckets = data.s3_buckets   || [];
  const wins    = data.quick_wins   || [];
  const cors    = data.cors         || [];
  const secrets = data.js_secrets   || [];
  const apis    = data.api_endpoints || [];
  const tls     = data.tls          || {};
  const dns     = data.dns_records  || {};
  const tech    = data.technologies || {};

  const critical = wins.filter(w => w.critical).length;

  const techBadges = Object.entries(tech)
    .map(([k, v]) => `<span class="badge">${escHtml(k)}: ${escHtml(v)}</span>`).join('');

  const tableRow  = cells => `<tr>${cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
  const thRow     = cells => `<tr>${cells.map(c => `<th>${c}</th>`).join('')}</tr>`;

  const subTable = subs.length
    ? `<table><thead>${thRow(['#','Host','IP'])}</thead><tbody>
       ${subs.map((s, i) => tableRow([i+1, `<span class="g">${escHtml(s.host)}</span>`, `<span class="b">${escHtml(s.ip)}</span>`])).join('')}
       </tbody></table>` : '<p class="none">None found.</p>';

  const s3Table = buckets.length
    ? `<table><thead>${thRow(['#','Bucket','URL','Status'])}</thead><tbody>
       ${buckets.map((b, i) => `<tr class="${b.status.includes('PUBLIC') ? 'crit' : ''}">
         <td>${i+1}</td><td class="y">${escHtml(b.bucket)}</td>
         <td class="b">${escHtml(b.url)}</td>
         <td class="${b.status.includes('PUBLIC') ? 'r' : 'y'}">${escHtml(b.status)}</td></tr>`).join('')}
       </tbody></table>` : '<p class="none">No buckets found.</p>';

  const winsTable = wins.length
    ? `<table><thead>${thRow(['#','Label','URL','Status','Size','Critical'])}</thead><tbody>
       ${wins.map((w, i) => `<tr class="${w.critical ? 'crit' : ''}">
         <td>${i+1}</td><td class="${w.critical ? 'r' : 'g'}">${escHtml(w.label)}</td>
         <td class="b">${escHtml(w.url)}</td><td>${escHtml(String(w.status))}</td>
         <td>${w.size}b</td><td>${w.critical ? '<span class="badge-r">⚠ YES</span>' : '—'}</td></tr>`).join('')}
       </tbody></table>` : '<p class="none">None found.</p>';

  const dnsRows = Object.entries(dns).map(([type, vals]) =>
    (vals || []).map(v => tableRow([`<span class="y">${type}</span>`, escHtml(v)])).join('')
  ).join('');
  const dnsTable = dnsRows ? `<table><thead>${thRow(['Type','Record'])}</thead><tbody>${dnsRows}</tbody></table>`
    : '<p class="none">No DNS records collected.</p>';

  const tlsHtml = tls.cn ? `
    <table><thead>${thRow(['Field','Value'])}</thead><tbody>
      ${tableRow(['Common Name', `<span class="g">${escHtml(tls.cn)}</span>`])}
      ${tableRow(['Issuer', escHtml(tls.issuer)])}
      ${tableRow(['TLS Version', `<span class="b">${escHtml(tls.tls_version)}</span>`])}
      ${tableRow(['Cipher', escHtml(tls.cipher)])}
      ${tableRow(['Expires', `<span class="${tls.days_left < 30 ? 'r' : 'g'}">${escHtml(tls.expires?.split('T')[0] || '?')} (${tls.days_left} days)</span>`])}
      ${tableRow(['SANs', (tls.sans || []).map(s => escHtml(s)).join(', ') || '—'])}
    </tbody></table>` : '<p class="none">No TLS data.</p>';

  const corsTable = cors.length
    ? `<table><thead>${thRow(['Severity','Origin','ACAO','Credentials'])}</thead><tbody>
       ${cors.map(c => `<tr class="${c.severity === 'high' ? 'crit' : ''}">
         <td><span class="${c.severity === 'high' ? 'badge-r' : 'badge-b'}">${escHtml(c.severity.toUpperCase())}</span></td>
         <td>${escHtml(c.origin)}</td><td class="y">${escHtml(c.acao)}</td>
         <td class="${c.credentials === 'true' ? 'r' : ''}">${escHtml(c.credentials || '—')}</td></tr>`).join('')}
       </tbody></table>` : '<p class="none g">✔ No CORS misconfigurations detected.</p>';

  const secretsTable = secrets.length
    ? `<table><thead>${thRow(['#','Type','Match','File'])}</thead><tbody>
       ${secrets.map((s, i) => `<tr class="crit"><td>${i+1}</td>
         <td><span class="badge-r">${escHtml(s.type)}</span></td>
         <td class="y">${escHtml(s.match)}</td>
         <td class="b" style="font-size:10px;word-break:break-all">${escHtml(s.file)}</td></tr>`).join('')}
       </tbody></table>` : '<p class="none g">✔ No secrets found.</p>';

  const apiTable = apis.length
    ? `<table><thead>${thRow(['#','Type','URL','Size'])}</thead><tbody>
       ${apis.map((e, i) => `<tr class="${e.type.includes('swagger') || e.type.includes('graphql') ? 'crit' : ''}">
         <td>${i+1}</td>
         <td><span class="${e.type.includes('swagger') || e.type.includes('graphql') ? 'badge-r' : 'badge-b'}">${escHtml(e.type)}</span></td>
         <td class="b">${escHtml(e.url)}</td><td>${e.size || 0}b</td></tr>`).join('')}
       </tbody></table>` : '<p class="none">No API endpoints found.</p>';

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>KAKASHI RECON Report — ${target}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0d1117;color:#c9d1d9;font-family:Consolas,'Courier New',monospace;font-size:13px;padding:24px}
  h1{color:#39d353;font-size:20px;letter-spacing:2px;margin-bottom:4px}
  .meta{color:#8b949e;font-size:11px;margin-bottom:24px}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}
  .stat{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px;text-align:center}
  .stat-num{font-size:26px;font-weight:700;line-height:1;margin-bottom:4px}
  .stat-lbl{font-size:10px;color:#8b949e;letter-spacing:0.5px}
  h2{font-size:13px;letter-spacing:1px;color:#8b949e;text-transform:uppercase;margin:20px 0 10px;
     padding-bottom:4px;border-bottom:1px solid #21262d}
  table{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:8px}
  th{text-align:left;padding:5px 10px;background:#161b22;color:#8b949e;font-size:10px;
     letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid #30363d}
  td{padding:5px 10px;border-bottom:1px solid #21262d;word-break:break-all}
  tr:hover td{background:#161b22}
  tr.crit td{background:rgba(248,81,73,0.07)}
  .g{color:#39d353}.b{color:#58a6ff}.y{color:#e3b341}.r{color:#f85149}
  .badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;
         background:#161b22;border:1px solid #30363d;margin:2px}
  .badge-r{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;
            background:rgba(248,81,73,0.15);border:1px solid #f85149;color:#f85149}
  .badge-b{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;
            background:rgba(88,166,255,0.15);border:1px solid #58a6ff;color:#58a6ff}
  .none{color:#8b949e;font-size:12px;padding:8px 0}
  .tech-wrap{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}
  .critical-banner{background:rgba(248,81,73,0.1);border:1px solid #f85149;
                   border-radius:6px;padding:12px;color:#f85149;font-size:12px;
                   font-weight:600;margin-bottom:20px}
  .critical-banner ul{margin-top:6px;padding-left:16px;font-weight:400;color:#c9d1d9;font-size:11px}
  .ascii{color:#39d353;font-size:7.5px;line-height:1.2;margin-bottom:8px}
  @media print{body{background:#fff;color:#000}th{background:#eee}
    .g{color:#0a0}.b{color:#00f}.y{color:#a80}.r{color:#f00}}
</style>
</head>
<body>
<pre class="ascii"> ██╗  ██╗ █████╗ ██╗  ██╗ █████╗ ███████╗██╗  ██╗██╗
 ██║ ██╔╝██╔══██╗██║ ██╔╝██╔══██╗██╔════╝██║  ██║██║
 █████╔╝ ███████║█████╔╝ ███████║███████╗███████║██║
 ██╔═██╗ ██╔══██║██╔═██╗ ██╔══██║╚════██║██╔══██║██║
 ██║  ██╗██║  ██║██║  ██╗██║  ██║███████║██║  ██║██║
 ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝
      ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗
      ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║
      ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║
      ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║
      ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
      ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝╚═╝  ╚═══╝</pre>
<h1>RECON REPORT</h1>
<div class="meta">Target: <span class="g">${target}</span> &nbsp;|&nbsp; Scanned: ${scanned} &nbsp;|&nbsp; Recon Like A Bug Hunter</div>

${critical > 0 ? `<div class="critical-banner">⚠ ${critical} CRITICAL FINDING(S) DETECTED
  <ul>${wins.filter(w=>w.critical).map(w=>`<li>${escHtml(w.url)} — ${escHtml(w.label)} [${escHtml(String(w.status))}]</li>`).join('')}</ul>
</div>` : ''}

<div class="stats">
  <div class="stat"><div class="stat-num g">${subs.length}</div><div class="stat-lbl">Subdomains</div></div>
  <div class="stat"><div class="stat-num ${buckets.length > 0 ? 'y' : ''}">${buckets.length}</div><div class="stat-lbl">S3 Buckets</div></div>
  <div class="stat"><div class="stat-num ${wins.length > 0 ? 'r' : ''}">${wins.length}</div><div class="stat-lbl">Quick Wins</div></div>
  <div class="stat"><div class="stat-num ${critical > 0 ? 'r' : ''}">${critical}</div><div class="stat-lbl">⚠ Critical</div></div>
  <div class="stat"><div class="stat-num b">${(data.js_endpoints||[]).length}</div><div class="stat-lbl">JS Endpoints</div></div>
  <div class="stat"><div class="stat-num">${(data.wayback_urls||[]).length}</div><div class="stat-lbl">Wayback URLs</div></div>
  <div class="stat"><div class="stat-num ${secrets.length > 0 ? 'r' : ''}">${secrets.length}</div><div class="stat-lbl">JS Secrets</div></div>
  <div class="stat"><div class="stat-num b">${apis.length}</div><div class="stat-lbl">API Endpoints</div></div>
</div>

<h2>🔍 Technology Stack</h2>
<div class="tech-wrap">${techBadges || '<span class="none">Not detected</span>'}</div>

<h2>🌐 Subdomains (${subs.length})</h2>${subTable}
<h2>🪣 S3 Buckets (${buckets.length})</h2>${s3Table}
<h2>⚡ Quick Wins (${wins.length})</h2>${winsTable}
<h2>🗺️ DNS Records</h2>${dnsTable}
<h2>🔒 TLS / SSL</h2>${tlsHtml}
<h2>🌐 CORS Issues (${cors.length})</h2>${corsTable}
<h2>🔑 JS Secrets (${secrets.length})</h2>${secretsTable}
<h2>🔌 API Endpoints (${apis.length})</h2>${apiTable}
</body>
</html>`;
}

// ── Enable/disable download buttons ──────────────────────────────────────────
function setDownloadEnabled(enabled) {
  ['dlHtml', 'dlCsv', 'dlPdf', 'dlJson'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = !enabled;
  });
}

// ── Load + render report ──────────────────────────────────────────────────────
async function loadReport() {
  const res = await window.electronAPI.readReport({
    domain: lastDomain,
    output: lastOutput,
  });
  if (res.success) {
    const d = res.data;
    lastReport = d;
    renderSummary(d);
    renderSubdomains(d);
    renderS3(d);
    renderTech(d);
    renderQuickWins(d);
    renderDns(d);
    renderTls(d);
    renderCors(d);
    renderSecrets(d);
    renderApi(d);
    renderJson(d);
    updateStats(d);
    setDownloadEnabled(true);
    document.querySelector('[data-tab="summary"]').click();
  }
}

// ── Event: Start Scan ─────────────────────────────────────────────────────────
startBtn.addEventListener('click', async () => {
  const domain = domainInput.value.trim()
    .replace(/^https?:\/\//, '')
    .replace(/\/+$/, '')
    .toLowerCase();

  if (!domain) {
    domainInput.focus();
    domainInput.classList.add('input-error');
    setTimeout(() => domainInput.classList.remove('input-error'), 1200);
    return;
  }

  const modules = getCheckedModules();
  const output  = outputInput.value.trim() || 'recon_output';

  lastDomain = domain;
  lastOutput = output;

  // Clear previous output
  terminalBody.innerHTML = '';
  moduleProgress.textContent = '';

  // Reset stats
  ['statSubs','statS3','statQW','statJS','statWB','statTech'].forEach(id => {
    document.getElementById(id).textContent = '–';
  });

  // Reset result tabs
  ['summary','subdomains','s3','tech','quickwins','dns','tls','cors','secrets','api'].forEach(tab => {
    document.getElementById(`tab-${tab}`).innerHTML =
      '<div class="empty-tab">Scanning…</div>';
  });
  document.getElementById('jsonView').textContent = 'Scanning…';

  setScanningState(true);
  setStatus('scanning');
  startTimer();

  window.electronAPI.removeListeners();

  window.electronAPI.onScanOutput(({ type, data }) => {
    appendToTerminal(data);
  });

  window.electronAPI.onScanComplete(async ({ code }) => {
    stopTimer();
    setScanningState(false);
    moduleProgress.textContent = '';

    if (code === 0 || code === null) {
      setStatus('done');
      appendToTerminal('\n\x1b[92m[✔] Scan complete! Loading results…\x1b[0m\n');
      await loadReport();
    } else if (code === -1) {
      setStatus('error');
    } else {
      setStatus('stopped');
    }
  });

  const result = await window.electronAPI.startScan({ domain, modules, output });
  if (!result.success) {
    setScanningState(false);
    stopTimer();
    setStatus('error');
    appendToTerminal(`\x1b[91m[✘] ${result.error}\x1b[0m\n`);
  }
});

// ── Event: Stop Scan ──────────────────────────────────────────────────────────
stopBtn.addEventListener('click', async () => {
  await window.electronAPI.stopScan();
  setScanningState(false);
  stopTimer();
  setStatus('stopped');
  appendToTerminal('\n\x1b[93m[!] Scan stopped by user.\x1b[0m\n');
  moduleProgress.textContent = '';
});

// ── Event: Clear ──────────────────────────────────────────────────────────────
clearBtn.addEventListener('click', () => {
  terminalBody.innerHTML = '';
  moduleProgress.textContent = '';
  timerDisplay.textContent = '00:00';
  setStatus('idle');
});

// ── Event: Open output dir ────────────────────────────────────────────────────
openDirBtn.addEventListener('click', () => {
  const output = outputInput.value.trim() || 'recon_output';
  window.electronAPI.openOutputDir({ output });
});

// ── Event: Browse for dir ─────────────────────────────────────────────────────
browseBtn.addEventListener('click', async () => {
  const result = await window.electronAPI.selectDir();
  if (result.path) outputInput.value = result.path;
});

// ── Event: Module quick buttons ───────────────────────────────────────────────
selectAllBtn.addEventListener('click',   () => setAllModules(true));
selectNoneBtn.addEventListener('click',  () => setAllModules(false));
selectQuickBtn.addEventListener('click', () => setQuickPreset());

// ── Event: Enter key on domain input ─────────────────────────────────────────
domainInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !scanning) startBtn.click();
});

// ── Event: Download HTML ──────────────────────────────────────────────────────
document.getElementById('dlHtml').addEventListener('click', async () => {
  if (!lastReport) return;
  const html     = generateHtml(lastReport);
  const safeName = (lastReport.target || 'report').replace(/[^a-z0-9_.-]/gi, '_');
  const res = await window.electronAPI.saveFile({
    content:     html,
    defaultName: `${safeName}_recon_report.html`,
    filters:     [{ name: 'HTML Files', extensions: ['html'] }],
  });
  if (res.success) showToast(`✔ HTML saved: ${res.filePath.split(/[/\\]/).pop()}`);
  else if (res.error !== 'cancelled') showToast(`✘ ${res.error}`, true);
});

// ── Event: Download CSV ───────────────────────────────────────────────────────
document.getElementById('dlCsv').addEventListener('click', async () => {
  if (!lastReport) return;
  const csv      = generateCsv(lastReport);
  const safeName = (lastReport.target || 'report').replace(/[^a-z0-9_.-]/gi, '_');
  const res = await window.electronAPI.saveFile({
    content:     csv,
    defaultName: `${safeName}_recon_report.csv`,
    filters:     [{ name: 'CSV Files', extensions: ['csv'] }],
  });
  if (res.success) showToast(`✔ CSV saved: ${res.filePath.split(/[/\\]/).pop()}`);
  else if (res.error !== 'cancelled') showToast(`✘ ${res.error}`, true);
});

// ── Event: Download PDF ───────────────────────────────────────────────────────
document.getElementById('dlPdf').addEventListener('click', async () => {
  if (!lastReport) return;
  const html     = generateHtml(lastReport);
  const safeName = (lastReport.target || 'report').replace(/[^a-z0-9_.-]/gi, '_');
  showToast('⏳ Generating PDF…');
  const res = await window.electronAPI.generatePdf({
    htmlContent: html,
    defaultName: `${safeName}_recon_report.pdf`,
  });
  if (res.success) showToast(`✔ PDF saved: ${res.filePath.split(/[/\\]/).pop()}`);
  else if (res.error !== 'cancelled') showToast(`✘ ${res.error}`, true);
});

// ── Event: Download JSON ──────────────────────────────────────────────────────
document.getElementById('dlJson').addEventListener('click', async () => {
  if (!lastReport) return;
  const json     = JSON.stringify(lastReport, null, 2);
  const safeName = (lastReport.target || 'report').replace(/[^a-z0-9_.-]/gi, '_');
  const res = await window.electronAPI.saveFile({
    content:     json,
    defaultName: `${safeName}_recon_report.json`,
    filters:     [{ name: 'JSON Files', extensions: ['json'] }],
  });
  if (res.success) showToast(`✔ JSON saved: ${res.filePath.split(/[/\\]/).pop()}`);
  else if (res.error !== 'cancelled') showToast(`✘ ${res.error}`, true);
});
