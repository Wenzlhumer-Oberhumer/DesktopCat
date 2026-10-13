"""Zentrale Pfade: Ressourcen (read-only, ggf. im PyInstaller-Bundle) und Nutzerdaten (%APPDATA%\\Mochi)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))   # assets/, vendor/
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Mochi"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def set_autostart(on: bool) -> None:
    """Setzt oder entfernt den Autostart-Eintrag in der Windows-Registry (nur wenn FROZEN)."""
    if not FROZEN:
        return
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if on:
                exe = f'"{sys.executable}"'
                winreg.SetValueEx(key, "Mochi", 0, winreg.REG_SZ, exe)
            else:
                try:
                    winreg.DeleteValue(key, "Mochi")
                except FileNotFoundError:
                    pass
    except OSError as exc:
        print(f"[paths] Autostart setzen fehlgeschlagen: {exc}")
