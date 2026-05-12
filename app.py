"""
app.py — Hess Plastics Print Server (Windows verze)
Používá Waitress místo Gunicorn (Gunicorn nefunguje na Windows).
"""

import json
import atexit
import hmac
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from logger import setup_logging, get_logger, read_log_tail, get_log_files
from models import (
    init_db, get_db,
    get_product_by_code, get_template_by_id,
    get_all_templates, get_all_products,
    log_print, get_log,
    get_setting, set_setting, get_all_settings,
    get_active_order, get_order_by_id, increment_order_count,
    finish_order, get_order_history
)
from printer import print_label, check_printer, _list_printers
from gpio_listener import start_gpio_listener, cleanup_gpio

app = Flask(__name__)
app.config.from_object(Config)

setup_logging()
log = get_logger(__name__)

with app.app_context():
    init_db()

log.info("=== Hess Print Server (Windows) start ===")

print_state = {'L': None, 'R': None}
active_order_id = None   # ID aktivniho VP


def _truthy(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or '').strip().lower() in ('1', 'true', 'yes', 'on', 'ano')

# Obnov aktivni VP z DB
try:
    _active = get_active_order()
    if _active:
        active_order_id = _active['id']
        for _side, _code, _tid in [
            ('L', _active['product_L_code'], _active['template_L_id']),
            ('R', _active['product_R_code'], _active['template_R_id']),
        ]:
            if _code:
                _p = get_product_by_code(_code)
                _t = get_template_by_id(_tid)
                if _p and _t:
                    print_state[_side] = {
                        'product_id': _p['id'], 'product_code': _p['product_code'],
                        'qr_content': _p['qr_content'], 'text_content': _p['text_content'],
                        'text2': _p['text2'] if 'text2' in _p.keys() else '',
                        'text3': _p['text3'] if 'text3' in _p.keys() else '',
                        'text4': _p['text4'] if 'text4' in _p.keys() else '',
                        'template_id': _t['id'], 'template_name': _t['name'],
                        'username': _active['operator'],
                    }
        log.info(f"Obnoven aktivni VP: #{_active['order_number']} (id={active_order_id})")
except Exception as _e:
    log.warning(f"Nelze obnovit VP: {_e}")

# Nacti nastaveni tiskarny z DB
try:
    Config.PRINTER_LEFT_NAME  = get_setting('printer_left',      Config.PRINTER_LEFT_NAME)
    Config.PRINTER_RIGHT_NAME = get_setting('printer_right',     Config.PRINTER_RIGHT_NAME)
    Config.PRINTER_PROTOCOL_LEFT  = get_setting('printer_protocol_left',  getattr(Config, 'PRINTER_PROTOCOL', 'tspl'))
    Config.PRINTER_PROTOCOL_RIGHT = get_setting('printer_protocol_right', getattr(Config, 'PRINTER_PROTOCOL', 'tspl'))
    Config.PRINTER_DPI_LEFT   = int(get_setting('printer_dpi_left',  str(getattr(Config, 'PRINTER_DPI', 300))))
    Config.PRINTER_DPI_RIGHT  = int(get_setting('printer_dpi_right', str(getattr(Config, 'PRINTER_DPI', 300))))
    Config.PRINTER_ENCODING_LEFT  = get_setting('printer_encoding_left',  getattr(Config, 'PRINTER_ENCODING', 'utf-8'))
    Config.PRINTER_ENCODING_RIGHT = get_setting('printer_encoding_right', getattr(Config, 'PRINTER_ENCODING', 'utf-8'))
    log.info(f"Tiskarna leva:  {Config.PRINTER_LEFT_NAME} ({Config.PRINTER_DPI_LEFT} DPI)")
    log.info(f"Tiskarna prava: {Config.PRINTER_RIGHT_NAME} ({Config.PRINTER_DPI_RIGHT} DPI)")
except Exception as e:
    log.warning(f"Nelze nacist nastaveni z DB: {e}")


