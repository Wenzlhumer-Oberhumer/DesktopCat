# 🐾 Desktop Cat – Kylie, deine KI-Katze für den Windows-Desktop

**Desktop Cat** (früher „Mochi“) ist ein extrem niedliches Desktop-Haustier für Windows. **Kylie**, eine Calico-Glückskatze, läuft auf deiner Taskleiste herum, lässt sich herumwerfen, plaudert mit dir und hilft dir per **Gemini-KI** (kostenloser Key) oder **Offline-Parser** bei echten Windows-Aufgaben.

---

## Neu in v3.2.1

- **Getrennte Spielpunkte:** Wollknäuel-Aktionen bringen zwei Punkte, bis zu zehnmal täglich, ohne das Leckerli-Kontingent zu verbrauchen.
- **Manuell heißt freiwillig:** Selbst gestartete Pet-Runden verbrauchen keine automatischen Fragen mehr. Sie setzen den normalen Abstand zur nächsten automatischen Frage zurück.
- **Eine Stunde Fragenpause:** Direkt auf der Antwortkarte oder im Tray pausieren; dort lässt sich die Pause vorzeitig beenden. Die Pause bleibt nach Neustart erhalten, manuelle Runden bleiben möglich.
- **Fortschritt live:** Das Freundschaftsfenster aktualisiert Punkte, Level und freigeschaltete Belohnungen während es geöffnet ist. Grundpunkte und Trophäenbonus einer Aktion erzeugen eine gemeinsame Meldung zum erreichten Level; Meldungen warten während Eingaben und Fokusmodus.
- **Updatefortschritt:** Download mit Prozentanzeige oder laufendem Balken bei unbekannter Größe, anschließende Prüfsummenprüfung, Fehler mit Wiederholen oder Verschieben. Der aktuelle Status lässt sich über das Tray wieder öffnen.

## Neu in v3.2.0

- **Zeit miteinander:** 20 lokale Entweder-oder-Fragen, freiwillige Freitextfragen und kleine Mitmachaktionen. Das Pet tanzt, streckt sich, knabbert oder macht eine Kuschelpause. Rechtsklick auf das Pet oder Tray → „Zeit miteinander“ startet sofort eine Runde.
- **Freiwillig und ruhig:** „Überspringen“ oder Escape schließt die Frage ohne Punktabzug. Freitext öffnet sich erst nach „Erzählen“. Automatische Angebote warten bei Gesprächen, Vollbild, Fokusmodus, verstecktem Pet und nachts. Die letzten sechs Angebote wiederholen sich nicht direkt.
- **Häufigkeit:** Einstellungen → Wohlbefinden → „Zeit miteinander“: selten (frühestens 90 Minuten, maximal 4 pro Tag), normal (45 Minuten, maximal 12) oder öfter (20 Minuten, maximal 24). Automatische Angebote lassen sich ausschalten; manuell bleibt die Funktion verfügbar.
- **Freundschaft repariert:** Figurenbaum, Freischaltung und Freundschaftsfenster lesen denselben gespeicherten Punktestand. Gleichzeitige Vergaben verlieren keine Punkte und überschreiten keine Tageslimits. Füttern im Figurenbaum zählt einmal; Trophäen zahlen ihre angegebene Belohnung genau einmal aus.
- **Kein zusätzlicher KI-Aufruf:** Die Interaktion selbst wird lokal beantwortet. Merken und Chat-Speicherung folgen den vorhandenen Datenschutzschaltern; aktivierte Erinnerungen und Chatverläufe können wie bisher bei späteren KI-Anfragen als Kontext verwendet werden.

## Neu in v3.1.0

