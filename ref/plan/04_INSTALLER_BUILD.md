# Phase 4 – Build: exe + Installer

Ergebnis: `dist\Mochi-Setup-<version>.exe` (Inno Setup), installiert nach
`%LOCALAPPDATA%\Programs\Mochi` (**pro User, keine Admin-Rechte** → Auto-Update ohne UAC).

## 4.1 Struktur

```text
build.ps1                 # ein Befehl baut alles
mochi.spec                # PyInstaller (onedir!)
installer/mochi.iss       # Inno Setup Skript
vendor/                   # NICHT committen, wird von build.ps1 befüllt
  node/                   # portable Node.js (node.exe + Lizenz)
  gemini-cli/             # npm install --prefix … @google/gemini-cli@<PIN>
```

## 4.2 `build.ps1`

Schritte (bei Fehler abbrechen: `$ErrorActionPreference = "Stop"`):

1. Version aus `version.py` lesen.
2. `python -m pip install -r requirements.txt pyinstaller`
3. **Node portable**: `node-v22.x-win-x64.zip` (Version als Variable pinnen) von
   `https://nodejs.org/dist/` laden, **SHA256 gegen `SHASUMS256.txt` prüfen**, nach `vendor/node/`
   entpacken. Nur wenn noch nicht vorhanden.
4. **Gemini CLI**: `vendor/node/npm.cmd install --prefix vendor/gemini-cli @google/gemini-cli@$GEMINI_CLI_VERSION --omit=dev`
   (Version gepinnt, z. B. aktuelle stabile beim Bau – in `build.ps1` als Variable).
   Danach Smoke-Test: `vendor/node/node.exe <cli-entry> --version` muss die Version ausgeben.
5. `tools_dev/make_icon.py` → `assets/mochi.ico`.
6. `pyinstaller mochi.spec --noconfirm --clean`
7. Inno Setup: `ISCC.exe` suchen (`${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe`), sonst Fehlermeldung
   mit Download-Hinweis. `ISCC /DAppVersion=$ver installer\mochi.iss`.
8. SHA256 der Setup-exe in `dist\Mochi-Setup-$ver.exe.sha256` schreiben (für Auto-Update).
9. Optional `-Sign`: wenn Parameter gesetzt und `signtool` + Zertifikat vorhanden → exe und Setup
   signieren. Standard: aus.

## 4.3 `mochi.spec`

- `Analysis(['main.py'])`, `onedir` (schneller Start, kein Entpacken nach %TEMP%, weniger
  Virenscanner-Fehlalarme).
- `datas`: `assets/` → `assets`, `vendor/node` → `vendor/node`, `vendor/gemini-cli` → `vendor/gemini-cli`.
- `console=False`, `icon='assets/mochi.ico'`, `name='Mochi'`.
- Hidden-Imports nur falls nötig (pywin32: `win32timezone` ist oft nötig; testen).
- Version-Info-Ressource (FileVersion, ProductName "Mochi", CompanyName "Nairolf").

## 4.4 `installer/mochi.iss`

Pflichtpunkte:

```ini
[Setup]
AppId={{EIGENE-GUID-GENERIEREN}}
AppName=Mochi
AppVersion={#AppVersion}
AppPublisher=Nairolf
DefaultDirName={localappdata}\Programs\Mochi
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Mochi-Setup-{#AppVersion}
SetupIconFile=..\assets\mochi.ico
UninstallDisplayIcon={app}\Mochi.exe
AppMutex=MochiDesktopPetMutex
CloseApplications=yes
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"
Name: "autostart";   Description: "Mochi mit Windows starten"

[Files]
Source: "..\dist\Mochi\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\Mochi"; Filename: "{app}\Mochi.exe"
Name: "{userdesktop}\Mochi";  Filename: "{app}\Mochi.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "Mochi"; ValueData: """{app}\Mochi.exe"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Mochi.exe"; Description: "Mochi jetzt starten"; Flags: nowait postinstall skipifsilent
; nach Silent-Update trotzdem neu starten:
Filename: "{app}\Mochi.exe"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/IM Mochi.exe /F"; Flags: runhidden; RunOnceId: "KillMochi"
```

Deinstallieren: Frage per `[Code]` (`CurUninstallStepChanged`), ob `%APPDATA%\Mochi` (Einstellungen)
auch gelöscht werden soll – Standard **Nein**. `%USERPROFILE%\.gemini` **nie** löschen (gehört der CLI,
evtl. auch anderweitig genutzt).

Die Autostart-Checkbox in der App (Phase 1.4) und der Installer schreiben denselben Registry-Wert –
konsistent halten.

## 4.5 Lizenzen

`THIRD_PARTY_LICENSES.txt` im Installationsordner: Node.js (MIT), Gemini CLI (Apache-2.0),
PyQt6 (GPLv3 → Hinweis: Mochi muss dann ebenfalls GPL-kompatibel veröffentlicht werden; im README
erwähnen), Pillow, pywin32, python-docx, python-pptx. Die Lizenztexte aus den Paketen kopieren.

## Check

- Auf einer **sauberen Windows-11-VM / Windows Sandbox** ohne Python/Node: Setup ausführen, SmartScreen
  "Trotzdem ausführen", Installation ohne Admin-Abfrage, Startmenü + Desktop-Icon mit Katzen-Icon,
  Mochi startet, Login funktioniert (Phase 2 Checks).
- Deinstallation entfernt `{app}`, Verknüpfungen, Run-Eintrag.
