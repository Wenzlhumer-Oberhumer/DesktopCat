# Phase 8 – Abnahme Desktop Cat v2.2.0

Jeden Punkt abhaken (`[x]`) oder ehrlich als **NICHT GETESTET – Grund** markieren. Nichts abhaken, was nur im Code angesehen wurde.

## Automatisch
- [ ] `python tests/run_tests.py` – alle alten (43) + neuen Tests grün
- [ ] `python -m pyflakes *.py tests/*.py tools_dev/*.py` – keine `undefined name`
- [ ] Grep-Test: kein `SetCursorPos`, `SendInput`, `mouse_event`, `keybd_event`, `pyautogui` im Code
- [ ] Tests nutzen nur Temp-DBs (grep: kein `mochi.db` aus `DATA_DIR` in `tests/`)

## Screenshots (ansehen, nicht nur erzeugen)
- [ ] `ref/plan/screenshots/characters.png` – Kylie heißt Kylie, alle 9 Figuren ok
- [ ] `ref/plan/screenshots/anchors.png` – Anker sitzen bei allen Figuren richtig
- [ ] `ref/plan/screenshots/accessories.png` – Hackerbrille + Wolke, Partyhut, Schirm bei allen 9 Figuren sehen gut aus
- [ ] Screenshots der neuen Fenster (offscreen gerendert): Meine Chats (mit Beispieldaten aus Temp-DB), Meine Daten, Freundschaft, Fokus, Lernkarten, Haftnotiz → `ref/plan/screenshots/ui_*.png`

## Manuell im Dev-Modus (`python main.py`)
- [ ] Name: „Kylie“ → „Ja? 😺“; schlafende Kylie wacht bei „Kylie!“ auf; „Kylie, wie spät ist es“ funktioniert
- [ ] Begrüßung mit Konfetti beim ersten Start nach Update, danach nicht mehr
- [ ] Chat führen → erscheint in „Meine Chats“, Suche findet ihn, Export erzeugt .txt, Löschen entfernt ihn
- [ ] „Ich habe am 14. März Geburtstag“ → „Gemerkt! 📝“ → steht in „Meine Daten“ → einzeln löschbar
- [ ] „vergiss alles“ → Rückfrage → „nein“ → nichts gelöscht; → „ja“ → Meine Daten leer, Meine Chats leer
- [ ] Neugier-Frage erscheint (zum Testen Intervall kurz stellen) und Antwort wird gemerkt
- [ ] IT-Guide: „Wie mache ich in Windows den Dunkelmodus an?“ → Brille + Wolke + Ring + Weiter-Buttons; Klick durch den Ring hindurch funktioniert; Fertig → Rückflug
- [ ] Fehlermeldungs-Doktor mit einem echten Fehlerdialog (z. B. `notepad C:\gibtsnicht\x.txt` → „Datei nicht gefunden“-Meldung)
- [ ] Kopieren & Erklären mit englischem Text → Übersetzen
- [ ] Saison-Outfit (Oktober → Kürbis), Wetter-Outfit (zum Testen Wetter mocken), PC-Fieber (zum Testen Schwelle senken)
- [ ] Freundschafts-Level steigt, Level-Up-Animation, Accessoire anlegen
- [ ] Pomodoro (zum Testen 1 Min.) → Fokus-Statistik zählt
- [ ] Lern-Quiz mit 3 eigenen Karten, Tippfehler wird als „fast richtig“ erkannt
- [ ] Fotobox → Bild in `Bilder\Desktop Cat` mit Rahmen
- [ ] Haftnotiz anlegen, verschieben, Neustart → noch da, abhaken → weg
- [ ] Schlafenszeit (Zeit auf in 2 Min. stellen) → Schlafmütze + Hinweis
- [ ] Englisch umschalten → Menüs, Kylie und KI-Antworten auf Englisch; zurück auf Deutsch

## Installer & Update
- [ ] `build.ps1` → `dist\DesktopCat-Setup-2.2.0.exe` + `.sha256`
- [ ] Installation **über laufende v2.1.0** (`/SILENT`): alte Mochi wird beendet, Desktop Cat startet, Gemini-Key noch da, Einstellungen noch da, `Mochi.lnk` und Autostart-Wert „Mochi“ entfernt, „Desktop Cat“-Verknüpfungen + Autostart vorhanden
- [ ] Apps & Features zeigt „Desktop Cat“, Task-Manager `DesktopCat.exe`
- [ ] Deinstallation mit „Einstellungen löschen“ entfernt auch `mochi.db` und den Gemini-Key

## Abschluss (macht der Reviewer, nicht der Coding-Agent)
- [ ] Review, Push auf `dev`, Release `v2.2.0` mit `DesktopCat-Setup-2.2.0.exe` + `.sha256`
