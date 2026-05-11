@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo CHYBA: venv nenalezeno - spust nejprve install.bat
    pause
    exit /b 1
)

if exist "venv\Scripts\pythonw.exe" (
    start "HESS Print Panel" "venv\Scripts\pythonw.exe" "tools\floating_print_panel.py"
) else (
    start "HESS Print Panel" "venv\Scripts\python.exe" "tools\floating_print_panel.py"
)
