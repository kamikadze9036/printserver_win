# HESS Plastics — Print Server (Windows 11)

Tiskový server pro dvě USB etiketové tiskárny. Webové rozhraní přístupné z libovolného zařízení v síti.

---

## Rychlý start

```
1. Rozbalit ZIP do C:\PrintServer\
2. Spustit install.bat (jako správce)
3. Spustit start.bat
4. Otevřít http://localhost:5000
5. Přihlásit se: admin / admin123
6. Admin → Nastavení → vybrat tiskárny
7. Admin → Šablony → vytvořit šablonu štítku
8. Admin → Produkty → přidat produkty a přiřadit šablonu
```

---

## Changelog

### Aktuální změny
- Číslo výrobního příkazu je volitelné.
- Admin → Produkty má tlačítko **DUPLIKOVAT** pro rychlé vytvoření kopie produktu.
- Produktový/admin modal má vnitřní scroll pro menší obrazovky.
- **UKONČIT VÝROBU** už nevyžaduje potvrzení; potvrzení zůstává u **ZRUŠIT VP**.
- Beze změny databázového schématu — původní `data\printserver.db` lze použít s touto verzí.
- Struktura projektu je sjednocená do jednoho rootu; aplikace už není ve vnořené složce `printserver_win\printserver_win`.

---

## Struktura projektu

```
printserver_win/
├── app.py                  # Flask server (Waitress)
├── config.py               # Výchozí konfigurace
├── models.py               # SQLite schéma + helpers
├── printer.py              # TSPL/ZPL generátor, win32print
├── gpio_listener.py        # HTTP / COM port trigger
├── logger.py               # Rotující file logger
├── requirements.txt        # Python závislosti
├── install.bat             # Instalace (spustit jednou)
├── start.bat               # Spuštění serveru
├── reset_db.bat            # Reset databáze na výchozí stav
├── templates/              # Jinja2 HTML šablony
├── static/css/main.css     # Styly (Hess Plastics branding)
├── static/js/
│   ├── main.js             # Sdílené utility
│   ├── index.js            # Logika tisku + scan flow
│   ├── admin.js            # Admin panel logika
│   └── debug.js            # Debug panel logika
├── data/
│   ├── printserver.db      # SQLite databáze (vše)
│   ├── last_print_L.prn    # Poslední TSPL levá (debug)
│   ├── last_print_R.prn    # Poslední TSPL pravá (debug)
│   └── logs/
│       └── printserver.log # Rotující log soubor
└── tools/
    └── detect_printer.py   # Detekce a test tiskárny
```

---

## Databáze (SQLite)

Vše v jednom souboru: `data\printserver.db`

| Tabulka | Obsah |
|---|---|
| `users` | Uživatelé — username, password_hash, role |
| `products` | Produkty — kód, QR obsah, text, strana, šablona |
| `templates` | Šablony štítků — rozměry, prvky (JSON) |
| `settings` | Nastavení tiskáren (uložené v DB) |
| `production_orders` | Výrobní příkazy — start/stop, počítadla kusů |
| `print_log` | Log každého tisku |

**Seed data** — vkládají se pouze při prázdné DB (první spuštění nebo po reset_db.bat). Restart serveru s existující DB nic nepřidá.

**Zálohování / přenos na jiný počítač** — stačí zkopírovat `data\printserver.db`. Server při kopírování ideálně vypni. Pokud vedle DB existují soubory `printserver.db-wal` nebo `printserver.db-shm`, zkopíruj je také, případně nejdřív server korektně ukonči.

**Reset** — spustit `reset_db.bat`.

**Aktuální změny bez migrace** — volitelné číslo výrobního příkazu, duplikace produktů, scroll modalů a odstranění potvrzení při ukončení výroby nemění strukturu DB.

---

## Výchozí přístupy

| Uživatel | Heslo | Role |
|---|---|---|
| admin | admin123 | Admin |
| operator1 | hess2025 | Uživatel |

Změňte hesla po prvním přihlášení v Admin → Uživatelé.

---

## Instalace

