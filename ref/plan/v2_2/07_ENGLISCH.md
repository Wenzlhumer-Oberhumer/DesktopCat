# Phase 7 – Englisch-Modus

## 7.1 `i18n.py` (neu, klein)
```python
_LANG = "de"
STRINGS = {"menu.chats": {"de": "📚 Meine Chats", "en": "📚 My chats"}, ...}
def set_language(lang: str) -> None
def tr(key: str, **kw) -> str      # Fallback: Deutsch, dann der Key selbst
def lang() -> str
```
- Config `language = "de"` (Einstellungen: Auswahl „Deutsch / English“, wirkt nach Speichern sofort für Menüs und neue Texte; Fenster, die schon offen sind, dürfen erst beim nächsten Öffnen umschalten).

## 7.2 Was übersetzt wird
- **Alle sichtbaren UI-Texte**: Rechtsklick- und Tray-Menü, Einstellungen, Meine Chats, Meine Daten (inkl. Datenschutz-Text!), Freundschaft, Fokus, Lernkarten, Haftnotizen, IT-Guide-Buttons, Sprechblasen-Standardsätze (Begrüßung, Erinnerungen, Akku, Timer, Fehler aus `gemini.py`), Installer bleibt Deutsch (optional: `[Languages]` English ergänzen).
- **Figuren**: `CHARACTERS[*]` Texte (`pet_sounds`, `ambient_lines`, `desc`, `species`, `ai_persona`, `task_start`, `task_done`, Neugier-Fragen) bekommen englische Varianten (z. B. Feld `"en": {...}` mit gleichen Keys); `get_character_info(id)` liefert je nach Sprache.
- **KI**: `system_prompt` + alle Gemini-Prompts mit Zeile „Answer in English.“ bzw. „Antworte auf Deutsch.“; JSON-Protokoll bleibt gleich.
- **Offline-Parser**: englische Schlüsselwörter für die wichtigsten Befehle (time/date, timer/pomodoro, weather, ip/network, screenshot, notes, help, clean, forget everything, quiz, what do you know about me, Kylie-Namensreaktion „What's your name?“). Nicht alle Sonderfälle nötig.
- Tool-Ergebnistexte aus `tools.py`: die häufigsten (Zeit, Timer, Wetter, Netzwerk, Aufräumen, Notizen, Screenshot) übersetzen.

## 7.3 Vorgehen
Strings schrittweise durch `tr("…")` ersetzen, Datei für Datei. **Keine Logik ändern.** Fehlende englische Texte fallen auf Deutsch zurück (nie Absturz).

## Tests (`tests/test_i18n.py`)
- Jeder Key in `STRINGS` hat `de` und `en`.
- Kein Key, der im Code mit `tr("...")` benutzt wird, fehlt in `STRINGS` (Test liest alle `*.py` per Regex `tr\("([^"]+)"`).
- `get_character_info` liefert in `en` englische Texte für alle 9 Figuren.
- Offline-Parser: „what time is it“, „set a timer for 5 minutes“, „what's the weather in vienna“ funktionieren im Englisch-Modus.
