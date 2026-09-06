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

# Windows PowerShell 5.1 still negotiates TLS 1.0 by default on older builds,
# and GitHub refuses anything below 1.2, so the download fails with a connection
# error that says nothing about protocols.
[Net.ServicePointManager]::SecurityProtocol =
  [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

# Resolved by RUNNING each candidate, not by locating it. Windows ships App
# Execution Aliases named python and python3: they are on PATH, Get-Command
# finds them, and they are not interpreters. A validator's entire run produced
# nothing because every step invoked one and got the Store advertisement. The
# old check here matched "*WindowsApps*" in the path, which is a guess about
# where the stub lives rather than a test of what it does.
$python = $null
foreach ($cand in @("python", "python3", "py")) {
  $cmd = Get-Command $cand -ErrorAction SilentlyContinue
  if (-not $cmd) { continue }
  $v = & $cand -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
  if ($LASTEXITCODE -eq 0 -and $v -match "^3\.(1[1-9]|[2-9][0-9])$") {
    $python = $cmd
    Write-Host "Python: $cand $v  ($($cmd.Source))"
    break
  }
}
if (-not $python) {
  Write-Host "No working Python 3.11 or newer was found." -ForegroundColor Red
  Write-Host "Tried python, python3 and py; each was absent, too old, or a stub."
  Write-Host "On Windows those names are often Microsoft Store aliases: on PATH,"
  Write-Host "and not interpreters."
  Write-Host "Install:  winget install Python.Python.3.12"
  Write-Host "Then close and reopen this terminal."
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