# ── Decoratory ──
def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session:
            return jsonify({'error': 'Nepřihlášen'}), 401
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session:
            return jsonify({'error': 'Nepřihlášen'}), 401
        if session.get('role') != 'admin':
            return jsonify({'error': 'Přístup odepřen'}), 403
        return f(*a, **kw)
    return d


# ── Stránky ──
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/debug')
def debug_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('debug.html')


# ── Auth ──
@app.post('/api/login')
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        log.warning(f"Neúspěšný login: {username}")
        return jsonify({'error': 'Nesprávné jméno nebo heslo'}), 401
    session.clear()
    session['user_id']  = user['id']
    session['username'] = user['username']
    session['role']     = user['role']
    session.permanent   = True
    log.info(f"Login: {username}")
    return jsonify({'username': username, 'role': user['role']})

@app.post('/api/login/pin')
def api_login_pin():
    data = request.json or {}
    user_id = data.get('user_id')
    pin     = data.get('pin', '').strip()
    if not user_id or not pin:
        return jsonify({'error': 'Chybí ID nebo PIN'}), 400
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id=? AND role='user'", (user_id,)).fetchone()
    if not user or not user['pin_hash'] or not check_password_hash(user['pin_hash'], pin):
        log.warning(f"Neúspěšný PIN login: user_id={user_id}")
        return jsonify({'error': 'Nesprávný PIN'}), 401
    session.clear()
    session['user_id']  = user['id']
    session['username'] = user['username']
    session['role']     = user['role']
    session.permanent   = True
    log.info(f"PIN login: {user['username']}")
    return jsonify({'username': user['username'], 'role': user['role']})

@app.get('/api/login/operators')
def api_login_operators():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, username FROM users WHERE role='user' AND pin_hash IS NOT NULL ORDER BY username"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post('/api/logout')
def api_logout():
    session.clear()
    return jsonify({'ok': True})

@app.post('/api/users/<int:uid>/pin')
@admin_required
def api_user_set_pin(uid):
    data = request.json or {}
    pin  = data.get('pin', '').strip()
    if not pin or not pin.isdigit() or not (4 <= len(pin) <= 8):
        return jsonify({'error': 'PIN musí být 4–8 číslic'}), 400
    with get_db() as db:
        db.execute("UPDATE users SET pin_hash=? WHERE id=? AND role='user'",
                   (generate_password_hash(pin), uid))
    log.info(f"PIN nastaven pro user_id={uid}")
    return jsonify({'ok': True})

@app.get('/api/me')
def api_me():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    return jsonify({'logged_in': True, 'username': session['username'], 'role': session['role']})


# ── Produkty ──
@app.get('/api/products')
@login_required
def api_products_list():
    return jsonify([dict(r) for r in get_all_products()])

@app.get('/api/products/search')
@login_required
def api_products_search():
    code = request.args.get('code', '').strip().upper()
    if not code:
        return jsonify({'error': 'Zadejte kód'}), 400
    row = get_product_by_code(code)
    if not row:
        return jsonify({'error': f'Produkt {code} nenalezen'}), 404
    d = dict(row)
    # Pridej info o sablone
    if d.get('template_id'):
        tmpl = get_template_by_id(d['template_id'])
        d['template_name'] = tmpl['name'] if tmpl else None
    else:
        d['template_name'] = None
    return jsonify(d)

@app.post('/api/products')
@admin_required
def api_product_create():
    data = request.json or {}
    code        = data.get('product_code', '').strip().upper()
    qr          = data.get('qr_content', '')
    txt         = data.get('text_content', '')
    txt2        = data.get('text2', '')
    txt3        = data.get('text3', '')
    txt4        = data.get('text4', '')
    side        = data.get('side', 'both')
    highlight_right = 1 if _truthy(data.get('highlight_right')) else 0
    template_id = data.get('template_id') or None
    if side not in ('L', 'R', 'both'):
        side = 'both'
    if not code or not qr:
        return jsonify({'error': 'Kód a QR obsah jsou povinné'}), 400
    with get_db() as db:
        try:
            db.execute("INSERT INTO products (product_code, qr_content, text_content, text2, text3, text4, side, highlight_right, template_id) VALUES (?,?,?,?,?,?,?,?,?)", (code, qr, txt, txt2, txt3, txt4, side, highlight_right, template_id))
        except Exception as e:
            return jsonify({'error': str(e)}), 409
    return jsonify({'ok': True}), 201

