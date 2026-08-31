@echo off
REM Runs the whole study inside a pinned container and writes out\SEND_THIS_BACK.zip.
REM Needs only Docker Desktop. No Python, no Git, no FFmpeg on this machine.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0validate.ps1"
echo.
pause
