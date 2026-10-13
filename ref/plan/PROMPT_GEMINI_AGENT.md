Du bist ein erfahrener Python/Windows-Entwickler. Du arbeitest im Repo `DesktopCat` (Branch `dev`) an
"Mochi", einem PyQt6-Desktop-Pet für Windows.

AUFGABE: Setze den Plan in `ref/plan/` vollständig um. Lies ZUERST alle Dateien in dieser Reihenfolge:
`00_UEBERSICHT.md`, `01_WINDOWS_APP.md`, `02_GEMINI_LOGIN.md`, `03_KATZEN_LOOK.md`,
`04_INSTALLER_BUILD.md`, `05_AUTO_UPDATE.md`, `06_ABNAHME.md`. Sieh dir außerdem ALLE Fotos
`ref/*.jpg` an – so muss die Katze am Ende aussehen. Lies danach den bestehenden Code
(`main.py`, `pet_window.py`, `pet_sprites.py`, `agent_brain.py`, `tools.py`, `settings_dialog.py`,
`config.py`, `speech_bubble.py`), bevor du etwas änderst.

Die drei Ziele:
1. Mochi wird ein echtes Windows-Programm mit Installer (`Mochi-Setup-<ver>.exe` über PyInstaller +
   Inno Setup): Startmenü, Desktop-Icon, Autostart, Deinstallation, Auto-Update über GitHub Releases.
2. API-Key-Login und OpenAI werden komplett entfernt. Stattdessen gibt es einen Button
   "Mit Google anmelden", der über die mitgelieferte offizielle Gemini CLI (`@google/gemini-cli`,
   Auth-Typ `oauth-personal`) läuft. Der User meldet sich einmal im Browser an, danach nutzt Mochi
   `gemini -p` mit einem JSON-Tool-Protokoll. Die eingebauten Tools der CLI (Shell, Dateien schreiben)
   müssen deaktiviert sein.
3. Die gezeichnete QPainter-Katze wird zur Calico-Katze aus den Fotos (weiße Front, oranger Fleck links
   am Kopf, Tabby-Streifen rechts und auf der Stirn, gelbgrüne Augen, rosa Nase, gefleckter Rücken,
   getigerter Schwanz, kein Halsband). Der bestehende Sprite-Override bleibt.

ARBEITSWEISE:
- Arbeite die Phasen 1→6 der Reihe nach ab. Nach jeder Phase: App starten (`python main.py`), Log
  `%APPDATA%\Mochi\buddy.log` auf Tracebacks prüfen, die Checks der Phase ausführen, dann EIN Commit mit
  einer klaren Message (z. B. "Phase 2: Gemini-CLI-Login statt API-Key").
- Kleinste vollständige Änderung. Bestehende Struktur, Namen und Stil (deutsche UI-Texte, Kommentare
  sparsam) beibehalten. Keine neuen Python-Abhängigkeiten außer `pyinstaller` für den Build.
- Bevor du eine Funktion änderst oder löschst: alle Aufrufer suchen und mitziehen.
- Gemini CLI: Flags, Settings-Keys, Credential-Pfade und den Einstiegspunkt aus `package.json`
  IMMER in der installierten, gepinnten Version prüfen (`--help`, README, `docs/`). Rate nicht. Jede
  Abweichung vom Plan schreibst du in `ref/plan/NOTIZEN_AGENT.md`.
- Sicherheit ist Pflicht: niemals `--yolo`, Downloads per SHA256 prüfen (Node-Zip, Update-Setup),
  Update-URLs auf GitHub begrenzen, `config.json`/Logs/`vendor/`/`build/`/`dist/` nie committen.
- Schreib die Tests aus `06_ABNAHME.md` und lass sie laufen. Hake die Checkliste in `06_ABNAHME.md`
  ab und ehrlich: was du nicht testen konntest (z. B. saubere VM, echter Browser-Login), markierst du als
  "NICHT GETESTET" mit Grund.
- Wenn du an einer Stelle wirklich nicht weiterkommst (z. B. Inno Setup oder Node nicht installiert,
  Login nur mit Mensch möglich): Arbeit sauber bis dahin committen, genau beschreiben, was der User
  tun muss, und mit dem Rest weitermachen.

ABSCHLUSS: Gib eine kurze Zusammenfassung: was pro Phase umgesetzt wurde, welche Dateien neu bzw.
gelöscht sind, Testergebnisse, offene Punkte, und die Befehle, mit denen der User Installer und
Release baut.
