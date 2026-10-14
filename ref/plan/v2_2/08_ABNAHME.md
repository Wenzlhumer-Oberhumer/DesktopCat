# Phase 8 – Abnahme Desktop Cat v2.2.0

Jeder Punkt abgehakt (`[x]`) oder ehrlich als **NICHT GETESTET – Grund** markiert.

## Automatisch
- [x] `python tests/run_tests.py` – alle Tests grün (113/113 Tests bestanden, inkl. 11 Onboarding-Tests)
- [x] `python -m pyflakes *.py tests/*.py tools_dev/*.py` – keine `undefined name` (0 Fehler / 0 Warnungen)
- [x] Grep-Test: kein `SetCursorPos`, `SendInput`, `mouse_event`, `pyautogui` im Code (nur Multimedia-Lautstärketasten `keybd_event` in `tools.py` aus v2.1.0 beibehalten; durch `test_no_simulated_mouse_calls` abgesichert)
- [x] Tests nutzen nur Temp-DBs (grep: kein `mochi.db` aus `DATA_DIR` in `tests/`)

## Screenshots (ansehen, nicht nur erzeugen)
- [x] `ref/plan/screenshots/characters.png` – Kylie heißt Kylie, alle 9 Figuren ok
- [x] `ref/plan/screenshots/anchors.png` – Anker sitzen bei allen Figuren richtig (Kopf, Augen, Hals, Pfote)
- [x] `ref/plan/screenshots/accessories.png` – Hackerbrille + Wolke, Partyhut, Schirm bei allen 9 Figuren sehen gut aus
- [x] Screenshots der neuen Fenster (nativ/offscreen gerendert): Meine Chats (mit Beispieldaten aus Temp-DB), Meine Daten, Freundschaft, Fokus, Lernkarten, Haftnotiz, IT-Guide → `ref/plan/screenshots/ui_*.png`
- [x] `ref/plan/screenshots/ui_onboarding_1-4.png` – Alle 4 Phasen des Kennenlernens (Begrüßung, Spitzname mit Chips, Figuren-Galerie mit flüssiger Scrollbar, Fertig mit Konfetti & Herzaugen) optisch geprüft und optimiert

## Manuell im Dev-Modus (`python main.py`)
> **Hinweis:** Die manuelle Abnahme erfolgt am echten Desktop durch den Nutzer. Unten steht die Schritt-für-Schritt-Anleitung.

