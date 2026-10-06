# Everything a Windows machine needs, from nothing to a results archive.
# Driven by Reproduce_on_Windows.cmd, which is the double-clickable entry.
#
# Nothing is installed without asking. A reproduction package that silently
# changes someone's machine should not be trusted, and the person running it is
# entitled to see what it does; that is also why this is a script and not a
# signed executable.
param(
  # -Check stops after the dependency check, running no experiments. Useful on
  # its own, and it is how continuous integration exercises the install path.
  [switch]$Check,
  # -Yes answers the install prompt. Only for automation: a person running this
  # should see what is about to be installed on their machine.
  [switch]$Yes
)
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol =
  [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

function Say  ($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Ok   ($m) { Write-Host $m -ForegroundColor Green }
function Bad  ($m) { Write-Host $m -ForegroundColor Red }
function Halt ($m) { Bad $m; Read-Host "`nPress Enter to close" | Out-Null; exit 2 }

# Locate the package: this file ships at the top, next to em-audio\.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($c in @($here, (Join-Path $here "em-audio"), (Split-Path -Parent $here))) {
  if (Test-Path (Join-Path $c "run_all.sh")) { $root = $c; break }
}
if (-not $root) { Halt "Cannot find run_all.sh next to this file." }
Set-Location $root

Say "EM-Audio: independent reproduction"
Write-Host "Folder: $root"

# espeak-ng truncates its output path past about 200 characters and reports
# success, and the run then dies somewhere unrelated. Windows also still
# defaults to MAX_PATH 260. Refuse early rather than let either happen.
if ($root.Length -gt 120) {
  Bad "The path is long ($($root.Length) characters)."
  Halt "Move this folder to C:\em-audio and double-click again."
}

$haveWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)

function Need($exe) { return -not (Get-Command $exe -ErrorAction SilentlyContinue) }

Say "1/7  What is missing"
$wants = @()
if (Need "git")       { $wants += @{ n="Git (brings bash, which run_all.sh needs)"; id="Git.Git" } }
if (Need "ffmpeg")    { $wants += @{ n="FFmpeg";    id="Gyan.FFmpeg" } }
if (Need "node")      { $wants += @{ n="Node.js";   id="OpenJS.NodeJS" } }
if (Need "espeak-ng") { $wants += @{ n="eSpeak NG"; id="eSpeak-NG.eSpeak-NG" } }
$needPython   = (Need "python") -and (Need "py")
$needC2patool = Need "c2patool"
if ($needPython) { $wants += @{ n="Python 3.12"; id="Python.Python.3.12" } }

if ($wants.Count -eq 0 -and -not $needC2patool) {
  Ok "  everything present"
} else {
  foreach ($w in $wants)  { Write-Host "  missing $($w.n)" }
  if ($needC2patool)      { Write-Host "  missing c2patool (downloaded from GitHub, no installer)" }
  Write-Host ""
  if ($wants.Count -gt 0 -and -not $haveWinget) {
    Bad "winget is missing. It is how Windows installs these programs."
    Halt "Update 'App Installer' from the Microsoft Store, or install them by hand."
  }
  if ($Yes) {
    Write-Host "Installing without asking (-Yes)."
  } else {
    $yn = Read-Host "Install what is missing now? [y/N]"
    if ($yn -notmatch '^[sSyY]$') { Halt "OK. Install it and double-click again." }
  }

  foreach ($w in $wants) {
    Say "Installing $($w.n)"
    winget install --id $($w.id) -e --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) { Bad "  winget exited $LASTEXITCODE for $($w.id). Continuing." }
  }
  if ($needC2patool) {
    Say "Installing c2patool"
    $v   = "0.27.15"
    $url = "https://github.com/contentauth/c2pa-rs/releases/download/c2patool-v$v/c2patool-v$v-x86_64-pc-windows-msvc.zip"
    $zip = Join-Path $env:TEMP "c2patool.zip"
    $dst = "C:\c2patool"
    Invoke-WebRequest $url -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $dst -Force
    $exe = Get-ChildItem $dst -Recurse -Filter c2patool.exe | Select-Object -First 1
    if (-not $exe) { Halt "The c2patool archive did not contain c2patool.exe." }
    $dir = $exe.Directory.FullName
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($user -notlike "*$dir*") {
      [Environment]::SetEnvironmentVariable("Path", "$user;$dir", "User")
    }
    $env:Path = "$env:Path;$dir"
    Ok "  c2patool in $dir"
  }
  # winget updates the machine PATH; this session does not see it yet.
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}

