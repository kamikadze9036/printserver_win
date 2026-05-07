import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hess-printserver-change-me')
    DATABASE   = os.path.join(BASE_DIR, 'data', 'printserver.db')

    # Windows: tiskárny podle názvu v systému NEBO raw port
    # Zjisti název: Nastavení → Bluetooth a zařízení → Tiskárny
    # Příklad: 'Xprinter XP-420B' nebo raw port '\\\\.\USB001'
    PRINTER_LEFT_NAME  = os.environ.get('PRINTER_LEFT',  'LABEL_PRINTER_LEFT')
    PRINTER_RIGHT_NAME = os.environ.get('PRINTER_RIGHT', 'LABEL_PRINTER_RIGHT')

    # Protokol: 'tspl' nebo 'zpl'
    PRINTER_PROTOCOL = 'tspl'

    # DPI tiskárny: 203 nebo 300
    PRINTER_DPI = 200   # TSC/cinske tiskarny casto 200 DPI

    # Kódování
    PRINTER_ENCODING = 'utf-8'

    # GPIO — na Windows není fyzické GPIO
    # Simulace přes HTTP endpoint /api/gpio/trigger/<side>
    # Pro PLC/HW trigger přes COM port nastav:
    GPIO_MODE = 'none'        # 'none' | 'serial' | 'http'
    GPIO_SERIAL_PORT_LEFT  = 'COM3'
    GPIO_SERIAL_PORT_RIGHT = 'COM4'
    GPIO_SERIAL_BAUD = 9600
    GPIO_PIN_LEFT  = 17       # zachováno pro kompatibilitu
    GPIO_PIN_RIGHT = 22
    GPIO_BOUNCE_MS = 300

    # Plovoucí Windows panel pro tisk bez překlikávání v prohlížeči.
    # Stejný token musí používat server i tools\floating_print_panel.py.
    OVERLAY_PRINT_TOKEN = os.environ.get('OVERLAY_PRINT_TOKEN', 'hess-overlay-change-me')

    # Logování
    LOG_DIR          = os.path.join(BASE_DIR, 'data', 'logs')
    LOG_FILE         = os.path.join(BASE_DIR, 'data', 'logs', 'printserver.log')
    LOG_MAX_BYTES    = 5 * 1024 * 1024
    LOG_BACKUP_COUNT = 5
