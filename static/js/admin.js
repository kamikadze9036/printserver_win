// ════════════════════════════════════════
//  admin.js — správa produktů, šablon, uživatelů
// ════════════════════════════════════════

window.addEventListener('DOMContentLoaded', () => {
  // Nacti jen produkty hned - sablony a uzivatele se nacitaji lazy pri kliknuti na tab
  loadProducts();
});

// switchTab je definovan inline v admin.html

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

// ══════════════════════════════════════
//  PRODUKTY
// ══════════════════════════════════════
// Cache sablon pro modaly
let _templates = [];
let _products = [];

async function ensureTemplates() {
  if (_templates.length) return;
  try {
    _templates = await api('/api/templates');
  } catch {}
}

async function loadProducts() {
  try {
    const rows = await api('/api/products');
    _products = rows;
    const tbody = document.getElementById('product-table');
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="td-loading">Žádné produkty.</td></tr>';
      return;
    }
    await ensureTemplates();
    const tmplMap = {};
    _templates.forEach(t => { tmplMap[t.id] = t.name; });
    const sideLabel = {
      'L':    '<span class="badge" style="background:var(--left);color:#fff">LEVÁ</span>',
      'R':    '<span class="badge" style="background:var(--right);color:#fff">PRAVÁ</span>',
      'both': '<span class="badge" style="background:var(--grey-dk);color:#fff">OBĚ</span>',
    };
    tbody.innerHTML = rows.map(p => `
      <tr>
        <td class="td-mono td-bold">${escHtml(p.product_code)}</td>
        <td>${sideLabel[p.side] || sideLabel['both']} ${Number(p.highlight_right || 0) ? '<span class="badge" style="background:#111;color:#fff;margin-left:4px">INV R</span>' : ''}</td>
        <td style="font-size:12px">${p.template_id ? escHtml(tmplMap[p.template_id] || '?') : '<span style="color:var(--err)">⚠ není</span>'}</td>
        <td class="td-mono" style="font-size:11px;color:var(--grey-dk)">${escHtml(p.qr_content)}</td>
        <td>${escHtml(p.text_content)}</td>
        <td style="font-size:11px;color:var(--grey-dk)">${(p.updated_at||'').split(' ')[0]}</td>
        <td><div class="td-actions">
          <button class="btn btn-ghost btn-sm"
            data-id="${p.id}"
            data-code="${escHtml(p.product_code)}"
            data-qr="${escHtml(p.qr_content)}"
            data-txt="${escHtml(p.text_content)}"
            data-txt2="${escHtml(p.text2||'')}"
            data-txt3="${escHtml(p.text3||'')}"
            data-txt4="${escHtml(p.text4||'')}"
            data-side="${p.side||'both'}"
            data-highlight-right="${Number(p.highlight_right || 0)}"
            data-tmpl="${p.template_id||''}"
            onclick="openProductModalFromBtn(this)">UPRAVIT</button>
          <button class="btn btn-blue btn-sm"
            data-code="${escHtml(p.product_code)}"
            data-qr="${escHtml(p.qr_content)}"
            data-txt="${escHtml(p.text_content)}"
            data-txt2="${escHtml(p.text2||'')}"
            data-txt3="${escHtml(p.text3||'')}"
            data-txt4="${escHtml(p.text4||'')}"
            data-side="${p.side||'both'}"
            data-highlight-right="${Number(p.highlight_right || 0)}"
            data-tmpl="${p.template_id||''}"
            onclick="duplicateProductFromBtn(this)">DUPLIKOVAT</button>
          <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id}, this)">SMAZAT</button>
        </div></td>
      </tr>
    `).join('');
  } catch (e) {
    toast('Chyba produktů: ' + e.message, true);
  }
}

function openProductModalFromBtn(btn) {
  const id  = parseInt(btn.dataset.id) || '';
  const tid = btn.dataset.tmpl ? parseInt(btn.dataset.tmpl) : null;
  openProductModal(id, btn.dataset.code, btn.dataset.qr, btn.dataset.txt, btn.dataset.side, tid, btn.dataset.txt2||'', btn.dataset.txt3||'', btn.dataset.txt4||'', btn.dataset.highlightRight === '1');
}

