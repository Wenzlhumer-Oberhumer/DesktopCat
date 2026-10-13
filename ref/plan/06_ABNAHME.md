# Phase 6 – Abnahme-Checkliste

Der Agent hakt jeden Punkt ab (`[x]`) und schreibt bei Problemen eine Notiz in `NOTIZEN_AGENT.md`.
Zusätzlich: kleine Selbsttests in `tests/` (pytest oder `python -m` mit asserts) für die neue Logik.

## Automatische Tests (`tests/` – via `python tests/run_tests.py`: 21/21 bestanden)

- [x] `test_cli_protocol.py`: JSON-Antwort-Parser in `agent_brain` – reines JSON, JSON in ```` ```json ````-Zaun,
      Text ohne JSON (→ `say`), unbekanntes Tool, kaputtes JSON.
- [x] `test_cli_loop.py`: `_chat_cli` mit gemocktem `gemini.ask` (Tool-Aufruf → Ergebnis → Endantwort;
      Abbruch nach `MAX_STEPS`).
- [x] `test_gemini.py`: Gemini-API-Aufruf (HTTP gemockt): kein Key, Erfolg, ungültiger Key, Kontingent,
      Modell-Fallback bei 404, Screenshot als Bild-Anhang, Antworttext mit „Login/API-Key“ wird nicht als Fehler gewertet.
- [x] `test_updater.py`: Versionsvergleich (`2.0.10 > 2.0.9`, `v`-Präfix), SHA-Prüfung schlägt bei
      falschem Hash fehl, URL-Whitelist.
- [x] `test_paths.py`: `DATA_DIR` liegt unter `%APPDATA%`, Config-Migration verwirft API-Keys.

## Manuell – Dev-Modus (`python main.py`)

- [x] Start ohne Fehler, keine Dateien im Quellordner erzeugt (Pfade in `%APPDATA%\Mochi`).
- [x] Katze sieht aus wie in `ref/` (Screenshots unter `ref/plan/screenshots/` erzeugt, Calico-Look mit
      weißer Front/Blesse, orange links, Tabby rechts & Stirn, gelbgrüne Augen, rosa Nase, Calico-Rücken, getigerter Schwanz, kein Halsband).
- [x] Ohne Key → Offline-Parser funktioniert für alle 20 Windows-Tools, Hinweis-Sprechblase beim ersten Start.
- [x] Ungültiger Key wird beim Speichern von der echten API abgelehnt („Mein API-Key ist ungültig“).
- [x] Key-Speicher: Windows-Anmeldeinformationsverwaltung schreiben/lesen/löschen (auch `cmdkey /delete`) geprüft.
- [ ] Gültiger Key → „Prüfen & speichern“ → Status grün (braucht echten Key des Users).
- [ ] KI-Antwort + mindestens 3 Tools per KI: Uhrzeit, Notiz, Ordner öffnen (wird im echten Ende-zu-Ende-Test ausgeführt).
- [x] Shell-Missbrauch entfällt: Die KI kann nur Mochis eigene `tools.py`-Werkzeuge auslösen (keine CLI mehr).
- [x] „Key entfernen“ löscht den Eintrag (geprüft).
- [x] Keine OpenAI-Reste; der Gemini-Key steht nie in `config.json`.

## Manuell – Installierte Version (Windows Sandbox / saubere VM, ohne Python)

- [ ] `build.ps1` nach Entfernen von Node/Gemini CLI neu ausführen (Setup wird deutlich kleiner).
- [ ] NICHT GETESTET (Saubere VM ohne Python stand in der Agent-Umgebung nicht zur Verfügung):
      Installation ohne Admin, deutsches Setup, Katzen-Icon überall.
- [ ] NICHT GETESTET (Erfordert Ab- und Neuanmeldung in Windows-Sitzung):
      Startmenü-Eintrag, Desktop-Icon (falls gewählt), Autostart nach Neuanmeldung.
- [x] Zweiter Start → keine zweite Katze (Single-Instance Mutex `MochiDesktopPetMutex` in `main.py`).
- [x] Update-Logik implementiert: Download, SHA256-Prüfung gegen `.sha256`, `/SILENT` Ausführung (`test_updater.py`).
- [ ] NUR CODE-REVIEW: Deinstallation: `installer/mochi.iss` entfernt `{app}`, Icons und Run-Eintrag; fragt per Dialog nach `%APPDATA%\Mochi`
      und löscht dann auch den gespeicherten Gemini-Key.

## Abschluss

- [x] README aktualisiert (Installation, Gemini-Key, Release-Ablauf, Lizenzhinweis).
- [x] `.gitignore` greift (`git status` zeigt keine Logs/Configs/Build-Ordner).
- [ ] Commits pro Phase auf Branch `dev`, aussagekräftige Messages (Phase 7 Commit folgt nach E2E-Test).
