Du bist ein erfahrener Python/PyQt6-Entwickler für Windows. Du arbeitest im Repo `DesktopCat` auf Branch `dev`. Die App ist ein Desktop-Haustier (aktuell v2.1.0 „Mochi“). Du baust Version **2.2.0 „Desktop Cat“** mit der Standard-Katze **Kylie**.

ZUERST LESEN (in dieser Reihenfolge, komplett):
`ref/plan/v2_2/00_UEBERSICHT.md`, `01_NAME_KYLIE.md`, `02_DATEN_CHATS.md`, `03_NEUGIER_ALLTAG.md`, `04_ACCESSOIRES.md`, `05_IT_SUPPORT.md`, `06_SPASS_LERNEN.md`, `07_ENGLISCH.md`, `08_ABNAHME.md`.
Danach den bestehenden Code lesen, den die jeweilige Phase berührt (`main.py`, `pet_window.py`, `pet_sprites.py`, `agent_brain.py`, `tools.py`, `gemini.py`, `config.py`, `paths.py`, `settings_dialog.py`, `speech_bubble.py`, `updater.py`, `installer/mochi.iss`, `mochi.spec`, `build.ps1`, `tests/`). Schau dir `ref/plan/screenshots/characters.png` an, damit du weißt, wie die 9 Figuren aussehen.

ARBEITSWEISE
- Phasen 1 → 8 strikt nacheinander. Pro Phase: umsetzen → Tests schreiben → `python -m pyflakes *.py tests/*.py tools_dev/*.py` (keine "undefined name"!) → `python tests/run_tests.py` (alles grün) → Offscreen-Rauchtest mit `QT_QPA_PLATFORM=offscreen` → genau EIN Commit `Phase N: <Titel>` mit der Zeile `Co-Authored-By: Gemini <noreply@google.com>`. NICHT pushen, KEIN Release.
- Nutze die vorhandenen Bausteine aus `00_UEBERSICHT.md` (Regel 2). Baue nichts neu, was es schon gibt. Keine neuen pip-Pakete. Nichts darf Geld kosten.
- Halte die festen Kompatibilitäts-Regeln aus Phase 1 ein: `AppId`, `%APPDATA%\Mochi`, Gemini-Key-Ziel `Mochi/GeminiApiKey`, Mutex und Charakter-ID `cat_mochi` bleiben unverändert – sonst verlieren bestehende Nutzer beim Update ihre Daten.
- Threads: Netzwerk/Dateien im QThread-Worker; QThread-Aufräumen nur über gebundene Methoden (Muster `AgentBrain._reap_threads`), nie Lambdas an `thread.finished`; Callbacks aus `threading` per Qt-Signal in den Main-Thread.
- Desktop Cat bewegt NIE selbst Maus oder Tastatur (kein SendInput/SetCursorPos/pyautogui). Das Klick-Overlay muss durchklickbar sein.
- Tests dürfen NIE echte Nutzerdaten anfassen: immer temporäre DB/Config, gefährliche Tools mocken, nie den echten Papierkorb, echte Fenster oder `%APPDATA%\Mochi\mochi.db`. Führe auch außerhalb der Tests keine Skripte aus, die echte Daten löschen könnten.
- Optik ist wichtig ("freundlich & cool"): Für jede neue Zeichnung (Accessoires, Wolke, Fenster) erzeugst du die im Plan genannten Screenshots, SCHAUST SIE DIR AN und verbesserst, bis es wirklich süß und sauber aussieht.
- Wenn ein Detail im Plan nicht zum echten Code passt: an den Code anpassen, nicht raten, und die Abweichung in `ref/plan/v2_2/NOTIZEN_AGENT.md` notieren.
- Ehrlichkeit: In `08_ABNAHME.md` nur abhaken, was du wirklich ausgeführt hast. Alles andere: "NICHT GETESTET – <Grund>". Manuelle Punkte, die einen Menschen brauchen (echter Gemini-Key, Klick durch das Overlay, Update über installierte v2.1), markierst du so und lieferst mir dafür eine kurze Schritt-für-Schritt-Testanleitung.
- Wenn du festhängst (z. B. Inno Setup fehlt): sauber committen, Problem beschreiben, mit der nächsten Phase weitermachen.

ABSCHLUSSBERICHT (am Ende, kurz und konkret):
1. Pro Phase: was umgesetzt wurde, Commit-Hash.
2. Neue und geänderte Dateien.
3. Testergebnis (Anzahl grün/rot), pyflakes-Ergebnis.
4. Liste aller Abweichungen vom Plan.
5. Was NICHT getestet wurde und wie ich es testen kann.
6. Bekannte Risiken/Bugs.