function makeProductCopyCode(code) {
  const base = (code || 'PRODUKT').trim().toUpperCase();
  const existing = new Set(_products.map(p => (p.product_code || '').toUpperCase()));
  let candidate = `${base} COPY`;
  let i = 2;
  while (existing.has(candidate)) {
    candidate = `${base} COPY ${i}`;
    i += 1;
  }
  return candidate;
}

async function duplicateProductFromBtn(btn) {
  const tid = btn.dataset.tmpl ? parseInt(btn.dataset.tmpl) : null;
  const copyCode = makeProductCopyCode(btn.dataset.code);
  const body = {
    product_code: copyCode,
    qr_content: btn.dataset.qr,
    text_content: btn.dataset.txt,
    text2: btn.dataset.txt2 || '',
    text3: btn.dataset.txt3 || '',
    text4: btn.dataset.txt4 || '',
    side: btn.dataset.side || 'both',
    highlight_right: btn.dataset.highlightRight === '1',
    template_id: tid,
  };
  btn.disabled = true;
  try {
    await api('/api/products', {method: 'POST', body: JSON.stringify(body)});
    toast('Produkt duplikován.');
    await loadProducts();
    const copy = _products.find(p => p.product_code === copyCode);
    if (copy) {
      openProductModal(copy.id, copy.product_code, copy.qr_content, copy.text_content, copy.side, copy.template_id, copy.text2||'', copy.text3||'', copy.text4||'', Number(copy.highlight_right || 0) === 1);
    }
  } catch (e) {
    toast('Chyba duplikace: ' + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

async function openProductModal(id='', code='', qr='', txt='', side='both', templateId=null, txt2='', txt3='', txt4='', highlightRight=false) {
  await ensureTemplates();
  // Naplň select šablon
  const tmplSel = document.getElementById('mp-template');
  if (tmplSel) {
    tmplSel.innerHTML = '<option value="">— bez šablony —</option>' +
      _templates.map(t => `<option value="${t.id}">${escHtml(t.name)}</option>`).join('');
    if (templateId) tmplSel.value = String(templateId);
  }
  document.getElementById('mp-id').value   = id;
  document.getElementById('mp-code').value = code;
  document.getElementById('mp-qr').value   = qr;
  document.getElementById('mp-txt').value  = txt;
  document.getElementById('mp-txt2').value = txt2;
  document.getElementById('mp-txt3').value = txt3;
  document.getElementById('mp-txt4').value = txt4;
  document.getElementById('mp-side').value = side || 'both';
  document.getElementById('mp-highlight-right').checked = !!highlightRight;
  document.getElementById('modal-product-title').textContent = id ? 'UPRAVIT PRODUKT' : 'NOVÝ PRODUKT';
  document.getElementById('modal-product').classList.remove('hidden');
  setTimeout(() => document.getElementById('mp-code').focus(), 100);
}

async function saveProduct() {
  const id   = document.getElementById('mp-id').value;
  const code = document.getElementById('mp-code').value.trim().toUpperCase();
  const qr   = document.getElementById('mp-qr').value.trim();
  const txt  = document.getElementById('mp-txt').value;
  const txt2 = document.getElementById('mp-txt2').value;
  const txt3 = document.getElementById('mp-txt3').value;
  const txt4 = document.getElementById('mp-txt4').value;
  const side       = document.getElementById('mp-side').value;
  const highlightRight = document.getElementById('mp-highlight-right').checked;
  const templateId = document.getElementById('mp-template').value || null;
  if (!code || !qr) { toast('Kód a QR jsou povinné.', true); return; }

  try {
    if (id) {
      await api('/api/products/' + id, {method: 'PUT', body: JSON.stringify({product_code: code, qr_content: qr, text_content: txt, text2: txt2, text3: txt3, text4: txt4, side, highlight_right: highlightRight, template_id: templateId ? parseInt(templateId) : null})});
      toast('Produkt upraven.');
    } else {
      await api('/api/products', {method: 'POST', body: JSON.stringify({product_code: code, qr_content: qr, text_content: txt, text2: txt2, text3: txt3, text4: txt4, side, highlight_right: highlightRight, template_id: templateId ? parseInt(templateId) : null})});
      toast('Produkt přidán.');
    }
    closeModal('modal-product');
    loadProducts();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}

async function deleteProduct(id, btn) {
  if (!confirm('Smazat produkt?')) return;
  try {
    await api('/api/products/' + id, {method: 'DELETE'});
    toast('Produkt smazán.');
    loadProducts();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}

// ══════════════════════════════════════
//  ŠABLONY
// ══════════════════════════════════════
async function loadTemplateList() {
  try {
    const rows = await api('/api/templates');
    const tbody = document.getElementById('tmpl-table');
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="td-loading">Žádné šablony.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(t => `
      <tr>
        <td style="font-weight:700">${escHtml(t.name)}</td>
        <td class="td-mono">${t.width_mm} × ${t.height_mm} mm</td>
        <td>—</td>
        <td><div class="td-actions">
          <button class="btn btn-blue btn-sm" onclick="openTemplateEditor(${t.id})">EDITOR</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTemplate(${t.id})">SMAZAT</button>
        </div></td>
      </tr>
    `).join('');
  } catch (e) {
    toast('Chyba šablon: ' + e.message, true);
  }
}

async function openTemplateEditor(id) {
  document.getElementById('tmpl-list-card').style.display = 'none';
  document.getElementById('tmpl-editor-wrap').style.display = 'block';
  document.getElementById('elements-list').innerHTML = '';
  document.getElementById('tmpl-edit-id').value = id || '';

  if (id) {
    try {
      const t = await api('/api/templates/' + id);
      document.getElementById('tmpl-name').value = t.name;
      document.getElementById('tmpl-w').value    = t.width_mm;
      document.getElementById('tmpl-h').value    = t.height_mm;
      (t.elements || []).forEach(el => addElement(el.type, el));
    } catch (e) {
      toast('Chyba načítání šablony: ' + e.message, true);
    }
  } else {
    document.getElementById('tmpl-name').value = 'Nová šablona';
    document.getElementById('tmpl-w').value    = '60';
    document.getElementById('tmpl-h').value    = '40';
  }
  renderPreview();
}

function closeTemplateEditor() {
  document.getElementById('tmpl-list-card').style.display = 'block';
  document.getElementById('tmpl-editor-wrap').style.display = 'none';
  loadTemplateList();
}

function newTemplate() { openTemplateEditor(null); }

function addElement(type, data = {}) {
  const list = document.getElementById('elements-list');
  const div = document.createElement('div');
  div.className = 'element-row';
  div.dataset.type = type;

  const VARS = `
    <option value="{product_code}" ${data.content==='{product_code}'?'selected':''}>{product_code}</option>
    <option value="{qr_content}"   ${data.content==='{qr_content}'?'selected':''}>{qr_content}</option>
    <option value="{text_content}" ${data.content==='{text_content}'?'selected':''}>{text_content}</option>
    <option value="{text1}"        ${data.content==='{text1}'?'selected':''}>{text1}</option>
    <option value="{text2}"        ${data.content==='{text2}'?'selected':''}>{text2}</option>
    <option value="{text3}"        ${data.content==='{text3}'?'selected':''}>{text3}</option>
    <option value="{text4}"        ${data.content==='{text4}'?'selected':''}>{text4}</option>
    <option value="{date}"         ${data.content==='{date}'?'selected':''}>{date}</option>
    <option value="{time}"         ${data.content==='{time}'?'selected':''}>{time}</option>
    <option value="{datetime_iso}" ${data.content==='{datetime_iso}'?'selected':''}>{datetime_iso}</option>
    <option value="{operator}"     ${data.content==='{operator}'?'selected':''}>{operator}</option>
  `;

  if (type === 'qr') {
    div.innerHTML = `
      <div class="element-row-head">
        <span class="el-type-badge el-qr">QR</span>
        <input class="el-name-input" type="text" value="${data.name||'QR kód'}" oninput="renderPreview()" />
        <button class="btn btn-danger btn-sm" onclick="this.closest('.element-row').remove();renderPreview()" style="margin-left:auto">✕</button>
      </div>
      <div class="el-fields" style="grid-template-columns:60px 60px 60px 60px 1fr">
        <div class="el-field"><label>X (mm)</label><input type="number" value="${data.x||2}" min="0" class="el-x" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Y (mm)</label><input type="number" value="${data.y||2}" min="0" class="el-y" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Šíř (mm)</label><input type="number" value="${data.w||20}" min="5" class="el-w" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Výš (mm)</label><input type="number" value="${data.h||20}" min="5" class="el-h" oninput="renderPreview()" /></div>
        <div class="el-field"><label>QR data (proměnná)</label>
          <select class="el-content" onchange="renderPreview()">${VARS}</select>
        </div>
      </div>`;
  } else {
    div.innerHTML = `
      <div class="element-row-head">
        <span class="el-type-badge el-text">TEXT</span>
        <input class="el-name-input" type="text" value="${data.name||'Textový blok'}" oninput="renderPreview()" />
        <button class="btn btn-danger btn-sm" onclick="this.closest('.element-row').remove();renderPreview()" style="margin-left:auto">✕</button>
      </div>
      <div class="el-fields" style="grid-template-columns:60px 60px 60px 60px 80px 1fr">
        <div class="el-field"><label>X (mm)</label><input type="number" value="${data.x||24}" min="0" class="el-x" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Y (mm)</label><input type="number" value="${data.y||2}" min="0" class="el-y" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Šíř (mm)</label><input type="number" value="${data.w||34}" min="5" class="el-w" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Výš (mm)</label><input type="number" value="${data.h||8}" min="3" class="el-h" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Font (pt)</label><input type="number" value="${data.font_size||8}" min="6" max="72" class="el-fs" oninput="renderPreview()" /></div>
        <div class="el-field"><label>Proměnná</label>
          <select class="el-content" onchange="renderPreview()">${VARS}</select>
        </div>
      </div>`;
  }
  list.appendChild(div);
  renderPreview();
}

function getElements() {
  return Array.from(document.querySelectorAll('#elements-list .element-row')).map(row => {
    const type = row.dataset.type;
    const el = {
      type,
      name:    row.querySelector('.el-name-input')?.value || type,
      x:       parseFloat(row.querySelector('.el-x')?.value) || 0,
      y:       parseFloat(row.querySelector('.el-y')?.value) || 0,
      w:       parseFloat(row.querySelector('.el-w')?.value) || 20,
      h:       parseFloat(row.querySelector('.el-h')?.value) || 20,
      content: row.querySelector('.el-content')?.value || '',
    };
    if (type === 'text') el.font_size = parseFloat(row.querySelector('.el-fs')?.value) || 8;
    return el;
  });
}

async function saveTemplate() {
  const id   = document.getElementById('tmpl-edit-id').value;
  const name = document.getElementById('tmpl-name').value.trim();
  const w    = parseFloat(document.getElementById('tmpl-w').value);
  const h    = parseFloat(document.getElementById('tmpl-h').value);
  if (!name) { toast('Zadejte název šablony.', true); return; }

  const body = JSON.stringify({name, width_mm: w, height_mm: h, elements: getElements()});
  try {
    if (id) {
      await api('/api/templates/' + id, {method: 'PUT', body});
      toast('Šablona uložena.');
    } else {
      await api('/api/templates', {method: 'POST', body});
      toast('Šablona vytvořena.');
    }
    closeTemplateEditor();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}

async function deleteTemplate(id) {
  if (!confirm('Smazat šablonu?')) return;
  try {
    await api('/api/templates/' + id, {method: 'DELETE'});
    toast('Šablona smazána.');
    loadTemplateList();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}

// ── PREVIEW ──────────────────────────────
function renderPreview() {
  const w = parseFloat(document.getElementById('tmpl-w')?.value) || 60;
  const h = parseFloat(document.getElementById('tmpl-h')?.value) || 40;
  const canvas = document.getElementById('label-canvas');
  if (!canvas) return;

  const maxW = 320;
  const scale = Math.min(5, maxW / w);
  canvas.style.width  = (w * scale) + 'px';
  canvas.style.height = (h * scale) + 'px';
  canvas.innerHTML = '';

  document.querySelectorAll('#elements-list .element-row').forEach(row => {
    const type = row.dataset.type;
    const x  = parseFloat(row.querySelector('.el-x')?.value) || 0;
    const y  = parseFloat(row.querySelector('.el-y')?.value) || 0;
    const ew = parseFloat(row.querySelector('.el-w')?.value) || 20;
    const eh = parseFloat(row.querySelector('.el-h')?.value) || 20;
    const name = row.querySelector('.el-name-input')?.value || type;
    const content = row.querySelector('.el-content')?.value || '';

    const el = document.createElement('div');
    el.className = 'el-preview' + (type === 'qr' ? ' qr-prev' : '');
    el.style.cssText = `left:${x*scale}px;top:${y*scale}px;width:${ew*scale}px;height:${eh*scale}px;flex-direction:column;align-items:center`;

    if (type === 'qr') {
      const qrSize = Math.min(ew, eh) * scale * 0.65;
      const qr = document.createElement('div');
      qr.style.cssText = `display:grid;grid-template-columns:repeat(5,1fr);width:${qrSize}px;height:${qrSize}px;gap:1px;flex-shrink:0`;
      for (let i = 0; i < 25; i++) {
        const c = document.createElement('div');
        c.style.background = (i%2===0||i%3===1) ? 'var(--navy)' : 'transparent';
        qr.appendChild(c);
      }
      el.appendChild(qr);
      const lbl = document.createElement('div');
      lbl.style.cssText = `font-family:var(--mono);font-size:7px;text-align:center;color:var(--navy);overflow:hidden;width:100%;margin-top:2px`;
      lbl.textContent = name;
      el.appendChild(lbl);
    } else {
      const fs = parseFloat(row.querySelector('.el-fs')?.value) || 8;
      const dispFs = Math.max(6, Math.min(fs * scale * 0.42, eh * scale * 0.75));
      el.style.alignItems = 'flex-start';
      el.style.padding = '2px';
      const lbl = document.createElement('div');
      lbl.style.cssText = `font-size:6px;color:var(--grey-dk);font-family:var(--mono);line-height:1`;
      lbl.textContent = name;
      const val = document.createElement('div');
      val.style.cssText = `font-size:${dispFs}px;color:var(--navy);font-family:var(--mono);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;width:100%`;
      val.textContent = content;
      el.appendChild(lbl);
      el.appendChild(val);
    }
    canvas.appendChild(el);
  });

  const info = document.getElementById('preview-info');
  if (info) info.innerHTML = `Štítek: <span>${w} × ${h} mm</span> · Prvků: <span>${canvas.children.length}</span>`;
}

// ══════════════════════════════════════
//  UŽIVATELÉ
// ══════════════════════════════════════
async function loadUsers() {
  try {
    const rows = await api('/api/users');
    const tbody = document.getElementById('user-table');
    tbody.innerHTML = rows.map(u => `
      <tr>
        <td style="font-weight:700">${escHtml(u.username)}</td>
        <td><span class="badge" style="background:${u.role==='admin'?'var(--admin)':'var(--blue)'};color:#fff">${u.role.toUpperCase()}</span></td>
        <td style="text-align:center">${u.role==='user' ? (u.has_pin ? '<span style="color:var(--ok)">\u2713 nastaven</span>' : '<span style="color:var(--warn)">\u26a0 nen\u00ed</span>') : '\u2014'}</td>
        <td><div class="td-actions">
          ${u.role==='user' ? `<button class="btn btn-ghost btn-sm" onclick="openPinModal(${u.id},'${escHtml(u.username)}')">PIN</button>` : ''}
          <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">SMAZAT</button>
        </div></td>
      </tr>
    `).join('');
  } catch (e) {
    toast('Chyba uživatel\u016f: ' + e.message, true);
  }
}

function openUserModal() {
  document.getElementById('mu-name').value = '';
  document.getElementById('mu-pass').value = '';
  document.getElementById('mu-role').value = 'user';
  document.getElementById('mu-pin').value = '';
  document.getElementById('mu-pin-row').style.display = 'none';
  document.getElementById('modal-user').classList.remove('hidden');
  setTimeout(() => document.getElementById('mu-name').focus(), 100);
}

async function saveUser() {
  const name = document.getElementById('mu-name').value.trim();
  const pass = document.getElementById('mu-pass').value;
  const role = document.getElementById('mu-role').value;
  const pin  = document.getElementById('mu-pin').value.trim();
  if (!name || !pass) { toast('Vypln\u011bte jm\u00e9no a heslo.', true); return; }
  if (role === 'user' && pin && !/^\d{4,8}$/.test(pin)) {
    toast('PIN mus\u00ed b\u00fdt 4\u20138 \u010d\u00edslic.', true); return;
  }
  try {
    await api('/api/users', {method: 'POST', body: JSON.stringify({username: name, password: pass, role, pin: pin || null})});
    toast('U\u017eivatel p\u0159id\u00e1n.');
    closeModal('modal-user');
    loadUsers();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}

function openPinModal(id, name) {
  document.getElementById('pin-modal-name').textContent = name;
  document.getElementById('pin-modal-id').value = id;
  document.getElementById('pin-modal-val').value = '';
  document.getElementById('modal-pin').classList.remove('hidden');
  setTimeout(() => document.getElementById('pin-modal-val').focus(), 100);
}

async function savePin() {
  const id  = document.getElementById('pin-modal-id').value;
  const pin = document.getElementById('pin-modal-val').value.trim();
  if (!/^\d{4,8}$/.test(pin)) { toast('PIN mus\u00ed b\u00fdt 4\u20138 \u010d\u00edslic.', true); return; }
  try {
    await api('/api/users/' + id + '/pin', {method: 'POST', body: JSON.stringify({pin})});
    toast('PIN ulo\u017een.');
    closeModal('modal-pin');
    loadUsers();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}

async function deleteUser(id) {
  if (!confirm('Smazat u\u017eivatele?')) return;
  try {
    await api('/api/users/' + id, {method: 'DELETE'});
    toast('U\u017eivatel smaz\u00e1n.');
    loadUsers();
  } catch (e) {
    toast('Chyba: ' + e.message, true);
  }
}


// ══════════════════════════════════════
//  NASTAVENÍ
// ══════════════════════════════════════
// Zobrazi/skryje custom DPI input
function toggleDpiCustom(side) {
  const sel = document.getElementById('set-dpi-' + side);
  const inp = document.getElementById('set-dpi-' + side + '-custom');
  if (!sel || !inp) return;
  inp.style.display = sel.value === 'custom' ? 'block' : 'none';
}

// Vrati skutecnou DPI hodnotu (ze selectu nebo custom inputu)
function getDpiValue(side) {
  const sel = document.getElementById('set-dpi-' + side);
  if (!sel) return '300';
  if (sel.value === 'custom') {
    const inp = document.getElementById('set-dpi-' + side + '-custom');
    return (inp && inp.value) ? inp.value : '300';
  }
  return sel.value;
}

async function loadSettings() {
  try {
    const d = await api('/api/settings');
    const s = d.settings;
    const printers = d.available_printers || [];

    console.log('loadSettings: printers=', printers);

    // Naplň selecty tiskáren
    ['set-printer-left', 'set-printer-right'].forEach(id => {
      const sel = document.getElementById(id);
      console.log('select element', id, '=', sel);
      if (!sel) return;
      sel.innerHTML = printers.map(p =>
        `<option value="${escHtml(p)}">${escHtml(p)}</option>`
      ).join('');
      console.log('options set for', id, ':', sel.innerHTML.substring(0, 100));
    });

    // Nastav aktuální hodnoty
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el && val) el.value = val;
    };
    setVal('set-printer-left',  s.printer_left);
    setVal('set-printer-right', s.printer_right);
    const dpiLeftVal  = s.printer_dpi_left  || s.printer_dpi || '300';
    const dpiRightVal = s.printer_dpi_right || s.printer_dpi || '300';
    const knownDpi = ['203', '300', '600'];

    // Nastav select nebo custom
    ['left', 'right'].forEach(side => {
      const val = side === 'left' ? dpiLeftVal : dpiRightVal;
      const sel = document.getElementById('set-dpi-' + side);
      const inp = document.getElementById('set-dpi-' + side + '-custom');
      if (!sel) return;
      sel.onchange = () => toggleDpiCustom(side);
      if (knownDpi.includes(String(val))) {
        sel.value = String(val);
      } else {
        sel.value = 'custom';
        if (inp) { inp.value = val; inp.style.display = 'block'; }
      }
    });
    setVal('set-protocol-left',   s.printer_protocol_left  || s.printer_protocol || 'tspl');
    setVal('set-protocol-right',  s.printer_protocol_right || s.printer_protocol || 'tspl');
    setVal('set-encoding-left',   s.printer_encoding_left  || s.printer_encoding || 'utf-8');
    setVal('set-encoding-right',  s.printer_encoding_right || s.printer_encoding || 'utf-8');

    // Status
    const statusL = document.getElementById('set-left-status');
    const statusR = document.getElementById('set-right-status');
    const dpiL = s.printer_dpi_left  || s.printer_dpi || '300';
    const dpiR = s.printer_dpi_right || s.printer_dpi || '300';
    if (statusL) statusL.textContent = 'Aktuální: ' + (s.printer_left  || '—') + ' · ' + dpiL + ' DPI';
    if (statusR) statusR.textContent = 'Aktuální: ' + (s.printer_right || '—') + ' · ' + dpiR + ' DPI';

    if (!printers.length) {
      toast('Žádné tiskárny nenalezeny — zkontroluj připojení.', true);
    }
  } catch (e) {
    toast('Chyba načítání nastavení: ' + e.message, true);
  }
}

async function saveSettings() {
  const get = id => document.getElementById(id)?.value || '';
  try {
    await api('/api/settings', {
      method: 'POST',
      body: JSON.stringify({
        printer_left:      get('set-printer-left'),
        printer_right:     get('set-printer-right'),
        printer_dpi_left:  getDpiValue('left'),
        printer_dpi_right: getDpiValue('right'),
        printer_protocol_left:  get('set-protocol-left'),
        printer_protocol_right: get('set-protocol-right'),
        printer_encoding_left:  get('set-encoding-left'),
        printer_encoding_right: get('set-encoding-right'),
      })
    });
    toast('✓ Nastavení uloženo — platí okamžitě.');

    // Obnov status
    const statusL = document.getElementById('set-left-status');
    const statusR = document.getElementById('set-right-status');
    if (statusL) statusL.textContent = 'Aktuální: ' + get('set-printer-left')  + ' · ' + get('set-protocol-left').toUpperCase()  + ' · ' + getDpiValue('left')  + ' DPI · ' + get('set-encoding-left');
    if (statusR) statusR.textContent = 'Aktuální: ' + get('set-printer-right') + ' · ' + get('set-protocol-right').toUpperCase() + ' · ' + getDpiValue('right') + ' DPI · ' + get('set-encoding-right');
  } catch (e) {
    toast('Chyba uložení: ' + e.message, true);
  }
}


// ══════════════════════════════════════
//  VÝROBNÍ PŘÍKAZY
// ══════════════════════════════════════
async function loadOrders() {
  try {
    const rows = await api('/api/order/history?limit=100');
    const tbody = document.getElementById('orders-table');
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="td-loading">Žádné záznamy.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(o => {
      const isActive    = o.status === 'active';
      const isCancelled = o.status === 'cancelled';
      const total = (o.count_L || 0) + (o.count_R || 0);
      const statusBadge = isActive
        ? '<span class="badge" style="background:var(--ok);color:#fff">AKTIVNÍ</span>'
        : isCancelled
          ? '<span class="badge" style="background:var(--warn);color:#fff">ZRUŠEN</span>'
          : '<span class="badge" style="background:var(--grey-dk);color:#fff">UKONČEN</span>';
      const finished = o.finished_at
        ? o.finished_at.substring(0, 16).replace('T', ' ')
        : '—';
      const started = (o.started_at || '').substring(0, 16).replace('T', ' ');
      return `<tr ${isActive ? 'style="background:rgba(46,125,50,.06)"' : ''}>
        <td class="td-mono td-bold">${escHtml(o.order_number || 'Bez zakázky')}</td>
        <td>${escHtml(o.operator)}</td>
        <td class="td-mono" style="font-size:11px">${escHtml(o.product_L_code || '—')}</td>
        <td class="td-mono" style="font-size:11px">${escHtml(o.product_R_code || '—')}</td>
        <td class="td-mono" style="font-size:11px">${started}</td>
        <td class="td-mono" style="font-size:11px">${finished}</td>
        <td style="text-align:center;font-family:var(--mono);font-weight:bold;color:var(--left)">${o.count_L || 0}</td>
        <td style="text-align:center;font-family:var(--mono);font-weight:bold;color:var(--right)">${o.count_R || 0}</td>
        <td style="text-align:center;font-family:var(--mono);font-weight:bold">${total}</td>
        <td>${statusBadge}</td>
      </tr>`;
    }).join('');
  } catch (e) {
    toast('Chyba načítání VP: ' + e.message, true);
  }
}

// ── CSV IMPORT ────────────────────────────────────────────
let _csvRows = [];

function openCsvModal() {
  csvReset();
  document.getElementById('modal-csv').classList.remove('hidden');
}

function closeCsvModal() {
  document.getElementById('modal-csv').classList.add('hidden');
}

function csvReset() {
  _csvRows = [];
  document.getElementById('csv-file-input').value = '';
  document.getElementById('csv-upload-err').textContent = '';
  document.getElementById('csv-step-upload').classList.remove('hidden');
  document.getElementById('csv-step-preview').classList.add('hidden');
}

async function csvPreview() {
  const fileInput = document.getElementById('csv-file-input');
  const errEl     = document.getElementById('csv-upload-err');
  errEl.textContent = '';
  if (!fileInput.files.length) {
    errEl.textContent = 'Vyberte soubor.';
    return;
  }
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  try {
    const res = await fetch('/api/products/csv_preview', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
    });
    const d = await res.json();
    if (!res.ok) { errEl.textContent = d.error || 'Chyba'; return; }

    _csvRows = d.rows;
    const newRows  = d.rows.filter(r => !r.duplicate);
    const skipRows = d.rows.filter(r =>  r.duplicate);

    // Souhrn
    document.getElementById('csv-summary').innerHTML =
      `Nalezeno <b>${d.rows.length}</b> řádků — ` +
      `<span style="color:var(--ok)">✓ ${newRows.length} nových</span>, ` +
      `<span style="color:var(--warn)">⚠ ${skipRows.length} duplikátů (přeskočí se)</span>` +
      (d.errors.length ? `, <span style="color:var(--err)">${d.errors.length} chyb</span>` : '');

    // Tabulka náhledu
    document.getElementById('csv-preview-body').innerHTML = d.rows.map(r => `
      <tr style="opacity:${r.duplicate ? 0.45 : 1}">
        <td style="font-size:11px;color:var(--grey-dk)">${r.row}</td>
        <td class="td-mono td-bold">${escHtml(r.product_code)}</td>
        <td style="font-size:11px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(r.qr_content)}</td>
        <td style="font-size:11px">${escHtml(r.text_content)}</td>
        <td style="text-align:center">${escHtml(r.side)}</td>
        <td style="font-size:11px">${escHtml(r.template_name)}</td>
        <td>${r.duplicate
          ? '<span style="color:var(--warn);font-size:11px">⚠ duplikát</span>'
          : '<span style="color:var(--ok);font-size:11px">✓ nový</span>'}</td>
      </tr>`).join('');

    // Chyby parsování
    document.getElementById('csv-preview-errors').innerHTML =
      d.errors.length ? d.errors.map(e => `⚠ ${escHtml(e)}`).join('<br>') : '';

    // Disable importu pokud není co importovat
    document.getElementById('csv-import-btn').disabled = newRows.length === 0;

    document.getElementById('csv-step-upload').classList.add('hidden');
    document.getElementById('csv-step-preview').classList.remove('hidden');
  } catch (e) {
    errEl.textContent = 'Chyba: ' + e.message;
  }
}

async function csvImport() {
  const newRows = _csvRows.filter(r => !r.duplicate);
  if (!newRows.length) return;
  try {
    const d = await api('/api/products/csv_import', {
      method: 'POST',
      body: JSON.stringify({ rows: newRows }),
    });
    toast(`Import hotov: ${d.imported} importováno, ${d.skipped} přeskočeno.`);
    closeCsvModal();
    await loadProducts();
  } catch (e) {
    toast('Chyba importu: ' + e.message, true);
  }
}
