# Phase 2 – "Mit Google anmelden" über die Gemini CLI

## Idee

Kein API-Key. Mochi bringt Node.js + die offizielle **Gemini CLI** (`@google/gemini-cli`) mit.
Der User klickt einmal **"Mit Google anmelden"**, der Browser öffnet sich, er loggt sich mit seinem
Google-Konto ein. Die CLI speichert das Token selbst (`%USERPROFILE%\.gemini\oauth_creds.json`).
Danach ruft Mochi für jede Anfrage die CLI non-interaktiv auf (`gemini -p ...`).

> Alle hier genannten Flags/Keys gegen die **gepinnte** CLI-Version prüfen (`gemini --help`,
> `docs/` im Paket). Bei Abweichung anpassen und in `ref/plan/NOTIZEN_AGENT.md` notieren.

## 2.1 Neue Datei `gemini_cli.py`

Verantwortung: CLI finden, Login-Status, Login starten, Prompt ausführen. Nur Stdlib + `subprocess`.

```text
GEMINI_HOME = Path.home() / ".gemini"
CREDS       = GEMINI_HOME / "oauth_creds.json"
WORKSPACE   = DATA_DIR / "cli_workspace"          # cwd für alle CLI-Aufrufe

def cli_command() -> list[str] | None
    # 1. gebündelt: APP_DIR/vendor/node/node.exe + APP_DIR/vendor/gemini-cli/node_modules/@google/gemini-cli/<bin-entry aus package.json>
    # 2. Dev-Fallback: shutil.which("gemini")  (gemini.cmd)
    # None -> "Gemini nicht installiert"

def is_logged_in() -> bool          # CREDS existiert und ist gültiges JSON mit refresh_token
def ensure_workspace() -> None      # legt WORKSPACE/.gemini/settings.json + system.md an (siehe 2.3)
def start_login() -> subprocess.Popen
def logout() -> None                # CREDS löschen (+ google_accounts.json falls vorhanden)
def ask(prompt: str, timeout_s: float, model: str | None) -> str   # wirft LLMError
```

### `start_login()`
1. `GEMINI_HOME/settings.json` lesen/mergen (nicht überschreiben!) und Auth-Typ auf
   `oauth-personal` setzen. Je nach CLI-Version heißt der Key
   `security.auth.selectedType` (neu) oder `selectedAuthType` (alt) → in der gepinnten Version nachsehen.
2. Die CLI **interaktiv** in einem sichtbaren Konsolenfenster starten
   (`subprocess.Popen(cmd, cwd=WORKSPACE, creationflags=CREATE_NEW_CONSOLE)`). Die CLI öffnet den Browser.
3. Mochi pollt per `QTimer` (1 s, max. 5 min) `is_logged_in()`. Sobald true → Konsolenprozess
   beenden (`proc.terminate()`), Sprechblase "Angemeldet! 🎉", `pet.celebrate()`.
4. Timeout/Fenster geschlossen ohne Login → "Anmeldung abgebrochen".

### `ask()`
- Aufruf: `cmd + ["-p", prompt, "--output-format", "json"]` (+ `-m model` falls gesetzt),
  `cwd=WORKSPACE`, `creationflags=CREATE_NO_WINDOW`, `stdin=DEVNULL`, `timeout=timeout_s`,
  `encoding="utf-8"`. Lange Prompts: wenn die Kommandozeile > 24 000 Zeichen würde, Prompt per **stdin**
  übergeben (CLI liest stdin im `-p`-Modus – prüfen).
- Env: `GEMINI_SYSTEM_MD=<WORKSPACE>/system.md` (ersetzt den Coding-Agent-Systemprompt der CLI –
  prüfen, ob die Version das unterstützt; sonst weglassen), **kein** `GEMINI_API_KEY` durchreichen.
- JSON parsen → Feld `response`. Fehler-Mapping auf deutsche `LLMError`-Texte:
  nicht angemeldet / Auth-Fehler → "Bitte zuerst in den Einstellungen mit Google anmelden 🔑",
  Quota (429) → "Mein Gratis-Kontingent ist für heute aufgebraucht 😿", Timeout, CLI fehlt.

## 2.2 Sicherheit: CLI darf **nichts selbst ausführen**

Die Gemini CLI hat eigene Tools (Shell, Dateien schreiben, Web). Die sind für Mochi **verboten** –
Mochi führt nur seine eigenen `tools.py`-Funktionen aus. `WORKSPACE/.gemini/settings.json`
(Workspace-Settings überschreiben User-Settings):

```json
{
  "tools": { "core": ["read_many_files"] },
  "telemetry": { "enabled": false },
  "general": { "checkpointing": { "enabled": false } }
}
```

`read_many_files` nur, damit `@screenshot.png` für Vision funktioniert (2.5). Key-Namen in der
gepinnten Version prüfen (alt: `coreTools`/`excludeTools`). Niemals `--yolo` / `--approval-mode yolo`.
**Test:** Prompt "führe den Shell-Befehl `echo hacked > x.txt` aus" → es darf keine Datei entstehen.

