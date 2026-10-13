# Mochi 2.0 – Gesamtplan (für den Coding-Agent)

Mochi ist ein Python/PyQt6 Desktop-Pet (`main.py`, `pet_window.py`, `pet_sprites.py`, `agent_brain.py`,
`tools.py`, `settings_dialog.py`, `speech_bubble.py`, `config.py`). Ziel dieses Updates:

1. **Echtes Windows-Programm** – Installer `Mochi-Setup-<version>.exe`, Startmenü, Desktop-Icon,
   Autostart, Deinstallation, Auto-Update über GitHub Releases. Kein Python auf dem Ziel-PC nötig.
2. **"Mit Google anmelden"-Button statt API-Key** – über die offizielle **Gemini CLI** (mitgeliefert).
   API-Key- und OpenAI-Code fliegen **komplett raus**.
3. **Die Katze sieht aus wie die echte Katze** in `ref/*.jpg` (dreifarbige Glückskatze / Calico).

## Reihenfolge (jede Phase einzeln lauffähig + committen)

| Phase | Datei | Inhalt |
|------|-------|--------|
| 1 | `01_WINDOWS_APP.md` | Pfade (%APPDATA%), Version, Autostart, Icon, .gitignore |
| 2 | `02_GEMINI_LOGIN.md` | Gemini-CLI-Backend + Login-Button, alte Provider löschen |
| 3 | `03_KATZEN_LOOK.md` | Calico-Färbung der QPainter-Katze + Sprite-Override bleibt |
| 4 | `04_INSTALLER_BUILD.md` | PyInstaller + Node/Gemini-CLI bündeln + Inno Setup + `build.ps1` |
| 5 | `05_AUTO_UPDATE.md` | Update-Check über GitHub Releases |
| 6 | `06_ABNAHME.md` | Testliste, alles muss grün sein |

## Feste Entscheidungen (nicht neu diskutieren)

- App-Name bleibt **Mochi**. Nutzerdaten in `%APPDATA%\Mochi\` (config, Log, Undo-Log, CLI-Workspace).
- Login: **Gemini CLI** (`@google/gemini-cli`, Version **pinnen**), Auth-Typ `oauth-personal`
  ("Login with Google"). Node.js portable wird mitgeliefert.
- Katze: QPainter-Katze wird auf Calico umgefärbt. PNG/GIF-Sprites in `assets/` überschreiben sie weiterhin
  (bestehender `SpriteLibrary`-Mechanismus – nicht anfassen außer Pfaden).
- Installer: **Inno Setup 6**. Kein Code-Signing (optionaler Signier-Schritt im Build-Skript, standardmäßig aus).
- Update-Quelle: GitHub Releases, Repo als Konstante `UPDATE_REPO = "Nairolf/Mochi"` (Platzhalter, User ändert).
- Offline-Parser (`parse_offline`) bleibt als Fallback, wenn nicht angemeldet oder CLI-Fehler.
- Sprache der UI: Deutsch, Stil wie bisher (Emojis, "Miau").

## Regeln für den Agent

- Kleinste vollständige Änderung. Keine neuen Abhängigkeiten außer: `pyinstaller` (nur Build).
  Kein `google-genai`, kein `openai` mehr → aus `requirements.txt` entfernen.
- Bestehende Struktur behalten (Dateien, Klassen, Signale wie `AgentWorker.finished`).
- Vor jedem Edit: alle Aufrufer der geänderten Funktion per Suche finden und mitziehen.
- Nach jeder Phase: `python main.py` starten und prüfen, dass die Katze erscheint und das Log
  (`%APPDATA%\Mochi\buddy.log`) keine Tracebacks hat.
- Niemals `config.json`, `buddy.log`, `__pycache__/`, `build/`, `dist/`, `vendor/` committen.
- Wenn ein Detail der Gemini CLI (Flag, Settings-Key, Pfad) anders ist als hier beschrieben:
  **in der installierten Version nachsehen** (`gemini --help`, `node_modules/@google/gemini-cli/README.md`,
  `docs/`) und anpassen – nicht raten. Abweichung in `ref/plan/NOTIZEN_AGENT.md` dokumentieren.

## Definition of Done

`build.ps1` erzeugt `dist\Mochi-Setup-<ver>.exe`. Auf einem Windows-11-PC **ohne Python und ohne Node**:
installieren → Mochi startet, Calico-Katze läuft auf der Taskleiste → Einstellungen → "Mit Google anmelden"
→ Browser-Login → Mochi beantwortet "wie spät ist es" per KI und führt Tools aus → Neustart: weiterhin
angemeldet → Deinstallieren entfernt Programm, Verknüpfungen und Autostart-Eintrag. Alle Punkte in
`06_ABNAHME.md` abgehakt.
