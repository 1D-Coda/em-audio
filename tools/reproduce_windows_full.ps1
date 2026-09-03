# Everything a Windows machine needs, from nothing to a results archive.
# Driven by Reproducir_en_Windows.cmd, which is the double-clickable entry.
#
# Nothing is installed without asking. A reproduction package that silently
# changes someone's machine is not one a reviewer should trust, and the person
# running it is entitled to see what it does; that is also why this is a script
# and not a signed executable.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol =
  [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

function Say  ($m) { Write-Host "`n== $m" -ForegroundColor Cyan }
function Ok   ($m) { Write-Host $m -ForegroundColor Green }
function Bad  ($m) { Write-Host $m -ForegroundColor Red }
function Halt ($m) { Bad $m; Read-Host "`nEnter para cerrar" | Out-Null; exit 2 }

# Locate the package: this file ships at the top, next to em-audio\.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($c in @($here, (Join-Path $here "em-audio"), (Split-Path -Parent $here))) {
  if (Test-Path (Join-Path $c "run_all.sh")) { $root = $c; break }
}
if (-not $root) { Halt "No encuentro run_all.sh junto a este archivo." }
Set-Location $root

Say "EM-Audio: reproduccion independiente"
Write-Host "Carpeta: $root"

# espeak-ng truncates its output path past about 200 characters and reports
# success, and the run then dies somewhere unrelated. Windows also still
# defaults to MAX_PATH 260. Refuse early rather than let either happen.
if ($root.Length -gt 120) {
  Bad "La ruta es larga ($($root.Length) caracteres)."
  Halt "Mueve esta carpeta a C:\em-audio y vuelve a hacer doble clic."
}

$haveWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)

function Need($exe) { return -not (Get-Command $exe -ErrorAction SilentlyContinue) }

Say "1/7  Que falta"
$wants = @()
if (Need "git")       { $wants += @{ n="Git (trae bash, que run_all.sh necesita)"; id="Git.Git" } }
if (Need "ffmpeg")    { $wants += @{ n="FFmpeg";    id="Gyan.FFmpeg" } }
if (Need "node")      { $wants += @{ n="Node.js";   id="OpenJS.NodeJS" } }
if (Need "espeak-ng") { $wants += @{ n="eSpeak NG"; id="eSpeak-NG.eSpeak-NG" } }
$needPython   = (Need "python") -and (Need "py")
$needC2patool = Need "c2patool"
if ($needPython) { $wants += @{ n="Python 3.12"; id="Python.Python.3.12" } }

if ($wants.Count -eq 0 -and -not $needC2patool) {
  Ok "  todo presente"
} else {
  foreach ($w in $wants)  { Write-Host "  falta   $($w.n)" }
  if ($needC2patool)      { Write-Host "  falta   c2patool (se baja de GitHub, sin instalador)" }
  Write-Host ""
  if ($wants.Count -gt 0 -and -not $haveWinget) {
    Bad "Falta winget, que es como Windows instala estos programas."
    Halt "Actualiza 'Instalador de aplicaciones' desde Microsoft Store, o instalalos a mano."
  }
  $yn = Read-Host "Instalar lo que falta ahora? [s/N]"
  if ($yn -notmatch '^[sSyY]$') { Halt "De acuerdo. Instalalo y vuelve a hacer doble clic." }

  foreach ($w in $wants) {
    Say "Instalando $($w.n)"
    winget install --id $($w.id) -e --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) { Bad "  winget salio $LASTEXITCODE para $($w.id); sigo." }
  }
  if ($needC2patool) {
    Say "Instalando c2patool"
    $v   = "0.27.15"
    $url = "https://github.com/contentauth/c2pa-rs/releases/download/c2patool-v$v/c2patool-v$v-x86_64-pc-windows-msvc.zip"
    $zip = Join-Path $env:TEMP "c2patool.zip"
    $dst = "C:\c2patool"
    Invoke-WebRequest $url -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $dst -Force
    $exe = Get-ChildItem $dst -Recurse -Filter c2patool.exe | Select-Object -First 1
    if (-not $exe) { Halt "El archivo de c2patool no traia c2patool.exe." }
    $dir = $exe.Directory.FullName
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($user -notlike "*$dir*") {
      [Environment]::SetEnvironmentVariable("Path", "$user;$dir", "User")
    }
    $env:Path = "$env:Path;$dir"
    Ok "  c2patool en $dir"
  }
  # winget updates the machine PATH; this session does not see it yet.
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}

