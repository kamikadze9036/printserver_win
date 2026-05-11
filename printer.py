# -*- coding: utf-8 -*-
"""
printer.py -- TSPL generator + tisk na Windows

Format overeny na tiskarne LabelPrinter 4xx 200DPI TSC:
  - SIZE v mm
  - GAP v mm  
  - Pozice TEXT a QRCODE v mm (ne dots)
  - Font v uvozovkach: TEXT x,y,"3",0,1,1,"text"
  - QRCODE x,y,L,cell,A,0,"data"  (cell = dots na modul)
"""

import os
import json
from datetime import datetime
from config import Config


def get_dpi(side='L'):
    if side == 'L':
        return int(getattr(Config, 'PRINTER_DPI_LEFT',  getattr(Config, 'PRINTER_DPI', 200)))
    return int(getattr(Config, 'PRINTER_DPI_RIGHT', getattr(Config, 'PRINTER_DPI', 200)))


def resolve_variables(text, product, username):
    now = datetime.now()
    # sqlite3.Row nepodporuje .get() – převedeme na dict
    if not isinstance(product, dict):
        product = dict(product)
    replacements = {
        '{product_code}': product.get('product_code', ''),
        '{qr_content}':   product.get('qr_content', ''),
        '{text_content}': product.get('text_content', ''),
        '{text1}':        product.get('text_content', ''),
        '{text2}':        product.get('text2', '') or '',
        '{text3}':        product.get('text3', '') or '',
        '{text4}':        product.get('text4', '') or '',
        '{date}':         now.strftime('%d.%m.%Y'),
        '{time}':         now.strftime('%H:%M:%S'),
        '{datetime_iso}': now.strftime('%Y-%m-%dT%H:%M:%S'),
        '{operator}':     username,
    }
    for key, val in replacements.items():
        text = text.replace(key, val)
    return text


# ════════════════════════════════════════
#  TSPL GENERATOR
#  Pozice v mm, font v uvozovkach
#  Stejny format jako overeny script
# ════════════════════════════════════════

