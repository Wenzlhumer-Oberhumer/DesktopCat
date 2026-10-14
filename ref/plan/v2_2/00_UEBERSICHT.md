# Desktop Cat v2.2 – Gesamtplan für den Coding-Agent

Projekt: Python 3.13 + PyQt6 Desktop-Pet für Windows. Repo `Wenzlhumer-Oberhumer/DesktopCat`, Branch **`dev`**.
Aktueller Stand: **v2.1.0** („Mochi“, 9 Figuren, Gemini-Gratis-Key, Installer, Auto-Update, 43 Tests).
Ziel: **v2.2.0 „Desktop Cat“** mit Standard-Katze **Kylie** und vielen neuen Features.

## Phasen (genau in dieser Reihenfolge, jede Phase = 1 Commit, danach Tests grün)

| Phase | Datei | Inhalt |
|---|---|---|
| 1 | `01_NAME_KYLIE.md` | App heißt „Desktop Cat“, Katze heißt „Kylie“, reagiert auf ihren Namen |
| 2 | `02_DATEN_CHATS.md` | Chats + Fakten lokal speichern (SQLite), „Meine Chats“, „Meine Daten“, alles löschbar |
| 3 | `03_NEUGIER_ALLTAG.md` | Kylie interessiert sich für dich, Guten-Morgen, Geburtstag, Schlafenszeit |
| 4 | `04_ACCESSOIRES.md` | Zubehör-System für alle 9 Figuren: Hackerbrille, Wolke, Saison-/Wetter-Outfits, Level-Belohnungen, PC-Fieber |
| 5 | `05_IT_SUPPORT.md` | IT-Guide (Brille + Wolke + Klick-Zeiger), Fehlermeldungs-Doktor, Kopieren & Erklären |
| 6 | `06_SPASS_LERNEN.md` | Freundschafts-Level, Fokus-Statistik, Lern-Quiz, Fotobox, Haftnotizen |
| 7 | `07_ENGLISCH.md` | Sprache Deutsch/Englisch umschaltbar |
| 8 | `08_ABNAHME.md` | Tests, Checkliste, Build, Release |

## Harte Regeln

1. **Nichts darf Geld kosten.** Nur Gemini Free Tier über das vorhandene `gemini.py`, sonst offline. Keine neuen pip-Pakete (Standardbibliothek + vorhandene: PyQt6, requests, pywin32, Pillow, python-docx, python-pptx). Wetter über das vorhandene `tools.get_weather` (wttr.in).
2. **Bestehende Architektur nutzen, nicht neu bauen.** Wichtige Bausteine:
   - `paths.py`: `DATA_DIR` (= `%APPDATA%\Mochi`, bleibt so!), `APP_DIR`, `FROZEN`
   - `config.py`: `Config.get/set/save`, `DEFAULTS` (neue Keys dort ergänzen)
   - `gemini.py`: `ask(prompt, timeout_s, model, image_b64, key)`, `has_key()`, `LLMError`
   - `agent_brain.py`: `AgentWorker` (QThread), JSON-Protokoll `_chat_cli` + `parse_cli_response`, `parse_offline`, `system_prompt`, Sicherheitsabfrage `DANGEROUS_TOOLS`/`pending_action`
   - `tools.py`: `ToolResult`, `TOOL_SPECS`, `execute()`, `get_weather`, `get_active_window_context`, `take_screenshot`
   - `pet_sprites.py`: `CHARACTERS`, `draw_character`, `get_character_info`, `Pose`, `compute_pose`, `_draw_effects`
   - `pet_window.py`: `PetWindow` (`_px/_py` Position, `_tick`, `set_state`, `build_menu`, `react_happy`, `celebrate`, `chase_mouse`)
   - `main.py`: `Buddy` (Timer-Muster `_schedule_wellbeing`/`_on_wellbeing`, `_say`, Tray `showMessage`, `open_settings`)
   - `speech_bubble.py`: `SpeechBubble`, `InputBar`, `FloatingCard`
   - `settings_dialog.py`: Stil-Vorlage für alle neuen Fenster (dunkel `#26282C`, Akzent `#FF8FB1`, Segoe UI, runde Buttons)
3. **Threads**: Alles, was Netzwerk oder Dateien braucht, im QThread-Worker (Muster `AgentWorker`). Aufräumen von QThreads **nur** über gebundene Methoden (siehe `AgentBrain._reap_threads`), **nie** Lambdas an `thread.finished`. Callbacks aus `threading.Thread` per Qt-Signal in den Main-Thread holen (siehe Timer-Callback in `main.py`).
4. **Sicherheit & Privatsphäre**: Desktop Cat übernimmt **nie** Maus oder Tastatur (kein `SendInput`, kein pyautogui). Löschen von Nutzerdaten nur nach Bestätigung. Keine Daten an Dritte außer Gemini (und nur das Nötige). Nichts loggen, was Chat-Inhalte enthält.
5. **Tests**: Jede neue Logik bekommt Tests in `tests/` (Stil wie `tests/test_gemini.py`, Runner `tests/run_tests.py`, neue Module in dessen Liste eintragen). **Tests dürfen niemals echte Nutzerdaten, den echten Papierkorb, echte Fenster oder `%APPDATA%\Mochi\mochi.db` anfassen** → immer temporäre DB-Datei / Mocks.
6. **Nach jeder Phase**: `python -m pyflakes *.py` (keine *undefined name*-Meldungen!), `python tests/run_tests.py` (alles grün), kurzer Offscreen-Rauchtest (`QT_QPA_PLATFORM=offscreen`), dann **ein** Commit `Phase N: …` mit Zeile `Co-Authored-By: Gemini <noreply@google.com>`. **Nicht pushen, kein Release** – das macht der Reviewer.
7. **Ehrlich berichten**: Was nicht ausgeführt wurde, in `08_ABNAHME.md` als „NICHT GETESTET – Grund“ markieren. Abweichungen vom Plan in `ref/plan/v2_2/NOTIZEN_AGENT.md`.
8. Sprache der UI: Deutsch (Englisch kommt in Phase 7 über das i18n-System), freundlich, Emojis sparsam, Anrede mit `pet.user_name`.

## Design-Leitlinie „freundlich & cool“
- Alle neuen Fenster im Stil von `settings_dialog.py`: dunkler Hintergrund, rosa Akzent, große runde Buttons, Karten mit 12 px Radius, Figur-Emoji im Titel, kurze lockere Texte („Hier ist alles, was Kylie über dich weiß 🐾“).
- Leere Zustände nie leer lassen: „Noch keine Chats – sag Kylie einfach Hallo! 👋“.
- Jede Aktion gibt Rückmeldung: Figur reagiert (Herzchen, Hüpfer) + Sprechblase.

## Definition of Done (v2.2.0)
Alle Punkte in `08_ABNAHME.md` erledigt oder ehrlich als nicht getestet markiert, alle Tests grün, `build.ps1` erzeugt `dist\DesktopCat-Setup-2.2.0.exe`, Update über eine installierte v2.1.0 funktioniert (Daten, Gemini-Key und Einstellungen bleiben erhalten).
