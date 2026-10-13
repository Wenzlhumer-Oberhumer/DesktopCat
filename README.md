# 🐾 Mochi – Dein autonomer AI Desktop Buddy für Windows

**Mochi** ist ein vollfunktionsfähiges, extrem niedliches Desktop-Pet für Windows. Er läuft selbstständig auf deiner Taskleiste herum, reagiert auf Klicks & Drag-and-Drop und führt per **Cloud-KI** (Gemini / OpenAI) oder **regelbasiertem Offline-Parser** echte Windows-Aktionen aus.

---

## ✨ Features

- **🐾 100 % Transparentes Always-on-Top Fenster:**
  - Kein störender Rahmen, keine Einträge in Alt-Tab oder Taskleiste (`Qt.WindowType.Tool`).
  - Echte Desktop-Physik: Schmiegt sich an die Oberkante der Windows-Taskleiste an.
  - Interaktives **Drag & Drop**: In der Luft halten (wackelt überrascht), loslassen (fällt mit weichem Squish & Mini-Bounce auf die Taskleiste zurück).
  - Autonomes Wandern: Alle 5–10 Sekunden entscheidet das Pet zufällig, ob es stehen bleibt, ein Nickerchen macht (`SLEEP`) oder neugierig spazieren geht.

- **🎨 Prozedurales Kawaii-Rendering & Neue Animationen:**
  - Ohne externe Bilddateien sofort startklar: Zeichnet eine handanimierte Kawaii-Katze ("Mochi") mit QPainter.
  - Große leuchtende Anime-Augen, Blickverfolgung zur Maus, Schnurrhaare, Tabby-Streifen, Halsband mit Glöckchen, Pfotenballen und schwingender Schwanz.
  - **Zustände & Animationen:**
    - `IDLE`: Ruhiges Atmen, Blinzeln & Ohrenzucken.
    - `DANCE`: Rhythmischer Tanz mit Ohrenwackeln, schwingenden Pfoten & bunten Vektor-Musiknoten (`♪`, `♫`, `♬`).
    - `COOL`: Coole schwarze Sonnenbrille mit Goldfassung, Star-Twinkle (`✦`) & lässiger Pose.
    - `WORKING`: Setzt eine Brille auf und tippt eifrig auf einem leuchtenden Mini-Laptop mit Denkblase.
    - `SUCCESS`: Freudentanz, Jubelsprünge & goldene Funkelsterne (`Sparkles`).
    - `SLEEP`: Zusammengerollt mit schwebenden 'Z's.
    - `DRAGGED`: Schreck-Schweißtropfen und zappelnde Pfötchen.
    - `SAD`: Tränchen bei Fehlern.
    - **Klick-Reaktion**: Echte Schnurr-Vibration, leuchtende Herzchen-Augen, Hüpfer & aufsteigende Herzchen (`Hearts`).
  - **Stufenloses Zoomen:** Mit **`Strg + Mausrad`** (oder `Shift + Mausrad`) direkt am Bildschirm vergrößern oder verkleinern (60 % bis 250 %)!

- **💬 Elegante Dark-Mode UI & Reiches Kontextmenü:**
  - Schwebende Sprechblase mit animiertem Fade-In/Fade-Out und Pfeil, der auf den Kopf des Pets zeigt.
  - Schlanke Eingabeleiste ("Was soll ich tun, Boss? 🐾"): Öffnet sich per **Doppelklick**, per globalem Hotkey (**`Strg + Alt + P`**), über das Tray-Icon oder Rechtsklick-Menü.
  - **Rechtsklick-Menü mit Schnellzugriffen:**
    - *✨ Tricks & Spaß:* Tanzen, Coole Katze, Schlafen legen, Aufwecken.
    - *⚡ Schnell-Tools:* Screenshot, Desktop aufräumen, Datum & Uhrzeit, System-Status, Lauter/Leiser/Mute, Musik Play/Pause.
    - *📂 Ordner öffnen:* Downloads, Dokumente, Desktop, Papierkorb.

- **⚡ 20 Echte Windows-Aktionen (`tools.py`):**
  1. **Word-Dokumente direkt erstellen (`create_file`):** Erstellt formatiertes `.docx` (Überschriften, Listen, Text) direkt am Desktop – ohne dass Word geöffnet werden muss und ohne Zwischenablage!
  2. **PowerPoint-Präsentationen erstellen (`create_file`):** Erstellt native `.pptx` Präsentationen am Desktop.
  3. **Dateien autonom löschen (`delete_file`):** Sucht und löscht Dateien (z. B. "lösche die PowerPoint am Desktop") vollautomatisch ohne lästige Explorer-Auswahldialoge!
  4. **Dateiinhalte lesen (`read_file_content`):** Liest Texte aus Word, PowerPoint, Textdateien oder Code direkt vor.
  5. **Bildschirm beobachten & Coden verstehen (`inspect_screen`):** Multimodale Gemini-Vision-Analyse & aktive Z-Order Fenstererkennung.
  6. **PowerShell-Befehle (`execute_powershell`):** Führt beliebige PowerShell- und Systembefehle direkt aus.
  7. **Word zu PDF (`convert_word_to_pdf`):** Nativ via Word COM-Automation oder Dialog.
  8. **Desktop aufräumen & rückgängig machen (`organize_desktop`, `undo_organize_desktop`):** Automatische Ordnerstrukturierung.
  9. **Screenshot (`take_screenshot`):** Ganzer Desktop wird per Tastendruck/Befehl auf dem Desktop gespeichert.
  10. **Lautstärke (`control_volume`):** Lauter, leiser oder stumm schalten (native Windows Virtual Keys).
  11. **Mediensteuerung (`media_control`):** Play/Pause, nächster Song, vorheriger Song, Stopp.
  12. **Notizen (`manage_notes`):** Schnelle Notizen hinzufügen, auflisten oder löschen in `Desktop/Notizen.txt`.
  13. **Zwischenablage (`clipboard_action`):** Text in Windows-Clipboard schreiben oder auslesen.
  14. **Taschenrechner (`calculate`):** Sichere mathematische Ausdrücke berechnen (z. B. `15 * 4`).
  15. **Uhrzeit & Datum (`show_time_and_date`):** Genaue Uhrzeit, Wochentag und deutsches Datum.
  16. **Ordner öffnen (`open_folder`):** Downloads, Dokumente, Desktop, Bilder, Musik, Papierkorb oder Laufwerk C:.
  17. **Programme starten (`open_program`):** Beliebige Windows-Apps oder Web-URLs.
  18. **Dateisuche (`find_files`):** Sucht Dateien und öffnet/markiert sie direkt im Explorer.
  19. **System-Check (`system_info`):** Akku, Ladestand, Festplattenkapazitäten.
  20. **Web-Recherche (`web_search`):** DuckDuckGo / Wikipedia / Web-Suche nach Wissen & Wetter.

