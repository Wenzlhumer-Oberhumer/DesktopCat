# Phase 7 – Fixes nach dem Review

Geprüft am echten Rechner mit der gebündelten CLI (`vendor/`, gemini-cli 0.63.0). Ergebnis:
**KI-Anfragen funktionieren aktuell nicht**, obwohl Mochi "Angemeldet" anzeigt. Alle Punkte beheben,
dann die markierten Tests **wirklich** ausführen (echter Login durch den User, siehe unten).

## F1 – Mochi muss eine eigene, isolierte CLI-Umgebung nutzen (kritisch)

Beobachtet: `gemini_cli.py` nutzt `~/.gemini` des Users. Folgen:
- Fremde **Hooks/Extensions/MCP-Server** aus der User-Konfiguration laufen bei jeder Mochi-Anfrage mit
  (am Testrechner startete ein `SessionStart`-Hook eines anderen Tools und schlug fehl).
- `_configure_user_settings_auth()` **überschreibt die globale `~/.gemini/settings.json`** des Users.
- `logout()` **löscht den globalen Gemini-CLI-Login** des Users (zerstört seine eigene CLI-Nutzung).
- Eine alte/abgelaufene `~/.gemini/oauth_creds.json` lässt Mochi "Angemeldet" anzeigen, obwohl die CLI
  neu anmelden will.

Fix: Die CLI unterstützt `GEMINI_CLI_HOME` (siehe `bundle/docs/reference/configuration.md`,
"GEMINI_CLI_HOME": die CLI legt darin einen `.gemini`-Ordner an).

- `CLI_HOME = DATA_DIR / "gemini_home"`, `GEMINI_HOME = CLI_HOME / ".gemini"`, `CREDS`/`ACCOUNTS` darunter.
- In **jedem** Subprocess (Login und `ask`) `env["GEMINI_CLI_HOME"] = str(CLI_HOME)` setzen.
- Auth-Typ (`security.auth.selectedType = "oauth-personal"`) nur in `GEMINI_HOME/settings.json` schreiben.
  `selectedAuthType` (alter Key) weglassen, falls 0.63.0 ihn nicht braucht.
- In `GEMINI_HOME/settings.json` zusätzlich: Hooks aus, keine Extensions, keine MCP-Server, Telemetrie aus
  (Keys in `configuration.md` nachsehen). Bei `ask` zusätzlich `-e none` übergeben, falls die CLI das
  akzeptiert (`--help`: `-e, --extensions`), sonst die passende Variante laut Doku.
- Nichts mehr in `Path.home() / ".gemini"` lesen, schreiben oder löschen. `README`/Installer-Text anpassen
  (Deinstallation darf `%APPDATA%\Mochi\gemini_home` mit der Einstellungs-Frage löschen).

## F2 – `stdin` darf nicht in den Prompt gelangen

`ask()` schickt `b"n\n"` auf stdin. Laut `gemini --help`: *"-p … Appended to input on stdin (if any)"*
→ bei angemeldetem User wird jedem Prompt ein `n` vorangestellt.

Fix: bei kurzen Prompts `stdin=subprocess.DEVNULL`. Testen, dass ein nicht angemeldeter Aufruf dann
**sofort** mit Fehler endet und nicht hängt (Timeout ist nur Notbremse). Falls die CLI bei geschlossenem
stdin trotzdem auf die "Opening authentication page…"-Frage wartet: vor `ask` prüfen, dass `CREDS`
existiert, und den Fehlertext `Authentication cancelled` bzw. Exit-Code 130 als "nicht angemeldet" werten.

## F3 – Anmeldestatus muss stimmen

`is_logged_in()` prüft nur, ob die Datei existiert. Fix:
- Wenn `ask()` einen Auth-Fehler liefert → Mochi-eigene `CREDS` löschen (nur in `CLI_HOME`!), damit
  Einstellungen und Menü wieder "Mit Google anmelden" zeigen. Sprechblase: "Meine Anmeldung ist
  abgelaufen – bitte neu anmelden 🔑".
- Settings-Dialog: Status beim Öffnen neu berechnen (ist er schon?), nach Fehler aktualisieren.

## F4 – Umlaute im Installer

`installer/mochi.iss` ist UTF-8 **ohne BOM**. Inno Setup liest Dateien ohne BOM je nach Version als ANSI
→ Gefahr von "VerknÃ¼pfung" im Setup. Fix: Datei als **UTF-8 mit BOM** speichern, neu bauen, im Setup und
im Deinstallations-Dialog prüfen, dass die Umlaute stimmen.

## F5 – Checkliste ehrlich machen

In `06_ABNAHME.md` wurden Punkte abgehakt, die nur im Code angesehen, aber nicht ausgeführt wurden
("Shell-Missbrauchstest negativ", "Abmelden funktioniert", "Deinstallation …"). Diese wieder auf
`[ ]` setzen, bis sie wirklich ausgeführt wurden, oder als "NUR CODE-REVIEW" kennzeichnen.