- **Update-Buttons:** „Ja, installieren“ startet den geprüften Download; „Später…“ bietet 15 Minuten, eine oder vier Stunden, morgen 09:00 oder einen eigenen Zeitpunkt. Erinnerungen bleiben nach Neustart gespeichert.
- **Gemütliche Figuren & Outfits:** Flocke (Polarfuchs) und Kakao (Schlappohrhase) sind sofort verfügbar. Strickjacke, Kuschelschal und Ohrwärmer lassen sich auch als komplettes Set auswählen; die Einstellungen zeigen eine Vorschau vor dem Speichern.
- **Ruhiges Katzenzimmer:** Putzwand, Holzfußboden, Wald am Fenster und lokale Tageszeiten. Links bleibt Platz für Desktop-Symbole. Animationen respektieren reduzierte Bewegung und pausieren im Hintergrund.
- **Zimmer bedienen:** Vorschau und Wiederherstellen direkt im Zimmer-Tab. Aktivierung läuft ohne blockierende Oberfläche; Regal und Fensterbank besitzen begrenzte Sprungflächen passend zum sichtbaren Raum auf dem Hauptbildschirm.
- **KI-Zugang ehrlich erklärt:** Der bisherige Browser-Link war keine Verbindung zwischen Kylie und einem Google-Abo und wurde entfernt. Kylie nutzt weiterhin deinen eigenen API-Key, ohne Entwickler-Key oder eigenen KI-Server. API-Nutzung richtet sich nach deinem Google-Projekt; Google-AI-Abos ersetzen diese API-Abrechnung nicht.

## Neu in v3.0.8

- **Bett ein-/ausblenden:** Rechtsklick direkt auf das Bett → „Bett ausblenden“. Über Rechtsklick auf die Katze oder das Tray-Menü → „Bett einblenden“ kommt es wieder zurück. Die Auswahl bleibt nach dem Neustart erhalten.
- **Ohne Bett überall schlafen:** Kylie schläft am Desktop-Boden an ihrer aktuellen horizontalen Position. Wird das Bett während des Schlafens oder auf dem Weg dorthin ausgeblendet, sinkt sie zum Boden und schläft dort weiter. Beim Wiedereinblenden oder Verschieben des Betts wird sie nicht dorthin teleportiert.

## Neu in v3.0.7

- **Bis v3.0.8, ersetzt in v3.1.0 – Gemini im Browser:** Über Tray-Menü oder Einstellungen „Gemini im Browser öffnen“ wählen. Optional eine Anfrage eingeben, kopieren und bei Gemini mit Strg+V einfügen. Dort nutzt du dein eigenes Google-Konto und dessen Abo. Im Chat funktioniert auch `gemini: deine Frage`. Antworten werden manuell gelesen; Desktop-Aktionen werden nicht automatisch aus Browser-Antworten ausgeführt. BYOK bleibt separat erhalten, ohne Entwickler-Key oder eigenen KI-Server.
- **Bis v3.0.8, ersetzt in v3.1.0 – Updates per Antwort:** Kylie bietet neue GitHub-Releases an. `ja` startet Download, SHA256-Prüfung und Installation; `später` verschiebt die Erinnerung um sechs Stunden. Der normale Klick auf eine Sprechblase öffnet die Eingabe. Neue Releases werden auch während längerer Laufzeiten geprüft.
- **Hintergrund:** Aktivierung wird anhand des Lively-Status geprüft. Desktop Cat schließt nur das eigene Katzenzimmer auf dessen Bildschirm und respektiert manuelle Hintergrundwechsel. Lively muss laufen und auf „Pro Bildschirm“ eingestellt sein.
- **Datenschutz:** Automatische Bildschirm-Tipps sind standardmäßig aus und benötigen eine eigene Freigabe unter Einstellungen → KI. Der KI-Schalter sperrt auch die übrigen KI-Einstiegspunkte.
- **Zuverlässigkeit:** Kein erneutes Ausführen erledigter Aktionen nach einem KI-Timeout. Lokale Builds brechen bei fehlgeschlagenen Schritten ab.

## 🆕 Neu in v3.0

