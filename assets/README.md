# Eigene Sprites (optional)

Lege hier Bilder ab - sobald `idle.gif` / `idle.png` existiert, nutzt Mochi **deine** Grafiken
statt der eingebauten Figur. Fehlende Zustaende werden aus dem Idle-Bild abgeleitet
(Huepfen, Wackeln ...), `walk_left` wird automatisch aus `walk_right` gespiegelt.

Die eigenen Sprites ersetzen die gezeichnete Figur **unabhaengig vom Charakter**, der in den
Einstellungen gewaehlt ist. Ohne eigene Dateien zeichnet Mochi den gewaehlten Charakter
(9 Figuren, z. B. Mochi, Luna, Hachi, Pip ...). Der Charakter laesst sich im Rechtsklick-Menue
oder in den Einstellungen umschalten.

| Datei (gif / png / webp)  | Zustand                     |
|---------------------------|-----------------------------|
| `idle`                    | Atmen / Blinzeln            |
| `walk_right` (`walk_left`)| Laufen (Bild schaut rechts) |
| `dragged`                 | wird gehalten               |
| `falling`                 | faellt (sonst `dragged`)    |
| `working`                 | Aufgabe laeuft              |
| `success`                 | Freude                      |
| `sleep`                   | schlaeft                    |
| `sad`                     | Fehler                      |

* **GIF**: alle Frames werden mit ihren Zeiten uebernommen.
* **PNG-Sprite-Sheet**: Frames nebeneinander (quadratische Frames werden automatisch erkannt).
  Sonst in `config.json` angeben: `"walk_right": {"file": "assets/walk.png", "frames": 6, "fps": 10}`.

## Calico-Sprites erzeugen

Wer eigene Pixelart- oder handgezeichnete Sprites der echten Katze erstellen möchte:
* **Referenzfotos**: Siehe `ref/*.jpg` (Glückskatze/Calico mit Tabby-Anteil: weiße Schnauze/Brust/Pfoten, oranger Fleck links, Tabby rechts und auf der Stirn mit M-Muster, kleiner oranger Stirntupfer, rosa Nase, gelbgrüne Augen, gefleckter Rücken, getigerter Schwanz, kein Halsband).
* **Empfohlene Größe**: 256×256 Pixel pro Frame.
* **Hintergrund**: Transparent (PNG/GIF).
* **Zustände**:
  - `idle`: Ruhiges Sitzen/Atmen, Blinzeln
  - `walk_right`: Geh-Animation nach rechts (wird für links automatisch gespiegelt)
  - `dragged`: Katze wird am Nackenfell / mit der Maus hochgehoben
  - `falling`: Katze fällt nach unten
  - `working`: Katze tippt am Laptop / arbeitet konzentriert
  - `success`: Jubel / Tanz / Freude mit Sternchen
  - `sleep`: Liegend eingerollt / schlafend (Zzz)
  - `sad`: Traurig / erschöpft