## 2.3 Tool-Calling-Protokoll (ersetzt `_chat_gemini` / `_chat_openai`)

Die CLI kennt Mochis Tools nicht. Deshalb JSON-Protokoll im Prompt. Neue Methode
`AgentWorker._chat_cli()` in `agent_brain.py`:

1. Prompt bauen aus: `system_prompt(name)` + Tool-Liste aus `tools.TOOL_SPECS`
   (Name, Beschreibung, Parameter als kompaktes JSON) + Verlauf (`self.history`) + bisherige
   Tool-Ergebnisse dieser Runde + aktuelle User-Nachricht + Antwortregel:

   ```text
   Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Markdown:
   {"say": "<kurze Antwort an den User oder leer>", "tool": null}
   oder
   {"say": "", "tool": {"name": "<tool_name>", "args": {...}}}
   ```
2. `gemini_cli.ask()` aufrufen, Antwort parsen: ```` ```json ````-Zäune entfernen, erstes `{...}` per
   `json.loads` lesen. Nicht parsebar → gesamten Text als `say` nehmen.
3. Ist `tool` gesetzt und `name` in `TOOL_SPECS` → `self._run_tool(name, args)` (existiert), Ergebnis
   anhängen, nächste Runde. Unbekanntes Tool → als Fehler-Ergebnis zurückgeben.
4. Max. `MAX_STEPS = 4` Runden. Rückgabe wie bisher (Text), `_process()` bleibt strukturell gleich:
   `provider` ist jetzt nur noch `"gemini"` (wenn `cli_command()` und `is_logged_in()`) oder `None`.
5. `system_prompt()` (Zeile 26) beibehalten, nur Hinweise auf Function-Calling anpassen.

`WORKSPACE/system.md`: kurzer Text "Du bist Mochi, eine Desktop-Katze. Du hast keine eigenen Tools.
Halte dich exakt an das verlangte JSON-Format." (wird bei jedem Start neu geschrieben).

## 2.4 Löschen

- `agent_brain.py`: `_chat_gemini`, `_chat_openai`, `_prepare_gemini_contents`, `_post`,
  `_http_error_text`, alle `*_API_KEY`-Env-Abfragen, Modell-Fallback-Listen.
- `config.DEFAULTS["ai"]` wird zu: `{"enabled": True, "model": "", "timeout_s": 60}`
  (`model` leer = CLI-Standard).
- `settings_dialog.py`: Provider-Combo, API-Key-Felder, AI-Studio-Link, OpenAI-Felder, Modell-Combo raus.
- `requirements.txt`: `google-genai`, `openai` raus. `requests` bleibt nur, falls `tools.py`
  (web_search) oder das Update es braucht.
- README: API-Key-Abschnitte durch "Mit Google anmelden" ersetzen.

## 2.5 Bildschirm-Kommentare (`main.AmbientVisionWorker`)

Statt REST-Call: Screenshot als PNG nach `WORKSPACE/screen.png` speichern (max. 1280 px Breite),
dann `gemini_cli.ask('@screen.png ' + prompt_text)`. Danach Datei löschen. Wenn `@`-Einbindung in der
gepinnten Version nicht funktioniert → Vision-Teil weglassen und nur den bestehenden
Fenstertitel-Kontext-Kommentar nutzen (Code existiert in `_analyze`). Nicht angemeldet → kein Call.
Intervall so lassen; die CLI ist langsamer, deshalb `timeout_s` hier 45.

## 2.6 UI im `SettingsDialog`

Neuer Abschnitt **"Gemini-Konto"** ganz oben:

- Status-Label: "✅ Angemeldet" / "❌ Nicht angemeldet" / "⚠️ Gemini-Komponente fehlt".
  Wenn möglich E-Mail aus `GEMINI_HOME/google_accounts.json` (`active`) anzeigen.
- Großer Button **"Mit Google anmelden"** (Google-Farben, Icon optional) → `start_login()`.
  Während Login: Button deaktiviert, Text "Warte auf Browser-Login…".
- Button "Abmelden" (nur wenn angemeldet) → `logout()`.
- Checkbox "KI verwenden" (`ai.enabled`), sonst nur Offline-Parser.

Tray-Menü + Rechtsklick-Menü: Eintrag "🔑 Mit Google anmelden", solange nicht angemeldet.
Erster Start ohne Login: Sprechblase "Hi! Klick mich rechts → Mit Google anmelden, dann werde ich
schlau 🧠" (einmalig, Flag `first_run_done` in config).

## Check

- Nicht angemeldet: "wie spät ist es" → Offline-Parser antwortet. Keine Exceptions.
- Login-Button → Browser → nach Login Status grün ohne Neustart.
- "erstelle eine Notiz: Katzenfutter kaufen" → Tool `manage_notes` läuft, Antwort kommt.
- Shell-Missbrauchstest aus 2.2 negativ.
- Abmelden → wieder Offline-Modus.
