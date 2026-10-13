# Phase 5 – Auto-Update über GitHub Releases

## Release-Konvention

- Tag `v<version>` (z. B. `v2.0.1`), Version in `version.py` identisch.
- Assets: `Mochi-Setup-<version>.exe` und `Mochi-Setup-<version>.exe.sha256` (von `build.ps1`).
- Kurzanleitung "Release veröffentlichen" ins README (Version erhöhen → `build.ps1` → GitHub
  Release anlegen, beide Dateien hochladen). Optional `gh release create` Befehl angeben.

## Neue Datei `updater.py`

Läuft in einem `QThread`-Worker (Muster wie `AgentWorker`), blockiert nie die UI.

1. `GET https://api.github.com/repos/{UPDATE_REPO}/releases/latest`
   (Header `Accept: application/vnd.github+json`, `User-Agent: Mochi/<ver>`, Timeout 10 s).
   Fehler/kein Netz/404 → still ignorieren (nur loggen).
2. `tag_name` ohne `v` mit `__version__` vergleichen (Tupel aus ints; kein `packaging` nötig).
3. Neuer? → Signal `update_available(version, notes, setup_url, sha_url)`.
4. Mochi sagt in der Sprechblase: "Es gibt ein Update auf v2.0.1! Klick mich zum Installieren ✨".
   Klick auf Sprechblase oder Tray "Update installieren" → Download.
5. Download nach `%TEMP%\Mochi-Setup-<ver>.exe` (streamend), SHA256 berechnen und mit `.sha256`-Datei
   vergleichen. Abweichung → abbrechen, Datei löschen, Fehlermeldung. **Nie ungeprüft ausführen.**
   URL muss mit `https://github.com/` bzw. `https://objects.githubusercontent.com/` beginnen.
6. Starten: `subprocess.Popen([setup, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"])`,
   dann `Buddy.quit()`. Installer startet Mochi danach selbst neu (siehe `[Run]` in Phase 4).

## Wann prüfen

- Beim Start (30 s verzögert), höchstens einmal pro 24 h (`update.last_check` Zeitstempel in config).
- Tray-Menü: "Nach Updates suchen" (manuell, sagt auch "Du hast die neueste Version 😺").
- Einstellungen: Checkbox "Automatisch nach Updates suchen" (`update.auto`, Standard an).
- Nur wenn `FROZEN` (im Dev-Modus aus).

## Check

- Test mit einem Fake-Release (Version in `version.py` temporär auf `1.9.0` setzen, gebaute exe gegen
  ein echtes Release `v2.0.0` testen): Meldung erscheint, Download, Hash ok, Silent-Update,
  Mochi startet neu mit neuer Version ("Über Mochi").
- Manipulierte `.sha256` → Update wird abgelehnt.
- Kein Internet → keine Fehlermeldung, kein Absturz.