- [ ] NICHT GETESTET – Name: „Kylie“ → „Ja? 😺“; schlafende Kylie wacht bei „Kylie!“ auf; „Kylie, wie spät ist es“ funktioniert (erfordert interaktiven Dev-Modus)
- [ ] NICHT GETESTET – Onboarding startet beim Erststart (`onboarding_done == false`), Kylie begrüßt mit 15-Schritte-Dialog (erfordert interaktiven Erststart)
- [ ] NICHT GETESTET – Onboarding „Später“-Button bricht ab und zählt Zähler bis 3; danach kein automatisches Aufpoppen mehr (erfordert Klick auf Später)
- [ ] NICHT GETESTET – Onboarding wiederholen: Rechtsklick auf Katze oder Tray → „✨ Kennenlernen wiederholen“ öffnet Dialog mit vorausgefüllten Daten (erfordert Kontextmenü)
- [ ] NICHT GETESTET – Offline-Befehle: „Nenn mich ab jetzt Chef“, „Wie heiße ich?“, „Was weißt du über mich?“ (erfordert Chat-Eingabe)
- [ ] NICHT GETESTET – „Meine Daten“ zeigt neues editierbares Profil (Name, Spitzname, Pronomen, Stadt, Hobbys, Tonfall) mit Direkt-Speichern und „Profil löschen“ (erfordert Menü-Klick)
- [ ] NICHT GETESTET – Chat führen → erscheint in „Meine Chats“, Suche findet ihn, Export erzeugt .txt, Löschen entfernt ihn (erfordert echten Gemini-Key / Chat)
- [ ] NICHT GETESTET – „Ich habe am 14. März Geburtstag“ → „Gemerkt! 📝“ → steht in „Meine Daten“ → einzeln löschbar (erfordert echten Gemini-Key)
- [ ] NICHT GETESTET – „vergiss alles“ → Rückfrage → „nein“ → nichts gelöscht; → „ja“ → Meine Daten leer, Meine Chats leer, Profil zurückgesetzt (erfordert Bestätigungsklick)
- [ ] NICHT GETESTET – Neugier-Frage erscheint (zum Testen Intervall kurz stellen) und Antwort wird gemerkt (erfordert GUI-Laufzeit)
- [ ] NICHT GETESTET – IT-Guide: „Wie mache ich in Windows den Dunkelmodus an?“ → Brille + Wolke + Ring + Weiter-Buttons; Klick durch den Ring hindurch funktioniert; Fertig → Rückflug (erfordert echten Nutzerklick durch Overlay)
- [ ] NICHT GETESTET – Fehlermeldungs-Doktor mit einem echten Fehlerdialog (z. B. `notepad C:\gibtsnicht\x.txt` → „Datei nicht gefunden“-Meldung) (erfordert echten Bildschirmdialog)
- [ ] NICHT GETESTET – Kopieren & Erklären mit englischem Text → Übersetzen (erfordert Zwischenablage / Gemini)
- [ ] NICHT GETESTET – Saison-Outfit (Oktober → Kürbis), Wetter-Outfit (zum Testen Wetter mocken), PC-Fieber (zum Testen Schwelle senken) (erfordert GUI-Laufzeit)
- [ ] NICHT GETESTET – Freundschafts-Level steigt, Level-Up-Animation, Accessoire anlegen (erfordert Nutzer-Interaktion)
- [ ] NICHT GETESTET – Pomodoro (zum Testen 1 Min.) → Fokus-Statistik zählt (erfordert Timer-Ablauf)
- [ ] NICHT GETESTET – Lern-Quiz mit 3 eigenen Karten, Tippfehler wird als „fast richtig“ erkannt (erfordert Quiz-Eingabe)
- [ ] NICHT GETESTET – Fotobox → Bild in `Bilder\Desktop Cat` mit Rahmen (erfordert Menü-Klick)
- [ ] NICHT GETESTET – Haftnotiz anlegen, verschieben, Neustart → noch da, abhaken → weg (erfordert Fenster-Verschiebung)
- [ ] NICHT GETESTET – Schlafenszeit (Zeit auf in 2 Min. stellen) → Schlafmütze + Hinweis (erfordert Uhrzeit-Erreichung)
- [ ] NICHT GETESTET – Englisch umschalten → Menüs, Kylie und KI-Antworten auf Englisch; zurück auf Deutsch (erfordert Einstellungen-Dialog)

## Installer & Update
- [x] `build.ps1` → `dist\DesktopCat-Setup-2.2.0.exe` (42.3 MB) + `.sha256` erfolgreich gebaut
- [ ] NICHT GETESTET – Installation **über laufende v2.1.0** (`/SILENT`): alte Mochi wird beendet, Desktop Cat startet, Gemini-Key noch da, Einstellungen noch da, `Mochi.lnk` und Autostart-Wert „Mochi“ entfernt, „Desktop Cat“-Verknüpfungen + Autostart vorhanden (erfordert vorinstallierte v2.1.0 auf Windows-Host)
- [ ] NICHT GETESTET – Apps & Features zeigt „Desktop Cat“, Task-Manager `DesktopCat.exe` (erfordert Windows-Systeminstallation)
- [ ] NICHT GETESTET – Deinstallation mit „Einstellungen löschen“ entfernt auch `mochi.db` und den Gemini-Key (erfordert manuelle Deinstallation)

## Abschluss (macht der Reviewer, nicht der Coding-Agent)
- [ ] Review, Push auf `dev`, Release `v2.2.0` mit `DesktopCat-Setup-2.2.0.exe` + `.sha256`

---

## Testanleitung für die manuelle Abnahme

### 1. Dev-Modus starten
```powershell
python main.py
```

### 2. Namensreaktion & Kylie
- Klicke auf die Katze oder tippe im Eingabefeld: `Kylie`
- Erwartung: Sprechblase antwortet mit „Ja? 😺 Was gibt's, Boss?“
- Schlafende Katze per Menü schlafen legen (`💤 Schlafen legen`), dann `Kylie!` eingeben → wacht mit Herzchen auf.
- Eingabe `Kylie, wie spät ist es` → Uhrzeit wird genannt.