```
1. Python 3.11+ z python.org — zatrhnout "Add Python to PATH"
2. Rozbalit ZIP do cílové složky, např. `C:\PrintServer\`
3. CMD jako správce ve složce projektu
4. install.bat
5. start.bat
6. http://localhost:5000
```

## Automatické spuštění po startu Windows

Nejjednodušší varianta pro Windows 11 Pro je naplánovaná úloha při
přihlášení uživatele. Spustí server a potom otevře prohlížeč s hlavní
obrazovkou.

PowerShell spusť jako správce a vlož:

```powershell
$dir = "C:\PrintServer"; $bat = "$dir\autostart.bat"; Set-Content -Path $bat -Encoding ASCII -Value '@echo off', "cd /d $dir", 'start "Print Server" /min "C:\PrintServer\start.bat"', 'timeout /t 8 /nobreak >nul', 'start "" "http://localhost:5000"', 'exit /b'; schtasks /Create /TN "Print Server Autostart" /TR "`"$bat`"" /SC ONLOGON /RL HIGHEST /F
```

Příkaz vytvoří `C:\PrintServer\autostart.bat` a naplánovanou úlohu
`Print Server Autostart`. Po přihlášení do Windows se spustí server a po
8 sekundách se otevře prohlížeč na `http://localhost:5000`.

Otestovat bez restartu:

```powershell
schtasks /Run /TN "Print Server Autostart"
```

Pokud je projekt v jiné složce než `C:\PrintServer`, změň v prvním příkazu
hodnotu `$dir`.

Zastavení serveru:

```bat
taskkill /f /im python.exe
```

---

## Nastavení tiskáren

Admin → záložka **Nastavení** — každá tiskárna má vlastní kartu:

| Parametr | Popis |
|---|---|
| Název tiskárny | Přesný název z Windows — ze seznamu v UI |
| Protokol | TSPL (čínské tiskárny) nebo ZPL (Zebra) |
| DPI | 200 (LabelPrinter 4xx TSC), 203 nebo 300 |
| Kódování | UTF-8, Latin-1, CP1250 |

Změny platí okamžitě bez restartu serveru.

**Diagnostika:**
```
venv\Scripts\python tools\detect_printer.py
```

**RAW port (bez ovladače):**
```
Nastav v UI: \\.\USB001
```

---

## Produkty a strany tiskáren

| Pole | Popis |
|---|---|
| Kód produktu | Identifikátor (skenuje se čtečkou) |
| QR obsah | Data zakódovaná do QR kódu |
| Textový obsah | Text vedle QR kódu |
| Strana | LEVÁ / PRAVÁ / OBĚ |
| Šablona | Přiřazená šablona štítku |

Naskenování produktu na špatnou stranu → červená chyba, nelze potvrdit.

Produkt bez šablony → oranžové varování v admin tabulce (⚠ není).

Šablonu nelze smazat pokud ji používá produkt — nejprve odeber šablonu z produktů.

**Duplikace produktu:** Admin → Produkty → **DUPLIKOVAT** vytvoří kopii se stejným QR obsahem, texty, stranou i šablonou. Nový kód bude například `PŮVODNÍ_KÓD COPY`, případně `COPY 2`, `COPY 3` atd.

---

## Šablony štítků

Editor v Admin → Šablony. Pozice v **mm**.

### Prvky
- **QR kód** — X, Y, šířka, výška (mm)
- **Text** — X, Y, šířka, výška (mm)

### Velikost textu

Velikost určuje **výška okýnka (h mm)**. Pole "Font (pt)" se nepoužívá.

| h v editoru | Výsledná výška textu (200 DPI) |
|---|---|
| < 4 mm | ~1 mm |
| 4–5 mm | ~1.5 mm |
| 6–7 mm | ~2 mm |
| ≥ 8 mm | ~3 mm |

### Proměnné

| Proměnná | Hodnota při tisku |
|---|---|
| `{product_code}` | Kód produktu |
| `{qr_content}` | Obsah QR kódu |
| `{text_content}` | Textový popis produktu |
| `{date}` | Datum tisku (dd.mm.yyyy) |
| `{time}` | Čas tisku (hh:mm:ss) |
| `{operator}` | Přihlášený uživatel |

