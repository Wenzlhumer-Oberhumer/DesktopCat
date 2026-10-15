# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Lively Wallpaper Integration (v2.4.0).

Erkennt die laufende Lively Wallpaper Installation, wendet das
dynamische HTML5-Katzenzimmer (assets/lively_room) als Live-Hintergrund an
und stellt beim Beenden automatisch das vorherige Wallpaper wieder her.
"""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from achievements import record_achievement_event
from paths import APP_DIR, DATA_DIR

LIVELY_CANDIDATES = [
    Path("C:/Program Files/Lively Wallpaper/Lively.exe"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Lively Wallpaper\Lively.exe")),
    Path("C:/Program Files (x86)/Lively Wallpaper/Lively.exe"),
]


def find_lively_exe() -> Optional[Path]:
    """Findet den Pfad zur Lively.exe oder livelycu.exe."""
    for p in LIVELY_CANDIDATES:
        if p.is_file():
            return p
    found = shutil.which("livelycu") or shutil.which("lively")
    if found:
        return Path(found)
    # Store installs are not in Program Files or necessarily on PATH.
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
             '(Get-Process -Name Lively -ErrorAction SilentlyContinue | Select-Object -First 1).Path'],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        candidate = Path(result.stdout.strip())
        if result.returncode == 0 and candidate.is_file():
            return candidate
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def get_lively_data_dir() -> Path:
    local = Path(os.environ.get('LOCALAPPDATA', ''))
    regular = local / 'Lively Wallpaper'
    store = local / 'Packages' / '12030rocksdanister.LivelyWallpaper_97hta09mmv6hy' / 'LocalCache' / 'Local' / 'Lively Wallpaper'
    return regular if (regular / 'Settings.json').is_file() else store if (store / 'Settings.json').is_file() else regular


def _read_layout() -> list[dict]:
    path = get_lively_data_dir() / 'WallpaperLayout.json'
    if not path.is_file():
        raise ValueError('Lively bitte einmal starten, bevor du das Katzenzimmer aktivierst.')
    layout = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(layout, list) or any(not isinstance(item, dict) for item in layout):
        raise ValueError('Der Lively-Hintergrundstatus konnte nicht gelesen werden.')
    return layout


def _same_path(left: str, right: str) -> bool:
    return bool(left and right) and os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _wait_for_room(room: str, monitor: int, present: bool) -> bool:
    deadline = time.monotonic() + 5
    while True:
        try:
            found = any(_same_path(item.get('LivelyInfoPath', ''), room)
                        and int(item.get('LivelyScreen', {}).get('Index', 1)) == monitor
                        for item in _read_layout())
            if found == present:
                return True
        except (OSError, ValueError, TypeError):
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)


def is_lively_installed() -> bool:
    return find_lively_exe() is not None


def get_room_package_dir() -> Path:
    """Gibt den Pfad zum assets/lively_room Verzeichnis zurueck."""
    return APP_DIR / "assets" / "lively_room"


def get_lively_library_wallpapers_dir() -> Optional[Path]:
    """Ermittelt das Wallpaper-Library-Verzeichnis von Lively Wallpaper."""
    settings_file = get_lively_data_dir() / 'Settings.json'
    if settings_file.is_file():
        try:
            import json
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            wp_dir = data.get("WallpaperDir")
            if wp_dir:
                p = Path(wp_dir)
                cand = p / "wallpapers" if p.name.lower() != "wallpapers" else p
                cand.mkdir(parents=True, exist_ok=True)
                return cand
        except Exception:
            pass

    default_cand = get_lively_data_dir() / "Library" / "wallpapers"
    try:
        default_cand.mkdir(parents=True, exist_ok=True)
        return default_cand
    except Exception:
        pass
    return None


def deploy_room_to_lively_library() -> Optional[Path]:
    """Kopiert oder aktualisiert das Cozy-Room-Paket in die Lively Wallpaper Library.

    Lively verlangt zwingend, dass Ordner-basierte Wallpaper innerhalb des
    Lively-eigenen Library-Verzeichnisses liegen, andernfalls wird setwp ignoriert.
    """
    wallpapers_dir = get_lively_library_wallpapers_dir()
    if not wallpapers_dir:
        return None

    target_dir = wallpapers_dir / "mochi_cozy_room"
    src_dir = get_room_package_dir()
    if not src_dir.is_dir():
        return None

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            if item.is_file():
                dest = target_dir / item.name
                if not dest.is_file() or dest.stat().st_mtime < item.stat().st_mtime or dest.stat().st_size != item.stat().st_size:
                    shutil.copy2(item, dest)
        return target_dir
    except Exception:
        return None


def _find_fuzzy_existing_file(cand: str) -> Optional[str]:
    """Findet existierende Dateien im selben Ordner bei Umlaut-/Zeichen-Varianten (z. B. s vs. ß)."""
    try:
        p = Path(cand)
        if not p.parent.is_dir():
            return None
        target_clean = p.stem.lower().replace("ß", "s").replace("ss", "s")
        for f in p.parent.iterdir():
            if f.is_file():
                f_clean = f.stem.lower().replace("ß", "s").replace("ss", "s")
                if f_clean == target_clean:
                    return str(f.resolve())
    except Exception:
        pass
    return None


def get_current_windows_wallpaper() -> str:
    """Liest den aktuellen Windows-Wallpaper-Pfad aus der Registry oder dem System-Cache aus."""
    cand = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
            val, _ = winreg.QueryValueEx(key, "Wallpaper")
            cand = str(val).strip()
    except Exception:
        pass

    if cand and os.path.isfile(cand):
        return cand

    if cand:
        fuzzy = _find_fuzzy_existing_file(cand)
        if fuzzy and os.path.isfile(fuzzy):
            return fuzzy

    # Fallback: Windows interner Wallpaper-Cache (TranscodedWallpaper)
    transcoded = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper"
    if transcoded.is_file() and transcoded.stat().st_size > 0:
        return str(transcoded.resolve())

    # Fallback: Standard Windows Wallpaper
    for win_default in (
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Web" / "Wallpaper" / "Windows" / "img0.jpg",
        Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Web" / "4K" / "Wallpaper" / "Windows" / "img0_3840x2160.jpg",
    ):
        if win_default.is_file():
            return str(win_default.resolve())

    return cand


def restore_windows_wallpaper(path: str) -> bool:
    """Stellt das vorherige Windows-Hintergrundbild wieder her (mit Datei-Pruefung und Cache-Fallback)."""
    target = path
    if not target or not os.path.isfile(target):
        if target:
            fuzzy = _find_fuzzy_existing_file(target)
            if fuzzy and os.path.isfile(fuzzy):
                target = fuzzy

    if not target or not os.path.isfile(target):
        reg_wp = get_current_windows_wallpaper()
        if reg_wp and os.path.isfile(reg_wp) and "lively" not in reg_wp.lower():
            target = reg_wp

    if not target or not os.path.isfile(target):
        transcoded = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper"
        if transcoded.is_file() and transcoded.stat().st_size > 0:
            target = str(transcoded.resolve())

    if not target or not os.path.isfile(target):
        for win_default in (
            Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Web" / "Wallpaper" / "Windows" / "img0.jpg",
            Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Web" / "4K" / "Wallpaper" / "Windows" / "img0_3840x2160.jpg",
        ):
            if win_default.is_file():
                target = str(win_default.resolve())
                break

    if not target or not os.path.isfile(target):
        return False

    try:
        import ctypes
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 1, SPIF_SENDCHANGE = 2
        return bool(ctypes.windll.user32.SystemParametersInfoW(20, 0, str(target), 3))
    except Exception:
        return False


def close_lively_wallpaper(monitor: int = 1) -> bool:
    """Close only the display occupied by our room; never kill Lively players."""
    lively_exe = find_lively_exe()
    if not lively_exe:
        return False
    try:
        result = subprocess.run(
            [str(lively_exe), "closewp", "--monitor", str(monitor)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=5)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def apply_lively_wallpaper(cfg=None, store=None) -> tuple[bool, str]:
    """Activate the room and verify Lively's persisted display layout."""
    lively_exe = find_lively_exe()
    if not lively_exe:
        return False, "Lively Wallpaper wurde nicht gefunden. Bitte Lively zuerst starten."
    try:
        layout = _read_layout()
        settings_path = get_lively_data_dir() / 'Settings.json'
        settings = json.loads(settings_path.read_text(encoding='utf-8-sig')) if settings_path.is_file() else {}
        if settings.get('WallpaperArrangement', 0) != 0:
            return False, 'Bitte in Lively die Anordnung „Pro Bildschirm“ wählen, damit andere Monitore unverändert bleiben.'
        monitor = next((int(item['LivelyScreen']['Index']) for item in layout
                        if item.get('LivelyScreen', {}).get('IsPrimary')), 1)
        room_dir = deploy_room_to_lively_library()
        if not room_dir or not (room_dir / 'LivelyInfo.json').is_file():
            return False, 'Das Katzenzimmer konnte nicht in die Lively-Bibliothek kopiert werden.'
        room = str(room_dir.resolve())
        already_ours = any(_same_path(item.get('LivelyInfoPath', ''), room)
                           and int(item.get('LivelyScreen', {}).get('Index', 1)) == monitor for item in layout)
        if cfg is not None and not already_ours:
            original = get_current_windows_wallpaper()
            # Windows can overwrite TranscodedWallpaper while a live wallpaper runs.
            if original and Path(original).name.lower() == 'transcodedwallpaper':
                backup = DATA_DIR / 'wallpaper-original.jpg'
                shutil.copy2(original, backup)
                original = str(backup)
            cfg.set('lively.prev_wallpaper', original)
            previous = next((item.get('LivelyInfoPath', '') for item in layout
                             if int(item.get('LivelyScreen', {}).get('Index', 1)) == monitor), '')
            cfg.set('lively.prev_lively', previous)
        if cfg is not None:
            # Persist ownership before sending the command, for crash recovery.
            cfg.set('lively.room_path', room)
            cfg.set('lively.monitor', monitor)
            cfg.set('lively.active', True)
            cfg.save()
        result = subprocess.run(
            [str(lively_exe), 'setwp', '--file', room, '--monitor', str(monitor)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=8)
        if result.returncode != 0 or not _wait_for_room(room, monitor, True):
            # Keep ownership if Lively did change the layout despite a command error.
            if cfg is not None:
                owned = any(_same_path(item.get('LivelyInfoPath', ''), room) for item in _read_layout())
                cfg.set('lively.active', owned)
                cfg.save()
            return False, 'Lively hat das Katzenzimmer nicht bestätigt. Bitte Lively öffnen und den Hintergrund prüfen.'
        if store is not None:
            record_achievement_event(store, 'wallpaper_activated', 1)
        return True, 'Katzenzimmer in Lively aktiviert! 🖼️✨'
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        return False, f'Katzenzimmer konnte nicht aktiviert werden: {exc}'


def restore_original_wallpaper(cfg, force: bool = False) -> bool:
    """Restore only our room. A manual Lively selection always takes precedence."""
    if cfg is None or not (cfg.get('lively.active', False) or force):
        return True
    try:
        room = cfg.get('lively.room_path', '')
        if not room:
            room = str(get_lively_library_wallpapers_dir() / 'mochi_cozy_room')
        monitor = int(cfg.get('lively.monitor', 1))
        ours = any(_same_path(item.get('LivelyInfoPath', ''), room)
                   and int(item.get('LivelyScreen', {}).get('Index', 1)) == monitor for item in _read_layout())
        restore_static = bool(cfg.get('lively.restore_pending', False))
        if not ours and any(int(item.get('LivelyScreen', {}).get('Index', 1)) == monitor for item in _read_layout()):
            restore_static = False  # The user's newer live wallpaper takes precedence.
        if ours:
            previous = cfg.get('lively.prev_lively', '')
            if previous:
                lively_exe = find_lively_exe()
                if not lively_exe or not Path(previous).is_dir():
                    return False
                result = subprocess.run(
                    [str(lively_exe), 'setwp', '--file', previous, '--monitor', str(monitor)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), timeout=8)
                if result.returncode != 0 or not _wait_for_room(previous, monitor, True):
                    return False
            else:
                if not close_lively_wallpaper(monitor) or not _wait_for_room(room, monitor, False):
                    return False
                restore_static = True
                cfg.set('lively.restore_pending', True)
                cfg.save()
        if restore_static and not restore_windows_wallpaper(cfg.get('lively.prev_wallpaper', '')):
            return False
        for key, value in [('lively.active', False), ('lively.prev_wallpaper', ''),
                           ('lively.prev_lively', ''), ('lively.restore_pending', False),
                           ('pet.is_at_home', False), ('pet.room_mode', False)]:
            cfg.set(key, value)
        cfg.save()
        return True
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return False
