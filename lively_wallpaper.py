# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Lively Wallpaper Integration (v2.4.0).

Erkennt die laufende Lively Wallpaper Installation, wendet das
dynamische HTML5-Katzenzimmer (assets/lively_room) als Live-Hintergrund an
und stellt beim Beenden automatisch das vorherige Wallpaper wieder her.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from achievements import record_achievement_event
from paths import APP_DIR

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
    return Path(found) if found else None


def is_lively_installed() -> bool:
    return find_lively_exe() is not None


def get_room_package_dir() -> Path:
    """Gibt den Pfad zum assets/lively_room Verzeichnis zurueck."""
    return APP_DIR / "assets" / "lively_room"


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
    if transcoded.is_file():
        return str(transcoded.resolve())

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
        transcoded = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper"
        if transcoded.is_file():
            target = str(transcoded.resolve())

    if not target or not os.path.isfile(target):
        return False

    try:
        import ctypes
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 1, SPIF_SENDCHANGE = 2
        return bool(ctypes.windll.user32.SystemParametersInfoW(20, 0, str(target), 3))
    except Exception:
        return False


def close_lively_wallpaper() -> bool:
    """Schliesst aktive Lively-Hintergruende zuverlaessig."""
    lively_exe = find_lively_exe()
    if not lively_exe:
        return False
    try:
        # Lively CLI schliesst Hintergruende mit 'closewp -1'
        subprocess.run(
            [str(lively_exe), "closewp", "-1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=5,
        )
        return True
    except Exception:
        pass
    return False


def apply_lively_wallpaper(cfg=None, store=None) -> tuple[bool, str]:
    """Aktiviert das HTML5-Katzenzimmer in Lively Wallpaper und speichert den vorherigen Hintergrund."""
    lively_exe = find_lively_exe()
    if not lively_exe:
        return False, "Lively Wallpaper wurde auf deinem PC nicht gefunden."

    room_dir = get_room_package_dir()
    if not room_dir.is_dir() or not (room_dir / "LivelyInfo.json").is_file():
        return False, f"Katzenzimmer-Paket nicht gefunden unter: {room_dir}"

    # Vorherigen Hintergrund sichern
    if cfg is not None and not cfg.get("lively.prev_wallpaper"):
        current_wp = get_current_windows_wallpaper()
        if current_wp:
            cfg.set("lively.prev_wallpaper", current_wp)
            cfg.save()

    abs_path = str(room_dir.resolve())
    try:
        # Lively setzt Wallpaper via 'setwp --file <path>'
        subprocess.Popen(
            [str(lively_exe), "setwp", "--file", abs_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if store is not None:
            record_achievement_event(store, "wallpaper_activated", 1)

        return True, "Cozy-Room Live-Wallpaper erfolgreich in Lively aktiviert! 🖼️✨"
    except Exception as exc:
        return False, f"Fehler beim Starten von Lively: {exc}"


def restore_original_wallpaper(cfg) -> bool:
    """Stellt das urspruengliche Hintergrundbild wieder her, wenn Desktop Cat beendet wird."""
    prev_wp = cfg.get("lively.prev_wallpaper", "")
    close_lively_wallpaper()
    res = restore_windows_wallpaper(prev_wp)
    if res and prev_wp:
        cfg.set("lively.prev_wallpaper", "")
        cfg.save()
    return res
