# Phase 6 – Abnahme-Checkliste

Der Agent hakt jeden Punkt ab (`[x]`) und schreibt bei Problemen eine Notiz in `NOTIZEN_AGENT.md`.
Zusätzlich: kleine Selbsttests in `tests/` (pytest oder `python -m` mit asserts) für die neue Logik.

## Automatische Tests (`tests/`)

- [ ] `test_cli_protocol.py`: JSON-Antwort-Parser in `agent_brain` – reines JSON, JSON in ```` ```json ````-Zaun,
      Text ohne JSON (→ `say`), unbekanntes Tool, kaputtes JSON.
- [ ] `test_cli_loop.py`: `_chat_cli` mit gemocktem `gemini_cli.ask` (Tool-Aufruf → Ergebnis → Endantwort;
      Abbruch nach `MAX_STEPS`).
- [ ] `test_updater.py`: Versionsvergleich (`2.0.10 > 2.0.9`, `v`-Präfix), SHA-Prüfung schlägt bei
      falschem Hash fehl, URL-Whitelist.
- [ ] `test_paths.py`: `DATA_DIR` liegt unter `%APPDATA%`, Config-Migration verwirft API-Keys.

## Manuell – Dev-Modus (`python main.py`)

- [ ] Start ohne Fehler, keine Dateien im Quellordner erzeugt.
- [ ] Katze sieht aus wie in `ref/` (siehe Phase 3 Check), alle Zustände getestet.
- [ ] Nicht angemeldet → Offline-Parser funktioniert, Hinweis-Sprechblase beim ersten Start.
- [ ] Login-Button → Browser → angemeldet ohne Neustart.
- [ ] KI-Antwort + mindestens 3 Tools per KI: Uhrzeit, Notiz, Ordner öffnen.
- [ ] Shell-Missbrauchstest (Phase 2.2) negativ.
- [ ] Abmelden funktioniert.
- [ ] Einstellungen enthalten **keine** API-Key-/OpenAI-Felder mehr; `grep -ri "api_key\|openai"` im
      Python-Code findet nichts mehr.

## Manuell – Installierte Version (Windows Sandbox / saubere VM, ohne Python + Node)

- [ ] `build.ps1` läuft durch, Setup-exe + `.sha256` in `dist\`.
- [ ] Installation ohne Admin, deutsches Setup, Katzen-Icon überall.
- [ ] Startmenü-Eintrag, Desktop-Icon (falls gewählt), Autostart nach Neuanmeldung.
- [ ] Login + KI funktionieren mit mitgelieferter Node/CLI.
- [ ] Zweiter Start → keine zweite Katze (Single-Instance).
- [ ] Update von einer älteren Version (Phase 5 Check).
- [ ] Deinstallation: Programm, Verknüpfungen, Run-Eintrag weg; Frage nach Einstellungen;
      `%USERPROFILE%\.gemini` unberührt.

## Abschluss

- [ ] README aktualisiert (Installation, Login, Release-Ablauf, Lizenzhinweis).
- [ ] `.gitignore` greift (`git status` zeigt keine Logs/Configs/Build-Ordner).
- [ ] Commits pro Phase auf Branch `dev`, aussagekräftige Messages.
