# Phase 4 – Zubehör-System für alle 9 Figuren

Grundlage für Hackerbrille, Wolke, Outfits und Level-Belohnungen. **Einmal sauber bauen, dann überall nutzen.**

## 4.1 Anker pro Figur
Jede Figur zeichnet ihren Kopf an einer anderen Stelle. In `pet_sprites.CHARACTERS[id]` neues Feld:
```python
"anchors": {"head_top": (80, 52), "eyes": (80, 92), "eye_dx": 16, "neck": (80, 118), "paw_r": (104, 140)}
```
(logische Koordinaten in der 160×160-Zeichenfläche `BASE`, Werte pro Figur durch Ansehen der Zeichnung bestimmen). `tools_dev/save_screenshots.py` soll ein Debug-Bild erzeugen, das die Anker als kleine Punkte über alle 9 Figuren zeichnet → `ref/plan/screenshots/anchors.png`, **ansehen und justieren**.

## 4.2 Zeichnen
- `Pose.accessories: tuple[str, ...] = ()` (neues Feld).
- Neue Funktion `draw_accessories(p, pose, char_id)` in `pet_sprites.py`, aufgerufen in `draw_character` **nach** der Figur, im selben Koordinatensystem (Kopf-Bewegung `head_dx/head_dy/head_rot` mitnehmen, damit Hut/Brille beim Atmen/Hüpfen mitwackeln).
- Zubehör (je eine kleine Zeichenfunktion, Vektor wie der Rest):

| Name | Aussehen | Verwendet von |
|---|---|---|
| `hacker_glasses` | Schmale, eckige Brille mit grün leuchtenden Gläsern (#39FF14, Glow), kleine `</>`- und `01`-Zeichen schweben nach oben | IT-Support |
| `cloud` | Weiße, fluffige Wolke **unter** der Figur (wird VOR der Figur gezeichnet), sanftes Wippen, kleines Gesicht mit Lächeln (Lakitu-Stil), dezente Schatten-Unterseite | IT-Support (Fliegen) |
| `party_hat` | Spitzer bunter Partyhut mit Bommel | Geburtstag, Level |
| `nightcap` | Blaue Schlafmütze mit Bommel, hängt zur Seite | Schlafenszeit |
| `pumpkin_hat` | Kleiner Kürbis als Hut / Kürbis neben der Figur | Halloween (15.–31.10.) |
| `santa_hat` | Weihnachtsmütze | 1.–26.12. |
| `new_year` | Glitzer-Brille „20xx“ + Konfetti | 31.12.–1.1. |
| `umbrella` | Kleiner Regenschirm in der Pfote, Regentropfen | Wetter: Regen |
| `sunglasses` | (vorhandene Sonnenbrille wiederverwenden, falls möglich) | Wetter: > 25 °C |
| `scarf` | Roter Schal | Wetter: < 3 °C / Schnee |
| `beanie` | Wollmütze | Schnee |
| `crown`, `bow`, `bandana` | Level-Belohnungen (Phase 6) | Freundschafts-Level |
| `fan` | Handfächer + Schweißtropfen | PC-Fieber |

- Mehrere Accessoires gleichzeitig erlaubt, aber Kopf-Slot nur eins (Priorität: hacker_glasses > nightcap > party_hat > Wetter > Saison > Level).

## 4.3 Wer setzt Accessoires
Neue Methode `PetWindow.set_accessory(name, on: bool, until: float | None = None)` + `PetWindow._accessories` (Set). Pose-Bau (`_build_pose`) überträgt das Set in `pose.accessories`.
- **Saison** (automatisch, täglich prüfen): Funktion `seasonal_accessory(date) -> str | None`.
- **Wetter** (1× pro Stunde im Worker-Thread über `tools.get_weather`, nur mit Internet; Schalter `fun.weather_outfits`): Funktion `weather_accessory(temp_c, condition_text) -> str | None` (Regen/Schauer/Gewitter → umbrella, Schnee → scarf+beanie, > 25 °C → sunglasses). Dafür `get_weather` so erweitern, dass es optional auch rohe Werte (Temperatur, Wetter-Code/Text) liefert (z. B. `ToolResult.data`), ohne seine bisherige Nachricht zu ändern.
- **PC-Fieber** (alle 15 s, Schalter `fun.pc_fever`): CPU-Last ohne neue Pakete über `ctypes` `GetSystemTimes` (Differenz zweier Messungen) und RAM über `GlobalMemoryStatusEx` (wie in `tools.system_info`). > 90 % CPU für 30 s oder > 92 % RAM → Accessoire `fan`, `pose.sweat=True`, einmalig „Puh, dein PC kocht! 🥵 Soll ich nachsehen, was so viel frisst?“ (Ja → `tools.system_info`). Max. 1× pro Stunde.

## 4.4 Fliegen auf der Wolke (Grundlage für Phase 5)
- Neuer `PetState.FLY` in `pet_window.py`: keine Schwerkraft, Ziel `self._fly_target: QPointF`, sanfte Bewegung (Ease-In-Out, max. ~600 px/s), leichtes Auf-und-ab-Wippen (sin), `cloud` an, Blickrichtung zum Ziel.
- `fly_to(x, y)` (globale Koordinaten, Figur so platzieren, dass sie **neben** dem Ziel schwebt und es nicht verdeckt; innerhalb des virtuellen Desktops bleiben, mehrere Monitore beachten).
- `land()` → fliegt zurück über die Taskleiste, Wolke löst sich in kleine Wölkchen auf (Partikel), normaler Fall/Landung.
- Signal `arrived` wenn das Ziel erreicht ist.
- Ziehen mit der Maus während FLY bricht den Flug ab (normales Drag-Verhalten).

## Tests (`tests/test_accessories.py`)
- Jede Figur zeichnet jedes Accessoire ohne Exception auf ein QImage (alle Kombinationen Figur × Accessoire).
- `seasonal_accessory` für 20.10., 24.12., 31.12., 15.07.; `weather_accessory` für Regen/Schnee/Hitze/mild; CPU-Berechnung aus zwei gemockten `GetSystemTimes`-Werten.
- `fly_to`-Zielberechnung bleibt im Bildschirm (reine Funktion `fly_position(target, pet_size, screen_rect)`).
- Screenshot-Sheet `ref/plan/screenshots/accessories.png` (alle Figuren mit hacker_glasses+cloud, party_hat, umbrella) – **ansehen und Optik verbessern**, bis es wirklich süß aussieht.
