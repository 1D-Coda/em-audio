#Requires -Version 5.1
<#
  EM-Audio independent reproduction, Windows bootstrapper.

  This script is deliberately thin. Everything it can defer to Python it does,
  because the Python is cross-platform and tested, while this layer is not: it
  was written on macOS and has never been executed on Windows. Treat any failure
  here as a bug in this file rather than in the reproduction, and send the output
  regardless. A bootstrapper that fails loudly is doing its job.

  What it does:
    1. checks Python and bash
    2. fetches the repository at the tag under study
    3. installs the pinned Python packages
    4. runs the package self-test, which names anything missing and how to get it
    5. runs the pipeline
    6. runs the comparison against the released results
    7. collects everything into one zip to send back

  Usage, from a PowerShell prompt:
      .\reproduce.ps1
      .\reproduce.ps1 -WorkDir D:\emaudio -Tag v1.0.2
#>
[CmdletBinding()]
param(
  [string]$WorkDir = "$env:USERPROFILE\em-audio-repro",
  [string]$Repo    = "https://github.com/1D-Coda/em-audio.git",
  [string]$Tag     = "v1.0.2"
)

$ErrorActionPreference = "Stop"
function Say($m) { Write-Host "`n=== $m" -ForegroundColor Cyan }
function Bad($m) { Write-Host "  $m" -ForegroundColor Red }
function Ok ($m) { Write-Host "  $m" -ForegroundColor Green }

Say "Checking what is available"
# Written for Windows PowerShell 5.1, which ships with Windows and does not
# have the null-coalescing operator. Plain if/else keeps this runnable without
# installing PowerShell 7 first.
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
  Bad "Python was not found. Install it with:  winget install Python.Python.3.12"
  exit 2
}
Ok "python: $(& $python.Source -V 2>&1)"

$bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bash) {
  Bad "bash was not found. run_all.sh is a bash script."
  Bad "Install Git for Windows (provides Git Bash):  winget install Git.Git"
  exit 2
}
Ok "bash: $($bash.Source)"

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) { Bad "git was not found:  winget install Git.Git"; exit 2 }
Ok "git: $(& git --version)"

Say "Fetching the repository at $Tag"
if (Test-Path $WorkDir) {
  Write-Host "  $WorkDir already exists; using it as is."
} else {
  & git clone --branch $Tag --depth 1 $Repo $WorkDir
  if ($LASTEXITCODE -ne 0) { Bad "clone failed"; exit 1 }
}
Set-Location $WorkDir
Ok "working in $WorkDir"

Say "Installing the pinned Python packages"
& $python.Source -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) {
  Bad "pip install failed. Send this output; do not continue."
  exit 1
}
Ok "requirements installed"

Say "Package self-test (fast, read-only)"
& $python.Source tools\repro_selftest.py
if ($LASTEXITCODE -ne 0) {
  Bad "The self-test found problems. Install what it names, then run this again."
  Bad "Nothing was run, so nothing was wasted."
  exit 1
}

Say "Running the pipeline (about 25 minutes, plus the corpus download)"
Write-Host "  Output is being written to run_all_output.txt as well as here."
& $bash.Source -c "./run_all.sh 2>&1 | tee run_all_output.txt"
$runExit = $LASTEXITCODE
if ($runExit -eq 0) { Ok "run_all.sh finished: RUN OK" }
else { Bad "run_all.sh exited $runExit. Send the log; a failure here is a result." }

Say "Comparing against the released results"
& $python.Source tools\verify_reproduction.py 2>&1 |
  Tee-Object -FilePath verify_output.txt
$verifyExit = $LASTEXITCODE
Write-Host "  verify_reproduction.py exit code: $verifyExit"
Write-Host "  A non-zero exit is not necessarily a defect; it means a"
Write-Host "  deterministic output differs, which is what we want reported."

Say "Collecting what to send back"
$stamp = Get-Date -Format "yyyy-MM-dd"
$out   = Join-Path $WorkDir "EM_Audio_results_$stamp"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Copy-Item -Recurse -Force "results\machine_readable" $out -ErrorAction SilentlyContinue
foreach ($f in @("results\PREFLIGHT.txt","run_all_output.txt","verify_output.txt")) {
  if (Test-Path $f) { Copy-Item -Force $f $out }
}
@"
Platform : $([System.Environment]::OSVersion.VersionString)
Machine  : $env:PROCESSOR_IDENTIFIER, $env:NUMBER_OF_PROCESSORS logical processors
Python   : $(& $python.Source -V 2>&1)
Tag      : $Tag
run_all.sh exit          : $runExit
verify_reproduction exit : $verifyExit
Collected: $(Get-Date -Format o)
"@ | Set-Content (Join-Path $out "WINDOWS_RUN.txt")

$zip = "$out.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "$out\*" -DestinationPath $zip
Ok "Send this file back: $zip"

Say "Done"
Write-Host "  run_all.sh exit $runExit, verify exit $verifyExit"
Write-Host "  Send $zip whatever the exit codes were. A failed run that is"
Write-Host "  reported is more useful to us than a run that was made to pass."
