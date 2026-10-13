# Phase 2 – Chats & Fakten speichern, „Meine Chats“, „Meine Daten“

## 2.1 `memory_store.py` (neu, nur Standardbibliothek `sqlite3`)
Datei: `DATA_DIR / "mochi.db"` (Pfad als Parameter, damit Tests eine Temp-DB nutzen).

```sql
CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY, started REAL, character TEXT, title TEXT);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, conversation_id INTEGER, ts REAL, role TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY, ts REAL, text TEXT, due_date TEXT NULL, kind TEXT DEFAULT 'fact');
CREATE TABLE IF NOT EXISTS stats(key TEXT PRIMARY KEY, value TEXT);   -- für Level/Fokus/Quiz (Phase 6)
```
API (klein halten, eine Klasse `MemoryStore(path)`):
- `add_message(role, text, character) -> None` – neues Gespräch, wenn das letzte > 30 Min. her ist; Titel = erste User-Nachricht gekürzt auf 40 Zeichen.
- `conversations(search: str = "") -> list[dict]` (neueste zuerst; Suche per `LIKE` über messages.text)
- `messages(conversation_id) -> list[dict]`
- `delete_conversation(id)`, `delete_all_chats()`
- `add_fact(text, due_date=None, kind="fact")`, `facts() -> list[dict]`, `delete_fact(id)`, `forget_matching(text) -> int`, `delete_all_facts()`
- `relevant_snippets(query, limit=3) -> list[str]` – lokale Stichwortsuche: Wörter ≥ 4 Buchstaben aus `query` (Stoppwörter raus), Treffer zählen, beste `limit` Nachrichten (max. 200 Zeichen je Ausschnitt), **nur aus anderen Gesprächen als dem aktuellen**
- `export_text(path) -> None` – alles als lesbare .txt
- `wipe_everything()` – alle Tabellen leeren + `VACUUM` (wirklich weg von der Platte)
- `get_stat/set_stat` (für Phase 6)
Thread-Sicherheit: eigene Verbindung pro Aufruf (`with sqlite3.connect(path) as db:`) – einfach und sicher aus Worker-Threads.

## 2.2 Einbau in `agent_brain.py`
- `AgentBrain._on_done`: User-Text + Antwort speichern, wenn `privacy.save_chats` an.
- Prompt in `_chat_cli` ergänzen:
  - `WAS DU ÜBER {user} WEISST:` + alle Fakten (max. 30, neueste zuerst), nur wenn `privacy.remember` an.
  - `FRÜHERE GESPRÄCHE, DIE PASSEN KÖNNTEN:` + `relevant_snippets(text)`, nur wenn `privacy.use_history` an und es Treffer gibt.
- JSON-Protokoll erweitern: optionales Feld `"remember": ["kurzer Fakt", …]` und `"remember_dates": [{"text": "...", "date": "YYYY-MM-DD"}]`. In der ANTWORT-REGEL erklären: nur dauerhaft nützliche, **nicht sensible** Fakten (keine Passwörter, Gesundheit, Adressen, Kontonummern). Gespeicherte Fakten → Sprechblase zeigt kurz „Gemerkt! 📝“. `parse_cli_response` muss diese Felder robust ignorieren, wenn sie fehlen/kaputt sind.
- Offline-Befehle in `parse_offline` (nutzen die bestehende Sicherheitsabfrage für das Löschen!):
  - „was weißt du über mich“ → Liste der Fakten (oder „Noch nichts – erzähl mir was! 🐾“)
  - „vergiss, dass …“ → `forget_matching` (Bestätigung ja/nein)
  - „vergiss alles“ / „lösch meine daten“ → `wipe_everything` (Bestätigung ja/nein)
  - „zeig meine chats“ → öffnet „Meine Chats“
  Neue Tools dafür in `tools.py`: `forget_facts`, `wipe_my_data` (beide in `DANGEROUS_TOOLS`), `list_facts`.

