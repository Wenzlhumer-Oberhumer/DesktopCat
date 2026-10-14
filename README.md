# 🐾 Desktop Cat – Kylie, deine KI-Katze für den Windows-Desktop

**Desktop Cat** (früher „Mochi“) ist ein extrem niedliches Desktop-Haustier für Windows. **Kylie**, eine Calico-Glückskatze, läuft auf deiner Taskleiste herum, lässt sich herumwerfen, plaudert mit dir und hilft dir per **Gemini-KI** (kostenloser Key) oder **Offline-Parser** bei echten Windows-Aufgaben.

---

## 🆕 Neu in v2.2

- **Desktop Cat & Kylie:** neuer Name, Standard-Katze heißt Kylie und reagiert auf ihren Namen („Kylie!“ → spitzt die Ohren, wacht auf, „Kylie, wie spät ist es?“).
- **✨ Kennenlernen beim ersten Start:** Kylie fragt dich in einem kleinen Chat nach Name, Spitzname, Hobbys, Stadt, gewünschtem Ton usw. Dein Profil geht kurz bei jeder KI-Frage mit, damit sie persönlich antwortet. Jederzeit wiederholbar und änderbar.
- **📚 Meine Chats:** alle Gespräche lokal gespeichert, durchsuchbar, exportierbar, „Unterhaltung fortsetzen“.
- **🔒 Meine Daten:** alles, was Kylie über dich weiß, ansehen, einzeln löschen oder „Alles vergessen“. Daten bleiben auf deinem PC; an Gemini gehen nur Frage, Profil, Fakten und höchstens 3 passende Chat-Ausschnitte (Hinweis zum kostenlosen Gemini-Zugang steht im Fenster).
- **💬 Neugierig:** Kylie fragt ab und zu nach dir, merkt sich Termine und Geburtstage, Guten-Morgen-Briefing, Schlafenszeit-Erinnerung.
- **🕶️ IT-Support:** bei Technikfragen setzt Kylie die Hackerbrille auf, fliegt auf ihrer Wolke zur richtigen Stelle und zeigt „Linksklick/Rechtsklick“ Schritt für Schritt – sie klickt nie selbst. Dazu Fehlermeldungs-Doktor und „Kopieren & Erklären“ (Hotkey).
- **🎩 Outfits:** Saison (Halloween, Weihnachten, Silvester), Wetter (Schirm, Sonnenbrille, Schal), PC-Fieber (Fächer), Freundschafts-Level mit Belohnungen.
- **📊 Fokus-Statistik, 📚 Lernkarten-Quiz, 📸 Fotobox, 📝 Haftnotizen.**
- **🌍 Englisch-Modus** (Einstellungen ➜ Sprache).
- **🤾 Werfen mit Schwung:** Figur packen und werfen – sie fliegt weiter, prallt an Wänden und Decke ab, hopst einmal am Boden und spaziert dann weiter.

## 🆕 Neu in v2.1

- **🐾 9 Charaktere zur Auswahl:** Umschalten live per Rechtsklick ➜ *Charakter* oder in den Einstellungen. Die KI-Antworten und die Offline-Antworten sprechen im Stil des gewählten Charakters.
  | Figur | Art |
  |---|---|
  | **Mochi** (Standard) | Calico-Glückskatze |
  | **Luna** | Midnight-Katze |
  | **Hachi** | Shiba Inu |
  | **Balu** | Golden-Welpe |
  | **Drago** | Baby-Drache |
  | **Byte** | Cyber-Bot |
  | **Spooky** | Geist-Slime |
  | **Lotti** | Rosa Axolotl |
  | **Pip** | Kaiser-Pinguin |
- **🗣️ Eigener Name / Anrede:** Mochi spricht dich nicht mehr fix mit „Boss“ an, sondern mit dem Namen, den du in den Einstellungen einträgst.
- **🛠️ Neue Werkzeuge:**
  - **Timer & Pomodoro:** Mochi erinnert dich per Tray-Benachrichtigung, wenn die Zeit um ist.
  - **Live-Wetter:** „Wie ist das Wetter in Wien?“ über wttr.in. Ohne API-Key und kostenlos.
  - **PC aufräumen:** leert den Papierkorb und löscht alte Temp-Dateien (mit Rückfrage).
  - **Netzwerk- & IP-Info:** zeigt deine IP-Adressen und Netzwerkdaten.
  - **Fenster wegschieben & schließen:** bringt Fenster aus dem Weg oder schließt sie (mit Rückfrage).