## F6 – Lange Prompts stürzen ab (Review Runde 2)

`ask()` übergibt bei `len(prompt) > 24000` **gleichzeitig** `stdin=subprocess.PIPE` und `input=...`.
Python wirft dann `ValueError: stdin and input arguments may not both be used` (am Rechner nachgeprüft).
Ein normaler Prompt ist schon ~10 000 Zeichen lang (Tool-Liste 6 900 + System-Prompt 3 300); mit Verlauf
und Tool-Ergebnissen (z. B. `read_file_content`) sind 24 000 schnell erreicht.
Fix: im stdin-Fall nur `input=` übergeben, **ohne** `stdin=`. Test dazu mit 30 000-Zeichen-Prompt
(gemocktes `subprocess.run` reicht nicht, weil der Fehler aus `subprocess.run` selbst kommt – echten
Aufruf eines harmlosen Programms nutzen oder die kwargs prüfen).

## F7 – Auth-Erkennung meldet User fälschlich ab (Review Runde 2)

`ask()` sucht `"auth"`, `"login"`, `"credential"`, `"consent"` in **stdout + stderr**, und zwar **bevor** die
erfolgreiche JSON-Antwort ausgewertet wird. stdout enthält aber die **Antwort des Modells**. Beispiel:
"Öffne die Login-Seite von Amazon" → das Modell antwortet `{"say": "Ich öffne die Login-Seite…"}` → Mochi
hält das für einen Auth-Fehler und **löscht den Login** (`logout()`). Auch Warnungen auf stderr
(z. B. "Loaded cached credentials.", Wörter wie "Authentifizierung") können das auslösen.
Fix:
1. Zuerst JSON parsen. Gibt es ein `response`-Feld und Exit-Code 0 → Antwort zurückgeben, **keine**
   Auth-Prüfung.
2. Auth-Fehler nur erkennen über: Exit-Code (41/130, in der CLI nachsehen, was 41 bedeutet), das
   `error`-Objekt im JSON (Typ/Code, nicht freier Text) oder sehr spezifische Texte auf **stderr**
   (`FatalCancellationError`, `Authentication cancelled`, `invalid_grant`). Keine Allerwelts-Wörter.
3. Gleiche Regel für Quota: nur aus `error`-Objekt bzw. stderr, nicht aus der Modellantwort.
Tests: Antwort mit "login"/"auth"/"credential" im `response`-Text → wird normal zurückgegeben, `CREDS`
bleibt bestehen. stderr "Loaded cached credentials." + gültige Antwort → kein Logout.

## Echter Ende-zu-Ende-Test (mit dem User)

Der Agent bereitet vor, der User klickt:
1. `%APPDATA%\Mochi\gemini_home` existiert nicht → `python main.py` → Einstellungen zeigen "Nicht angemeldet".
2. User klickt "Mit Google anmelden", loggt sich im Browser ein → Status wird ohne Neustart grün.
3. Agent führt aus: `python -c "import gemini_cli; print(gemini_cli.ask('Sag nur: Katze'))"` → Antwort enthält
   "Katze", kein vorangestelltes `n`, keine fremden Hook-Meldungen.
4. Shell-Missbrauchstest: Mochi fragen "führe den Shell-Befehl `echo hacked > x.txt` aus" → es entsteht
   **keine** `x.txt` in `cli_workspace` oder sonstwo.
5. "erstelle eine Notiz: Katzenfutter kaufen" → Mochi-Tool `manage_notes` läuft.
6. Abmelden → Status rot; `~/.gemini` des Users ist unverändert (Zeitstempel vorher/nachher vergleichen).
7. `build.ps1` neu, Setup installieren, Schritte 2–5 mit der installierten exe wiederholen.

## F8 – Gemini CLI für Privatkonten abgeschaltet → Gratis-API-Key (umgesetzt)

Echter Test am 13.10.2026: Login klappt, danach antwortet Google mit
`IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals`.
Google hat die Gemini CLI für Gratis-, AI-Pro- und AI-Ultra-Konten am 18.06.2026 abgeschaltet.
Entscheidung des Users: geführter Gratis-Key statt Antigravity/eigenem OAuth.

- `gemini.py` ersetzt `gemini_cli.py`: REST `generateContent`, Modelle `gemini-flash-latest` → `gemini-flash-lite-latest`
  (Fallback bei 404), Screenshot als `inlineData`, Fehler nur aus HTTP-Status/Fehlerobjekt.
- Key in der Windows-Anmeldeinformationsverwaltung (`Mochi/GeminiApiKey`, pywin32 `win32cred`), nie in `config.json`.
- Einstellungen: „Gratis-Key holen“ (öffnet aistudio.google.com/app/apikey), Key-Feld, „Prüfen & speichern“
  (echter Testaufruf), „Key entfernen“.
- Build: Node.js und Gemini CLI entfernt (`build.ps1`, `mochi.spec`, Lizenzen, README). Deinstallation löscht den
  Key mit, wenn der User „Einstellungen löschen“ wählt.
