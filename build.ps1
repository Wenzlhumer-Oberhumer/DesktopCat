# Build-Skript fuer Mochi: erzeugt portable Distribution und Setup-Installer
param(
    [switch]$Sign = $false,
    [switch]$SkipInstaller = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "=== Desktop Cat Build gestartet ===" -ForegroundColor Cyan

# 1. Version aus version.py auslesen
$versionPy = Get-Content "$ScriptDir\version.py" -Raw
if ($versionPy -match '__version__\s*=\s*["'']([^"'']+)["'']') {
    $Version = $Matches[1]
} else {
    throw "Konnte __version__ in version.py nicht finden!"
}
Write-Host "Baue Desktop Cat Version: $Version" -ForegroundColor Green

# exe-Versionsinfo (Eigenschaften > Details) an version.py angleichen
$v = ($Version.Split('.') + @('0','0','0'))[0..2]
$vi = Get-Content "$ScriptDir\version_info.txt" -Raw
$vi = $vi -replace '(filevers|prodvers)=\(\d+, \d+, \d+, \d+\)', "`$1=($($v[0]), $($v[1]), $($v[2]), 0)"
$vi = $vi -replace "(FileVersion|ProductVersion)', '[\d.]+'", "`$1', '$($v -join '.').0'"
[IO.File]::WriteAllText("$ScriptDir\version_info.txt", $vi, (New-Object Text.UTF8Encoding $false))

# 2. Eigenes Build-venv: sonst packt PyInstaller alles aus dem globalen Python mit (torch, cv2, ...)
$venvDir = "$ScriptDir\.venv-build"
$py = "$venvDir\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Erzeuge Build-venv..." -ForegroundColor Yellow
    python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "venv konnte nicht erstellt werden!" }
}
Write-Host "Installiere/aktualisiere Python-Pakete im Build-venv..." -ForegroundColor Yellow
& $py -m pip install --disable-pip-version-check -q -r "$ScriptDir\requirements.txt" pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install fehlgeschlagen!" }

# 3. Multi-Size-Icon erzeugen
Write-Host "Erzeuge Multi-Size-Icon..." -ForegroundColor Yellow
& $py "$ScriptDir\tools_dev\make_icon.py"

# 4. PyInstaller-Build
Write-Host "Fuehre PyInstaller aus (onedir)..." -ForegroundColor Yellow
& $py -m PyInstaller "$ScriptDir\mochi.spec" --noconfirm --clean

$distApp = "$ScriptDir\dist\DesktopCat\DesktopCat.exe"
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
        Write-Warning "Der onedir-Build unter dist\DesktopCat\ ist dennoch fertiggestellt."
    } else {
        Write-Host "Erstelle Installer mit Inno Setup ($iscc)..." -ForegroundColor Yellow
        & $iscc "/DAppVersion=$Version" "$ScriptDir\installer\mochi.iss"

        $setupExe = "$ScriptDir\dist\DesktopCat-Setup-$Version.exe"
        if (-not (Test-Path $setupExe)) {
            throw "Inno Setup Build fehlgeschlagen: $setupExe wurde nicht gefunden!"
        }
        Write-Host "Installer erfolgreich erstellt: $setupExe" -ForegroundColor Green

        # 8. SHA256-Pruefsumme fuer Auto-Update schreiben
        $setupHash = (Get-FileHash -Path $setupExe -Algorithm SHA256).Hash.ToLower()
        $shaFile = "$ScriptDir\dist\DesktopCat-Setup-$Version.exe.sha256"
        # ohne BOM: aeltere Desktop-Cat-Versionen (<= 2.2.1) koennen eine BOM nicht lesen
        [IO.File]::WriteAllText($shaFile, "$setupHash  DesktopCat-Setup-$Version.exe`n", (New-Object Text.UTF8Encoding $false))
        Write-Host "SHA256 fuer Setup geschrieben: $shaFile ($setupHash)" -ForegroundColor Green

        # 8b. Portable Zip erzeugen
        $zipFile = "$ScriptDir\dist\DesktopCat-Windows-Portable.zip"
        if (Test-Path $zipFile) { Remove-Item -Force $zipFile }
        Write-Host "Erstelle Portable Zip: $zipFile..." -ForegroundColor Yellow
        Compress-Archive -Path "$ScriptDir\dist\DesktopCat\*" -DestinationPath $zipFile
        Write-Host "Portable Zip erfolgreich erstellt: $zipFile" -ForegroundColor Green

        # 9. Optionales Code-Signing
        if ($Sign) {
            $signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
            if ($signtool) {
                Write-Host "Signiere DesktopCat.exe und Installer..." -ForegroundColor Yellow
                & signtool.exe sign /a /fd SHA256 "$distApp"
                & signtool.exe sign /a /fd SHA256 "$setupExe"
            } else {
                Write-Warning "-Sign angegeben, aber signtool.exe wurde im PATH nicht gefunden."
            }
        }
    }
}

Write-Host "=== Desktop Cat Build erfolgreich abgeschlossen! ===" -ForegroundColor Cyan
