@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   HESS PLASTICS - PRINT SERVER - INSTALACE
echo ============================================
echo.

set "APP_DIR=%~dp0"
set "AUTOSTART_SCRIPT=%APP_DIR%start_all.bat"

:: Kontrola Pythonu
python --version
if errorlevel 1 (
    echo CHYBA: Python nenalezen!
    echo Stahnete Python 3.11+ z https://python.org
    echo Zatrhnete "Add Python to PATH" pri instalaci.
    pause
    exit /b 1
)

echo.
echo [1/5] Vytvarim Python prostredi...
python -m venv venv
if errorlevel 1 (
    echo CHYBA: Vytvoreni venv selhalo
    pause
    exit /b 1
)
echo OK - venv vytvoren

echo.
echo [2/5] Aktualizuji pip...
venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
    echo CHYBA: pip upgrade selhal
    pause
    exit /b 1
)

echo.
echo [3/5] Instaluji zavislosti...
venv\Scripts\pip.exe install flask werkzeug waitress pywin32 psutil qrcode pyserial
if errorlevel 1 (
    echo CHYBA: Instalace zavislosti selhala
    pause
    exit /b 1
)
echo OK - zavislosti nainstalovany

echo.
echo [4/5] Pripravuji slozky a soubory...
if not exist data mkdir data
if not exist data\logs mkdir data\logs
echo OK - slozky vytvoreny

echo.
echo Spoustim pywin32 post-install...
venv\Scripts\python.exe venv\Scripts\pywin32_postinstall.py -install
echo OK

echo.
echo [5/5] Nastavuji automaticke spusteni po prihlaseni do Windows...
if exist "%AUTOSTART_SCRIPT%" (
    schtasks /Create /TN "Print Server Autostart" /TR "\"%AUTOSTART_SCRIPT%\"" /SC ONLOGON /RL HIGHEST /F
    if errorlevel 1 (
        echo VAROVANI: Automaticke spusteni se nepodarilo nastavit.
        echo Spust install.bat jako spravce, nebo nastav ulohu rucne podle README.md.
    ) else (
        echo OK - uloha Print Server Autostart vytvorena/aktualizovana
    )
) else (
    echo VAROVANI: Soubor start_all.bat nenalezen, automaticke spusteni preskoceno.
)

echo.
echo ============================================
echo   INSTALACE DOKONCENA
echo ============================================
echo.
echo   Spusteni serveru:  venv\Scripts\python.exe app.py
echo   Prohlizec:         http://localhost:5000
echo   Autostart:         Print Server Autostart
echo.
echo   Vychozi ucty:
echo     admin     / admin123
echo     operator1 / hess2025
echo.
pause