- **🎙️ Mit Kylie sprechen (Push-to-Talk):** Hotkey gedrückt halten, sprechen, loslassen. Die Aufnahme geht an Gemini (wie eine getippte Frage) und wird danach sofort gelöscht. Funktioniert nur mit Gemini-Key und eingeschalteter KI.
- **🔊 Vorlesen mit Lip-Sync:** Standard ist die eingebaute Windows-Stimme – kein Text verlässt den PC. Optional eine natürlichere Online-Stimme (Microsoft Edge, Text wird dorthin gesendet) – nur wenn du sie in den Einstellungen einschaltest.
- **🐍 Eigene Python-Skripte & Routinen:** Kylie kann dir kleine Skripte schreiben. **Sie laufen erst, wenn du den Code im Skripte-Manager angesehen und „Speichern & freigeben“ gedrückt hast** – auch als Zeitplan (Start, täglich, alle X Minuten). Ändert sich der Code, muss er neu freigegeben werden. Dafür muss Python installiert sein.
- **🍖 Pflege (Füttern & Waschen), 15 Figuren mit Freischalt-Baum, Minispiele (Seifenblasen, Wollknäuel), Katzenbett.**
- **🏠 Katzenzimmer-Modus** mit dem kostenlosen Programm *Lively Wallpaper* (optional).
- **🔑 KI-Zugang:** weiterhin nur der kostenlose Gemini-Key. Ein „Mit Google-Konto/Abo anmelden“ gibt es bewusst nicht: Ein privates Google-Abo (Google One, AI Pro) schaltet die Gemini-API nicht frei.

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
  | **Kylie** (Standard) | Calico-Glückskatze |
  | **Luna** | Midnight-Katze |
  | **Hachi** | Shiba Inu |
  | **Balu** | Golden-Welpe |
  | **Drago** | Baby-Drache |
  | **Byte** | Cyber-Bot |
  | **Spooky** | Geist-Slime |
  | **Lotti** | Rosa Axolotl |
  | **Pip** | Kaiser-Pinguin |
- **🗣️ Eigener Name / Anrede:** Kylie spricht dich nicht mehr fix mit „Boss“ an, sondern mit dem Namen, den du in den Einstellungen einträgst.
- **🛠️ Neue Werkzeuge:**
  - **Timer & Pomodoro:** Kylie erinnert dich per Tray-Benachrichtigung, wenn die Zeit um ist.
  - **Live-Wetter:** „Wie ist das Wetter in Wien?“ über wttr.in. Ohne API-Key und kostenlos.
  - **PC aufräumen:** leert den Papierkorb und löscht alte Temp-Dateien (mit Rückfrage).
  - **Netzwerk- & IP-Info:** zeigt deine IP-Adressen und Netzwerkdaten.
  - **Fenster wegschieben & schließen:** bringt Fenster aus dem Weg oder schließt sie (mit Rückfrage).
- **🛡️ Sicherheitsabfrage:** Vor gefährlichen Aktionen (Papierkorb/Temp leeren, Fenster schließen, Datei löschen, PowerShell) fragt Kylie nach. Antworte mit **„ja“** oder **„nein“**. Ohne „ja“ passiert nichts.
- **✨ Extras:**
  - **Wohlfühl-Erinnerungen:** Kylie erinnert ans Strecken und Wassertrinken, in der Stimme deines Charakters. Pausiert automatisch, wenn eine Anwendung im Vollbild läuft.
  - **Akku-Warnung:** meldet sich, wenn der Akku unter 15 % fällt und das Gerät nicht am Netzteil hängt.
  - **Nachtmodus (23–7 Uhr):** Kylie schläft öfter und ruft seltener dazwischen.
  - **Spielmodus „Fang die Maus“:** Kylie läuft 15 Sekunden lang deinem Mauszeiger hinterher.
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
  - Autonomes Wandern: Alle 5–10 Sekunden entscheidet Kylie zufällig, ob sie stehen bleibt, ein Nickerchen macht (`SLEEP`) oder neugierig spazieren geht.
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
  - Schwebende Sprechblase mit animiertem Fade-In/Fade-Out und Pfeil, der auf den Kopf der Figur zeigt.
  - Schlanke Eingabeleiste ("Was soll ich tun, Boss? 🐾" – „Boss“ wird durch deinen eingestellten Namen ersetzt): Öffnet sich per **Doppelklick**, per globalem Hotkey (**`Strg + Alt + P`**), über das Tray-Icon oder Rechtsklick-Menü.
  - Klick auf die Sprechblase öffnet direkt den Antwort-Modus oder installiert anstehende Updates.

