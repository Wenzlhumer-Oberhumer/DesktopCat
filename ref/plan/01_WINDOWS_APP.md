# Phase 1 – Mochi als echtes Windows-Programm vorbereiten

Ziel: Der Code läuft identisch aus dem Quellordner **und** als PyInstaller-exe aus `C:\Program Files\Mochi\`
(schreibgeschützt!). Alles Beschreibbare geht nach `%APPDATA%\Mochi\`.

## 1.1 Neue Datei `paths.py` (klein halten)

```python
"""Zentrale Pfade: Ressourcen (read-only, ggf. im PyInstaller-Bundle) und Nutzerdaten (%APPDATA%\\Mochi)."""
import os, sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))   # assets/, vendor/
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Mochi"
DATA_DIR.mkdir(parents=True, exist_ok=True)
```

## 1.2 Neue Datei `version.py`

```python
__version__ = "2.0.0"
UPDATE_REPO = "Nairolf/Mochi"   # GitHub owner/repo für Releases – vom User anpassen
```

## 1.3 Pfade umstellen (alle Stellen!)

| Datei | Alt | Neu |
|------|-----|-----|
| `config.py:11-12` | `BASE_DIR / "config.json"` | `DATA_DIR / "config.json"` |
| `main.py:13-14` | `BASE_DIR` + `os.chdir(BASE_DIR)` | `os.chdir(DATA_DIR)` (beschreibbar) |
| `main.py:18` | `BASE_DIR / "buddy.log"` | `DATA_DIR / "buddy.log"` – bei >2 MB beim Start nach `buddy.log.1` rotieren |
| `main.py:206` | `PetWindow(cfg, BASE_DIR)` | `PetWindow(cfg, APP_DIR)` (Sprites aus Bundle) |
| `tools.py:22-23` | `BASE_DIR / "desktop_organize_log.json"` | `DATA_DIR / ...` |
| `settings_dialog.py` | Button "config.json öffnen" | öffnet `DATA_DIR / "config.json"` |

Zusätzlich: `pet_sprites.SpriteLibrary` soll **auch** `DATA_DIR / "assets"` durchsuchen (zuerst), damit
User eigene Sprites ablegen können, ohne in `Program Files` zu schreiben.

**Migration (einmalig):** Wenn `DATA_DIR/config.json` fehlt, aber neben dem Quellcode eine alte
`config.json` liegt → kopieren, dabei Schlüssel `gemini_api_key`, `openai_*`, `provider` verwerfen.

## 1.4 Autostart

In `config.DEFAULTS` neu: `"autostart": True`. Umsetzung mit `winreg` (Stdlib):

- Schlüssel `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, Wert `Mochi`.
- Wert = `"<sys.executable>"` wenn `FROZEN`, sonst nicht setzen (im Dev-Modus Autostart ignorieren).
- Funktion `set_autostart(on: bool)` in `paths.py` oder `main.py`; aufrufen beim Start und beim
  Speichern der Einstellungen. Checkbox "Mit Windows starten" im `SettingsDialog`.
- Installer setzt den Wert ebenfalls (Task-Checkbox) und löscht ihn beim Deinstallieren (siehe Phase 4).

## 1.5 Single-Instance + Installer-Mutex

`main._single_instance()` existiert. Ergänzen: einen benannten Windows-Mutex `MochiDesktopPetMutex`
erzeugen (`win32event.CreateMutex`, pywin32 ist schon Abhängigkeit) und für die Laufzeit halten.
Inno Setup nutzt `AppMutex=MochiDesktopPetMutex`, um vor Update/Deinstallation zu warnen bzw. zu schließen.

## 1.6 Icon

`pet_sprites.render_icon()` existiert. Einmaliges Hilfsskript `tools_dev/make_icon.py`: rendert die (neue
Calico-)Katze in 16/24/32/48/64/128/256 px und speichert `assets/mochi.ico` (Pillow kann
Multi-Size-ICO). Das ICO wird für exe, Installer, Verknüpfungen und Tray benutzt. Erst nach Phase 3
final erzeugen.

## 1.7 Aufräumen

- `.gitignore` anlegen: `__pycache__/`, `*.pyc`, `buddy.log*`, `config.json`, `desktop_organize_log.json`,
  `build/`, `dist/`, `vendor/`, `*.spec.bak`.
- `start.bat` / `start_mit_konsole.bat` bleiben für Entwickler.
- Tray-Menü: Eintrag "Über Mochi" zeigt `__version__`.

## Check

`python main.py` startet, `%APPDATA%\Mochi\config.json` + `buddy.log` werden angelegt, im Quellordner
entsteht **keine** neue Datei.