@app.put('/api/products/<int:pid>')
@admin_required
def api_product_update(pid):
    data = request.json or {}
    side        = data.get('side', 'both')
    highlight_right = 1 if _truthy(data.get('highlight_right')) else 0
    template_id = data.get('template_id') or None
    if side not in ('L', 'R', 'both'):
        side = 'both'
    with get_db() as db:
        db.execute("UPDATE products SET product_code=?, qr_content=?, text_content=?, text2=?, text3=?, text4=?, side=?, highlight_right=?, template_id=?, updated_at=datetime('now') WHERE id=?",
                   (data.get('product_code','').strip().upper(), data.get('qr_content',''), data.get('text_content',''), data.get('text2',''), data.get('text3',''), data.get('text4',''), side, highlight_right, template_id, pid))
    return jsonify({'ok': True})

@app.delete('/api/products/<int:pid>')
@admin_required
def api_product_delete(pid):
    with get_db() as db:
        db.execute("DELETE FROM products WHERE id = ?", (pid,))
    return jsonify({'ok': True})


@app.post('/api/products/csv_preview')
@admin_required
def api_products_csv_preview():
    import csv, io
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'Žádný soubor'}), 400
    try:
        text = f.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            f.seek(0)
            text = f.read().decode('cp1250')
        except Exception:
            return jsonify({'error': 'Nepodařilo se dekódovat soubor (zkus UTF-8 nebo CP1250)'}), 400

    reader = csv.DictReader(io.StringIO(text))
    reader.fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]
    REQUIRED = {'product_code', 'qr_content'}
    missing = REQUIRED - set(reader.fieldnames)
    if missing:
        return jsonify({'error': f'Chybí sloupce: {", ".join(missing)}. Povinné: product_code, qr_content'}), 400

    with get_db() as db:
        existing = {r['product_code'] for r in db.execute("SELECT product_code FROM products").fetchall()}
    templates = {str(t['id']): t['name'] for t in get_all_templates()}

    rows = []
    errors = []
    for i, row in enumerate(reader, start=2):
        code = row.get('product_code', '').strip().upper()
        qr   = row.get('qr_content',   '')
        if not code or not qr:
            errors.append(f'Řádek {i}: prázdný product_code nebo qr_content')
            continue
        tid = row.get('template_id', '').strip() or None
        rows.append({
            'row':           i,
            'product_code':  code,
            'qr_content':    qr,
            'text_content':  row.get('text_content', ''),
            'text2':         row.get('text2', ''),
            'text3':         row.get('text3', ''),
            'text4':         row.get('text4', ''),
            'side':          row.get('side', 'both').strip() or 'both',
            'highlight_right': 1 if _truthy(row.get('highlight_right')) else 0,
            'template_id':   tid,
            'template_name': templates.get(tid, '—') if tid else '—',
            'duplicate':     code in existing,
        })
    return jsonify({'rows': rows, 'errors': errors, 'columns': reader.fieldnames})


@app.post('/api/products/csv_import')
@admin_required
def api_products_csv_import():
    data = request.json or {}
    rows = data.get('rows', [])
    if not rows:
        return jsonify({'error': 'Žádné řádky k importu'}), 400

    with get_db() as db:
        existing = {r['product_code'] for r in db.execute("SELECT product_code FROM products").fetchall()}
        imported = skipped = 0
        for row in rows:
            code = row.get('product_code', '').strip().upper()
            if code in existing:
                skipped += 1
                continue
            qr   = row.get('qr_content',   '')
            txt  = row.get('text_content',  '')
            txt2 = row.get('text2', '')
            txt3 = row.get('text3', '')
            txt4 = row.get('text4', '')
            side = row.get('side', 'both').strip() or 'both'
            highlight_right = 1 if _truthy(row.get('highlight_right')) else 0
            if side not in ('L', 'R', 'both'):
                side = 'both'
            tid = row.get('template_id') or None
            try:
                tid = int(tid) if tid else None
            except (ValueError, TypeError):
                tid = None
            try:
                db.execute(
                    "INSERT INTO products (product_code, qr_content, text_content, text2, text3, text4, side, highlight_right, template_id) VALUES (?,?,?,?,?,?,?,?,?)",
                    (code, qr, txt, txt2, txt3, txt4, side, highlight_right, tid)
                )
                existing.add(code)
                imported += 1
            except Exception as e:
                log.warning(f"CSV import skip {code}: {e}")
                skipped += 1

    log.info(f"CSV import: {imported} importováno, {skipped} přeskočeno")
    return jsonify({'ok': True, 'imported': imported, 'skipped': skipped})


