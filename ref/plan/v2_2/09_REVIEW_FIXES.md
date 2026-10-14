# Review v2.2 (Claude, 14.10.2026) – Fix-Runde für den Coding-Agent

## Geprüft und in Ordnung ✅
- 8 Phasen-Commits, **101/101 Tests grün**, `pyflakes` sauber, keine neuen Pakete, kein `SendInput/SetCursorPos/pyautogui`.
- **Echtes Update v2.1 → v2.2 auf dem Entwickler-PC**: `Mochi.exe` + Autostart „Mochi“ + `Mochi.lnk` entfernt, `DesktopCat.exe` läuft, Verknüpfungen „Desktop Cat“, Apps & Features „Desktop Cat Version 2.2.0“, **Gemini-Key und Einstellungen erhalten**.
- Datenschutz-Logik: Schalter `save_chats` / `remember` / `use_history` greifen, max. 3 Ausschnitte, Regel gegen sensible Fakten im Prompt, `wipe_everything` leert alle 9 Tabellen + `VACUUM`, Deinstallation löscht DB + Key.
- Namensreaktion, „vergiss alles“ → Rückfrage-Tool, englischer Offline-Parser (Zeit, Timer, Wetter, forget everything).
- Accessoires sitzen bei allen 9 Figuren (`accessories.png`).

## Muss behoben werden ❌

### F1 – Einheitliches Design (wichtigster Punkt)
`ui_friendship.png`, `ui_focus.png`, `ui_flashcards.png` sind **hell mit Lila/Indigo** – Plan-Regel war: alle neuen Fenster im dunklen Stil von `settings_dialog.py` (Hintergrund `#26282C`, Karten `#33353B`, Akzent `#FF8FB1`, Text `#F2F3F5`, Segoe UI, Radius 10–12 px). Gilt auch für das Quiz-Fenster und alle weiteren Dialoge aus `fun_dialogs.py`.
- Balken im Fokus-Diagramm in Rosa-Verlauf statt Indigo, Kärtchen „Heute“ / „Serie“ als dunkle Karten mit farbigem Akzent.
- Lernkarten-Tabelle: der **schwarze Balken links (vertikaler Header)** muss weg (`verticalHeader().setVisible(False)` oder passend stylen), Tabelle dunkel, Zeilen abwechselnd leicht heller.
- Ein gemeinsames Stylesheet verwenden (z. B. `STYLE` aus `settings_dialog.py` importieren und ergänzen) statt pro Fenster neu.

### F2 – „Meine Daten“
- Die **Datenschutz-Box ist abgeschnitten** („… Schreib deshalb keine Passwörter“ – Rest fehlt). Der komplette Text muss sichtbar sein (Höhe an Inhalt anpassen bzw. Fenster/Box scrollbar). Das ist der wichtigste Text des Fensters.
- Die Löschen-Buttons zeigen ein kaputtes Symbol (sieht aus wie eine Kette). Ein Icon verwenden, das unter Windows sicher rendert (`"🗑️"` inkl. U+FE0F, oder Text „Löschen“ / „✕“), mit Tooltip „Diesen Fakt löschen“.
- Fakten-Anzeige: „Geburtstag am 14. März (Frist: 03-14)“ → menschlich: „🎂 Geburtstag am 14. März“; Termine: „📅 Prüfung · 20. Okt.“. Kein „Frist“, kein ISO-Datum.

### F3 – „Meine Chats“
- Proportionen umdrehen: Gesprächsliste links schmal (~35 %), Verlauf rechts breit (~65 %).
- Bubbles: **User rechts (Rosa), Figur links (Grau, mit Figur-Emoji)** – aktuell stehen beide rechts.
- Bubble-Breite max. ~70 % der Verlaufsbreite, Text umbrechen.

### F4 – Wolke
Die Wolke ist eine flache weiße Scheibe („Teller“). Plan: **fluffige Lakitu-Wolke** – mehrere überlappende Kreise (oben hügelig), weiße Füllung mit zartblauem Rand/Schatten unten, kleines freundliches Gesicht (zwei Punkt-Augen, Lächeln), sanftes Wippen. Neu rendern (`accessories.png`) und ansehen.

### F5 – IT-Guide-Optik prüfbar machen
Es gibt keinen Screenshot vom Guide. Ergänze in `tools_dev/save_screenshots.py` ein Bild `ref/plan/screenshots/ui_guide.png`: Fake-Hintergrund (z. B. grau mit einem Button „Einstellungen“), Overlay-Ring + Label „🖱️ Linksklick“ + Pfeil, Kylie mit Hackerbrille auf der Wolke daneben, Sprechblase mit „Weiter ▶ / Nochmal 🔁 / Fertig ✖“. Ansehen und schön machen.

### F6 – Kleinkram
- „Ich bin Kylie, deine verschmuste Glückskatze 🐾! 🐾“ → doppeltes Emoji/Satzzeichen entfernen (Vorstellungs-Text in `agent_brain.py`).
- Smoke-Tests nicht mehr über `import main` mit Konsolenausgabe ins echte `%APPDATA%\Mochi\buddy.log` schreiben lassen (das Log enthält jetzt Test-Tracebacks wie `config.load_config`). Für Tests/Smoke-Skripte `stdout` nicht umleiten bzw. Temp-Log nutzen.
- Keine gebaute `dist\DesktopCat\DesktopCat.exe` direkt starten (sie hat sich mit dem `dist`-Pfad in den Autostart eingetragen). Wenn nötig, nur Dev-Modus (`python main.py`) verwenden.

### F7 – Ehrlicher Bericht
Der letzte Bericht nannte Dinge, die es nicht gibt: Datei `doctor_dialog.py`, „OCR/Tesseract“, „Windows Vision Fallback“, `gemini.ask_image`, „Leitner-Klickring“. Bitte nur berichten, was im Code existiert.

## Vorgehen
Alle Fixes in **einem** Commit `Phase 9: Review-Fixes (Design, Meine Daten, Chats, Wolke)` mit `Co-Authored-By: Gemini <noreply@google.com>`. Danach: Tests + pyflakes grün, **alle** Screenshots neu erzeugen (`characters`, `accessories`, `ui_*` inkl. neuem `ui_guide.png`) und ansehen. Nicht pushen, nicht bauen, kein Release.
