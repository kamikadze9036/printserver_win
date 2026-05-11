"""
Malý Windows plovoucí panel pro tisk bez přepínání záložek v prohlížeči.

Spuštění:
    venv\\Scripts\\python.exe tools\\floating_print_panel.py

Volitelné proměnné prostředí:
    PRINT_SERVER_URL=http://localhost:5000
    OVERLAY_PRINT_TOKEN=hess-overlay-change-me
"""

import json
import os
import threading
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import ttk


SERVER_URL = os.environ.get("PRINT_SERVER_URL", "http://localhost:5000").rstrip("/")
TOKEN = os.environ.get("OVERLAY_PRINT_TOKEN", "hess-overlay-change-me")


class FloatingPrintPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Print")
        self.root.geometry("290x150")
        self.root.minsize(260, 130)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#111827")

        self.status_var = tk.StringVar(value="Připraveno")

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Left.TButton",
            font=("Segoe UI", 15, "bold"),
            padding=(10, 16),
            background="#E8A000",
            foreground="#ffffff",
        )
        style.map("Left.TButton", background=[("active", "#C98900")])
        style.configure(
            "Right.TButton",
            font=("Segoe UI", 15, "bold"),
            padding=(10, 16),
            background="#2F6EA5",
            foreground="#ffffff",
        )
        style.map("Right.TButton", background=[("active", "#285F8E")])

        title = tk.Label(
            self.root,
            text="HESS PRINT",
            bg="#111827",
            fg="#d1d5db",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        title.pack(fill="x", padx=10, pady=(8, 4))

        row = tk.Frame(self.root, bg="#111827")
        row.pack(fill="both", expand=True, padx=10)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        self.btn_left = ttk.Button(
            row,
            text="LEVÁ",
            style="Left.TButton",
            command=lambda: self.print_side("L"),
        )
        self.btn_left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.btn_right = ttk.Button(
            row,
            text="PRAVÁ",
            style="Right.TButton",
            command=lambda: self.print_side("R"),
        )
        self.btn_right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#111827",
            fg="#9ca3af",
            font=("Segoe UI", 9),
            anchor="w",
        )
        status.pack(fill="x", padx=10, pady=(5, 8))

    def print_side(self, side):
        self._set_busy(True)
        self.status_var.set(f"Tisknu {'levou' if side == 'L' else 'pravou'}...")
        threading.Thread(target=self._send_print, args=(side,), daemon=True).start()

    def _send_print(self, side):
        try:
            url = f"{SERVER_URL}/api/overlay/print/{side}"
            req = urllib.request.Request(
                url,
                data=b"{}",
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Print-Token": TOKEN,
                },
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                body = response.read().decode("utf-8", errors="replace")
                data = json.loads(body or "{}")
                if data.get("ok"):
                    self._finish(f"OK: {'levá' if side == 'L' else 'pravá'} vytištěna")
                else:
                    self._finish("Chyba: neznámá odpověď")
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode("utf-8", errors="replace")
            try:
                msg = json.loads(msg).get("error", msg)
            except Exception:
                pass
            self._finish(f"Chyba: {msg}")
        except Exception as exc:
            self._finish(f"Chyba spojení: {exc}")

    def _finish(self, message):
        self.root.after(0, lambda: self._set_done(message))

    def _set_done(self, message):
        self.status_var.set(message)
        self._set_busy(False)

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_left.configure(state=state)
        self.btn_right.configure(state=state)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FloatingPrintPanel().run()
