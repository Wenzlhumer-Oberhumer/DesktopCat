# Phase 1 – „Desktop Cat“ und Kylie

## 1.1 App-Name „Desktop Cat“ (nur sichtbare Namen!)

| Ort | Neu |
|---|---|
| `installer/mochi.iss` | `AppName=Desktop Cat`, Verknüpfungen `{userprograms}\Desktop Cat`, `{userdesktop}\Desktop Cat`, `OutputBaseFilename=DesktopCat-Setup-{#AppVersion}`, `UninstallDisplayIcon={app}\DesktopCat.exe`, `[Run]`/`[UninstallRun]`/`InitializeSetup` auf `DesktopCat.exe` (taskkill für **beide**: `Mochi.exe` und `DesktopCat.exe`) |
| `mochi.spec` | `name='DesktopCat'` (EXE und COLLECT) → `dist\DesktopCat\DesktopCat.exe` |
| `build.ps1` | Pfade `dist\DesktopCat\DesktopCat.exe`, Setup-Name `DesktopCat-Setup-$Version.exe` (+ `.sha256`) |
| `version_info.txt` | ProductName/FileDescription „Desktop Cat“, OriginalFilename `DesktopCat.exe` |
| `main.py` | Tray-Tooltip, „Über Desktop Cat (vX)“, Fenstertitel, Sprechblasen-Texte |
| `pet_window.py` | `setWindowTitle("Desktop Cat")` |
| `updater.py` | Download-Dateiname `DesktopCat-Setup-{version}.exe`, User-Agent `DesktopCat/{ver}` |
| README, Release-Notes | „Desktop Cat“ |

**Bleibt unverändert (unsichtbare IDs, sonst Datenverlust beim Update):** `AppId` im .iss, `paths.DATA_DIR` (`%APPDATA%\Mochi`), Gemini-Key-Ziel `Mochi/GeminiApiKey` in `gemini.py`, Mutex `MochiDesktopPetMutex` (`AppMutex` im .iss), Dateiname `installer/mochi.iss`, Charakter-ID `cat_mochi`.

**Installer-Aufräumen beim Update von v2.1:**
```ini
[InstallDelete]
Type: files; Name: "{app}\Mochi.exe"
Type: files; Name: "{userprograms}\Mochi.lnk"
Type: files; Name: "{userdesktop}\Mochi.lnk"
```
Autostart: alten Registry-Wert `Mochi` löschen (`[Registry]` mit `Flags: deletevalue` oder `[Code]`), neuen Wert `Desktop Cat` schreiben (Task `autostart`, `uninsdeletevalue`). `paths.set_autostart()` entsprechend auf den neuen Wertnamen umstellen und den alten Wert `Mochi` dabei entfernen.

Der Updater (`updater.py`) erkennt jede `.exe` mit „Setup“ im Namen → installierte v2.1 findet `DesktopCat-Setup-2.2.0.exe`. **Nicht ändern.**

## 1.2 Kylie
- `pet_sprites.CHARACTERS["cat_mochi"]`: `name="Kylie"`, Persona-Text anpassen („Ich bin Kylie, eine verschmuste Glückskatze …“), `pet_sounds`/`ambient_lines` mit „Kylie“ wo es passt. ID bleibt `cat_mochi`.
- `config.DEFAULTS["pet"]["name"] = "Kylie"`. Migration in `Config.load()`: steht `pet.name == "Mochi"` → `"Kylie"` (einmalig, dann speichern).
- Überall, wo der Buddy-Name im Text vorkommt, `get_character_info(char)["name"]` bzw. `pet.name` verwenden – nie fest „Mochi“ (grep nach `Mochi` in `*.py`; Ausnahmen nur die unsichtbaren IDs oben).

## 1.3 Kylie reagiert auf ihren Namen (für jede Figur mit ihrem Namen)
Neue Funktion `name_reaction(text, char_name) -> Optional[str]` in `agent_brain.py` (rein, testbar):
- Text ist nur der Name (`"kylie"`, `"kylie!"`, `"kylie?"`, Groß/Klein egal, auch Kosenamen-Varianten `"kyliiie"`): → Antwort „Ja? 😺 Was gibt's, {user}?“ und **keine** KI-Anfrage.
- Text beginnt mit dem Namen (`"Kylie, wie spät ist es"`): Name + Satzzeichen abschneiden, Rest normal verarbeiten.
- „Wie heißt du?“ / „Wer bist du?“: stolze Vorstellung offline in Figur-Stimme.
In `main.py`/`pet_window.py`:
- Wird der Name erkannt: Ohren hoch (`ear_l/ear_r`), kleiner Hüpfer (`react_happy`), Blick zum Cursor.
- Schläft die Figur (`PetState.SLEEP`) und der Name wird gerufen: Aufwach-Animation (Gähnen = `mouth "o"` + Strecken) + „Mrrrp… ich bin wach! 😽“.
- Name irgendwo in einer längeren Nachricht → zusätzlich Herzchen (`pose.hearts`).

## 1.4 Begrüßung nach dem Update
Config-Flag `rename_intro_done` (Default `False`). Beim ersten Start mit v2.2: Konfetti (`pose.sparkles` + neue bunte Konfetti-Partikel in `_draw_effects`), Sprechblase „Hi {user}! Ich heiße jetzt Kylie – und wohne in Desktop Cat 🎉“, dann Flag setzen.

## Tests (`tests/test_name_kylie.py`)
- `name_reaction` für: „kylie“, „KYLIE!“, „Kylie, wie spät ist es“ (Rest = „wie spät ist es“), „ich mag kylie“ (Herz-Fall), „wie heißt du“, Text ohne Namen (None).
- Config-Migration Mochi → Kylie mit temporärer config.json (nie die echte!).
- `CHARACTERS["cat_mochi"]["name"] == "Kylie"`.