- **🛡️ Sicherheitsabfrage:** Vor gefährlichen Aktionen (Papierkorb/Temp leeren, Fenster schließen, Datei löschen, PowerShell) fragt Mochi nach. Antworte mit **„ja“** oder **„nein“**. Ohne „ja“ passiert nichts.
- **✨ Extras:**
  - **Wohlfühl-Erinnerungen:** Mochi erinnert ans Strecken und Wassertrinken, in der Stimme deines Charakters. Pausiert automatisch, wenn eine Anwendung im Vollbild läuft.
  - **Akku-Warnung:** meldet sich, wenn der Akku unter 15 % fällt und das Gerät nicht am Netzteil hängt.
  - **Nachtmodus (23–7 Uhr):** Mochi schläft öfter und ruft seltener dazwischen.
  - **Spielmodus „Fang die Maus“:** Mochi läuft 15 Sekunden lang deinem Mauszeiger hinterher.
  - **„Leckerli geben“:** Herzchen und ein Spruch, dazu ein Zähler („Schon 12 Leckerli bekommen!“).
  - **Hotkey änderbar:** der globale Hotkey (Standard `Strg + Alt + P`) lässt sich in den Einstellungen umstellen.
- **💸 Alles bleibt kostenlos:** Keine kostenpflichtigen APIs. Gemini läuft wie bisher mit dem eigenen Gratis-Key, Wetter über wttr.in ohne Schlüssel.
- **📝 Status:** v2.1 ist im Entwicklungsstand. Die Abnahme-Checkliste steht in `ref/plan/08_V2_1.md`.

---

## ✨ Features

- **🐾 100 % Transparentes Always-on-Top Fenster:**
  - Kein störender Rahmen, keine Einträge in Alt-Tab oder Taskleiste (`Qt.WindowType.Tool`).
  - Echte Desktop-Physik: Schmiegt sich an die Oberkante der Windows-Taskleiste an.
  - Interaktives **Drag & Drop**: In der Luft halten (zappelt überrascht mit Schweißtröpfchen), loslassen (fällt mit weichem Squish & Mini-Bounce auf die Taskleiste zurück).
  - Autonomes Wandern: Alle 5–10 Sekunden entscheidet Mochi zufällig, ob er stehen bleibt, ein Nickerchen macht (`SLEEP`) oder neugierig spazieren geht.
  - Single-Instance-Schutz über Windows-Mutex (`MochiDesktopPetMutex`).

- **🎨 Handgezeichneter Calico-Katzen-Look (nach echten Fotos):**
  - Prozedurales Vektor-Rendering in reinem `QPainter` (keine externen Assets zwingend erforderlich).
  - Aussehen einer echten dreifarbigen Glückskatze (Calico) mit Tabby-Anteil:
    - Weiße Schnauze, Blesse, Brust, Bauch und Pfötchen (mit rosa Ballen).
    - Asymmetrischer oranger Fleck links am Kopf und linkes Ohr.
    - Braun-graues Tabby mit Streifen auf der rechten Seite und "M"-Muster auf der Stirn.
    - Kleiner oranger Stirntupfer, rosa Nase und ausdrucksstarke gelbgrüne Augen.
    - Gefleckter Rücken (Schwarz-Braun mit Tabby-Zeichnung + Orange) und getigerter Schwanz.
    - Kein Halsband oder Glöckchen.
  - **Zustände & Animationen:**
    - `IDLE`: Ruhiges Atmen, Blinzeln & Ohrenzucken.
    - `DANCE`: Rhythmischer Tanz mit bunten Vektor-Musiknoten (`♪`, `♫`, `♬`).
    - `COOL`: Coole Sonnenbrille mit Star-Twinkle (`✦`).
    - `WORKING`: Konzentriertes Tippen auf einem leuchtenden Mini-Laptop.
    - `SUCCESS`: Freudentanz, Jubelsprünge & goldene Funkelsterne (`Sparkles`).
    - `SLEEP`: Zusammengerollt mit schlafendem Schwanz & schwebenden 'Z's.
    - `DRAGGED`: Schreck-Schweißtröpfchen und zappelnde Pfötchen.
    - `SAD`: Tränchen bei Fehlern.
  - **Stufenloses Zoomen:** Mit **`Strg + Mausrad`** (oder `Shift + Mausrad`) direkt am Bildschirm vergrößern oder verkleinern (60 % bis 250 %).

