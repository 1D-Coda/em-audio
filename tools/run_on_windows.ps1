#Requires -Version 5.1
<#
  EM-Audio reproduction on Windows, through Docker Desktop.

  Why Docker and not a native run: the native Windows path does not currently
  work. Experiments C2, D and E fail there inside FFmpeg and c2patool for
  reasons that have not been diagnosed, and handing you a package that fails
  would waste your afternoon and tell us nothing. What runs inside the container
  is Linux and is identical on every host, so this path is the one we can stand
  behind.

  This file is forty lines and has never been executed on Windows. Everything it
  does is in tools/run_container.py, which was exercised on the machine that
  wrote it. If this misbehaves, run the Python directly; it needs nothing here:

      python tools\run_container.py

  Usage:
      .\run_on_windows.ps1            build, run, collect
      .\run_on_windows.ps1 -Check     check Docker only, run nothing
#>
[CmdletBinding()]
param([switch]$Check)

$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
  Write-Host "Python was not found:  winget install Python.Python.3.12" -ForegroundColor Red
  exit 2
}
if ($python.Source -like "*WindowsApps*") {
  Write-Host "That is the Microsoft Store's Python stub, not a real install." -ForegroundColor Red
  Write-Host "Install Python:  winget install Python.Python.3.12"
  Write-Host "Then close and reopen this terminal."
  exit 2
}

$script = Join-Path $PSScriptRoot "run_container.py"
if (-not (Test-Path $script)) {
  Write-Host "run_container.py is not next to this file; run this from the repository's tools directory." -ForegroundColor Red
  exit 2
}

$argv = @($script)
if ($Check) { $argv += "--check" }

& $python.Source @argv
$rc = $LASTEXITCODE

Write-Host ""
switch ($rc) {
  0 { Write-Host "Done. Conformance passed and the declarations held here." -ForegroundColor Green }
  3 { Write-Host "Done. Conformance passed and a declared footprint does not hold on this build." -ForegroundColor Green
      Write-Host "That is a result, not a failure. Please send the out directory." -ForegroundColor Green }
  2 { Write-Host "Nothing was run: something is missing. See the message above." -ForegroundColor Yellow }
  default { Write-Host "Unexpected exit $rc. Please send everything, including this output." -ForegroundColor Red }
}
exit $rc
