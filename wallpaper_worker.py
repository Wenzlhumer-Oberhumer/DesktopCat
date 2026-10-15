# SPDX-License-Identifier: GPL-3.0-or-later
"""Run verified wallpaper operations outside the Qt event loop."""
from PyQt6.QtCore import QThread, pyqtSignal

import lively_wallpaper


class WallpaperWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, cfg, activate: bool, store=None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.activate = activate
        self.store = store

    def run(self) -> None:
        try:
            if self.activate:
                success, message = lively_wallpaper.apply_lively_wallpaper(self.cfg, self.store)
            else:
                success = lively_wallpaper.restore_original_wallpaper(self.cfg, force=True)
                message = ("Der vorherige Hintergrund wurde wiederhergestellt." if success else
                           "Der Hintergrund konnte nicht wiederhergestellt werden. Bitte Lively öffnen und den Hintergrund prüfen.")
        except Exception as exc:
            success = False
            message = f"Der Hintergrund konnte nicht geändert werden: {exc}"
        self.completed.emit(success, message)