## 2.3 Config (`config.DEFAULTS`)
```python
"privacy": {"save_chats": True, "remember": True, "use_history": True, "intro_shown": False},
```
Beim ersten Start (wenn `intro_shown` False) sagt die Figur in einer längeren Sprechblase:
„Kleiner Hinweis: Ich speichere unsere Chats und Dinge, die du mir erzählst, nur hier auf deinem PC 🔒 Rechtsklick → ‚Meine Daten‘ zeigt alles und löscht es mit einem Klick.“ → Flag setzen.

## 2.4 Fenster „📚 Meine Chats“ (`chat_history.py`, neu)
- QDialog im Stil von `settings_dialog.py`, ca. 820×560, Titel „📚 Meine Chats mit {Figurname}“.
- Oben: Suchfeld („Suchen … 🔍“, Live-Filter).
- Links: Liste der Gespräche als Karten (Datum „Heute 14:32“ / „Gestern“ / „12. Okt.“, Titel, Figur-Emoji).
- Rechts: Verlauf als Chat-Bubbles (User rechts in Rosa, Figur links in Grau mit Emoji), scrollbar, Text auswählbar.
- Buttons unten: „💬 Weiterreden“ (lädt die letzten 18 Nachrichten in `AgentBrain._history` und öffnet die Eingabe), „📤 Exportieren“ (QFileDialog → .txt), „🗑️ Gespräch löschen“ (Bestätigungs-Dialog im selben Stil).
- Leerzustand: großes Emoji + „Noch keine Chats – sag {Figurname} einfach Hallo! 👋“.

## 2.5 Fenster „🔒 Meine Daten“ (`my_data_dialog.py`, neu)
- Abschnitt **„Was {Figurname} über dich weiß“**: Liste der Fakten mit Datum, je ein 🗑️-Button; Leerzustand „Noch nichts gemerkt.“
- Abschnitt **Schalter**: „Chats speichern“, „{Figurname} darf sich Dinge merken“, „Frühere Chats nutzen, wenn sie zur Frage passen“.
- Große Buttons: **„🗑️ Alle Chats löschen“**, **„🧹 Alles vergessen“** (Fakten + Chats + Statistiken, `wipe_everything`), **„📤 Alles exportieren“**. Löschen immer mit Bestätigungsdialog („Wirklich alles vergessen? Das kann nicht rückgängig gemacht werden.“).
- **Info-Box (wörtlich sinngemäß, gut sichtbar):**
  > 🔒 Deine Daten bleiben auf diesem PC (`%APPDATA%\Mochi\mochi.db`). Die Entwickler von Desktop Cat bekommen nichts.
  > 🤖 Wenn du Kylie etwas fragst, schickt sie deine Frage, deine gemerkten Fakten und höchstens 3 passende Ausschnitte aus früheren Chats an Google Gemini – nur damit die Antwort besser passt.
  > ⚠️ Beim **kostenlosen** Gemini-Zugang darf Google gesendete Inhalte laut seinen Nutzungsbedingungen zur Verbesserung seiner Dienste verwenden und von Menschen prüfen lassen. Schreib deshalb keine Passwörter oder sehr privaten Dinge. Ohne Gemini-Key bleibt alles komplett offline.
- Erreichbar über: Rechtsklick-Menü „🔒 Meine Daten“, Tray-Menü, Button in den Einstellungen.

## 2.6 Menüs
Rechtsklick auf die Figur (`PetWindow.build_menu`) und Tray: „📚 Meine Chats“, „🔒 Meine Daten“ (weit oben, gut sichtbar).

## Tests (`tests/test_memory_store.py`)
Immer mit `tempfile`-DB: Nachrichten speichern + neues Gespräch nach 30 Min. (Zeit mocken), Suche, `relevant_snippets` (findet passendes, ignoriert Stoppwörter, max. 3, nicht aus aktuellem Gespräch), Fakten add/delete/forget_matching, `wipe_everything` → alle Tabellen leer, `export_text` enthält Inhalte, `parse_cli_response` mit/ohne `remember`-Feld, „vergiss alles“ erzeugt Rückfrage statt zu löschen.
