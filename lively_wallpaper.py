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


def get_lively_library_wallpapers_dir() -> Optional[Path]:
    """Ermittelt das Wallpaper-Library-Verzeichnis von Lively Wallpaper."""
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    settings_file = local_app_data / "Lively Wallpaper" / "Settings.json"
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

    default_cand = local_app_data / "Lively Wallpaper" / "Library" / "wallpapers"
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


def close_lively_wallpaper() -> bool:
    """Schliesst aktive Lively-Hintergruende zuverlaessig."""
    lively_exe = find_lively_exe()
    closed = False
    if lively_exe:
        try:
            # Lively CLI schliesst Hintergruende mit 'closewp --monitor -1'
            subprocess.run(
                [str(lively_exe), "closewp", "--monitor", "-1"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=4,
            )
            closed = True
        except Exception:
            pass

    # Sicherheits-Cleanup: Falls Lively Player (WebView2 oder CefSharp) noch den Desktop verdecken
    for player_exe in ("Lively.Player.WebView2.exe", "Lively.Player.CefSharp.exe"):
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", player_exe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=2,
            )
            closed = True
        except Exception:
            pass

    return closed


def apply_lively_wallpaper(cfg=None, store=None) -> tuple[bool, str]:
    """Aktiviert das HTML5-Katzenzimmer in Lively Wallpaper und speichert den vorherigen Hintergrund."""
    lively_exe = find_lively_exe()
    if not lively_exe:
        return False, "Lively Wallpaper wurde auf deinem PC nicht gefunden."

    room_dir = get_room_package_dir()
    if not room_dir.is_dir() or not (room_dir / "LivelyInfo.json").is_file():
        return False, f"Katzenzimmer-Paket nicht gefunden unter: {room_dir}"

    # Vorherigen Hintergrund sichern (nur wenn valide Datei und kein temporäres Lively-Paket)
    if cfg is not None and not cfg.get("lively.prev_wallpaper"):
        current_wp = get_current_windows_wallpaper()
        if current_wp and os.path.isfile(current_wp) and "lively" not in current_wp.lower():
            cfg.set("lively.prev_wallpaper", current_wp)
            cfg.save()

    # Lively verlangt Ordner innerhalb der eigenen Library (sonst wird setwp ignoriert)
    deployed_dir = deploy_room_to_lively_library()
    target_dir = deployed_dir if (deployed_dir and (deployed_dir / "LivelyInfo.json").is_file()) else room_dir

    abs_path = str(target_dir.resolve())
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
    prev_wp = cfg.get("lively.prev_wallpaper", "") if cfg is not None else ""
    if not prev_wp or not os.path.isfile(prev_wp):
        cand = get_current_windows_wallpaper()
        if cand and os.path.isfile(cand) and "lively" not in cand.lower():
            prev_wp = cand
            if cfg is not None:
                cfg.set("lively.prev_wallpaper", prev_wp)
                cfg.save()

    close_lively_wallpaper()
    res = restore_windows_wallpaper(prev_wp)
    # WICHTIG: prev_wallpaper bewusst NICHT löschen, damit das Originalbild dauerhaft
    # als sichere Referenz erhalten bleibt und jederzeit wiederhergestellt werden kann!
    return res
