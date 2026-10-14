# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Startet Buddy wirklich (start()), mit Temp-Config und Temp-DB - fing den _is_test_mode()-Absturz."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

import memory_store
from config import Config


def test_buddy_start_runs_without_exception():
    import main
    app = QApplication.instance()
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / "config.json")
        cfg.set("update.auto", False)
        store = memory_store.MemoryStore(Path(td) / "test.db")
        with patch.object(memory_store, "_STORE", store), patch("main.set_autostart"):
            buddy = main.Buddy(app, cfg)
            buddy.start()
            app.processEvents()
            buddy.pet.hide()
            buddy.tray.hide()
