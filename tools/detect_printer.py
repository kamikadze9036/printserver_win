"""
detect_printer.py — Detekce tiskárny na Windows
Spustit: python tools\detect_printer.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

G='\033[92m'; R='\033[91m'; Y='\033[93m'; B='\033[94m'; W='\033[97m'; X='\033[0m'; BOLD='\033[1m'
def ok(m):   print(f"  {G}✓{X}  {m}")
def err(m):  print(f"  {R}✗{X}  {m}")
def warn(m): print(f"  {Y}!{X}  {m}")
def info(m): print(f"  {B}→{X}  {m}")
def hdr(m):  print(f"\n{BOLD}{W}{m}{X}")


hdr("═══ 1. NAINSTALOVANÉ TISKÁRNY (Windows) ═══")
try:
    import win32print
    printers = win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    )
    if not printers:
        err("Žádné tiskárny nenalezeny")
    else:
        print(f"\n  Nalezeno {len(printers)} tiskáren:\n")
        label_printers = []
        for flags, desc, name, comment in printers:
            keywords = ['label', 'xprinter', 'zebra', 'hprt', 'idprt', 'tsc',
                        'barcode', 'etiketa', 'thermal', 'zd', 'xp-']
            is_label = any(k in name.lower() or k in desc.lower() for k in keywords)
            marker = f"  {G}← PRAVDĚPODOBNĚ ETIKETOVÁ{X}" if is_label else ""
            print(f"    [{G if is_label else ''}{name}{X}]{marker}")
            if is_label:
                label_printers.append(name)
        if label_printers:
            print()
            ok(f"Doporučené tiskárny pro config.py:")
            for p in label_printers:
                print(f"    PRINTER_LEFT_NAME  = '{p}'")
        else:
            warn("Žádná etiketová tiskárna automaticky nerozpoznána")
            warn("Nastav PRINTER_LEFT_NAME ručně v config.py")
except ImportError:
    err("win32print není nainstalován")
    info("Instalace: pip install pywin32")


hdr("═══ 2. RAW USB PORTY ═══")
import subprocess
try:
    out = subprocess.check_output(
        'wmic path Win32_USBControllerDevice get Dependent',
        shell=True, text=True, timeout=5
    ).strip()
    usb_lines = [l.strip() for l in out.splitlines() if 'USB' in l]
    if usb_lines:
        print(f"\n  USB zařízení ({len(usb_lines)}):")
        for l in usb_lines[:10]:
            print(f"    {l}")
    else:
        info("Žádná USB zařízení")
except Exception as e:
    warn(f"wmic selhal: {e}")

# Zkusíme RAW porty
print()
info("RAW porty \\\\.\USB001 až \\\\.\USB009:")
for i in range(1, 10):
    port = f'\\\\.\\USB00{i}'
    try:
        with open(port, 'wb') as f:
            pass
        ok(f"{port} dostupný")
    except FileNotFoundError:
        pass
    except PermissionError:
        warn(f"{port} existuje ale přístup odepřen (tiskárna může být obsazená)")
    except Exception:
        pass


hdr("═══ 3. TEST TISKU ═══")
try:
    import win32print

    printers_list = [p[2] for p in win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    )]

    if not printers_list:
        err("Žádné tiskárny")
    else:
        print(f"\n  Vyber tiskárnu pro test:\n")
        for i, p in enumerate(printers_list):
            print(f"    [{i+1}] {p}")
        print(f"    [0] Přeskočit")
        print()

        try:
            choice = int(input("  Volba: ").strip())
        except ValueError:
            choice = 0

        if 1 <= choice <= len(printers_list):
            printer_name = printers_list[choice - 1]
            print()

            TSPL_TEST = (
                "SIZE 60 mm, 40 mm\r\n"
                "GAP 3 mm, 0 mm\r\n"
                "CLS\r\n"
                'TEXT 10,10,"4",0,1,1,"HESS TEST PRINT"\r\n'
                'TEXT 10,35,"3",0,1,1,"Windows 11 - TSPL"\r\n'
                f'TEXT 10,55,"3",0,1,1,"Tiskarna: {printer_name[:25]}"\r\n'
                'TEXT 10,75,"3",0,1,1,"Pokud vidis tento text,"\r\n'
                'TEXT 10,95,"3",0,1,1,"vse funguje spravne!"\r\n'
                "PRINT 1,1\r\n"
            )

            try:
                hPrinter = win32print.OpenPrinter(printer_name)
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Test", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, TSPL_TEST.encode('utf-8'))
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
                win32print.ClosePrinter(hPrinter)
                ok(f"TSPL odesláno na '{printer_name}'")
                print()
                answer = input(f"  {Y}Vytiskla se etiketa?{X} [a/n]: ").strip().lower()
                if answer == 'a':
                    ok("Tiskárna funguje s TSPL!")
                    print()
                    print(f"  {BOLD}Nastav v config.py:{X}")
                    print(f"    PRINTER_LEFT_NAME  = '{printer_name}'")
                    print(f"    PRINTER_PROTOCOL   = 'tspl'")
                else:
                    warn("TSPL nefungovalo — zkus změnit PRINTER_PROTOCOL = 'zpl' v config.py")
            except Exception as e:
                err(f"Tisk selhal: {e}")
                warn("Tiskárna může vyžadovat RAW port místo Windows spooleru")
                warn("Zkus nastav PRINTER_LEFT_NAME = '\\\\\\\\.\\\\USB001' v config.py")

except ImportError:
    err("win32print není dostupný")


hdr("═══ SOUHRN ═══")
print()
info("Po nastavení config.py restartuj server: start.bat")
info("Debug panel: http://localhost:5000/debug")
print()
