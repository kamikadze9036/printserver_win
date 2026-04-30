// ════════════════════════════════════════
//  debug.js — debug panel logika
// ════════════════════════════════════════

let allLogs = [];
let activeFilter = 'ALL';
let autoTimer = null;

window.addEventListener('DOMContentLoaded', () => {
  loadSystem();
  loadStatus();
  loadLogs();
  toggleAuto(true);
  setInterval(loadStatus, 10000);
});

async function loadSystem() {
  try {
    const d = await api('/api/debug/system');
    const rows = [
      ['Hostname', d.hostname],
      ['IP adresa', d.ip],
      ['Uptime', d.uptime],
      ['CPU teplota', d.cpu_temp],
      ['CPU zátěž', d.cpu_load],
      ['RAM celkem', d.mem_total],
      ['RAM použito', d.mem_used],
      ['Disk celkem', d.disk_total],
      ['Disk volno', d.disk_free],
      ['Python', d.python],
    ];
    document.getElementById('sysinfo').innerHTML = rows.map(([l, v]) =>
      `<div class="si-row"><span class="si-lbl">${l}</span><span class="si-val">${escHtml(String(v))}</span></div>`
    ).join('');
    // Naplnit nazvy tiskarnen
    const devL = document.getElementById('pcard-dev-L');
    const devR = document.getElementById('pcard-dev-R');
    if (devL) devL.textContent = d.printer_L_dev || '—';
    if (devR) devR.textContent = d.printer_R_dev || '—';
  } catch (e) {
    document.getElementById('sysinfo').innerHTML =
      `<div class="si-row"><span class="si-val err">${e.message}</span></div>`;
  }
}

async function loadStatus() {
  try {
    const d = await api('/api/status');
    ['L', 'R'].forEach(s => {
      const ok   = d['printer_' + s];
      const dot  = document.getElementById('pdot-' + s);
      const txt  = document.getElementById('ptxt-' + s);
      const card = document.getElementById('pcard-' + s);
      if (!dot) return;
      dot.className = 'sdot ' + (ok ? 'sdot-ok' : 'sdot-err');
      txt.textContent = ok ? 'ONLINE' : 'OFFLINE';
      card.className  = 'pcard ' + (ok ? 'online' : 'offline');
    });
  } catch (e) { toast('Stav: ' + e.message, true); }
}

async function testPrint(side) {
  try {
    const d = await api(`/api/debug/testprint/${side}`, {method: 'POST'});
    toast('✓ ' + d.message);
  } catch (e) { toast('Test tisk chyba: ' + e.message, true); }
}

async function simGpio(side) {
  const dot = document.getElementById('gpio-dot-' + side);
  dot.classList.add('triggered');
  setTimeout(() => dot.classList.remove('triggered'), 800);
  try {
    await api(`/api/debug/gpio/${side}`, {method: 'POST'});
    const now = new Date().toLocaleTimeString('cs-CZ', {hour12: false});
    document.getElementById('gpio-last-' + side).textContent = `OK — ${now}`;
    toast(`GPIO simulace strana ${side} OK`);
  } catch (e) {
    document.getElementById('gpio-last-' + side).textContent = 'Chyba: ' + e.message;
    toast('GPIO chyba: ' + e.message, true);
  }
}

async function loadTspl(side) {
  const el = document.getElementById('tspl-' + side);
  el.innerHTML = '<span style="color:var(--grey-dk)">Načítám…</span>';
  try {
    const d = await api(`/api/debug/tspl/${side}`);
    el.textContent = d.tspl;
  } catch (e) {
    el.innerHTML = `<span style="color:var(--err)">${escHtml(e.message)}</span>`;
  }
}

async function loadLogs() {
  try {
    allLogs = await api('/api/debug/logs?lines=300');
    renderLog();
  } catch (e) {
    document.getElementById('log-console').innerHTML =
      `<div style="color:var(--err);font-family:var(--mono);font-size:12px">${escHtml(e.message)}</div>`;
  }
}

function setFilter(level, btn) {
  activeFilter = level;
  document.querySelectorAll('.lf-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderLog();
}

function renderLog() {
  const search  = document.getElementById('log-search').value.toLowerCase();
  const console = document.getElementById('log-console');

  let filtered = allLogs;
  if (activeFilter !== 'ALL') filtered = filtered.filter(l => l.level.trim() === activeFilter);
  if (search) filtered = filtered.filter(l => l.raw.toLowerCase().includes(search));

  const counts = {DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0};
  allLogs.forEach(l => { const lv = l.level.trim(); if (counts[lv] !== undefined) counts[lv]++; });
  document.getElementById('log-stats').innerHTML =
    `Celkem: <span>${allLogs.length}</span> &nbsp;|&nbsp; INFO: <span>${counts.INFO}</span> &nbsp;|&nbsp; WARN: <span>${counts.WARNING}</span> &nbsp;|&nbsp; ERROR: <span>${counts.ERROR}</span>`;

  if (!filtered.length) {
    console.innerHTML = '<div style="color:var(--grey-dk);font-size:11px;font-family:var(--mono)">Žádné záznamy.</div>';
    return;
  }

  console.innerHTML = filtered.map(l => {
    const lv = l.level.trim();
    return `<div class="log-line">
      <span class="log-ts">${escHtml(l.timestamp)}</span>
      <span class="log-lvl lvl-${lv}">${lv}</span>
      <span class="log-mod">${escHtml(l.module)}</span>
      <span class="log-msg">${escHtml(l.message)}</span>
    </div>`;
  }).join('');

  console.scrollTop = console.scrollHeight;
}

function clearDisplay() { allLogs = []; renderLog(); }

function toggleAuto(on) {
  if (autoTimer) clearInterval(autoTimer);
  if (on) autoTimer = setInterval(loadLogs, 5000);
}
