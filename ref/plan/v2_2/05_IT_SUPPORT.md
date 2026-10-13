# Phase 5 – IT-Support: Hackerbrille, Wolke, Klick-Anleitung

## Ablauf aus User-Sicht
1. User fragt etwas Technisches („Wo ändere ich in Word die Formatvorlage?“, „Wie mache ich in Windows den Dunkelmodus an?“).
2. Figur setzt `hacker_glasses` auf, kleine Code-Zeichen schweben, Sprechblase: „IT-Support-Modus aktiviert! 🕶️ Ich zeig's dir Schritt für Schritt.“
3. Figur steigt auf die `cloud` und fliegt (`fly_to`) neben die Stelle, wo geklickt werden muss.
4. Dort erscheint der **Klick-Zeiger** (Overlay): pulsierender Ring um das Ziel + Pfeil von der Figur zum Ziel + Label **„Linksklick“ / „Rechtsklick“ / „Doppelklick“ / „Tippen: …“ / „Scrollen“**.
5. Sprechblase: „Schritt 1 von ~3: Klick hier auf ‚Entwurf‘.“ mit Buttons **„Weiter ▶“**, **„Nochmal zeigen 🔁“**, **„Fertig ✖“**.
6. User klickt selbst. Nach „Weiter“ → neues Bildschirmfoto → nächster Schritt.
7. Fertig → Ring weg, Figur fliegt zurück, Brille ab, „Geschafft! 🎉“ + `celebrate()`.

**Desktop Cat klickt, tippt oder bewegt NIE selbst die Maus.** Kein `SendInput`, kein `SetCursorPos`, kein pyautogui.

## 5.1 Erkennen
- Neues Tool `start_it_guide(question: str)` in `tools.TOOL_SPECS` (Beschreibung für Gemini: „Nutze dies, wenn der Nutzer wissen will, WO/WIE er etwas in einem Programm oder in Windows findet, einstellt oder klickt.“). Ausführung **nicht** in `tools.execute`, sondern als Signal an die UI (ähnlich wie Fenster öffnen): `AgentWorker` liefert ein Ergebnis mit `action="it_guide"`, `main.py` startet den Guide.
- Offline (ohne Key) gibt es keinen Guide: freundliche Antwort „Für die Klick-Anleitung brauche ich meinen Gemini-Key 🔑“.

## 5.2 `it_guide.py` (neu): Schritt-Logik
- `GuideSession(question, user_name, char)` hält `step_no`, `history` (bisherige Schritte als Text).
- `next_step()` im QThread-Worker:
  1. Bildschirmfoto des **Monitors, auf dem das aktive Fenster ist** (Qt `QScreen.grabWindow(0)`), auf max. 1600 px Breite skalieren, PNG → base64. Figur und Overlay vorher kurz ausblenden (`hide()`, 120 ms warten), damit sie nicht auf dem Foto sind; danach wieder zeigen.
  2. `gemini.ask(prompt, image_b64=..., timeout_s=45)` mit Prompt:
     ```
     Du bist ein geduldiger IT-Helfer. Frage des Nutzers: "<question>".
     Bisherige Schritte: <history>.
     Schau dir den Screenshot an und gib GENAU EINEN nächsten Schritt als JSON zurück, ohne Markdown:
     {"say": "<kurze Anweisung auf Deutsch, 1 Satz>", "action": "left|right|double|type|scroll|none",
      "target": "<Name des Elements>", "box_2d": [ymin, xmin, ymax, xmax], "done": false,
      "total_steps": <Schätzung>}
     box_2d in 0-1000 normierten Koordinaten des Bildes. Wenn das Ziel nicht sichtbar ist (z. B. Programm nicht offen), action "none", box_2d null und say erklärt, was der Nutzer zuerst öffnen soll. Wenn fertig: "done": true.
     Erfinde keine Positionen. Wenn du unsicher bist, box_2d null.
     ```
  3. Antwort robust parsen (gleiche Technik wie `parse_cli_response`): `parse_guide_step(text) -> dict | None`.
  4. `box_to_screen(box_2d, screen_geometry, image_size) -> QRect` (0–1000 → Pixel, Monitor-Offset addieren, **DPI-Skalierung** beachten: Qt-Geometrie ist in logischen Pixeln, das Foto in Geräte-Pixeln → `devicePixelRatio` berücksichtigen). Box auf den Bildschirm clampen; unplausible Boxen (Fläche 0, > 50 % des Bildschirms) → wie `null` behandeln.
- Max. 12 Schritte, dann freundlich beenden.

## 5.3 `guide_overlay.py` (neu): Klick-Zeiger
- Rahmenloses, transparentes, **durchklickbares** Vollbild-Overlay über dem betroffenen Monitor: `Qt.WindowType.FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowTransparentForInput`, `WA_TranslucentBackground`, `WA_ShowWithoutActivating`.
- Zeichnet: pulsierenden Ring (Rosa/Grün, 2 Ringe, 60 fps via QTimer), dezenten Pfeil von der Figur zur Box, Label-Pille mit Maus-Icon und Text („🖱️ Linksklick“, „🖱️ Rechtsklick“, „🖱️🖱️ Doppelklick“, „⌨️ Tippen: …“, „🖲️ Scrollen“).
- Das Overlay darf **nie** Klicks abfangen (Test: User kann durch den Ring hindurch klicken).

## 5.4 Sprechblase mit Buttons
`SpeechBubble` (vorhandene Klasse) um optionale Buttons erweitern (`show_with_actions(text, actions: list[(label, callback)])`) – im vorhandenen Bubble-Stil. Buttons: Weiter / Nochmal zeigen / Fertig. Esc = Fertig.

## 5.5 Fehlermeldungs-Doktor
- Rechtsklick-Menü „🩺 Was heißt dieser Fehler?“ und Sprachbefehl („was bedeutet diese fehlermeldung“).
- Bildschirmfoto → `gemini.ask` („Erkläre die sichtbare Fehlermeldung in einfachen Worten, 2–3 Sätze, dann 1–3 Lösungsschritte.“) → Hackerbrille + Antwort in Sprechblase; Button „Zeig's mir 🕶️“ startet den Guide mit der Lösung als Frage.

## 5.6 Kopieren & Erklären
- Eigener globaler Hotkey (Default `ctrl+alt+e`, in Einstellungen änderbar, gleiches Muster wie der vorhandene Hotkey / `HotkeyFilter` – zweite Registrierung mit eigener ID).
- Liest die Zwischenablage (Qt `QGuiApplication.clipboard().text()`), max. 4000 Zeichen.
- Kleines Auswahlmenü an der Figur: „💡 Erklären“, „🌍 Übersetzen (DE↔EN)“, „📝 Zusammenfassen“, „✍️ Verbessern“. Ergebnis in einer größeren `FloatingCard` mit „📋 Kopieren“-Button.
- Leere Zwischenablage → „Markier erst etwas und drück Strg+C 😺“.

## Tests (`tests/test_it_guide.py`)
- `parse_guide_step` mit gültigem JSON, Markdown-Zaun, `box_2d: null`, kaputtem JSON, `done: true`.
- `box_to_screen` mit 2 Monitoren (zweiter links mit negativem x), DPI 1.0 und 1.5, unplausiblen Boxen.
- `GuideSession` mit gemocktem `gemini.ask` und gemocktem Screenshot: 3 Schritte bis `done`, Abbruch nach 12.
- Overlay-Flags: `windowFlags()` enthält `WindowTransparentForInput`.
- Kein Code-Pfad ruft `SetCursorPos`/`SendInput`/`mouse_event` auf (grep-Test über alle `*.py`).