- **💬 Elegante Dark-Mode UI & Reiches Kontextmenü:**
  - Schwebende Sprechblase mit animiertem Fade-In/Fade-Out und Pfeil, der auf Mochis Kopf zeigt.
  - Schlanke Eingabeleiste ("Was soll ich tun, Boss? 🐾" – „Boss“ wird durch deinen eingestellten Namen ersetzt): Öffnet sich per **Doppelklick**, per globalem Hotkey (**`Strg + Alt + P`**), über das Tray-Icon oder Rechtsklick-Menü.
  - Klick auf die Sprechblase öffnet direkt den Antwort-Modus oder installiert anstehende Updates.

- **🤖 Gemini-KI mit kostenlosem Key in 3 Klicks:**
  - Einstellungen ➜ *Gratis-Key holen* öffnet Google AI Studio, dort mit Google anmelden und *Create API key* klicken. Ein Bezahlkonto ist nicht nötig (Free Tier); Angebote für Billing, Firebase oder Guthaben kann man überspringen.
  - Key einfügen ➜ *Prüfen & speichern*. Der Key liegt sicher in der Windows-Anmeldeinformationsverwaltung, nicht in `config.json`.
  - Jeder Nutzer verwendet sein eigenes Gratis-Kontingent; keine Kosten für den Entwickler.
  - Sicheres JSON-Tool-Protokoll: die KI kann nur Mochis eigene Werkzeuge auslösen.
  - Ohne Key oder ohne Internet arbeitet Mochi automatisch im **100 % Offline-Modus**.
  - Hinweis: Der frühere „Mit Google anmelden“-Weg über die Gemini CLI funktioniert seit dem 18.06.2026 für private Google-Konten nicht mehr (Google hat ihn abgeschaltet).

- **⚡ 20 Echte Windows-Aktionen (`tools.py`):**
  1. **Word-Dokumente erstellen (`create_file`):** Erstellt formatiertes `.docx` direkt am Desktop.
  2. **PowerPoint-Präsentationen erstellen (`create_file`):** Erstellt native `.pptx` am Desktop.
  3. **Dateien löschen (`delete_file`):** Sucht und löscht Dateien am Desktop ohne lästige Dialoge.
  4. **Dateiinhalte lesen (`read_file_content`):** Liest Word-, PowerPoint- oder Textdateien vor.
  5. **Bildschirm beobachten (`inspect_screen`):** Multimodale Vision-Analyse & aktive Z-Order Fenstererkennung.
  6. **PowerShell-Befehle (`execute_powershell`):** Führt Systembefehle auf Nutzerwunsch aus.
  7. **Word zu PDF (`convert_word_to_pdf`):** Nativ via Word COM-Automation.
  8. **Desktop aufräumen & rückgängig machen (`organize_desktop`, `undo_organize_desktop`).**
  9. **Screenshot (`take_screenshot`):** Ganzer Desktop wird auf dem Desktop gespeichert.
  10. **Lautstärke (`control_volume`):** Lauter, leiser oder stummschalten.
  11. **Mediensteuerung (`media_control`):** Play/Pause, nächster Song, vorheriger Song, Stopp.
  12. **Notizen (`manage_notes`):** Schnelle Notizen in `Desktop/Notizen.txt`.
  13. **Zwischenablage (`clipboard_action`):** Text kopieren oder einfügen.
  14. **Taschenrechner (`calculate`):** Mathematische Ausdrücke berechnen.
  15. **Uhrzeit & Datum (`show_time_and_date`):** Genaue Uhrzeit, Wochentag und Datum.
  16. **Ordner öffnen (`open_folder`):** Downloads, Dokumente, Desktop, Bilder, Musik etc.
  17. **Programme starten (`open_program`):** Windows-Apps oder URLs öffnen.
  18. **Dateisuche (`find_files`):** Sucht Dateien und öffnet/markiert sie im Explorer.
  19. **System-Check (`system_info`):** Akku, Ladestand, Festplattenkapazitäten.
  20. **Web-Recherche (`web_search`):** DuckDuckGo / Wikipedia / Websuche.

