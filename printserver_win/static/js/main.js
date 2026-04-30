// ════════════════════════════════════════
//  main.js — sdílené utility
// ════════════════════════════════════════

// ── Clock ──
setInterval(() => {
  const el = document.getElementById('clock');
  if (el) el.textContent = new Date().toLocaleTimeString('cs-CZ', {hour12: false});
}, 1000);

// ── Toast ──
function toast(msg, isErr = false) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = 'toast show' + (isErr ? ' error' : '');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), 3500);
}

// ── API helper ──
async function api(url, opts = {}) {
  const r = await fetch(url, {
    headers: {'Content-Type': 'application/json'},
    ...opts
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
  return d;
}

// ── Logout ──
async function doLogout() {
  try { await api('/api/logout', {method: 'POST'}); } catch {}
  window.location.href = '/login';
}

// ── Status polling (header tiskárny) ──
async function pollStatus() {
  try {
    const d = await api('/api/status');
    const map = {
      'LP0': d.printer_L,
      'LP1': d.printer_R,
      'GPIO': true,
    };
    const printers = document.getElementById('h-printers');
    if (!printers) return;
    printers.querySelectorAll('.h-printer').forEach(el => {
      const label = el.textContent.trim().split('\n').pop().trim();
      const dot = el.querySelector('.sdot');
      if (!dot) return;
      const key = Object.keys(map).find(k => label.includes(k));
      if (key !== undefined) {
        const ok = map[key];
        dot.className = 'sdot ' + (ok ? 'sdot-ok' : 'sdot-err');
      }
    });
  } catch {}
}

pollStatus();
setInterval(pollStatus, 15000);

// ── Escape HTML ──
function escHtml(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Format datetime ──
function fmtNow() {
  const n = new Date();
  return {
    date: n.toLocaleDateString('cs-CZ'),
    time: n.toLocaleTimeString('cs-CZ', {hour12: false}),
  };
}
