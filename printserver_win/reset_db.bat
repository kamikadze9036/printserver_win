@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo   RESET DATABAZE
echo ============================================
echo.
echo POZOR: Smaze vsechna data (produkty, sablony, log, uzivatele)
echo a vytvori novou cistou databazi se vzorovymi daty.
echo.
set /p CONFIRM="Opravdu chces smazat databazi? [ano/ne]: "
if /i "%CONFIRM%" neq "ano" (
    echo Zruseno.
    pause
    exit /b 0
)

if exist "data\printserver.db" (
    del "data\printserver.db"
    echo Stara databaze smazana.
)

echo Vytvarim novou databazi...
venv\Scripts\python.exe -c "from models import init_db; init_db(); print('Databaze vytvorena se vzorovymi daty.')"

echo.
echo Hotovo. Spust server pres start.bat
pause
