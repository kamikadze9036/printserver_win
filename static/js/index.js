// ════════════════════════════════════════
//  index.js — hlavní tisková obrazovka
// ════════════════════════════════════════

let templates = [];
let pickedProducts = {L: null, R: null};

async function doAdminLoginRedirect() {
  try { await api('/api/logout', {method: 'POST'}); } catch {}
  window.location.href = '/login?admin=1';
}

// ── INIT ─────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  await loadActiveOrder();  // Nejdriv zjisti jestli bezi VP
  await loadState();
  await loadLog();
  await loadPrinterNames();
  setInterval(loadLog, 30000);
  setInterval(refreshOrderCounts, 10000);
  // Otevri modal jen pokud NENI aktivni VP
  if (!window._activeOrderId) {
    openProductModal();
  }
});

async function loadPrinterNames() {
  try {
    const d = await api('/api/debug/system');
    const L = d.printer_L_dev || '—';
    const R = d.printer_R_dev || '—';
    ['printer-info-L', 'pp-printer-tag-L'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = L;
    });
    ['printer-info-R', 'pp-printer-tag-R'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = R;
    });
  } catch (e) { /* tiché selhání – není kritické */ }
}


// ── ŠABLONY ──────────────────────────────
async function loadTemplates() {
  try {
    templates = await api('/api/templates');
    ['L', 'R'].forEach(side => {
      const sel = document.getElementById('tmpl-' + side);
      if (!sel) return;
      sel.innerHTML = templates.map(t =>
        `<option value="${t.id}">${t.name} (${t.width_mm}×${t.height_mm}mm)</option>`
      ).join('');
    });
  } catch (e) {
    toast('Chyba načítání šablon: ' + e.message, true);
  }
}

// ── PRODUCT MODAL ────────────────────────
function openProductModal() {
  // Vzdy vymaz oba predchozi vybery pri otevreni modalu
  ['L', 'R'].forEach(side => {
    pickedProducts[side] = null;
    const input = document.getElementById('pick-code' + side);
    if (input) { input.value = ''; input.style.borderColor = ''; input.style.boxShadow = ''; }
    document.getElementById('prev-' + side).classList.add('hidden');
    document.getElementById('empty-' + side).style.display = '';
    document.getElementById('err-' + side).classList.add('hidden');
  });
  // Vzdy vymaz cislo VP
  const vpInput = document.getElementById('inp-order-number');
  if (vpInput) { vpInput.value = ''; vpInput.style.borderColor = ''; }
  document.getElementById('ov-product').classList.remove('hidden');
  setTimeout(() => document.getElementById('pick-codeL').focus(), 100);
}

function clearPreview(side) {
  document.getElementById('prev-' + side).classList.add('hidden');
  document.getElementById('empty-' + side).style.display = '';
  document.getElementById('err-' + side).classList.add('hidden');
  const input = document.getElementById('pick-code' + side);
  if (input) { input.style.borderColor = ''; input.style.boxShadow = ''; }
  pickedProducts[side] = null;
}

async function pickSearch(side) {
  const code  = document.getElementById('pick-code' + side).value.trim().toUpperCase();
  const errEl = document.getElementById('err-' + side);
  const input = document.getElementById('pick-code' + side);
  errEl.classList.add('hidden');
  input.style.borderColor = '';

  if (!code) return;

  try {
    const p = await api('/api/products/search?code=' + encodeURIComponent(code));

    // Validace strany produktu
    const productSide = p.side || 'both';
    if (productSide !== 'both' && productSide !== side) {
      const wrongSide = side === 'L' ? 'LEVÉ' : 'PRAVÉ';
      const correctSide = productSide === 'L' ? 'LEVÉ' : 'PRAVÉ';
      errEl.textContent = `Produkt ${p.product_code} patří na ${correctSide} tiskárnu — nelze přidat do ${wrongSide}.`;
      errEl.classList.remove('hidden');
      input.style.borderColor = 'var(--err)';
      input.style.boxShadow = '0 0 0 2px rgba(198,40,40,.3)';
      pickedProducts[side] = null;
      // Vymaz input a vrat focus pro dalsi scan
      setTimeout(() => {
        input.value = '';
        input.style.borderColor = '';
        input.style.boxShadow = '';
        input.focus();
      }, 1500);
      return;
    }

    // Varuj pokud produkt nema sablonu
    if (!p.template_id) {
      errEl.textContent = `Produkt ${p.product_code} nemá přiřazenou šablonu — nastav ji v Admin → Produkty.`;
      errEl.classList.remove('hidden');
      input.style.borderColor = 'var(--warn)';
      input.style.boxShadow = '0 0 0 2px rgba(232,160,0,.3)';
      // Umozni pokracovat ale s varovanim
    }

    // OK - nastav produkt
    pickedProducts[side] = p;
    if (p.template_id) {
      input.style.borderColor = 'var(--ok)';
      input.style.boxShadow = '0 0 0 2px rgba(46,125,50,.3)';
    }

    document.getElementById('prev-' + side + '-code').textContent = p.product_code;
    document.getElementById('prev-' + side + '-qr').textContent   = p.qr_content;
    document.getElementById('prev-' + side + '-txt').textContent  = p.text_content;
    // Zobraz sablonu pokud existuje
    const tmplEl = document.getElementById('prev-' + side + '-tmpl');
    if (tmplEl) tmplEl.textContent = p.template_name || '⚠ šablona není přiřazena';

    document.getElementById('empty-' + side).style.display = 'none';
    document.getElementById('prev-' + side).classList.remove('hidden');

  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
    input.style.borderColor = 'var(--err)';
    input.style.boxShadow = '0 0 0 2px rgba(198,40,40,.3)';
    pickedProducts[side] = null;
    // Vymaz input a vrat focus pro dalsi scan
    setTimeout(() => {
      input.value = '';
      input.style.borderColor = '';
      input.style.boxShadow = '';
      input.focus();
    }, 1500);
  }
}

