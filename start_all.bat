@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo CHYBA: venv nenalezeno - spust nejprve install.bat
    pause
    exit /b 1
)

start "Print Server" /min "%~dp0start.bat"
timeout /t 8 /nobreak >nul
start "" "http://localhost:5000"
call "%~dp0start_floating_panel.bat"
exit /b
