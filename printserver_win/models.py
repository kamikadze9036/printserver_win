import sqlite3
import os
from config import Config


def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # bezpečné pro více čtenářů
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(Config.DATABASE), exist_ok=True)
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'user',  -- 'admin' | 'user'
            pin_hash      TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code  TEXT    NOT NULL UNIQUE,
            qr_content    TEXT    NOT NULL,
            text_content  TEXT    NOT NULL DEFAULT '',
            text2         TEXT    NOT NULL DEFAULT '',
            text3         TEXT    NOT NULL DEFAULT '',
            text4         TEXT    NOT NULL DEFAULT '',
            side          TEXT    NOT NULL DEFAULT 'both',
            template_id   INTEGER REFERENCES templates(id),
            created_at    TEXT    DEFAULT (datetime('now')),
            updated_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS templates (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL UNIQUE,
            width_mm      REAL    NOT NULL,
            height_mm     REAL    NOT NULL,
            elements      TEXT    NOT NULL DEFAULT '[]',  -- JSON pole prvků
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS production_orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number   TEXT    NOT NULL,
            product_L_id   INTEGER REFERENCES products(id),
            product_L_code TEXT,
            template_L_id  INTEGER REFERENCES templates(id),
            template_L_name TEXT,
            product_R_id   INTEGER REFERENCES products(id),
            product_R_code TEXT,
            template_R_id  INTEGER REFERENCES templates(id),
            template_R_name TEXT,
            operator       TEXT    NOT NULL,
            started_at     TEXT    DEFAULT (datetime('now')),
            finished_at    TEXT,
            count_L        INTEGER DEFAULT 0,
            count_R        INTEGER DEFAULT 0,
            status         TEXT    DEFAULT 'active'   -- 'active' | 'finished'
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS print_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    DEFAULT (datetime('now')),
            user_id       INTEGER REFERENCES users(id),
            username      TEXT    NOT NULL,
            side          TEXT    NOT NULL,   -- 'L' | 'R'
            product_id    INTEGER REFERENCES products(id),
            product_code  TEXT    NOT NULL,
            template_id   INTEGER REFERENCES templates(id),
            template_name TEXT    NOT NULL,
            trigger       TEXT    NOT NULL,   -- 'gpio' | 'manual'
            status        TEXT    NOT NULL,   -- 'ok' | 'error'
            error_msg     TEXT
        );
        """)

        # Vychozi nastaveni tiskarny
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_left',      'LABEL_PRINTER_LEFT'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_right',     'LABEL_PRINTER_RIGHT'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_protocol_left',  'tspl'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_protocol_right', 'tspl'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_dpi_left',  '300'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_dpi_right', '300'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_encoding_left',  'utf-8'))
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('printer_encoding_right', 'utf-8'))

        # Migrace: pin_hash
        try:
            db.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT")
        except Exception:
            pass

        # Migrace: pridej sloupec side do existujici DB pokud chybi
        try:
            db.execute("ALTER TABLE products ADD COLUMN side TEXT NOT NULL DEFAULT 'both'")
        except Exception:
            pass  # Sloupec uz existuje

        # Migrace: text2/3/4
        for _col in ('text2', 'text3', 'text4'):
            try:
                db.execute(f"ALTER TABLE products ADD COLUMN {_col} TEXT NOT NULL DEFAULT ''")
            except Exception:
                pass  # Sloupec uz existuje

        # Výchozí admin účet (heslo: admin123)
        from werkzeug.security import generate_password_hash
        db.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, role)
            VALUES (?, ?, 'admin')
        """, ('admin', generate_password_hash('admin123')))

        # Výchozí operátor (heslo: hess2025)
        db.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, role)
            VALUES (?, ?, 'user')
        """, ('operator1', generate_password_hash('hess2025')))

        # Vzorová šablona
        # Seed sablony a produkty jen pri uplne prazdne DB (prvni spusteni)
        _tmpl_count = db.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
        _prod_count  = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if _tmpl_count == 0:
            import json
            elements = json.dumps([
                {"type": "qr",   "name": "QR kód",        "x": 2,  "y": 2,  "w": 20, "h": 20, "content": "{qr_content}"},
                {"type": "text", "name": "Kód produktu",   "x": 24, "y": 2,  "w": 34, "h": 8,  "font_size": 10, "content": "{product_code}"},
                {"type": "text", "name": "Popis",          "x": 24, "y": 12, "w": 34, "h": 8,  "font_size": 7,  "content": "{text_content}"},
                {"type": "text", "name": "Datum a čas",    "x": 24, "y": 22, "w": 34, "h": 6,  "font_size": 6,  "content": "{date} {time}"},
                {"type": "text", "name": "Operátor",       "x": 24, "y": 30, "w": 34, "h": 6,  "font_size": 6,  "content": "{operator}"},
            ])
            db.execute("""
                INSERT INTO templates (name, width_mm, height_mm, elements)
                VALUES (?, ?, ?, ?)
            """, ('60×40 mm STANDARD', 60, 40, elements))

        if _prod_count == 0:
            # Vzorové produkty - jen pri prazdne DB
            first_tmpl = db.execute("SELECT id FROM templates LIMIT 1").fetchone()
            tmpl_id = first_tmpl['id'] if first_tmpl else None
            db.executemany("""
                INSERT INTO products (product_code, qr_content, text_content, text2, text3, text4, side, template_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
            ('FG 001235', 'https://erp.local/fg/001235', 'MOTOR SESTAVA A / LOT 2024Q4', '', '', '', 'L', tmpl_id),
            ('FG 001234', 'https://erp.local/fg/001234', 'MOTOR SESTAVA B / LOT 2024Q4', '', '', '', 'R', tmpl_id),
            ('FG 000877', 'https://erp.local/fg/000877', 'KRYT PREVODOVKY XL / 2025Q1',  '', '', '', 'both', tmpl_id),
        ])


