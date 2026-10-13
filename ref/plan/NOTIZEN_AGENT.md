# Notizen des Coding-Agents

Hier werden Entscheidungen, Beobachtungen und etwaige Abweichungen von den Plan-Dateien festgehalten.

## Phase 1
- `paths.py` angelegt mit `APP_DIR`, `DATA_DIR`, `FROZEN`, `set_autostart()`.
- `version.py` mit `__version__ = "2.0.0"` und `UPDATE_REPO = "Nairolf/Mochi"` erstellt.
- `config.py` migriert bei Bedarf alte `config.json` aus dem Codeverzeichnis nach `DATA_DIR`, verwirft dabei veraltete API-Keys (`gemini_api_key`, `openai_*`, `provider`).
- Log-Rotation bei > 2 MB beim Start implementiert (`buddy.log` -> `buddy.log.1`).
- Benannter Windows-Mutex `MochiDesktopPetMutex` in `main.py` erzeugt und für die Laufzeit gehalten.
- `SpriteLibrary` durchsucht zuerst `DATA_DIR / "assets"`, dann `APP_DIR / "assets"`.
