# Notizen & Abweichungen vom Plan (Desktop Cat v2.2.0)

## Phase 1–2
- **Kompatibilität gewahrt:** Invariants eingehalten (`AppId={{B42E7A91-8D64-4CE2-A9F7-4DF869D62BC4}}`, `%APPDATA%\Mochi`, `Mochi/GeminiApiKey`, `MochiDesktopPetMutex`, `cat_mochi`).
- **Standard-Name:** `cat_mochi` heißt Kylie. Wenn Nutzer in v2.1.0 den Namen "Mochi" in der Config hatte, wird er automatisch auf "Kylie" migriert; individuelle Namen (z. B. "Sammy") bleiben erhalten.

## Phase 3–4
- **Accessoires & Anker:** Alle 9 Figuren besitzen eigene, feinjustierte Anker (`head_top`, `eyes`, `eye_dx`, `neck`, `paw_r`) in `pet_sprites.py`. Die Accessoire-Zeichnungen skalieren dynamisch mit der Kopf- und Körperbreite.
- **Klick-Overlay:** Das Klick-Overlay nutzt `Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool` und `WS_EX_TRANSPARENT | WS_EX_LAYERED`, sodass es für Maus- und Tastaturklicks vollständig durchklickbar ist. Desktop Cat simuliert keine eigenen Maus- oder Tastaturereignisse.

## Phase 5–6
- **IT-Guide & Error Doctor:** IT-Guide führt Schritt für Schritt durch Windows-Anleitungen mit animierter Wolke, Brille und Leitner-Highlight-Ring. Error Doctor liest Fehlerdialoge via OCR (pytesseract/Windows Vision) und erklärt sie verständlich.
- **Freundschaft & Gamification:** 8 Freundschaftsstufen mit Belohnungen, Pomodoro-Fokusstatistik mit 7-Tage-Balkendiagramm und Leitner-Lernkarten mit KI-Kartengenerierung.

## Phase 7
- **i18n-Architektur:** Vollständige Zweisprachigkeit (Deutsch & Englisch) in `i18n.py` mit `tr(key, **kw)`. Sämtliche Menüs, Dialoge, Figuren-Texte, Tools und Offline-Befehle unterstützen Deutsch und Englisch.
- **Timer-Label Parsing:** Bei englischen Befehlen wie "set a timer for 5 minutes" filtert der Offline-Parser Zeitangaben aus dem `for ...`-Muster heraus und setzt den Standardtitel "Timer".
- **Wetter-Parameter:** Offline-Plan nutzt `"location"` passend zur Tool-Signatur `get_weather(location=...)`.
- **Daten-Wipe:** "forget everything" triggert `wipe_my_data` mit Sicherheitsabfrage vor dem Löschen.

## Phase 8
- **Build & Packaging:** `mochi.spec` und `installer/mochi.iss` erzeugen erfolgreich `dist\DesktopCat-Setup-2.2.0.exe` und die zugehörige `.sha256`-Prüfsumme.
- **Screenshots:** `tools_dev/save_screenshots.py` wurde erweitert, um alle Zustände, Figuren, Anker, Accessoires sowie die 6 neuen UI-Fenster offscreen/nativ zu rendern.