Say "2/7  bash"
$bash = Get-Command bash -ErrorAction SilentlyContinue
if (-not $bash) {
  foreach ($p in @("$env:ProgramFiles\Git\bin\bash.exe",
                   "${env:ProgramFiles(x86)}\Git\bin\bash.exe")) {
    if (Test-Path $p) { $bash = Get-Item $p; break }
  }
}
if (-not $bash) { Halt "No encuentro bash. Cierra esta ventana, abrela de nuevo y reintenta; si sigue, instala Git for Windows." }
# Not ??, which is PowerShell 7 syntax; Windows ships 5.1.
$bashExe = if ($bash.PSObject.Properties.Name -contains "Source" -and $bash.Source) { $bash.Source } else { $bash.FullName }
Ok "  $bashExe"

Say "3/7  Interprete de Python"
# Resolved by running each candidate. On Windows the name python3 is usually an
# App Execution Alias: on PATH, and not an interpreter. An earlier validator's
# entire run produced nothing because every step invoked it.
$py = $null
foreach ($c in @("python", "python3", "py")) {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
  $v = & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
  if ($LASTEXITCODE -eq 0 -and $v -match '^3\.(1[1-9]|[2-9][0-9])$') { $py = $c; break }
}
if (-not $py) { Halt "No hay un Python 3.11+ utilizable. Cierra la ventana, abrela otra vez y reintenta." }
Ok "  $py"

Say "4/7  Dependencias de Python"
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) { & $py -m venv $venv }
$vpy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $vpy)) { Halt "No se pudo crear el entorno virtual en .venv" }
& $vpy -m pip install --quiet --upgrade pip
& $vpy -m pip install --quiet -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Halt "pip fallo." }
$env:PY = $vpy
Ok "  listas"

Say "5/7  Revision previa (no corre experimentos)"
& $vpy (Join-Path $root "tools\repro_selftest.py")
if ($LASTEXITCODE -ne 0) { Halt "La revision previa encontro problemas. Resuelvelos y vuelve a hacer doble clic." }

Say "6/7  Corrida completa (unos 25 minutos, mas 322 MB la primera vez)"
Write-Host "No cierres esta ventana."
& $bashExe -lc "cd '$($root -replace '\\','/')' && ./run_all.sh" 2>&1 |
  Tee-Object -FilePath (Join-Path $root "run_all_output.txt")
$runRc = $LASTEXITCODE
if ($runRc -eq 0) { Ok "  run_all.sh termino en RUN OK" }
else { Bad "  run_all.sh salio $runRc. Eso es un resultado: mandanoslo igual." }

& $vpy (Join-Path $root "tools\verify_reproduction.py") 2>&1 |
  Tee-Object -FilePath (Join-Path $root "verify_output.txt")
$verRc = $LASTEXITCODE
Write-Host "`n  verify_reproduction.py salio $verRc"
Write-Host "  Un valor distinto de cero NO es un fallo tuyo: significa que una salida"
Write-Host "  difiere, que es justo lo que queremos saber."

Say "7/7  Empaquetando lo que hay que mandar"
$label = ($env:COMPUTERNAME -replace '[^A-Za-z0-9_-]','_')
$arch  = $env:PROCESSOR_ARCHITECTURE
$stamp = Get-Date -Format "yyyy-MM-dd"
$outDir = Join-Path $here "resultados_${label}_${arch}_$stamp"
if (Test-Path $outDir) { Remove-Item $outDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item (Join-Path $root "results\machine_readable") $outDir -Recurse -ErrorAction SilentlyContinue
foreach ($f in @("results\PREFLIGHT.txt","run_all_output.txt","verify_output.txt")) {
  $p = Join-Path $root $f
  if (Test-Path $p) { Copy-Item $p $outDir }
}
@"
maquina     : $label
arquitectura: $arch
windows     : $([Environment]::OSVersion.VersionString)
run_all     : $runRc
verify      : $verRc
fecha       : $((Get-Date).ToUniversalTime().ToString("s"))Z
"@ | Set-Content (Join-Path $outDir "CORRIDA.txt")
$zip = "$outDir.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $outDir -DestinationPath $zip
Remove-Item $outDir -Recurse -Force
Ok "Listo: $zip"
Write-Host "`nManda ese archivo."
Read-Host "`nEnter para cerrar" | Out-Null
