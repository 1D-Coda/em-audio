@echo off
REM Double-click this. It hands off to PowerShell, which does the work.
REM
REM Deliberately a script and not a signed executable: an unsigned .exe that
REM downloads and installs software is what a person should refuse to run, and a
REM reproduction package has to be one the reproducer can read.
setlocal
set "HERE=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%reproduce_windows_full.ps1"
if errorlevel 1 (
  echo.
  echo El procedimiento termino con error. Manda run_all_output.txt si existe.
  pause
)
endlocal