- **👁️ Proaktiver Coding- & Screen-Companion:**
  - Erkennt in Echtzeit, in welchem Programm du arbeitest (z. B. **Angular**, **Python**, **React**, **TypeScript**, IDE oder Browser).
  - Gibt unaufdringliche, charmante Tipps & Feedback (z. B. *"Schön, was du da in Angular programmierst, Boss! 🅰️✨ Brauchst du Tipps für Routing oder Signals?"*).
  - Schnellzugriff per Rechtsklick: **"👁️ Bildschirm beobachten (Vision)"** oder Frage *"Was mache ich gerade?"*.

- **🧠 Cloud-KI & Ausgereifter Offline-Parser (`agent_brain.py`):**
  - **Moderne Gemini-Modelle:** `gemini-3.5-flash`, `gemini-flash-latest`, `gemini-flash-lite-latest`, `gemini-3.8-flash`, `gemini-pro-latest`.
  - **Automatisches Model-Fallback:** Sollte ein Modell ein Kontingentlimit (429) oder 404 erreichen, probiert Mochi automatisch blitzschnell das nächste Modell!
  - **100 % Offline-Fallback:** Alle 15 Tools und viele deutsche Sprachvariationen funktionieren auch ganz ohne Internet/Key zuverlässig offline.

---

## ⌨️ Bedienung & Gesten

| Aktion | Geste / Taste |
|---|---|
| **Kraulen / Streicheln** | Einfacher Linksklick (Mochi schnurrt mit Herzaugen & Herzchen) |
| **Befehl eingeben** | Doppelklick auf das Pet oder **`Strg + Alt + P`** |
| **Größe ändern (Zoom)** | **`Strg + Mausrad`** oder **`Shift + Mausrad`** direkt über dem Pet |
| **Hochheben / Werfen** | Mit linker Maustaste ziehen und mit Schwung loslassen |
| **Schnell-Aktionen** | Rechtsklick ➜ *✨ Tricks & Spaß* oder *⚡ Schnell-Tools* |
| **Einstellungen** | Rechtsklick ➜ *Einstellungen* (1-Klick Gemini-Key Button vorhanden) |
| **Beenden** | Rechtsklick ➜ *Beenden* |


---

## ⚙️ Einstellungen & API-Keys (`config.json`)

Über das Rechtsklick-Menü ➜ **Einstellungen** (oder direkt in `config.json`):
- **KI-Anbieter:** `auto` (wählt automatisch anhand der Keys), `gemini`, `openai` oder `offline`.
- **Gemini API-Key:** Kostenloser API-Key von Google AI Studio eintragen.
- **OpenAI API-Key:** OpenAI API-Key eintragen.
- **Geschwindigkeit & Größe:** Per Schieberegler stufenlos anpassbar.
- **Wandern & Plaudern:** Deaktivierbar, falls Mochi ruhig an einer Stelle sitzen soll.

---

## 📁 Projektstruktur

```
WindowsAgent/
├── main.py              # Einstiegspunkt, App-Lifecycle, System-Tray & Hotkey
├── pet_window.py        # Transparentes Overlay, Zustandsmaschine & Desktop-Physik
├── pet_sprites.py       # Prozeduraler Kawaii-Katzen-Renderer & Sprite-Loader
├── speech_bubble.py     # Schwebende Sprechblase & abgerundete Dark-Mode Input-Leiste
├── agent_brain.py       # Cloud-KI (Gemini/OpenAI), Multithreading Worker & Offline-Parser
├── tools.py             # Reale Windows-Aktionen (Word2PDF, Desktop-Organizer, Tools)
├── settings_dialog.py   # Grafischer Einstellungsdialog
├── config.py            # Thread-sicherer Config-Manager
├── config.json          # Konfigurationsdatei (Geschwindigkeit, Skalierung, Keys)
├── start.bat            # Silent-Launcher (pythonw.exe)
├── assets/              # Ordner für optionale eigene GIFs/Sprites
│   └── README.md        # Anleitung für eigene Sprite-Sheets
└── requirements.txt     # Python-Bibliotheken
```