- **🤖 Gemini-KI mit kostenlosem Key in 3 Klicks:**
  - Einstellungen ➜ *Gratis-Key holen* öffnet Google AI Studio, dort mit Google anmelden und *Create API key* klicken. Ein Bezahlkonto ist nicht nötig (Free Tier); Angebote für Billing, Firebase oder Guthaben kann man überspringen.
  - Key einfügen ➜ *Prüfen & speichern*. Der Key liegt sicher in der Windows-Anmeldeinformationsverwaltung, nicht in `config.json`.
  - Jeder Nutzer verwendet sein eigenes Gratis-Kontingent; keine Kosten für den Entwickler.
  - Sicheres JSON-Tool-Protokoll: die KI kann nur Desktop Cats eigene Werkzeuge auslösen.
  - Ohne Key oder ohne Internet arbeitet Kylie automatisch im **100 % Offline-Modus**.
  - Das eigene Gemini-Abo nutzt du über die separate Browser-Option. Desktop Cat übernimmt dabei keine Google-Zugangsdaten oder Browser-Antworten.

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
| **Kraulen / Streicheln** | Einfacher Linksklick (Kylie schnurrt mit Herzaugen & Herzchen) |
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

Nutzerdaten und Logs werden automatisch unter `%APPDATA%\Kylie\` abgelegt:
- `%APPDATA%\Kylie\config.json`: Einstellungen
- `%APPDATA%\Kylie\buddy.log`: Logdatei

---

## 📦 Build & Installer erstellen

Desktop Cat bringt ein vollständiges Build-System mit:

```powershell
# Baut PyInstaller-Bundle und das Inno Setup Setup:
.\build.ps1
```

Das Skript:
1. Baut das Multi-Size-Icon (`assets/mochi.ico`).
2. Erzeugt das PyInstaller-Bundle (`dist\DesktopCat\`).
3. Kompiliert das Inno-Setup-Installationsprogramm (`dist\DesktopCat-Setup-<version>.exe`) inklusive `.sha256`-Prüfsumme.

### Release auf GitHub veröffentlichen
Releases werden lokal gebaut. Der GitHub-Workflow hat nur noch einen manuellen Start (`workflow_dispatch`); Branch- und Tag-Pushes starten keinen Build und verbrauchen keine Actions-Minuten.

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

## 📄 Lizenz (Copyleft: GNU GPL v3)

Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer

Desktop Cat ist **freie Software**: Du darfst sie unter den Bedingungen der **GNU General Public License, Version 3 oder (nach deiner Wahl) jeder späteren Version**, wie von der Free Software Foundation veröffentlicht, weitergeben und/oder verändern. Den vollständigen Lizenztext findest du in [`LICENSE`](LICENSE) (SPDX: `GPL-3.0-or-later`).

Desktop Cat wird in der Hoffnung verbreitet, dass es nützlich ist, aber **OHNE JEDE GEWÄHRLEISTUNG**, sogar ohne die implizite Gewährleistung der MARKTREIFE oder der EIGNUNG FÜR EINEN BESTIMMTEN ZWECK. Details stehen in der GNU General Public License.

**Was Copyleft für dich bedeutet:**
- ✅ Du darfst Desktop Cat benutzen, kopieren, verändern und weitergeben – auch verändert.
- 🔁 Wenn du eine (veränderte) Version weitergibst, muss sie **ebenfalls unter der GPL v3** stehen, und du musst den **Quellcode** mitliefern oder zugänglich machen.
- 📝 Copyright- und Lizenzhinweise dürfen nicht entfernt werden; Änderungen müssen als solche erkennbar sein.

Desktop Cat nutzt PyQt6 (GPL v3) und weitere Open-Source-Bibliotheken; deren Hinweise stehen in [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt). Der Wetterdienst wttr.in wird nur online abgefragt (keine mitgelieferte Software).
