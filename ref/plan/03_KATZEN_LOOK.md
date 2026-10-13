# Phase 3 – Die Katze sieht aus wie die echte Katze (`ref/*.jpg`)

Referenzfotos: `ref/PXL_*.jpg` (9 Fotos). **Vor dem Coden alle Fotos ansehen.**
Die echte Katze ist eine **dreifarbige Glückskatze (Calico) mit Tabby-Anteil**. Der Kawaii-Stil
(große Augen, runde Formen, alle Animationen) bleibt – nur Färbung/Muster/Details ändern sich.

## Merkmale (aus den Fotos)

| Bereich | Aussehen |
|--------|----------|
| Gesicht Mitte | **Weiß**: Schnauze, Kinn, Wangen unten, schmale weiße Blesse von der Nase bis zwischen die Augen |
| Kopf links (vom Betrachter) | **Oranger Fleck** über Wange, Auge-Außenseite und linkem Ohr |
| Kopf rechts + Stirn | **Braun-graues Tabby** mit dunklen, fast schwarzen Streifen; typisches "M"-Streifenmuster auf der Stirn |
| Stirn Mitte | kleiner **oranger Tupfer** zwischen den Tabby-Streifen |
| Ohren | außen in Fellfarbe der jeweiligen Seite (links orange, rechts tabby), innen **hellrosa**, helle Haarbüschel |
| Augen | **gelbgrün** (Iris), dunkle Pupille, dunkler Lidstrich – im Kawaii-Stil groß lassen |
| Nase | **rosa** |
| Brust, Bauch, Beine, Pfoten | **Weiß** |
| Rücken / Flanken | **Calico-Flecken**: große Bereiche Schwarz-Braun (mit leichter Tabby-Zeichnung) und Orange, unregelmäßig verteilt, dazwischen weiße Stellen am Übergang zum Bauch |
| Schwanz | **braun-schwarz getigert** (Ringe), Spitze dunkel |
| Halsband | **keins** – echte Katze trägt keins → Halsband + Glöckchen entfernen |
| Schnurrhaare | weiß |

## Farbpalette (ersetzt Konstanten in `pet_sprites.py:123-137`)

```python
OUTLINE     = QColor("#3B2A22")   # dunkles Braun statt Rotbraun
WHITE_FUR   = QColor("#FBF8F3")
WHITE_SHADE = QColor("#E9E2D8")   # Schatten im weißen Fell
ORANGE      = QColor("#D9893F")
ORANGE_LIGHT= QColor("#EDAA68")
BLACK_FUR   = QColor("#2A211C")
TABBY       = QColor("#7A6553")   # braun-grau
TABBY_LIGHT = QColor("#9C8A76")
STRIPE      = QColor("#2B2119")
PINK        = QColor("#F2B8BC")   # Ohr innen
NOSE        = QColor("#E99AA3")
MOUTH       = QColor("#B5606C")
EYE_IRIS    = QColor("#C4C25A")   # gelbgrün
EYE_IRIS_DK = QColor("#8FA046")
EYE_PUPIL   = QColor("#1E1A16")
WHISKER     = QColor(255, 255, 255, 200)
```

`FUR`, `FUR_LIGHT`, `FUR_DARK`, `CREAM`, `COLLAR`, `BELL` entfernen bzw. durch obige ersetzen –
**jede Verwendung suchen und umstellen**. Effektfarben (Herzen, Sterne, Musiknoten, Sonnenbrille,
Laptop) bleiben.

## Umsetzung in `pet_sprites.py`

Prinzip: Grundform jeder Körperpartie **weiß** füllen, dann Flecken als `QPainterPath` darüber, die per
`p.setClipPath(<Körperteil-Pfad>)` auf die Silhouette beschnitten werden. So bleiben Flecken bei
allen Animationen (Atmen, Squish, Laufen) automatisch an Ort und Stelle.

1. **`_draw_head`**: weiße Kopfform → Clip auf Kopfform → linke Hälfte orange Ellipse (bis knapp
   unter das Auge) → rechte Hälfte + Stirn Tabby-Ellipse → 3–4 dunkle Streifen auf der Stirn ("M") und
   2 Wangenstreifen rechts → kleiner oranger Tupfer Stirnmitte → weiße Blesse (schmales Oval
   Nase→Stirn) und weiße Schnauzen-/Kinnpartie oben drauf. Clip zurücksetzen. Dann Augen, Nase, Mund,
   Schnurrhaare wie bisher.
2. **`_draw_ear(sign, rot)`**: Außenfarbe abhängig von `sign` (eine Seite orange, andere tabby),
   Innenohr `PINK`.
3. **`_draw_eye`**: Iris-Verlauf `EYE_IRIS`→`EYE_IRIS_DK`, große runde Pupille (Kawaii), Glanzpunkte
   bleiben. Modi (Herz-Augen, geschlossen, Schlaf) unverändert lassen.
4. **Körper (in `draw_cat`)**: weißer Körper → Clip → 2–3 große unregelmäßige Flecken auf dem Rücken
   (schwarz-braun + orange, z. B. je 2–3 überlappende Ellipsen pro Fleck) → 3 feine dunkle
   Tabby-Striche im schwarzen Fleck. Bauch, Brust, Beine, Pfoten bleiben weiß.
5. **`_draw_tail`**: Grundfarbe `TABBY`, 4–5 dunkle Ringe (`STRIPE`) entlang des Pfads, Spitze dunkel.
6. **Halsband/Glöckchen** komplett raus.
7. Flecken **seitenfest**: Beim Spiegeln (Laufen nach links, `flip`) wird die ganze Katze gespiegelt –
   das ist ok, kein Extra-Code.

Performance: `pet_window._signature()` cached Frames – nichts ändern. Pfade, die sich nicht bewegen,
dürfen als Modul-Konstanten vorberechnet werden.

## Sprite-Override (bleibt)

`assets/README.md` + `SpriteLibrary` bleiben. Ergänze in `assets/README.md` einen Abschnitt
"Calico-Sprites erzeugen": Zustandsliste, empfohlene Größe 256×256 pro Frame, transparenter
Hintergrund, Hinweis "Referenz: ref/*.jpg". Keine Sprites erfinden oder generieren.

## Check

- Screenshot der Katze in IDLE, WALK, SLEEP, DANCE, DRAGGED nebeneinander mit einem Referenzfoto
  vergleichen: weiße Front, oranger Fleck links am Kopf, Tabby rechts/Stirn, gelbgrüne Augen, rosa
  Nase, gefleckter Rücken, getigerter Schwanz, kein Halsband.
- Screenshots unter `ref/plan/screenshots/` ablegen.
- Danach Icon neu erzeugen (Phase 1.6).
