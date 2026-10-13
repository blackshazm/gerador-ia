@echo off
cd /d "%~dp0"
python run_studio.py
if errorlevel 1 pause
