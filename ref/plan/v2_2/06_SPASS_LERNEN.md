# Phase 6 – Freundschaft, Fokus, Lernen, Fotobox, Haftnotizen

Alle Zähler/Daten in `MemoryStore` (`stats`- bzw. eigene Tabellen) → werden von „Alles vergessen“ mit gelöscht.

## 6.1 Freundschafts-Level ❤️
- Punkte: Gespräch +1 (max. 20/Tag), Leckerli +2 (max. 10/Tag), abgeschlossener Pomodoro +5, Quiz-Runde +3, Neugier-Frage beantwortet +3.
- Level-Schwellen: 0, 25, 75, 150, 300, 500, 800, 1200 (Level 1–8). Reine Funktion `level_for(points) -> (level, progress_0_1)`.
- Level-Up: Konfetti + „Level 3! Wir sind jetzt richtig gute Freunde, {user} 💖“ + Belohnung freigeschaltet: L2 `bow`, L3 `bandana`, L4 `scarf` (ganzjährig wählbar), L5 `party_hat`, L6 `sunglasses`-Trick, L7 `crown`, L8 „Goldener Glanz“ (glint-Effekt dauerhaft).
- Rechtsklick → „💖 Freundschaft“: Karte mit Herz-Leiste, Level, nächste Belohnung, freigeschaltete Accessoires zum An-/Ablegen (gewähltes Accessoire in Config `fun.worn`).

## 6.2 Fokus-Statistik ⏱️
- Pomodoros zählen (`set_timer` mit Label „Pomodoro Fokus“ abgeschlossen) in Tabelle `focus(date, minutes, count)`.
- Rechtsklick → „📊 Fokus-Statistik“: Karte mit heute / diese Woche (7 Balken, einfache QPainter-Balken im App-Stil), Serie („3 Tage in Folge! 🔥“), Lob in Figur-Stimme.

## 6.3 Lern-Quiz 📚
- Befehle: „frag mich Vokabeln ab“, „quiz starten“, „lernkarten“.
- Lernkarten-Sets in neuer Tabelle `cards(id, deck, front, back, box INTEGER, due REAL)` (einfaches Leitner-System: richtig → Box+1, falsch → Box 1).
- Kartenverwaltung in einem Fenster „📚 Lernkarten“: Decks anlegen, Karten hinzufügen (Vorderseite/Rückseite), Import aus Text („Wort = Übersetzung“ pro Zeile), löschen.
- Mit Gemini-Key zusätzlich: „Kylie, mach mir 10 Lernkarten zu Photosynthese“ → Gemini liefert JSON-Liste → Vorschau → Speichern.
- Abfrage-Modus: Figur stellt die Frage in der Sprechblase, User tippt die Antwort in die Eingabe; Vergleich offline (Groß/Klein, Umlaute, Leerzeichen egal, kleine Tippfehler mit `difflib.SequenceMatcher` ≥ 0.85 = „fast richtig“). Mit Key optional tolerantere Bewertung. Am Ende: „8 von 10 richtig! 🌟“, Freundschaftspunkte.
- Kylie merkt sich schwierige Karten (Box 1) und schlägt später vor: „Wollen wir die 5 kniffligen Wörter nochmal üben?“

## 6.4 Fotobox 📸
- Rechtsklick → „📸 Foto mit {Figurname}“: 3-2-1-Countdown in der Sprechblase, Figur macht eine Pose (dance/cool/happy zufällig), Bildschirmfoto des Monitors **mit** Figur, dazu ein hübscher Rahmen (abgerundete Ecken, Polaroid-Rand, Datum + „Desktop Cat 🐾“-Stempel, kleine Sticker-Herzen) per QPainter.
- Speichern in `Bilder\Desktop Cat\Foto_YYYY-MM-DD_HH-MM-SS.png`, Tray-Meldung „Foto gespeichert!“ mit Klick → Ordner öffnen.
- Hinweis-Sprechblase vor dem Foto: „Achtung, der ganze Bildschirm ist auf dem Foto 📸“.

## 6.5 Haftnotizen 📝
- Befehl: „merk dir: Mama anrufen“, „notiz: Hausübung Mathe“, oder Rechtsklick → „📝 Neue Haftnotiz“.
- Kleine, rahmenlose Notiz-Fenster (gelb/rosa/mint, abgerundet, leichter Schatten, handschriftartige Schrift falls Segoe Print vorhanden, sonst Segoe UI), stapeln sich am rechten Bildschirmrand.
- Animation: Figur läuft/fliegt zur Stelle und „klebt“ die Notiz hin.
- Pro Notiz: Häkchen ✔ (erledigt → Notiz flattert weg, Figur freut sich), ✏️ bearbeiten, verschieben per Drag (Position gespeichert).
- Gespeichert in Tabelle `notes(id, text, color, x, y, done)`, bleiben nach Neustart. „Alles vergessen“ löscht sie mit.
- Die bestehende Notizen.txt-Funktion (`manage_notes`) bleibt unverändert.

## Config
```python
"fun": {"weather_outfits": True, "pc_fever": True, "worn": ""},
```

## Tests (`tests/test_fun.py`)
`level_for`, Punkte-Tageslimits, Leitner-Logik, Antwortvergleich (Umlaute/Tippfehler), Lernkarten-Import aus Text, Gemini-Lernkarten-JSON-Parser, Fokus-Serie (Tage in Folge), Fotobox-Dateiname/Rahmen auf einem Test-QImage, Notizen speichern/laden/erledigen (Temp-DB).