- **🔄 Auto-Update über GitHub Releases:**
  - Prüft im Hintergrund diskret nach neuen Versionen auf GitHub.
  - SHA256-geprüfter Download und vollautomatisches Silent-Update ohne UAC-Adminrechte.

---

## ⌨️ Bedienung & Gesten

| Aktion | Geste / Taste |
|---|---|
| **Kraulen / Streicheln** | Einfacher Linksklick (Mochi schnurrt mit Herzaugen & Herzchen) |
| **Befehl eingeben** | Doppelklick auf das Pet oder **`Strg + Alt + P`** |
| **Größe ändern (Zoom)** | **`Strg + Mausrad`** oder **`Shift + Mausrad`** direkt über dem Pet |
| **Hochheben / Werfen** | Mit linker Maustaste ziehen und loslassen |
| **Schnell-Aktionen** | Rechtsklick ➜ *✨ Tricks & Spaß* oder *⚡ Schnell-Tools* |
| **Charakter wechseln** | Rechtsklick ➜ *Charakter* (oder in den Einstellungen) |
| **Leckerli geben** | Rechtsklick ➜ *Tricks & Spaß* ➜ *Leckerli geben* |
| **Fang die Maus** | Rechtsklick ➜ *Tricks & Spaß* ➜ *Fang die Maus!* (Figur läuft 15 s dem Mauszeiger nach) |
| **Einstellungen** | Rechtsklick ➜ *Einstellungen* (Gemini-Key, Charakter, Name, Hotkey, Erinnerungen, Autostart) |
| **Beenden** | Rechtsklick ➜ *Beenden* |

---

## 🛠️ Entwicklung & Manuelle Installation

### Voraussetzungen
- Python 3.10+ (auf Windows)

### Starten im Dev-Modus
```powershell
pip install -r requirements.txt
python main.py
```

Nutzerdaten und Logs werden automatisch unter `%APPDATA%\Mochi\` abgelegt:
- `%APPDATA%\Mochi\config.json`: Einstellungen
- `%APPDATA%\Mochi\buddy.log`: Logdatei

---

## 📦 Build & Installer erstellen

Mochi bringt ein vollständiges Build-System mit:

```powershell
# Baut PyInstaller-Bundle und das Inno Setup Setup:
.\build.ps1
```

Das Skript:
1. Baut das Multi-Size-Icon (`assets/mochi.ico`).
2. Erzeugt das PyInstaller-Bundle (`dist\Mochi\`).
3. Kompiliert das Inno-Setup-Installationsprogramm (`dist\DesktopCat-Setup-<version>.exe`) inklusive `.sha256`-Prüfsumme.

### Release auf GitHub veröffentlichen
1. Version in `version.py` erhöhen (z. B. `"2.0.1"`).
2. `.\build.ps1` ausführen.
3. Release auf GitHub erstellen und die beiden Dateien aus `dist\` hochladen:
   - `DesktopCat-Setup-2.0.1.exe`
   - `DesktopCat-Setup-2.0.1.exe.sha256`
   (oder via `gh release create v2.0.1 dist\DesktopCat-Setup-2.0.1.exe dist\DesktopCat-Setup-2.0.1.exe.sha256 --title "v2.0.1"`).

---

## 🙏 Credits

Die Charakter-Designs, die Persona-Texte und die Werkzeuge Timer, Wetter, PC aufräumen, Netzwerk-Info und Fenster wegschieben stammen aus dem Projekt **WindowsCat** von **Stefan Wenzlhumer** (Repo: `Wenzlhumer-Oberhumer/WindowsCat`) und wurden in Mochi v2.1 übernommen. Vielen Dank dafür!

---

## 📄 Lizenz & Third-Party

Mochi steht unter der **GNU General Public License v3.0 (GPLv3)**, da es die PyQt6-Bibliothek nutzt.
Detaillierte Lizenzhinweise zu allen Drittanbieter-Komponenten (PyQt6, Pillow, pywin32, docx, pptx, wttr.in) finden sich in `THIRD_PARTY_LICENSES.txt`.
