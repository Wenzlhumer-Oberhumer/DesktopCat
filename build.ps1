# Build-Skript fuer Mochi: erzeugt portable Distribution und Setup-Installer
param(
    [switch]$Sign = $false,
    [switch]$SkipInstaller = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "=== Mochi Build gestartet ===" -ForegroundColor Cyan

# 1. Version aus version.py auslesen
$versionPy = Get-Content "$ScriptDir\version.py" -Raw
if ($versionPy -match '__version__\s*=\s*["'']([^"'']+)["'']') {
    $Version = $Matches[1]
} else {
    throw "Konnte __version__ in version.py nicht finden!"
}
Write-Host "Baue Mochi Version: $Version" -ForegroundColor Green

# 2. Python-Abhaengigkeiten pruefen/installieren
Write-Host "Installiere/aktualisiere Python-Pakete..." -ForegroundColor Yellow
python -m pip install -r "$ScriptDir\requirements.txt" pyinstaller

# 3. Node.js Portable vorbereiten
$NODE_VERSION = "22.23.3"
$NODE_ZIP_NAME = "node-v$NODE_VERSION-win-x64.zip"
$NODE_URL = "https://nodejs.org/dist/v$NODE_VERSION/$NODE_ZIP_NAME"
$NODE_EXPECTED_SHA = "2b0ff57b049cda1bbcea2240eec20467018713c1efe1f7360c2681859b90ed71"
$vendorDir = "$ScriptDir\vendor"
$nodeVendorDir = "$vendorDir\node"
$nodeExe = "$nodeVendorDir\node.exe"

if (-not (Test-Path $nodeExe)) {
    Write-Host "Lade portable Node.js v$NODE_VERSION herunter..." -ForegroundColor Yellow
    $tempZip = "$env:TEMP\$NODE_ZIP_NAME"
    if (-not (Test-Path $tempZip)) {
        Invoke-WebRequest -Uri $NODE_URL -OutFile $tempZip
    }

    $actualHash = (Get-FileHash -Path $tempZip -Algorithm SHA256).Hash.ToLower()
    if ($actualHash -ne $NODE_EXPECTED_SHA.ToLower()) {
        Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
        throw "SHA256-Pruefung fuer Node.js fehlgeschlagen! Erwartet: $NODE_EXPECTED_SHA, Erhalten: $actualHash"
    }
    Write-Host "Node.js SHA256-Pruefung erfolgreich." -ForegroundColor Green

    Write-Host "Entpacke Node.js..." -ForegroundColor Yellow
    $tempExtract = "$env:TEMP\node_extract_$NODE_VERSION"
    if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
    Expand-Archive -Path $tempZip -DestinationPath $tempExtract

    if (Test-Path $nodeVendorDir) { Remove-Item $nodeVendorDir -Recurse -Force }
    New-Item -ItemType Directory -Path $nodeVendorDir -Force | Out-Null

    $extractedRoot = Join-Path $tempExtract "node-v$NODE_VERSION-win-x64"
    Copy-Item -Path "$extractedRoot\*" -Destination $nodeVendorDir -Recurse -Force
    Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Node.js bereitgestellt unter $nodeVendorDir." -ForegroundColor Green
} else {
    Write-Host "Node.js bereits vorhanden unter $nodeVendorDir." -ForegroundColor Green
}

# 4. Gemini CLI installieren & Smoke-Test
$GEMINI_CLI_VERSION = "0.63.0"
$geminiVendorDir = "$vendorDir\gemini-cli"
$geminiEntry = "$geminiVendorDir\node_modules\@google\gemini-cli\bundle\gemini.js"

if (-not (Test-Path $geminiEntry)) {
    Write-Host "Installiere @google/gemini-cli@$GEMINI_CLI_VERSION in $geminiVendorDir..." -ForegroundColor Yellow
    if (-not (Test-Path $geminiVendorDir)) {
        New-Item -ItemType Directory -Path $geminiVendorDir -Force | Out-Null
    }
    $npmCmd = "$nodeVendorDir\npm.cmd"
    & $npmCmd install --prefix $geminiVendorDir "@google/gemini-cli@$GEMINI_CLI_VERSION" --omit=dev
}

# Smoke-Test Gemini CLI
Write-Host "Fuehre Smoke-Test fuer gebuendelte Gemini CLI durch..." -ForegroundColor Yellow
$cliVersionOut = & "$nodeExe" "$geminiEntry" --version
if ($LASTEXITCODE -ne 0 -or -not $cliVersionOut) {
    throw "Smoke-Test fuer Gemini CLI fehlgeschlagen!"
}
Write-Host "Gemini CLI bereit: $cliVersionOut" -ForegroundColor Green

# 5. Multi-Size-Icon erzeugen
Write-Host "Erzeuge Multi-Size-Icon..." -ForegroundColor Yellow
python "$ScriptDir\tools_dev\make_icon.py"

# 6. PyInstaller-Build
Write-Host "Fuehre PyInstaller aus (onedir)..." -ForegroundColor Yellow
python -m PyInstaller "$ScriptDir\mochi.spec" --noconfirm --clean

$distApp = "$ScriptDir\dist\Mochi\Mochi.exe"
if (-not (Test-Path $distApp)) {
    throw "PyInstaller-Build fehlgeschlagen: $distApp wurde nicht erzeugt!"
}
Write-Host "PyInstaller-Build erfolgreich abgeschlossen: $distApp" -ForegroundColor Green

# 7. Inno Setup Compiler ausfuehren
if (-not $SkipInstaller) {
    $isccPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    $iscc = $null
    foreach ($p in $isccPaths) {
        if (Test-Path $p) { $iscc = $p; break }
    }
    if (-not $iscc) {
        $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($cmd) { $iscc = $cmd.Source }
    }

    if (-not $iscc) {
        Write-Warning "Inno Setup 6 (ISCC.exe) wurde nicht gefunden!"
        Write-Warning "Bitte Inno Setup von https://jrsoftware.org/isdl.php installieren."
        Write-Warning "Der onedir-Build unter dist\Mochi\ ist dennoch fertiggestellt."
    } else {
        Write-Host "Erstelle Installer mit Inno Setup ($iscc)..." -ForegroundColor Yellow
        & $iscc "/DAppVersion=$Version" "$ScriptDir\installer\mochi.iss"

        $setupExe = "$ScriptDir\dist\Mochi-Setup-$Version.exe"
        if (-not (Test-Path $setupExe)) {
            throw "Inno Setup Build fehlgeschlagen: $setupExe wurde nicht gefunden!"
        }
        Write-Host "Installer erfolgreich erstellt: $setupExe" -ForegroundColor Green

        # 8. SHA256-Pruefsumme fuer Auto-Update schreiben
        $setupHash = (Get-FileHash -Path $setupExe -Algorithm SHA256).Hash.ToLower()
        $shaFile = "$ScriptDir\dist\Mochi-Setup-$Version.exe.sha256"
        "$setupHash  Mochi-Setup-$Version.exe" | Set-Content -Path $shaFile -Encoding UTF8
        Write-Host "SHA256 fuer Setup geschrieben: $shaFile ($setupHash)" -ForegroundColor Green

        # 9. Optionales Code-Signing
        if ($Sign) {
            $signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
            if ($signtool) {
                Write-Host "Signiere Mochi.exe und Installer..." -ForegroundColor Yellow
                & signtool.exe sign /a /fd SHA256 "$distApp"
                & signtool.exe sign /a /fd SHA256 "$setupExe"
            } else {
                Write-Warning "-Sign angegeben, aber signtool.exe wurde im PATH nicht gefunden."
            }
        }
    }
}

Write-Host "=== Mochi Build erfolgreich abgeschlossen! ===" -ForegroundColor Cyan
