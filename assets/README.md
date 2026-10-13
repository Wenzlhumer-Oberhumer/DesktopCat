# Eigene Sprites (optional)

Lege hier Bilder ab - sobald `idle.gif` / `idle.png` existiert, nutzt Mochi **deine** Grafiken
statt der eingebauten Kawaii-Katze. Fehlende Zustaende werden aus dem Idle-Bild abgeleitet
(Huepfen, Wackeln ...), `walk_left` wird automatisch aus `walk_right` gespiegelt.

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
