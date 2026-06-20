#Requires -Version 5.1
<#
.SYNOPSIS
    Einmaliges Setup für PrintAssist auf einem neuen Gerät.
    Ausführen mit: powershell -ExecutionPolicy Bypass -File setup.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Write-OK([string]$msg) {
    Write-Host "    OK: $msg" -ForegroundColor Green
}

function Write-Skip([string]$msg) {
    Write-Host "    Übersprungen: $msg bereits installiert." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 1. SumatraPDF
# ---------------------------------------------------------------------------
Write-Step "SumatraPDF prüfen / installieren"

$sumatraPaths = @(
    "$env:LOCALAPPDATA\SumatraPDF\SumatraPDF.exe",
    "C:\Program Files\SumatraPDF\SumatraPDF.exe",
    "C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe"
)
$sumatraFound = $sumatraPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($sumatraFound) {
    Write-Skip "SumatraPDF ($sumatraFound)"
} else {
    winget install SumatraPDF.SumatraPDF --silent --accept-package-agreements --accept-source-agreements
    Write-OK "SumatraPDF installiert"
}

# ---------------------------------------------------------------------------
# 2. LibreOffice
# ---------------------------------------------------------------------------
Write-Step "LibreOffice prüfen / installieren"

$librePaths = @(
    "C:\Program Files\LibreOffice\program\soffice.exe",
    "C:\Program Files (x86)\LibreOffice\program\soffice.exe"
)
$libreFound = $librePaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($libreFound) {
    Write-Skip "LibreOffice ($libreFound)"
} else {
    winget install TheDocumentFoundation.LibreOffice --silent --accept-package-agreements --accept-source-agreements
    Write-OK "LibreOffice installiert"
}

# ---------------------------------------------------------------------------
# 3. Python-Pakete
# ---------------------------------------------------------------------------
Write-Step "Python-Pakete installieren (pip)"

$requirementsFile = Join-Path $scriptDir "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Error "requirements.txt nicht gefunden: $requirementsFile"
    exit 1
}

pip install -r $requirementsFile
Write-OK "Python-Pakete installiert"

# ---------------------------------------------------------------------------
# 4. Hostname in printers.yaml eintragen (falls noch Platzhalter)
# ---------------------------------------------------------------------------
Write-Step "Drucker-Konfiguration prüfen"

$printerConfig = Join-Path $scriptDir "config\printers.yaml"
$hostname = $env:COMPUTERNAME
$content = Get-Content $printerConfig -Raw

if ($content -match '<HOSTNAME') {
    Write-Host "    Hostname dieses Geräts: $hostname" -ForegroundColor White
    Write-Host "    Drucker auf diesem Gerät:" -ForegroundColor White
    try {
        Get-Printer | Select-Object -ExpandProperty Name | ForEach-Object { Write-Host "      - $_" }
    } catch {
        wmic printer get name 2>$null
    }
    Write-Host ""
    Write-Host "    ACHTUNG: Trage Hostname und Druckernamen manuell in config\printers.yaml ein," -ForegroundColor Red
    Write-Host "    falls dieses Gerät einen anderen Drucker verwendet." -ForegroundColor Red
} else {
    Write-OK "printers.yaml enthält keine Platzhalter mehr"
}

# ---------------------------------------------------------------------------
# 5. Adobe MCP-Hinweis
# ---------------------------------------------------------------------------
Write-Step "Adobe MCP-Connector"
Write-Host "    Öffne Claude Code und führe einmalig aus: /mcp" -ForegroundColor White
Write-Host "    Dann 'adobe-creativity' auswählen und einloggen." -ForegroundColor White

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Setup abgeschlossen!" -ForegroundColor Green
Write-Host "  Teste mit:" -ForegroundColor Green
Write-Host "    python scripts\print.py <datei.pdf>" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
