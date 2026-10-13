# Notizen des Coding-Agents

Hier werden Entscheidungen, Beobachtungen und etwaige Abweichungen von den Plan-Dateien festgehalten.

## Phase 1
- `paths.py` angelegt mit `APP_DIR`, `DATA_DIR`, `FROZEN`, `set_autostart()`.
- `version.py` mit `__version__ = "2.0.0"` und `UPDATE_REPO = "Nairolf/Mochi"` erstellt.
- `config.py` migriert bei Bedarf alte `config.json` aus dem Codeverzeichnis nach `DATA_DIR`, verwirft dabei veraltete API-Keys (`gemini_api_key`, `openai_*`, `provider`).
- Log-Rotation bei > 2 MB beim Start implementiert (`buddy.log` -> `buddy.log.1`).
- Benannter Windows-Mutex `MochiDesktopPetMutex` in `main.py` erzeugt und für die Laufzeit gehalten.
- `SpriteLibrary` durchsucht zuerst `DATA_DIR / "assets"`, dann `APP_DIR / "assets"`.

## Phase 2
- Gemini CLI Version `@google/gemini-cli@0.63.0` gepinnt.
- Entry-Point in `package.json`: `"bin": {"gemini": "bundle/gemini.js"}`.
- Auth-Settings-Key: In v0.63.0 liegt der ausgewählte Auth-Typ unter `security.auth.selectedType` (Wert `"oauth-personal"`). Zur Abwärtskompatibilität wird auch `selectedAuthType` gesetzt.
- Core-Tools-Sandbox: In `.gemini/settings.json` im Workspace wird `"tools": {"core": ["read_many_files"]}` gesetzt. Dies deaktiviert alle eingebauten Shell- und Datei-Tools der CLI.
- System-Prompt: CLI liest `GEMINI.md` im Workspace (`cwd=WORKSPACE`). Daher werden im Workspace sowohl `system.md` als auch `GEMINI.md` angelegt.
- Output-Format: `--output-format json` liefert ein JSON-Objekt mit den Feldern `session_id`, `response` (im Erfolgsfall) oder `error` (im Fehlerfall).