@app.get('/api/products/csv_export')
@admin_required
def api_products_csv_export():
    import csv, io
    products = get_all_products()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['product_code', 'qr_content', 'text_content', 'text2', 'text3', 'text4', 'side', 'highlight_right', 'template_id'])
    for p in products:
        writer.writerow([
            p['product_code'], p['qr_content'], p['text_content'],
            p['text2'] if 'text2' in p.keys() else '',
            p['text3'] if 'text3' in p.keys() else '',
            p['text4'] if 'text4' in p.keys() else '',
            p['side'], p['highlight_right'] if 'highlight_right' in p.keys() else 0, p['template_id'] or ''
        ])
    from flask import Response
    return Response(
        '\ufeff' + out.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="produkty_export.csv"'}
    )


# ── Šablony ──
@app.get('/api/templates')
@login_required
def api_templates_list():
    return jsonify([dict(r) for r in get_all_templates()])

@app.get('/api/templates/<int:tid>')
@login_required
def api_template_get(tid):
    row = get_template_by_id(tid)
    if not row:
        return jsonify({'error': 'Nenalezena'}), 404
    d = dict(row)
    d['elements'] = json.loads(d['elements'])
    return jsonify(d)

@app.post('/api/templates')
@admin_required
def api_template_create():
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Název je povinný'}), 400
    with get_db() as db:
        try:
            db.execute("INSERT INTO templates (name, width_mm, height_mm, elements) VALUES (?,?,?,?)",
                       (name, data.get('width_mm', 60), data.get('height_mm', 40), json.dumps(data.get('elements', []))))
        except Exception as e:
            return jsonify({'error': str(e)}), 409
    return jsonify({'ok': True}), 201

@app.put('/api/templates/<int:tid>')
@admin_required
def api_template_update(tid):
    data = request.json or {}
    with get_db() as db:
        db.execute("UPDATE templates SET name=?, width_mm=?, height_mm=?, elements=? WHERE id=?",
                   (data.get('name'), data.get('width_mm'), data.get('height_mm'),
                    json.dumps(data.get('elements', [])), tid))
    return jsonify({'ok': True})

@app.delete('/api/templates/<int:tid>')
@admin_required
def api_template_delete(tid):
    with get_db() as db:
        # Zkontroluj kolik produktu sablonu pouziva
        used = db.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE template_id = ?", (tid,)
        ).fetchone()['cnt']
        if used > 0:
            return jsonify({
                'error': f'Šablonu používá {used} produkt(ů). '
                         f'Nejprve jim přiřaď jinou šablonu v Admin → Produkty.'
            }), 409
        db.execute("DELETE FROM templates WHERE id = ?", (tid,))
    return jsonify({'ok': True})


# ── Tiskový stav ──
@app.get('/api/state')
@login_required
def api_get_state():
    return jsonify(print_state)

