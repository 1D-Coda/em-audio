#Requires -Version 5.1
<#
  EM-Audio independent reproduction, Windows entry point.

  This file is deliberately almost empty. It finds Python and hands over to
  tools/bootstrap_reproduction.py, which does the fetching, checking, running
  and collecting. That split is the point: the Python was written and exercised
  on the machine that produced it, and this wrapper is the only part that has
  never run on Windows. Keeping it to a dozen lines keeps the untested surface
  to a dozen lines.

  Usage, from any PowerShell prompt:
      .\reproduce.ps1                 fetch, check, run, collect
      .\reproduce.ps1 -Check          check the environment and stop
      .\reproduce.ps1 -Dir D:\repro -Ref v1.0.2

  If this file misbehaves, run the Python directly; it needs nothing from here:
      python tools\bootstrap_reproduction.py
#>
[CmdletBinding()]
param(
  [string]$Dir,
  [string]$Ref = "main",
  [switch]$Check
)

$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
  Write-Host "Python was not found." -ForegroundColor Red
  Write-Host "Install it with:  winget install Python.Python.3.12"
  exit 2
}

# Prefer a bootstrap sitting next to this file; fall back to downloading just
# that one file, so this script works on its own without a checkout.
$boot = Join-Path $PSScriptRoot "bootstrap_reproduction.py"
if (-not (Test-Path $boot)) {
  $boot = Join-Path $env:TEMP "bootstrap_reproduction.py"
  $url  = "https://raw.githubusercontent.com/1D-Coda/em-audio/main/tools/bootstrap_reproduction.py"
  Write-Host "Fetching the bootstrapper from $url"
  Invoke-WebRequest -Uri $url -OutFile $boot -UseBasicParsing
}

$argv = @($boot, "--ref", $Ref)
if ($Dir)   { $argv += @("--dir", $Dir) }
if ($Check) { $argv += "--check" }

& $python.Source @argv
exit $LASTEXITCODE
