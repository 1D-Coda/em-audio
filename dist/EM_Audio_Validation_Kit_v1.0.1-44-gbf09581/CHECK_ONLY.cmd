@echo off
REM Checks the machine and changes nothing. Double-click this first.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0validate.ps1" -Check
echo.
pause