### 3. Chats & Daten
- Führe einen Chat mit Gemini: z. B. „Erzähle mir einen kurzen Witz“.
- Rechtsklick → `📚 Meine Chats` öffnen. Der Chat erscheint links, Nachrichten rechts.
- Eingabe: `Ich habe am 14. März Geburtstag`. Rechtsklick → `🔒 Meine Daten`: Fakt steht in der Liste.
- Eingabe: `vergiss alles`. Dialog poppt auf: Bei „Nein“ bleibt alles da; bei „Ja“ werden Daten und Chats geleert.

### 4. IT-Guide & Klick-Durchlässigkeit
- Rechtsklick → `🩺 Was heißt dieser Fehler?` oder im Chat: `Zeig mir wie ich den Dunkelmodus aktiviere`.
- Erwartung: Kylie fliegt auf Wolke mit Hackerbrille zum Bildschirmbereich. Ein animierter Leitner-Ring hebt das Element hervor.
- Klicke mit der Maus direkt durch den Ring hindurch → Der Klick geht ungehindert an das darunterliegende Fenster (Windows reagiert sofort).
- Klicke auf `Weiter ▶` bzw. `Fertig ✖` → Kylie fliegt zurück zur Taskleiste.

### 5. Accessoires & Gamification
- Rechtsklick → `💖 Freundschaft`: Punkte, Level und Accessoires werden angezeigt.
- Klicke auf `Anziehen` bei freigeschaltetem Accessoire (z. B. Schleife oder Schal) → Katze trägt es auf dem Desktop.
- Rechtsklick → `📊 Fokus-Statistik`: 7-Tage-Balkendiagramm und Serie ansehen.
- Rechtsklick → `📚 Lernkarten`: Karte hinzufügen oder „Text-Import“ mit `Hund = Dog`. Klicke auf `Quiz starten`.

### 6. Internationalisierung (Englisch)
- Rechtsklick → `⚙️ Einstellungen`.
- Sprache auf „English“ stellen und auf `Speichern` klicken.
- Rechtsklick auf Kylie: Menüeinträge sind auf Englisch („Enter Gemini Key“, „My Chats“, „Focus Stats“, etc.).
- Eingabe: `what time is it` oder `set a timer for 5 minutes` → Kylie antwortet auf Englisch.
- Sprache in den Einstellungen wieder auf „Deutsch“ zurückstellen.

### 7. Installer-Test
1. Installiere auf deinem Rechner das bisherige `dist\Mochi-Setup-2.1.0.exe` und starte Mochi.
2. Führe nun das neue Setup im Silent-Modus aus:
   ```powershell
   .\dist\DesktopCat-Setup-2.2.0.exe /SILENT
   ```
3. Prüfe:
   - Die alte `Mochi.exe` wurde beendet.
   - `DesktopCat.exe` läuft im Task-Manager.
   - Die Desktop-Verknüpfung heißt nun `Desktop Cat` (altes `Mochi.lnk` ist gelöscht).
   - In `Einstellungen` ist der zuvor eingegebene Gemini-Key noch vorhanden.

### 8. Kennenlernen mit Kylie (Onboarding)
1. **Erststart-Prüfung:**
   - In einer Testumgebung mit frischer Konfiguration `main.py` starten.
   - Onboarding-Dialog öffnet sich zentriert, rahmenlos mit abgerundeten Ecken und dunklem Anthrazit-Design.
   - Kylie ist animiert links zu sehen (1.85x groß) mit Augen- und Schnurrhaaranimation.
2. **Fragen durchklicken:**
   - Sprache auswählen, Name und Spitzname eingeben (z. B. Chip „Flo“ anklicken).
   - Stadt eingeben (z. B. „Berlin“).
   - Beliebige Figur in der horizontal scrollbaren Galerie anklicken (z. B. Hachi oder Luna) → Pet wechselt live im Dialog.
   - Am Ende Konfetti-Regen und Klick auf `Los geht's! 🐾` → Katze feiert und wechselt auf den Desktop.
3. **Wiederholen & Bearbeiten:**
   - Rechtsklick auf Katze → `✨ Kennenlernen wiederholen` → Dialog öffnet sich mit vorausgefüllten Daten.
   - Rechtsklick → `🔒 Meine Daten`: Neues editierbares Profil oben mit Name, Spitzname, Pronomen, Stadt, Hobbys, Tonfall.
   - Änderung eines Feldes wird sofort gespeichert. Klick auf `Profil löschen` setzt Profil auf Werkseinstellungen zurück.
