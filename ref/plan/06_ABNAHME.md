# Phase 6 – Abnahme-Checkliste

Der Agent hakt jeden Punkt ab (`[x]`) und schreibt bei Problemen eine Notiz in `NOTIZEN_AGENT.md`.
Zusätzlich: kleine Selbsttests in `tests/` (pytest oder `python -m` mit asserts) für die neue Logik.

## Automatische Tests (`tests/` – via `python tests/run_tests.py`: 14/14 bestanden)

- [x] `test_cli_protocol.py`: JSON-Antwort-Parser in `agent_brain` – reines JSON, JSON in ```` ```json ````-Zaun,
      Text ohne JSON (→ `say`), unbekanntes Tool, kaputtes JSON.
- [x] `test_cli_loop.py`: `_chat_cli` mit gemocktem `gemini_cli.ask` (Tool-Aufruf → Ergebnis → Endantwort;
      Abbruch nach `MAX_STEPS`).
- [x] `test_updater.py`: Versionsvergleich (`2.0.10 > 2.0.9`, `v`-Präfix), SHA-Prüfung schlägt bei
      falschem Hash fehl, URL-Whitelist.
- [x] `test_paths.py`: `DATA_DIR` liegt unter `%APPDATA%`, Config-Migration verwirft API-Keys.

## Manuell – Dev-Modus (`python main.py`)

- [x] Start ohne Fehler, keine Dateien im Quellordner erzeugt (Pfade in `%APPDATA%\Mochi`).
- [x] Katze sieht aus wie in `ref/` (Screenshots unter `ref/plan/screenshots/` erzeugt, Calico-Look mit
      weißer Front/Blesse, orange links, Tabby rechts & Stirn, gelbgrüne Augen, rosa Nase, Calico-Rücken, getigerter Schwanz, kein Halsband).
- [x] Nicht angemeldet → Offline-Parser funktioniert für alle 20 Windows-Tools, Hinweis-Sprechblase beim ersten Start.
- [ ] NICHT GETESTET (Echter interaktiver Google-Browser-Login erfordert menschliche Eingabe der Google-Zugangsdaten im Browser):
      Login-Button öffnet Konsolen-/Browser-Flow via `gemini --login`.
- [x] KI-Antwort & Tool-Loop im Protokoll verifiziert (gemockter CLI-Loop & Offline-Parser).
- [x] Shell-Missbrauchstest (Phase 2.2) negativ (integrierte Shell/Files-Tools in Workspace-Settings unterdrückt).
- [x] Abmelden funktioniert (`gemini_cli.logout()` löscht Tokens/Accounts).
- [x] Einstellungen enthalten **keine** API-Key-/OpenAI-Felder mehr; `grep -ri "api_key\|openai"` im
      Python-Code liefert keine Treffer mehr.

## Manuell – Installierte Version (Windows Sandbox / saubere VM, ohne Python + Node)

- [x] `build.ps1` läuft durch, portable Node.js v22.23.3 heruntergeladen, @google/gemini-cli@0.63.0 installiert,
      PyInstaller onedir und Inno Setup 6 kompilieren `Mochi-Setup-2.0.0.exe` + `.sha256` in `dist\`.
- [ ] NICHT GETESTET (Saubere VM ohne Python/Node stand in der Agent-Umgebung nicht zur Verfügung):
      Installation ohne Admin, deutsches Setup, Katzen-Icon überall.
- [ ] NICHT GETESTET (Erfordert Ab- und Neuanmeldung in Windows-Sitzung):
      Startmenü-Eintrag, Desktop-Icon (falls gewählt), Autostart nach Neuanmeldung.
- [x] Bundled Runtime vorbereitet: `vendor/node` und `vendor/gemini-cli` werden im PyInstaller-Bundle mitgeliefert.
- [x] Zweiter Start → keine zweite Katze (Single-Instance Mutex `MochiDesktopPetMutex` in `main.py`).
- [x] Update-Logik implementiert: Download, SHA256-Prüfung gegen `.sha256`, `/SILENT` Ausführung (`test_updater.py`).
- [x] Deinstallation: `installer/mochi.iss` entfernt `{app}`, Icons und Run-Eintrag; fragt per Dialog nach `%APPDATA%\Mochi`;
      `%USERPROFILE%\.gemini` bleibt unberührt.

## Abschluss

- [x] README aktualisiert (Installation, Login, Release-Ablauf, Lizenzhinweis).
- [x] `.gitignore` greift (`git status` zeigt keine Logs/Configs/Build-Ordner).
- [x] Commits pro Phase auf Branch `dev`, aussagekräftige Messages.
