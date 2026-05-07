@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo CHYBA: venv nenalezeno - spust nejprve install.bat
    pause
    exit /b 1
)

start "HESS Print Panel" venv\Scripts\python.exe tools\floating_print_panel.py
