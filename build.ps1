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

# 3. Multi-Size-Icon erzeugen
Write-Host "Erzeuge Multi-Size-Icon..." -ForegroundColor Yellow
python "$ScriptDir\tools_dev\make_icon.py"

# 4. PyInstaller-Build
Write-Host "Fuehre PyInstaller aus (onedir)..." -ForegroundColor Yellow
python -m PyInstaller "$ScriptDir\mochi.spec" --noconfirm --clean

$distApp = "$ScriptDir\dist\Mochi\Mochi.exe"
if (-not (Test-Path $distApp)) {
    throw "PyInstaller-Build fehlgeschlagen: $distApp wurde nicht erzeugt!"
}
Write-Host "PyInstaller-Build erfolgreich abgeschlossen: $distApp" -ForegroundColor Green

# 5. Inno Setup Compiler ausfuehren
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
