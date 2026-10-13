# 🐾 Mochi – Dein autonomer AI Desktop Buddy für Windows

**Mochi** ist ein vollfunktionsfähiges, extrem niedliches Desktop-Pet für Windows. Er läuft selbstständig auf deiner Taskleiste herum, reagiert auf Klicks & Drag-and-Drop und führt per **Gemini KI** oder **regelbasiertem Offline-Parser** echte Windows-Aktionen aus.

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
  - Schlanke Eingabeleiste ("Was soll ich tun, Boss? 🐾"): Öffnet sich per **Doppelklick**, per globalem Hotkey (**`Strg + Alt + P`**), über das Tray-Icon oder Rechtsklick-Menü.
  - Klick auf die Sprechblase öffnet direkt den Antwort-Modus oder installiert anstehende Updates.

- **🤖 Nahtlose Gemini-KI-Anmeldung (Google-Login statt API-Keys):**
  - Keine komplizierten API-Keys oder Kontingent-Abos nötig.
  - Offizielle Gemini CLI (`@google/gemini-cli`) mit sicherem OAuth-Login (`oauth-personal`).
  - Ein Klick auf "Mit Google anmelden" öffnet den Browser, autorisiert einmalig und Mochi ist startklar.
  - Sicheres JSON-Tool-Protokoll ohne Shell-Zugriff für die KI.
  - Bei fehlender Anmeldung oder Verbindungsverlust arbeitet Mochi automatisch im **100 % Offline-Modus**.

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
| **Einstellungen** | Rechtsklick ➜ *Einstellungen* (Google-Login, Verhalten, Autostart) |
| **Beenden** | Rechtsklick ➜ *Beenden* |

---

## 🛠️ Entwicklung & Manuelle Installation

### Voraussetzungen
- Python 3.10+ (auf Windows)
- Node.js (für Entwicklung mit Gemini CLI)

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
# Baut die portable Runtime, PyInstaller-Bundle und das Inno Setup Setup:
.\build.ps1
```

Das Skript:
1. Lädt eine portable Node.js-Laufzeit herunter und prüft die SHA256-Prüfsumme.
2. Installiert die gepinnte Gemini CLI (`@google/gemini-cli@0.63.0`) in `vendor/gemini-cli`.
3. Baut das Multi-Size-Icon (`assets/mochi.ico`).
4. Erzeugt das PyInstaller-Bundle (`dist\Mochi\`).
5. Kompiliert das Inno-Setup-Installationsprogramm (`dist\Mochi-Setup-<version>.exe`) inklusive `.sha256`-Prüfsumme.

### Release auf GitHub veröffentlichen
1. Version in `version.py` erhöhen (z. B. `"2.0.1"`).
2. `.\build.ps1` ausführen.
3. Release auf GitHub erstellen und die beiden Dateien aus `dist\` hochladen:
   - `Mochi-Setup-2.0.1.exe`
   - `Mochi-Setup-2.0.1.exe.sha256`
   (oder via `gh release create v2.0.1 dist\Mochi-Setup-2.0.1.exe dist\Mochi-Setup-2.0.1.exe.sha256 --title "v2.0.1"`).

---

## 📄 Lizenz & Third-Party

Mochi steht unter der **GNU General Public License v3.0 (GPLv3)**, da es die PyQt6-Bibliothek nutzt.
Detaillierte Lizenzhinweise zu allen Drittanbieter-Komponenten (Node.js, Gemini CLI, Pillow, pywin32, docx, pptx) finden sich in `THIRD_PARTY_LICENSES.txt`.
