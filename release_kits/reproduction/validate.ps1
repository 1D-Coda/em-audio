#Requires -Version 5.1
<#
  EM-Audio independent validation, Windows.

  Needs Docker Desktop and nothing else. Python, Node, FFmpeg, eSpeak NG,
  c2patool and Git are all inside the image; the source under test is shipped in
  this package rather than cloned, so the kit is self-contained and immutable.

  An earlier version of this kit said "only Docker is required" while its wrapper
  also needed Python and Git on the host. That is fixed here, and it is the kind
  of mismatch worth stating rather than quietly correcting.

  Exit codes, two of which are successes:
     0  conformance passed and every declared footprint held on this build
     3  conformance passed, and a declared footprint does not hold on this
        image's FFmpeg. That is the paper's own finding measured again.
     1  something else failed, which is a defect worth reporting
    10  Docker missing or not running; nothing scientific was attempted
#>
[CmdletBinding()]
param([switch]$Check)

$ErrorActionPreference = "Stop"
$root  = $PSScriptRoot
$src   = Join-Path $root "source_snapshot"
$out   = Join-Path $root "out"
$image = "em-audio:validation"

function Head($m) { Write-Host "`n=== $m" -ForegroundColor Cyan }
function Ok  ($m) { Write-Host "  $m" -ForegroundColor Green }
function Note($m) { Write-Host "  $m" }
function Bad ($m) { Write-Host "  $m" -ForegroundColor Red }

Head "This machine"
Note "OS       : $([System.Environment]::OSVersion.VersionString)"
Note "CPU      : $env:PROCESSOR_IDENTIFIER"
Note "Cores    : $env:NUMBER_OF_PROCESSORS"
Note "PowerShell: $($PSVersionTable.PSVersion)"

Head "Docker"
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
  Bad "Docker was not found."
  Bad "Install Docker Desktop from https://www.docker.com/products/docker-desktop"
  Bad "then open it once and wait until it says Running."
  exit 10
}
Note (& docker --version)
& docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Bad "Docker is installed but the engine is not running."
  Bad "Open Docker Desktop and wait until the whale icon says Running, then run this again."
  Bad "If it will not start, Windows may need virtualisation or the WSL2 backend enabled."
  exit 10
}
Ok "engine is running"

Head "Package"
if (-not (Test-Path (Join-Path $src "run_all.sh"))) {
  Bad "source_snapshot is missing from this package; the ZIP is incomplete."
  exit 1
}
$files = (Get-ChildItem $src -Recurse -File | Measure-Object).Count
Ok "source snapshot present ($files files); nothing will be downloaded from GitHub"

$free = (Get-PSDrive -Name ($root.Substring(0,1))).Free / 1GB
Note ("free disk on this drive: {0:N1} GB" -f $free)
if ($free -lt 12) { Bad "Less than 12 GB free. The corpus and image need roughly that." }

if ($Check) {
  Head "Check only"
  Ok "Nothing was built or run. When you are ready, run RUN_EM_AUDIO_VALIDATION.cmd"
  exit 0
}

Head "Building the pinned image (several minutes the first time, cached after)"
& docker build -t $image $src
if ($LASTEXITCODE -ne 0) { Bad "the image did not build; please send this output"; exit 1 }
Ok "image built"

New-Item -ItemType Directory -Force -Path $out | Out-Null
Head "Running the study (about 25 minutes, plus the corpus download)"
Note "Everything is written to $out"
$started = Get-Date
& docker run --rm -v "${out}:/out" $image
$rc = $LASTEXITCODE
$mins = [int]((Get-Date) - $started).TotalMinutes

Head "What this run concluded"
switch ($rc) {
  0 { Ok "Conformance passed, and every declared footprint held on this build." }
  3 { Ok "Conformance passed."
      Ok "A declared kernel footprint does not hold on this machine's FFmpeg."
      Ok "That is a result, not a failure of your run, and it is the one we most"
      Ok "want to see. Please send the bundle." }
  default { Bad "The container exited $rc, which is neither expected outcome."
            Bad "That is a defect. Please send everything, including this window." }
}

Head "Bundling what to send back"
$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
@"
run finished (UTC) : $((Get-Date).ToUniversalTime().ToString("o"))
exit code          : $rc
minutes            : $mins
OS                 : $([System.Environment]::OSVersion.VersionString)
CPU                : $env:PROCESSOR_IDENTIFIER
logical processors : $env:NUMBER_OF_PROCESSORS
docker             : $(& docker --version)
"@ | Set-Content (Join-Path $out "HOST.txt")

@"
Reproducer statement (optional; the run does not need any of this)

name          :
institution   :
date          :
did you modify any file in this package?      yes / no
did anyone guide you while running it?        yes / no
was any failing check bypassed by hand?       yes / no
comments      :
"@ | Set-Content (Join-Path $out "REPRODUCER_STATEMENT.txt")

$zip = Join-Path $root "SEND_THIS_BACK.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path (Join-Path $out "*") -DestinationPath $zip
Ok "send this one file back: $zip"

Head "Done"
Note "exit code $rc after $mins minutes"
Note "Send the ZIP whatever the exit code was. A run that is reported is worth"
Note "more than a run that was made to pass: the previous reproduction exited"
Note "non-zero and found two real defects that are now published as results."
exit $rc