def generate_tspl(template_row, product, username, side='L'):
    w_mm     = float(template_row['width_mm'])
    h_mm     = float(template_row['height_mm'])
    elements = json.loads(template_row['elements'])
    dpi      = get_dpi(side)

    lines = [
        "SIZE {} mm,{} mm".format(w_mm, h_mm),
        "GAP 3 mm,0 mm",
        "SPEED 4",
        "DENSITY 8",
        "CLS",
    ]

    for el in elements:
        etype      = el.get('type')
        el_content = el.get('content', '')
        # Prevod mm -> dots (tiskarna bere dots v TEXT/QRCODE)
        x = int(round(float(el.get('x', 0)) * dpi / 25.4))
        y = int(round(float(el.get('y', 0)) * dpi / 25.4))

        if etype == 'qr':
            qr_data    = resolve_variables(el_content or '{qr_content}', product, username)
            qr_escaped = qr_data.replace('"', "'")
            w_dots  = int(round(float(el.get('w', 20)) * dpi / 25.4))
            qr_cell = max(2, w_dots // 21)
            lines.append('QRCODE {},{},L,{},A,0,"{}"'.format(
                x, y, qr_cell, qr_escaped
            ))

        elif etype == 'text':
            text         = resolve_variables(el_content, product, username)
            text_escaped = text.replace('"', "'")
            h_mm_el = float(el.get('h', 6))
            if h_mm_el >= 8:
                font = '4'
            elif h_mm_el >= 6:
                font = '3'
            elif h_mm_el >= 4:
                font = '2'
            else:
                font = '1'
            lines.append('TEXT {},{},"{}",0,1,1,"{}"'.format(
                x, y, font, text_escaped
            ))

    lines += ["PRINT 1", ""]
    return '\r\n'.join(lines)


# ════════════════════════════════════════
#  ZPL GENERATOR
# ════════════════════════════════════════

def mm2dots(mm_val, dpi):
    return int(round(float(mm_val) * dpi / 25.4))


def generate_zpl(template_row, product, username, side='L'):
    w_mm     = float(template_row['width_mm'])
    h_mm     = float(template_row['height_mm'])
    elements = json.loads(template_row['elements'])
    dpi      = get_dpi(side)

    lines = [
        "^XA",
        "^MMT",
        "^PW{}".format(mm2dots(w_mm, dpi)),
        "^LL{}".format(mm2dots(h_mm, dpi)),
        "^LH0,0",
    ]

    for el in elements:
        etype      = el.get('type')
        el_content = el.get('content', '')
        x = mm2dots(el.get('x', 0), dpi)
        y = mm2dots(el.get('y', 0), dpi)

        if etype == 'qr':
            qr_data = resolve_variables(el_content or '{qr_content}', product, username)
            w_dots  = mm2dots(el.get('w', 20), dpi)
            qr_mag  = max(2, min(10, w_dots // 21))
            lines += [
                "^FO{},{}".format(x, y),
                "^BQN,2,{}".format(qr_mag),
                "^FDMM,A{}^FS".format(qr_data),
            ]
        elif etype == 'text':
            text = resolve_variables(el_content, product, username)
            fh   = max(20, int(el.get('font_size', 8) * dpi / 25.4 * 0.35))
            lines += [
                "^FO{},{}".format(x, y),
                "^A0N,{},{}".format(fh, fh),
                "^FD{}^FS".format(text.replace('^', '').replace('~', '')),
            ]

    lines += ["^PQ1,0,1,Y", "^XZ", ""]
    return '\r\n'.join(lines)


def generate_label(template_row, product, username, side='L'):
    if side == 'L':
        protocol = getattr(Config, 'PRINTER_PROTOCOL_LEFT',
                   getattr(Config, 'PRINTER_PROTOCOL', 'tspl')).lower()
    else:
        protocol = getattr(Config, 'PRINTER_PROTOCOL_RIGHT',
                   getattr(Config, 'PRINTER_PROTOCOL', 'tspl')).lower()
    if protocol == 'zpl':
        return generate_zpl(template_row, product, username, side)
    return generate_tspl(template_row, product, username, side)


# ════════════════════════════════════════
#  WINDOWS TISK
# ════════════════════════════════════════

def _print_win32(printer_name, data_bytes):
    import win32print
    if not printer_name:
        printer_name = win32print.GetDefaultPrinter()
    hPrinter = win32print.OpenPrinter(printer_name)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("TSPL Label", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, data_bytes)
            win32print.EndPagePrinter(hPrinter)
        finally:
            win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)


def _print_raw_port(port, data_bytes):
    with open(port, 'wb') as f:
        f.write(data_bytes)


def _save_prn_file(side, data_bytes):
    out = os.path.join(
        os.path.dirname(Config.DATABASE),
        'last_print_{}.prn'.format(side)
    )
    with open(out, 'wb') as f:
        f.write(data_bytes)
    return out


def print_label(side, template_row, product, username):
    printer_name = (Config.PRINTER_LEFT_NAME if side == 'L'
                    else Config.PRINTER_RIGHT_NAME)

    if side == 'L':
        encoding = getattr(Config, 'PRINTER_ENCODING_LEFT',
                   getattr(Config, 'PRINTER_ENCODING', 'utf-8'))
    else:
        encoding = getattr(Config, 'PRINTER_ENCODING_RIGHT',
                   getattr(Config, 'PRINTER_ENCODING', 'utf-8'))

    data_bytes = generate_label(template_row, product, username, side).encode(
        encoding, errors='replace'
    )

    try:
        import win32print
        use_default = (not printer_name or
                       printer_name in ('LABEL_PRINTER_LEFT', 'LABEL_PRINTER_RIGHT'))
        _print_win32(printer_name if not use_default else '', data_bytes)
        return True, None
    except ImportError:
        pass
    except Exception as e:
        return False, "win32print chyba: {}".format(e)

    raw_prefixes = ('\\\\.\\', 'COM', 'com')
    if any(printer_name.startswith(p) for p in raw_prefixes):
        try:
            _print_raw_port(printer_name, data_bytes)
            return True, None
        except Exception as e:
            return False, "RAW port chyba ({}): {}".format(printer_name, e)

    try:
        path = _save_prn_file(side, data_bytes)
        return False, (
            "Tiskarna '{}' nenalezena.\nPRN ulozen: {}\nDostupne: {}".format(
                printer_name, path, _list_printers()
            )
        )
    except Exception as e:
        return False, str(e)


def check_printer(side):
    printer_name = (Config.PRINTER_LEFT_NAME if side == 'L'
                    else Config.PRINTER_RIGHT_NAME)
    try:
        import win32print
        use_default = (not printer_name or
                       printer_name in ('LABEL_PRINTER_LEFT', 'LABEL_PRINTER_RIGHT'))
        if use_default:
            win32print.GetDefaultPrinter()
            return True
        return printer_name in _list_printers()
    except Exception:
        raw_prefixes = ('\\\\.\\', 'COM', 'com')
        if any(printer_name.startswith(p) for p in raw_prefixes):
            try:
                with open(printer_name, 'wb') as _:
                    pass
                return True
            except Exception:
                return False
        return False


def _list_printers():
    try:
        import win32print
        result = []
        printers = win32print.EnumPrinters(6)
        for p in printers:
            if len(p) >= 3 and p[2]:
                name = p[2].strip()
                if name and name not in result:
                    result.append(name)
        return result
    except Exception:
        return []
