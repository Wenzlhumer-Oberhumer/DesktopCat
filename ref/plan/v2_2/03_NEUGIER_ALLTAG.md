# Phase 3 – Kylie interessiert sich für dich + Alltag

## 3.1 Neugier-Fragen
- Neuer Timer in `main.py` (Muster `_schedule_wellbeing`): alle 2–4 h zufällig, **max. 2 Fragen pro Tag** (Zähler in `stats`), nicht nachts (`is_night`), nicht im Vollbild, nicht wenn eine Aufgabe/Eingabe läuft, nur wenn `privacy.remember` an.
- Mit Gemini-Key: kurzer Prompt („Stell {user} eine kurze, freundliche, neugierige Frage über sein Leben/Hobbys/Tag. Beziehe dich wenn möglich auf diese Fakten: …“). Ohne Key: Liste von 20 Fragen pro Figurtyp (Katze/Hund/Fantasy) in `pet_sprites.CHARACTERS[...]["curious_questions"]` oder einer gemeinsamen Liste.
- Die Frage öffnet die Sprechblase im **Antwort-Modus** (vorhandenes `open_input(reply_mode=True)`), die Frage kommt in den Verlauf (`record_assistant_message`) → Antwort läuft normal durchs JSON-Protokoll und kann `remember` auslösen.
- Folge-Fragen: Fakten mit `due_date` (z. B. Prüfung) → am Tag danach: „Wie lief die Prüfung gestern? 🍀“.

## 3.2 Erinnerungen aus Fakten
Fakten mit `due_date`: am Vortag 18 Uhr und am Tag selbst morgens eine Sprechblase („Morgen ist deine Prüfung – du schaffst das! 💪“). Pro Fakt und Tag nur einmal (`stats`).

## 3.3 Guten-Morgen-Briefing
Beim ersten Start/Aufwachen des PCs **nach 5 Uhr** an einem neuen Tag (`stats["last_briefing"]`):
- Wetter (vorhandenes `tools.get_weather` im Worker-Thread), laufende Timer, heutige/morgige Fakten-Termine, ein Motivationsspruch in Figur-Stimme.
- Als freundliche Karte (`FloatingCard`-Stil) neben der Figur, 12 s sichtbar, Klick schließt.
- Schalter `daily.briefing` (Default an).

## 3.4 Geburtstag
- Sagt der User seinen Geburtstag („ich habe am 14. März Geburtstag“) → Fakt mit `kind="birthday"`, `due_date` = nächstes Vorkommen (jährlich wiederholen).
- Am Geburtstag: Partyhut (Accessoire aus Phase 4), Konfetti, Musiknoten, „Alles Gute zum Geburtstag, {user}! 🎂🎉“ beim Start und einmal mittags.

## 3.5 Schlafenszeit-Erinnerung
- Config `daily.bedtime = "23:00"` (leer = aus), einstellbar in den Einstellungen (Zeitfeld).
- Zur Uhrzeit: Figur gähnt, setzt Schlafmütze auf (Accessoire Phase 4), „Es ist schon spät, {user} – Zeit fürs Bett? 😴“. Einmal pro Abend; wenn der User weiterarbeitet, nach 30 Min. noch einmal sanft, dann nicht mehr.

## Config (`config.DEFAULTS`)
```python
"daily": {"briefing": True, "bedtime": "23:00", "curious": True},
```

## Tests (`tests/test_daily.py`)
Reine Funktionen auslagern und testen: `should_ask_curious(now, stats, cfg)`, `next_birthday(day, month, today)`, `due_reminders(facts, now)`, `should_brief(now, last_briefing)`, `bedtime_due(now, bedtime, last_shown)`. Zeit immer übergeben, nie `datetime.now()` in den Funktionen selbst.
