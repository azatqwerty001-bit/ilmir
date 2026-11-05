@echo off
cd /d "%~dp0"
py -3 start_bot.py --reset-token
if errorlevel 1 pause
