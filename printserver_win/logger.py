"""
logger.py — Centrální logger s rotací souborů

Použití v jakémkoliv modulu:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("Zpráva")
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from config import Config

_initialized = False


def setup_logging():
    """Inicializuje root logger — volat jednou při startu app."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    os.makedirs(Config.LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        fmt='%(asctime)s [%(levelname)-8s] %(name)-20s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ── File handler (rotující) ──
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # ── Console handler (pro SSH / journalctl) ──
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Potlač verbose logy z Werkzeug/Gunicorn
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def read_log_tail(lines=200) -> list[dict]:
    """
    Přečte posledních N řádků z log souboru.
    Vrací list dict: {timestamp, level, module, message}
    """
    result = []
    if not os.path.exists(Config.LOG_FILE):
        return result

    try:
        with open(Config.LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()

        for raw in all_lines[-lines:]:
            raw = raw.rstrip()
            if not raw:
                continue
            try:
                # Format: 2025-01-01 12:00:00 [INFO    ] module               zpráva
                parts = raw.split(']', 1)
                meta  = parts[0].split('[')
                ts    = meta[0].strip()
                level = meta[1].strip() if len(meta) > 1 else 'INFO'
                rest  = parts[1].strip() if len(parts) > 1 else raw
                # Odděl modul od zprávy
                rest_parts = rest.split(None, 1)
                module  = rest_parts[0] if rest_parts else ''
                message = rest_parts[1] if len(rest_parts) > 1 else ''
            except Exception:
                ts, level, module, message = '', 'INFO', '', raw

            result.append({
                'timestamp': ts,
                'level':     level,
                'module':    module,
                'message':   message,
                'raw':       raw,
            })
    except Exception as e:
        result.append({'timestamp': '', 'level': 'ERROR', 'module': 'logger', 'message': str(e), 'raw': str(e)})

    return result


def get_log_files() -> list[dict]:
    """Seznam všech log souborů s velikostí."""
    files = []
    if not os.path.exists(Config.LOG_DIR):
        return files
    for fname in sorted(os.listdir(Config.LOG_DIR), reverse=True):
        if not fname.endswith('.log') and '.log.' not in fname:
            continue
        fpath = os.path.join(Config.LOG_DIR, fname)
        size  = os.path.getsize(fpath)
        files.append({
            'name': fname,
            'size': size,
            'size_human': _human_size(size),
        })
    return files


def _human_size(b: int) -> str:
    for unit in ('B', 'KB', 'MB'):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"
