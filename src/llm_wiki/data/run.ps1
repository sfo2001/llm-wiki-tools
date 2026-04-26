# run.ps1 — lwt wrapper for this wiki. Bootstraps a per-wiki venv from tools\*.whl.
# Usage: .\run.ps1 <command> [args]
param(
    [string]$Command = "help",
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Venv = Join-Path $ScriptDir "venv"
$WheelDir = Join-Path $ScriptDir "tools"
$Marker = Join-Path $Venv ".installed-wheel"

# Locate newest wheel
$Wheel = Get-ChildItem -Path $WheelDir -Filter "llm_wiki_tools-*.whl" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $Wheel) {
    Write-Error "No wheel found in $WheelDir\. Drop a llm_wiki_tools-*.whl there and re-run."
    exit 1
}

# Bootstrap venv
if (-not (Test-Path $Venv)) {
    Write-Host "→ Creating venv at $Venv"
    python -m venv $Venv
    & "$Venv\Scripts\pip.exe" install --quiet --upgrade pip
}

# Install wheel if changed
$Installed = if (Test-Path $Marker) { Get-Content $Marker } else { "" }
if ($Installed -ne $Wheel.Name) {
    Write-Host "→ Installing $($Wheel.Name)"
    & "$Venv\Scripts\pip.exe" install --quiet --force-reinstall "$($Wheel.FullName)[mkdocs]"
    $Wheel.Name | Out-File -FilePath $Marker -Encoding ASCII
}

$Lwt = "$Venv\Scripts\lwt.exe"
$WikiDir = Join-Path $ScriptDir "wiki"

switch ($Command) {
    "ingest"    { & $Lwt ingest @Rest --wiki-dir $WikiDir }
    "serve"     { & $Lwt deploy --target mkdocs --wiki-dir $WikiDir @Rest }
    "build"     { & $Lwt deploy --target mkdocs --build --wiki-dir $WikiDir @Rest }
    "lint"      { & $Lwt lint --wiki-dir $WikiDir @Rest }
    "search"    { & $Lwt search @Rest --wiki-dir $WikiDir }
    "log-entry" { & $Lwt log-entry @Rest --wiki-dir $WikiDir }
    "update"    { & $Lwt update $ScriptDir @Rest }
    {"help","--help","-h" -contains $_} {
        Write-Host "Usage: .\run.ps1 <command> [args]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  ingest <file-or-url>      Convert source -> wiki\.tmp\ then open claude"
        Write-Host "  serve                     Serve wiki at http://localhost:8000"
        Write-Host "  build                     Build static site -> .build\site\"
        Write-Host "  lint                      Run lint checks"
        Write-Host "  search <query>            BM25 keyword search over wiki pages"
        Write-Host "  log-entry --op X --title Y  Atomically append to wiki\log.md"
        Write-Host "  update [--apply] [--force]  Refresh bundled assets"
        Write-Host "  update --tools <wheel>      Swap in a new lwt version"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\run.ps1 ingest raw\paper.pdf"
        Write-Host "  .\run.ps1 serve"
        Write-Host "  .\run.ps1 update --apply"
    }
    Default { & $Lwt $Command @Rest }
}
exit $LASTEXITCODE