// ── SCAN FLOW ─────────────────────────────────────────
// Levý scan → načte produkt → přeskočí na pravé pole
async function pickSearchAndNext(side) {
  await pickSearch(side);
  if (pickedProducts['L']) {
    // Uspech - skoc na prave pole
    const rightInput = document.getElementById('pick-codeR');
    if (rightInput) {
      rightInput.focus();
      rightInput.select();
    }
  }
  // Chyba - focus se vrati sam po 1500ms v pickSearch
}

async function pickSearchAndConfirm(side) {
  await pickSearch(side);
  if (pickedProducts['R']) {
    // Uspech - potvrd po kratke pauze aby uzivatel videl nahled
    setTimeout(() => confirmProducts(), 600);
  }
  // Chyba - focus se vrati sam po 1500ms v pickSearch
}

async function confirmProducts() {
  if (!pickedProducts.L && !pickedProducts.R) {
    toast('Vyberte alespoň jeden produkt.', true);
    return;
  }

  // Blokuj pokud je viditelna chyba strany
  const errL = document.getElementById('err-L');
  const errR = document.getElementById('err-R');
  if ((!errL.classList.contains('hidden') && !pickedProducts.L) ||
      (!errR.classList.contains('hidden') && !pickedProducts.R)) {
    toast('Nejprve oprav chyby ve výběru produktů.', true);
    return;
  }

  // Cislo VP je volitelne
  const orderNumber = document.getElementById('inp-order-number').value.trim();
  document.getElementById('inp-order-number').style.borderColor = '';

  // Odeslat stav stran na backend - sablona se bere z produktu
  for (const side of ['L', 'R']) {
    try {
      if (pickedProducts[side]) {
        await api('/api/state/' + side, {
          method: 'POST',
          body: JSON.stringify({
            product_code: pickedProducts[side].product_code,
            // template_id se bere z produktu automaticky
          })
        });
      } else {
        await api('/api/state/' + side, { method: 'DELETE' });
      }
    } catch (e) {
      toast(`Chyba strana ${side}: ${e.message}`, true);
      return;
    }
  }

  // Zahaj VP
  try {
    await api('/api/order/start', {
      method: 'POST',
      body: JSON.stringify({ order_number: orderNumber })
    });
  } catch (e) {
    toast('Chyba zahájení VP: ' + e.message, true);
    return;
  }

  document.getElementById('ov-product').classList.add('hidden');
  await loadState();
  await loadActiveOrder();
}

// ── STAV TISKU ───────────────────────────
async function loadState() {
  try {
    const state = await api('/api/state');
    applyState('L', state.L);
    applyState('R', state.R);
  } catch (e) {
    toast('Chyba načítání stavu: ' + e.message, true);
  }
}

function applyState(side, st) {
  const btn    = document.getElementById('btn-' + side);
  const gpioSt = document.getElementById('gpio-' + side + '-st');
  const gp1    = document.getElementById('gp-' + side + '1');
  const gp2    = document.getElementById('gp-' + side + '2');

  if (!st) {
    // Žádný produkt
    if (side === 'R') {
      document.getElementById('np-R').style.display = '';
      document.getElementById('sp-R').classList.add('hidden');
    }
    btn.classList.add('disabled');
    gpioSt.textContent = '● ČEKÁ';
    gpioSt.className = 'gpio-status gpio-wait';
    gp1.className = gp2.className = 'gpin';
    return;
  }

  // Naplň data
  document.getElementById('sp-' + side + '-code').textContent = st.product_code;
  document.getElementById('sp-' + side + '-qr').textContent   = st.qr_content;
  document.getElementById('sp-' + side + '-txt').textContent  = st.text_content;
  document.getElementById('sp-' + side + '-tmpl').textContent = st.template_name;

  if (side === 'R') {
    document.getElementById('np-R').style.display = 'none';
    document.getElementById('sp-R').classList.remove('hidden');
  }

  btn.classList.remove('disabled');
  gpioSt.textContent = '■ READY';
  gpioSt.className = 'gpio-status gpio-ready-' + side;
  gp1.className = gp2.className = 'gpin ok-' + side;
}