# ── Settings helpers ─────────────────────────────────────

# ── Production order helpers ─────────────────────────────

def get_active_order():
    with get_db() as db:
        return db.execute(
            "SELECT * FROM production_orders WHERE status='active' ORDER BY id DESC LIMIT 1"
        ).fetchone()

def get_order_by_id(oid):
    with get_db() as db:
        return db.execute("SELECT * FROM production_orders WHERE id=?", (oid,)).fetchone()

def increment_order_count(order_id, side):
    col = 'count_L' if side == 'L' else 'count_R'
    with get_db() as db:
        db.execute(f"UPDATE production_orders SET {col}={col}+1 WHERE id=?", (order_id,))

def finish_order(order_id):
    with get_db() as db:
        db.execute(
            "UPDATE production_orders SET status='finished', finished_at=datetime('now') WHERE id=?",
            (order_id,)
        )

def get_order_history(limit=50):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM production_orders ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def get_setting(key, default=''):
    with get_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row['value'] if row else default

def set_setting(key, value):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))

def get_all_settings():
    with get_db() as db:
        rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {r['key']: r['value'] for r in rows}


# ── Helpers ──────────────────────────────────────────────

def get_product_by_code(code):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM products WHERE product_code = ?", (code.upper(),)
        ).fetchone()

def get_template_by_id(tid):
    with get_db() as db:
        return db.execute("SELECT * FROM templates WHERE id = ?", (tid,)).fetchone()

def get_all_templates():
    with get_db() as db:
        return db.execute("SELECT id, name, width_mm, height_mm FROM templates ORDER BY name").fetchall()

def get_all_products():
    with get_db() as db:
        return db.execute("SELECT * FROM products ORDER BY product_code").fetchall()

def log_print(username, user_id, side, product, template, trigger, status, error_msg=None):
    with get_db() as db:
        db.execute("""
            INSERT INTO print_log
              (username, user_id, side, product_id, product_code,
               template_id, template_name, trigger, status, error_msg)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            username, user_id, side,
            product['id'], product['product_code'],
            template['id'], template['name'],
            trigger, status, error_msg
        ))

def get_log(limit=100):
    with get_db() as db:
        return db.execute("""
            SELECT * FROM print_log ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
