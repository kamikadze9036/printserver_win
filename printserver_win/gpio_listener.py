"""
gpio_listener.py — Windows verze

Na Windows není fyzické GPIO. Podporované módy:
  'none'   — pouze HTTP trigger přes /api/gpio/trigger/<side>
  'serial' — trigger přes COM port (signál z PLC/tlačítka přes USB-Serial)

HTTP trigger lze volat z libovolného zařízení v síti nebo z testovacího
tlačítka v debug panelu.
"""

import threading
import logging
log = logging.getLogger(__name__)


def start_gpio_listener(callback_left, callback_right,
                        pin_left=None, pin_right=None, bounce_ms=300):
    """
    Spustí listener podle GPIO_MODE v config.
    Na Windows výchozí = 'none' (pouze HTTP trigger).
    """
    from config import Config
    mode = getattr(Config, 'GPIO_MODE', 'none').lower()

    if mode == 'none':
        log.info("GPIO mode: none — používej HTTP trigger /api/gpio/trigger/<side>")
        return

    if mode == 'serial':
        _start_serial_listener(callback_left, callback_right)
        return

    log.warning(f"Neznámý GPIO_MODE: {mode}")


def _start_serial_listener(cb_left, cb_right):
    """
    Poslouchá na COM portech — čeká na byte '1' (levá) nebo '2' (pravá).
    Zapojení: USB-Serial adaptér → tlačítko → GND.
    Arduino/PLC pošle '1' nebo '2' při stisku.
    """
    from config import Config

    def listen(port, callback, side):
        try:
            import serial
            log.info(f"Serial GPIO listener: {port} ({side})")
            with serial.Serial(port, Config.GPIO_SERIAL_BAUD, timeout=1) as ser:
                while True:
                    try:
                        byte = ser.read(1)
                        if byte:
                            _safe_call(callback, side)
                    except Exception as e:
                        log.error(f"Serial read chyba ({port}): {e}")
        except ImportError:
            log.warning("pyserial není nainstalován — serial GPIO nedostupný")
            log.warning("Instalace: pip install pyserial")
        except Exception as e:
            log.error(f"Serial GPIO init chyba ({port}): {e}")

    threading.Thread(
        target=listen,
        args=(Config.GPIO_SERIAL_PORT_LEFT, cb_left, 'L'),
        daemon=True, name='gpio-serial-L'
    ).start()

    threading.Thread(
        target=listen,
        args=(Config.GPIO_SERIAL_PORT_RIGHT, cb_right, 'R'),
        daemon=True, name='gpio-serial-R'
    ).start()


def _safe_call(fn, side):
    try:
        fn(side)
    except Exception as e:
        log.error(f"GPIO callback chyba (strana {side}): {e}")


def cleanup_gpio():
    pass   # Na Windows není co uvolňovat