@app.post('/api/state/<side>')
@login_required
def api_set_state(side):
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400
    data = request.json or {}
    product = get_product_by_code(data.get('product_code', '').upper())
    if not product:
        return jsonify({'error': 'Produkt nenalezen'}), 404
    # Pouzij sablonu z produktu, nebo override z requestu
    template_id = data.get('template_id') or product['template_id']
    if not template_id:
        # Fallback: prvni dostupna sablona
        with get_db() as db:
            first = db.execute("SELECT id FROM templates LIMIT 1").fetchone()
            template_id = first['id'] if first else None
    template = get_template_by_id(template_id)
    if not template:
        return jsonify({'error': 'Produkt nemá přiřazenou šablonu. Nastav ji v Admin → Produkty.'}), 400
    print_state[side] = {
        'product_id':    product['id'],
        'product_code':  product['product_code'],
        'qr_content':    product['qr_content'],
        'text_content':  product['text_content'],
        'text2':         product['text2'] if 'text2' in product.keys() else '',
        'text3':         product['text3'] if 'text3' in product.keys() else '',
        'text4':         product['text4'] if 'text4' in product.keys() else '',
        'template_id':   template['id'],
        'template_name': template['name'],
        'username':      session['username'],
    }
    return jsonify({'ok': True, 'state': print_state[side]})

@app.delete('/api/state/<side>')
@login_required
def api_clear_state(side):
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400
    print_state[side] = None
    return jsonify({'ok': True})


# ── Tisk ──
def do_print(side, trigger='manual'):
    state = print_state.get(side)
    if not state:
        return False, 'Žádný produkt nevybrán'
    product  = get_product_by_code(state['product_code'])
    template = get_template_by_id(state['template_id'])
    # Vždy použij aktuálně přihlášeného uživatele, ne toho kdo skenoval
    username = session.get('username') or state.get('username', 'system')
    if not product or not template:
        return False, 'Produkt nebo šablona nenalezena'

    log.info(f"Tisk START: strana={side} produkt={state['product_code']} trigger={trigger}")
    ok, err = print_label(side, template, product, username)

    with get_db() as db:
        user_row = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        user_id  = user_row['id'] if user_row else None

    log_print(username=username, user_id=user_id, side=side,
              product=product, template=template,
              trigger=trigger, status='ok' if ok else 'error', error_msg=err)

    if ok:
        log.info(f"Tisk OK: strana={side}")
        if active_order_id:
            try:
                increment_order_count(active_order_id, side)
            except Exception as _e:
                log.warning(f"VP pocitadlo chyba: {_e}")
    else:
        log.error(f"Tisk CHYBA: strana={side} err={err}")
    return ok, err

@app.post('/api/print/<side>')
@login_required
def api_print(side):
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400
    ok, err = do_print(side, trigger='manual')
    if ok:
        return jsonify({'ok': True})
    return jsonify({'error': err}), 500


@app.post('/api/overlay/print/<side>')
def api_overlay_print(side):
    """Tokenem chráněný endpoint pro lokální plovoucí tlačítkový panel."""
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400

    expected = str(getattr(Config, 'OVERLAY_PRINT_TOKEN', '') or '')
    supplied = request.headers.get('X-Print-Token', '')
    if not expected or not hmac.compare_digest(supplied, expected):
        log.warning(f"Overlay tisk odmítnut: strana={side} ip={request.remote_addr}")
        return jsonify({'error': 'Neplatný token'}), 403

    ok, err = do_print(side, trigger='overlay')
    if ok:
        return jsonify({'ok': True, 'side': side})
    return jsonify({'error': err}), 500


# ── Status ──
@app.get('/api/status')
@login_required
def api_status():
    return jsonify({
        'printer_L':  check_printer('L'),
        'printer_R':  check_printer('R'),
        'state_L':    print_state['L'] is not None,
        'state_R':    print_state['R'] is not None,
        'time':       datetime.now().strftime('%H:%M:%S'),
        'date':       datetime.now().strftime('%d.%m.%Y'),
    })

@app.get('/api/log')
@login_required
def api_log():
    limit = int(request.args.get('limit', 100))
    return jsonify([dict(r) for r in get_log(limit)])


# ── Debug ──
@app.get('/api/debug/logs')
@admin_required
def api_debug_logs():
    lines = int(request.args.get('lines', 200))
    return jsonify(read_log_tail(lines))

@app.get('/api/debug/logfiles')
@admin_required
def api_debug_logfiles():
    return jsonify(get_log_files())