Say "2/7  bash"
# Git for Windows first, and never C:\Windows\system32\bash.exe. With the WSL
# feature enabled that file is on PATH and Get-Command bash returns it, but it
# is the WSL launcher, not a shell: with no distribution installed it fails
# with "WSL (9 - Relay) ERROR: CreateProcessCommon: execvpe(/bin/bash)", which
# is what an independent reproducer hit on the v1.0.5 package.
$bashExe = $null
$cands = @("$env:ProgramFiles\Git\bin\bash.exe",
           "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
           "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe")
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git -and $git.Source) {
  # git.exe lives in <Git>\cmd or <Git>\bin; bash.exe is in <Git>\bin. Strip the
  # last two path components with a regex rather than Split-Path so the same
  # line can be exercised on the non-Windows machine that maintains this file.
  $gitRoot = $git.Source -replace "\\[^\\]+\\[^\\]+$", ""
  # String concatenation, not Join-Path: Join-Path validates the drive, and
  # under $ErrorActionPreference = "Stop" a git on a detached drive would end
  # the whole script here instead of falling through to the next candidate.
  $cands += "$gitRoot\bin\bash.exe"
}
foreach ($p in $cands) { if ($p -and (Test-Path $p)) { $bashExe = $p; break } }
if (-not $bashExe) {
  $b = Get-Command bash -ErrorAction SilentlyContinue
  if ($b -and $b.Source -and ($b.Source -notlike "*\system32\*")) { $bashExe = $b.Source }
}
if (-not $bashExe) { Halt "Cannot find the Git for Windows bash. The system32 bash is the WSL launcher and will not work. Install Git for Windows, close this window and double-click again." }
Ok "  $bashExe"

Say "3/7  Python interpreter"
# Resolved by running each candidate. On Windows the name python3 is usually an
# App Execution Alias: on PATH, and not an interpreter. An earlier validator's
# entire run produced nothing because every step invoked it.
$py = $null
foreach ($c in @("python", "python3", "py")) {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
  $v = & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
  if ($LASTEXITCODE -eq 0 -and $v -match '^3\.(1[1-9]|[2-9][0-9])$') { $py = $c; break }
}
if (-not $py) { Halt "No usable Python 3.11+ found. Close the window, open it again and retry." }
Ok "  $py"

Say "4/7  Python dependencies"
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) { & $py -m venv $venv }
$vpy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $vpy)) { Halt "Could not create the virtual environment in .venv" }
& $vpy -m pip install --quiet --upgrade pip
& $vpy -m pip install --quiet -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Halt "pip failed." }
$env:PY = $vpy
Ok "  ready"

Say "5/7  Pre-check (runs no experiments)"
& $vpy (Join-Path $root "tools\repro_selftest.py")
if ($LASTEXITCODE -ne 0) { Halt "The pre-check found problems. Fix them and double-click again." }

if ($Check) {
  Ok "`nCheck complete: everything is present and usable."
  Write-Host "Run it again without -Check for the full run."
  exit 0
}

Say "6/7  Full run (about 25 minutes, plus 322 MB the first time)"
Write-Host "Do not close this window."
# Windows PowerShell 5.1 turns every stderr line of a native command into a
# NativeCommandError once stderr is redirected, and under "Stop" the first one
# is terminating: curl's progress meter, a Python SyntaxWarning, or one curl
# TLS complaint ended the whole run at this line for an independent
# reproducer. Native output is text here, whichever stream it came on.
$ErrorActionPreference = "Continue"
& $bashExe -lc "cd '$($root -replace '\\','/')' && ./run_all.sh" 2>&1 |
  ForEach-Object { "$_" } |
  Tee-Object -FilePath (Join-Path $root "run_all_output.txt") -Encoding utf8
$runRc = $LASTEXITCODE
if ($runRc -eq 0) { Ok "  run_all.sh finished with RUN OK" }
else { Bad "  run_all.sh exited $runRc. That is a result: send it to us anyway." }

& $vpy (Join-Path $root "tools\verify_reproduction.py") 2>&1 |
  ForEach-Object { "$_" } |
  Tee-Object -FilePath (Join-Path $root "verify_output.txt") -Encoding utf8
$verRc = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Write-Host "`n  verify_reproduction.py exited $verRc"
Write-Host "  A non-zero value is NOT your fault. It means an output"
Write-Host "  differs, which is exactly what we want to know."

Say "7/7  Packing what to send back"
$label = ($env:COMPUTERNAME -replace '[^A-Za-z0-9_-]','_')
$arch  = $env:PROCESSOR_ARCHITECTURE
$stamp = Get-Date -Format "yyyy-MM-dd"
$outDir = Join-Path $here "results_${label}_${arch}_$stamp"
if (Test-Path $outDir) { Remove-Item $outDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item (Join-Path $root "results\machine_readable") $outDir -Recurse -ErrorAction SilentlyContinue
foreach ($f in @("results\PREFLIGHT.txt","run_all_output.txt","verify_output.txt")) {
  $p = Join-Path $root $f
  if (Test-Path $p) { Copy-Item $p $outDir }
}
@"
machine     : $label
architecture: $arch
windows     : $([Environment]::OSVersion.VersionString)
run_all     : $runRc
verify      : $verRc
date        : $((Get-Date).ToUniversalTime().ToString("s"))Z
"@ | Set-Content (Join-Path $outDir "RUN_INFO.txt")
$zip = "$outDir.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $outDir -DestinationPath $zip
Remove-Item $outDir -Recurse -Force
Ok "Done: $zip"
Write-Host "`nSend that file."
Read-Host "`nPress Enter to close" | Out-Null
