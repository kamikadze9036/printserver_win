@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo   HESS PLASTICS - PRINT SERVER
echo ============================================
echo.

:: Kontrola venv
if not exist "venv\Scripts\python.exe" (
    echo CHYBA: venv nenalezeno - spust nejprve install.bat
    pause
    exit /b 1
)

echo Spoustim server...
echo Prohlizec: http://localhost:5000
echo Pro ukonceni stiskni Ctrl+C
echo.

venv\Scripts\python.exe app.py

echo.
echo Server zastaven.
pause