@app.get('/api/debug/system')
@admin_required
def api_debug_system():
    import platform, psutil, socket
    try:
        cpu_temp = 'N/A (Windows)'
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        cpu_temp = f"{entries[0].current:.1f}°C"
                        break
        except Exception:
            pass

        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')

        return jsonify({
            'hostname':      socket.gethostname(),
            'ip':            socket.gethostbyname(socket.gethostname()),
            'os':            platform.platform(),
            'uptime':        'N/A',
            'cpu_temp':      cpu_temp,
            'cpu_load':      f"{psutil.cpu_percent(interval=1)}%",
            'mem_total':     f"{mem.total // (1024**2)} MB",
            'mem_used':      f"{mem.used // (1024**2)} MB",
            'disk_total':    f"{disk.total // (1024**3)} GB",
            'disk_used':     f"{disk.used // (1024**3)} GB",
            'disk_free':     f"{disk.free // (1024**3)} GB",
            'python':        platform.python_version(),
            'printer_L_dev': Config.PRINTER_LEFT_NAME,
            'printer_R_dev': Config.PRINTER_RIGHT_NAME,
            'printer_L_ok':  check_printer('L'),
            'printer_R_ok':  check_printer('R'),
            'available_printers': _list_printers(),
            'gpio_mode':     getattr(Config, 'GPIO_MODE', 'none'),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.post('/api/debug/gpio/<side>')
@admin_required
def api_debug_gpio(side):
    """Simuluje GPIO trigger — dostupné vždy na Windows."""
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400
    log.info(f"HTTP GPIO trigger: strana={side} user={session['username']}")
    ok, err = do_print(side, trigger='gpio-http')
    if ok:
        return jsonify({'ok': True, 'message': f'GPIO HTTP trigger OK — strana {side}'})
    return jsonify({'error': err}), 500

@app.post('/api/debug/testprint/<side>')
@admin_required
def api_debug_testprint(side):
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400
    from printer import _print_win32
    printer_name = Config.PRINTER_LEFT_NAME if side == 'L' else Config.PRINTER_RIGHT_NAME
    protocol = (Config.PRINTER_PROTOCOL_LEFT if side == 'L' else Config.PRINTER_PROTOCOL_RIGHT).lower()
    dpi = Config.PRINTER_DPI_LEFT if side == 'L' else Config.PRINTER_DPI_RIGHT

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    if protocol == 'zpl':
        def d(mm): return int(round(mm * dpi / 25.4))
        data = (
            "^XA\r\n"
            "^MMT\r\n"
            f"^PW{d(60)}\r\n"
            f"^LL{d(40)}\r\n"
            "^LH0,0\r\n"
            f"^FO{d(5)},{d(5)}^A0N,{d(5)},{d(5)}^FDHESS TEST PRINT^FS\r\n"
            f"^FO{d(5)},{d(12)}^A0N,{d(4)},{d(4)}^FDStrana: {side}^FS\r\n"
            f"^FO{d(5)},{d(18)}^A0N,{d(3)},{d(3)}^FD{now_str}^FS\r\n"
            "^PQ1,0,1,Y\r\n"
            "^XZ\r\n"
        )
    else:
        data = (
            "SIZE 60 mm, 40 mm\r\n"
            "GAP 3 mm, 0 mm\r\n"
            "CLS\r\n"
            'TEXT 10,10,"4",0,1,1,"HESS TEST PRINT"\r\n'
            f'TEXT 10,35,"3",0,1,1,"Strana: {side}"\r\n'
            f'TEXT 10,55,"3",0,1,1,"{now_str}"\r\n'
            "PRINT 1,1\r\n"
        )

    try:
        import win32print
        _print_win32(printer_name, data.encode('utf-8'))
        return jsonify({'ok': True, 'message': f'Test štítek ({protocol.upper()}) odeslán na {printer_name}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.get('/api/debug/tspl/<side>')
@admin_required
def api_debug_tspl(side):
    if side not in ('L', 'R'):
        return jsonify({'error': 'Neplatná strana'}), 400
    state = print_state.get(side)
    if not state:
        return jsonify({'error': 'Žádný produkt nevybrán'}), 400
    from printer import generate_label
    product  = get_product_by_code(state['product_code'])
    template = get_template_by_id(state['template_id'])
    tspl     = generate_label(template, product, state.get('username', 'debug'))
    return jsonify({'tspl': tspl, 'lines': tspl.split('\r\n')})

# ── Uživatelé ──
@app.get('/api/users')
@admin_required
def api_users():
    with get_db() as db:
        rows = db.execute("SELECT id, username, role, pin_hash FROM users ORDER BY username").fetchall()
    return jsonify([{'id': r['id'], 'username': r['username'], 'role': r['role'], 'has_pin': bool(r['pin_hash'])} for r in rows])

@app.post('/api/users')
@admin_required
def api_user_create():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role     = data.get('role', 'user')
    pin      = data.get('pin') or None
    if not username or not password:
        return jsonify({'error': 'Jméno a heslo jsou povinné'}), 400
    if pin and not pin.isdigit():
        return jsonify({'error': 'PIN musí být číslice'}), 400
    pin_hash = generate_password_hash(pin) if pin else None
    with get_db() as db:
        try:
            db.execute("INSERT INTO users (username, password_hash, role, pin_hash) VALUES (?,?,?,?)",
                       (username, generate_password_hash(password), role, pin_hash))
        except Exception as e:
            return jsonify({'error': str(e)}), 409
    return jsonify({'ok': True}), 201

@app.delete('/api/users/<int:uid>')
@admin_required
def api_user_delete(uid):
    if uid == session['user_id']:
        return jsonify({'error': 'Nelze smazat sám sebe'}), 400
    with get_db() as db:
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
    return jsonify({'ok': True})


# ════════════════════════════════════════════════════════
#  VYROBNI PRIKAZ API
# ════════════════════════════════════════════════════════

@app.get('/api/order/active')
@login_required
def api_order_active():
    order = get_active_order()
    if not order:
        return jsonify({'active': False})
    return jsonify({'active': True, 'order': dict(order)})


@app.post('/api/order/start')
@login_required
def api_order_start():
    global active_order_id
    data = request.json or {}

    existing = get_active_order()
    if existing:
        existing_number = existing['order_number'] or 'bez zakazky'
        return jsonify({'error': f"VP #{existing_number} jiz bezi — nejprve ukoncete."}), 409

    order_number = data.get('order_number', '').strip()

    stateL = print_state.get('L')
    stateR = print_state.get('R')
    if not stateL and not stateR:
        return jsonify({'error': 'Nejprve vyberte produkt alespon pro jednu stranu'}), 400

    with get_db() as db:
        cur = db.execute(
            "INSERT INTO production_orders "
            "(order_number, operator, "
            "product_L_id, product_L_code, template_L_id, template_L_name, "
            "product_R_id, product_R_code, template_R_id, template_R_name) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                order_number, session['username'],
                stateL['product_id']    if stateL else None,
                stateL['product_code']  if stateL else None,
                stateL['template_id']   if stateL else None,
                stateL['template_name'] if stateL else None,
                stateR['product_id']    if stateR else None,
                stateR['product_code']  if stateR else None,
                stateR['template_id']   if stateR else None,
                stateR['template_name'] if stateR else None,
            )
        )
        active_order_id = cur.lastrowid

    log_order_number = order_number or 'bez zakazky'
    log.info(f"VP zahajen: #{log_order_number} operator={session['username']} id={active_order_id}")
    return jsonify({'ok': True, 'order_id': active_order_id})


@app.post('/api/order/finish')
@login_required
def api_order_finish():
    global active_order_id
    order = get_active_order()
    if not order:
        return jsonify({'error': 'Zadny aktivni VP'}), 404

    finish_order(order['id'])
    log.info(f"VP ukoncen: #{order['order_number']} L={order['count_L']} R={order['count_R']}")

    active_order_id = None
    print_state['L'] = None
    print_state['R'] = None
    return jsonify({'ok': True, 'order': dict(order)})


@app.post('/api/order/cancel')
@login_required
def api_order_cancel():
    """Zrusi aktivni VP bez ulozeni — pro zasekle/chybne prikazy."""
    global active_order_id
    order = get_active_order()
    if not order:
        return jsonify({'error': 'Zadny aktivni VP'}), 404

    with get_db() as db:
        db.execute(
            "UPDATE production_orders SET status='cancelled', finished_at=datetime('now') WHERE id=?",
            (order['id'],)
        )
    log.info(f"VP zrusen: #{order['order_number']} operator={session['username']}")

    active_order_id = None
    print_state['L'] = None
    print_state['R'] = None
    return jsonify({'ok': True})


@app.get('/api/order/history')
@login_required
def api_order_history():
    limit = int(request.args.get('limit', 50))
    return jsonify([dict(r) for r in get_order_history(limit)])


# ════════════════════════════════════════════════════════
#  NASTAVENI API
# ════════════════════════════════════════════════════════

@app.get('/api/settings')
@admin_required
def api_settings_get():
    # Nacti vsechny dostupne tiskarny
    try:
        import win32print
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )]
    except Exception:
        printers = []
    settings = get_all_settings()
    # Migrace DPI
    if 'printer_dpi' in settings and 'printer_dpi_left' not in settings:
        settings['printer_dpi_left']  = settings['printer_dpi']
        settings['printer_dpi_right'] = settings['printer_dpi']
    # Migrace encoding
    if 'printer_encoding' in settings and 'printer_encoding_left' not in settings:
        settings['printer_encoding_left']  = settings['printer_encoding']
        settings['printer_encoding_right'] = settings['printer_encoding']
    # Migrace protocol
    if 'printer_protocol' in settings and 'printer_protocol_left' not in settings:
        settings['printer_protocol_left']  = settings['printer_protocol']
        settings['printer_protocol_right'] = settings['printer_protocol']
    return jsonify({
        'settings': settings,
        'available_printers': printers,
    })

@app.post('/api/settings')
@admin_required
def api_settings_save():
    data = request.json or {}
    allowed = {'printer_left', 'printer_right', 'printer_protocol',
               'printer_dpi_left', 'printer_dpi_right', 'printer_encoding_left', 'printer_encoding_right',
               'printer_protocol_left', 'printer_protocol_right'}
    for key, value in data.items():
        if key in allowed:
            set_setting(key, str(value))
            # Aktualizuj Config za behu
            if key == 'printer_left':      Config.PRINTER_LEFT_NAME  = value
            if key == 'printer_right':     Config.PRINTER_RIGHT_NAME = value
            if key == 'printer_protocol':  Config.PRINTER_PROTOCOL   = value
            if key == 'printer_dpi_left':  Config.PRINTER_DPI_LEFT   = int(value)
            if key == 'printer_dpi_right': Config.PRINTER_DPI_RIGHT  = int(value)
            if key == 'printer_encoding_left':   Config.PRINTER_ENCODING_LEFT   = value
            if key == 'printer_encoding_right':  Config.PRINTER_ENCODING_RIGHT  = value
            if key == 'printer_protocol_left':   Config.PRINTER_PROTOCOL_LEFT   = value
            if key == 'printer_protocol_right':  Config.PRINTER_PROTOCOL_RIGHT  = value
    log.info(f"Nastaveni ulozeno: {data}")
    return jsonify({'ok': True})


# ── GPIO callbacks ──
def gpio_trigger_left():
    log.info("GPIO trigger: LEVÁ")
    do_print('L', trigger='gpio')

def gpio_trigger_right():
    log.info("GPIO trigger: PRAVÁ")
    do_print('R', trigger='gpio')

start_gpio_listener(
    callback_left=gpio_trigger_left,
    callback_right=gpio_trigger_right,
)
atexit.register(cleanup_gpio)


# ── Start ──
if __name__ == '__main__':
    from waitress import serve
    host = '0.0.0.0'
    port = 5000
    log.info(f"Server běží na http://localhost:{port}")
    log.info(f"Dostupné tiskárny: {_list_printers()}")
    serve(app, host=host, port=port, threads=4)