// ── TISK ─────────────────────────────────
async function doPrint(side) {
  const btn = document.getElementById('btn-' + side);
  if (btn.classList.contains('disabled')) return;

  const orig = btn.textContent;
  btn.textContent = '⏳  TISKNU…';
  btn.style.opacity = '.55';
  btn.style.pointerEvents = 'none';

  try {
    await api('/api/print/' + side, {method: 'POST'});
    btn.textContent = '✓  VYTISKNUTO';
    toast(`Strana ${side === 'L' ? 'LEVÁ' : 'PRAVÁ'} — tisk OK`);
    setTimeout(loadLog, 800);
  } catch (e) {
    btn.textContent = '✕  CHYBA';
    toast('Chyba tisku: ' + e.message, true);
  } finally {
    btn.style.opacity = '';
    setTimeout(() => {
      btn.textContent = orig;
      btn.style.pointerEvents = '';
    }, 2000);
  }
}

// ── LOG ──────────────────────────────────
async function loadLog() {
  try {
    const rows = await api('/api/log?limit=50');
    const tbody = document.getElementById('log-body');
    document.getElementById('log-meta').textContent =
      `ZOBRAZENO: ${Math.min(rows.length, 50)} / ${rows.length}`;

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="td-loading">Žádné záznamy.</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${(r.timestamp || '').split(' ')[0]}</td>
        <td class="td-mono">${(r.timestamp || '').split(' ')[1] || ''}</td>
        <td>${escHtml(r.username)}</td>
        <td class="td-mono td-bold">${escHtml(r.product_code)}</td>
        <td><span class="badge b${r.side}">${r.side === 'L' ? 'LEVÁ' : 'PRAVÁ'}</span></td>
        <td>${escHtml(r.template_name)}</td>
        <td><span class="badge ${r.trigger === 'gpio' || r.trigger === 'gpio-sim' ? 'bGPIO' : ''}"
          style="${!r.trigger.includes('gpio') ? 'background:var(--grey-mid);color:var(--white)' : ''}">
          ${r.trigger.toUpperCase()}</span></td>
        <td><span class="badge ${r.status === 'ok' ? 'bOK' : 'bERR'}">${r.status.toUpperCase()}</span></td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Log error:', e);
  }
}


// ── VÝROBNÍ PŘÍKAZ ───────────────────────────────────────

async function loadActiveOrder() {
  try {
    const d = await api('/api/order/active');
    if (d.active) {
      showOrderBanner(d.order);
      window._activeOrderId = d.order.id;
    } else {
      hideOrderBanner();
      window._activeOrderId = null;
    }
  } catch (e) {
    console.error('VP load error:', e);
  }
}

async function cancelOrder() {
  if (!confirm('Zrušit výrobní příkaz? Nebude uložen do historie jako dokončený.')) return;
  try {
    await api('/api/order/cancel', { method: 'POST' });
    toast('VP zrušen.');
    window._activeOrderId = null;
    hideOrderBanner();
    applyState('L', null);
    applyState('R', null);
    await loadLog();
    setTimeout(() => openProductModal(), 400);
  } catch (e) {
    toast('Chyba zrušení VP: ' + e.message, true);
  }
}

async function refreshOrderCounts() {
  if (!window._activeOrderId) return;
  try {
    const d = await api('/api/order/active');
    if (d.active) updateOrderCounts(d.order);
  } catch {}
}

function showOrderBanner(order) {
  const banner = document.getElementById('vp-banner');
  if (!banner) return;
  banner.style.display = 'flex';
  document.getElementById('vp-number').textContent   = order.order_number ? '#' + order.order_number : 'Bez zakázky';
  document.getElementById('vp-operator').textContent = order.operator;
  document.getElementById('vp-started').textContent  = (order.started_at || '').replace('T', ' ').substring(0, 16);
  // Zobraz produkty
  const prodL = document.getElementById('vp-prod-L');
  const prodR = document.getElementById('vp-prod-R');
  if (prodL) prodL.textContent = order.product_L_code || '—';
  if (prodR) prodR.textContent = order.product_R_code || '—';
  updateOrderCounts(order);
}

function updateOrderCounts(order) {
  const cL = order.count_L || 0;
  const cR = order.count_R || 0;
  document.getElementById('vp-count-L').textContent     = cL;
  document.getElementById('vp-count-R').textContent     = cR;
  document.getElementById('vp-count-total').textContent = cL + cR;
}

function hideOrderBanner() {
  const banner = document.getElementById('vp-banner');
  if (banner) banner.style.display = 'none';
}

async function finishOrder() {
  try {
    const d = await api('/api/order/finish', { method: 'POST' });
    toast('✓ Výrobní příkaz ukončen.');
    window._activeOrderId = null;
    hideOrderBanner();
    // Vymaz zobrazene produkty
    applyState('L', null);
    applyState('R', null);
    await loadLog();
    // Otevri modal pro novy VP
    setTimeout(() => openProductModal(), 800);
  } catch (e) {
    toast('Chyba ukončení VP: ' + e.message, true);
  }
}