### Jak se generuje TSPL

- `SIZE` a `GAP` → mm
- `TEXT` a `QRCODE` souřadnice → dots (mm × DPI / 25.4)
- Font v uvozovkách: `TEXT 189,16,"4",0,1,1,"text"`

**Převodní tabulka 200 DPI:**

| mm | dots |
|---|---|
| 2 | 16 |
| 5 | 39 |
| 10 | 79 |
| 20 | 157 |
| 30 | 236 |

---

## Výrobní příkazy

### Zahájení
1. Naskenovat produkt(y)
2. Volitelně zadat číslo výrobního příkazu
3. ZAHÁJIT VÝROBU →

### Banner na hlavní obrazovce
- Číslo VP, operátor, čas zahájení
- Pokud číslo VP není zadané, zobrazí se **Bez zakázky**
- Počítadla kusů L / P / Celkem (obnovují se každých 10s)
- Kódy produktů

### Ukončení
- **UKONČIT VÝROBU** — řádné ukončení, uloží s počty kusů, bez potvrzovacího okna
- **ZRUŠIT VP** — pro zaseknuté příkazy, uloží jako ZRUŠEN, vyžaduje potvrzení

VP přežije restart serveru — obnoví se automaticky z DB.

### Historie
Admin → **Výrobní příkazy** — statusy AKTIVNÍ / UKONČEN / ZRUŠEN.

---

## UX flow — scan skenerem

```
Přihlášení → Modal výběru (nebo obnova aktivního VP)
    │
    ├── Scan levého → Enter
    │     ├── OK: focus skočí na pravé pole
    │     └── CHYBA: červené pole, po 1.5s vymaže, focus zpět
    │
    └── Scan pravého → Enter
          ├── OK: po 0.6s automaticky potvrdí
          └── CHYBA: červené pole, po 1.5s vymaže, focus zpět

Hlavní obrazovka
    ├── GPIO / HTTP trigger → automatický tisk
    └── Tlačítko TISKNOUT → ruční tisk
```

Při otevření modalu se vždy vymažou oba předchozí výběry.

---

## Trigger na Windows

### HTTP (výchozí)
```
POST http://localhost:5000/api/debug/gpio/L
POST http://localhost:5000/api/debug/gpio/R
```
Nebo Debug panel → GPIO → SIMULOVAT.

### COM port (USB-Serial adaptér)
```python
# config.py
GPIO_MODE              = 'serial'
GPIO_SERIAL_PORT_LEFT  = 'COM3'
GPIO_SERIAL_PORT_RIGHT = 'COM4'
```

---

## Správa a monitoring

```bat
:: Logy
data\logs\printserver.log

:: Live log (PowerShell)
Get-Content data\logs\printserver.log -Wait -Tail 20

:: Ověření portu
netstat -ano | findstr :5000

:: Debug panel
http://localhost:5000/debug
```

**PRN soubory** — `data\last_print_L.prn` a `data\last_print_R.prn` obsahují poslední TSPL příkazy. Lze otevřít v poznámkovém bloku pro kontrolu.

---

## Časté problémy

| Problém | Řešení |
|---|---|
| `python` není rozpoznán | Přeinstaluj Python se zatrženým "Add to PATH" |
| Tiskárna se nezobrazuje v Nastavení | Zkontroluj instalaci v Windows → Nastavení → Tiskárny |
| Port 5000 obsazen | Změň port: poslední řádek `app.py` → `serve(app, port=8080)` |
| Tiskárna tiskne jen QR, bez textu | Debug → TSPL náhled → zkontroluj TEXT příkazy |
| Pozice textu neodpovídají | Zkontroluj DPI v Admin → Nastavení (200 DPI pro LabelPrinter 4xx TSC) |
| Šablona se vrací po restartu | Aktualizuj `models.py` ze ZIPu |
| Šablonu nelze smazat | Odeber šablonu ze všech produktů v Admin → Produkty |
| `win32print` chyba | `venv\Scripts\python venv\Scripts\pywin32_postinstall.py -install` |
| Prázdná DB | Spustit `reset_db.bat` |
