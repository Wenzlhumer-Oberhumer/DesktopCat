# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests für v3.0.2 Fixes:
1. Kein Teleportieren zum Bett: Die Katze geht zu Fuß zum Bettchen und legt sich erst dort schlafen.
2. Zuverlässige Desktop-Hintergrund Wiederherstellung (Fuzzy-Match & TranscodedWallpaper-Fallback).
3. Saubere Lively Wallpaper closewp-1 Steuerung.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from config import Config
import lively_wallpaper
from paths import APP_DIR
from pet_window import PetState, PetWindow


def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_go_to_sleep_walks_to_bed(qapp=None):
    """Testet, dass die Katze zum Bettchen spaziert und nicht sofort dorthin teleportiert."""
    _ensure_qapp()
    cfg = Config()
    cfg.set("pet.room_mode", False)
    cfg.set("furniture.bed_visible", True)

    win = PetWindow(cfg, APP_DIR)
    win.show()

    # Mock-Bett erstellen
    mock_bed = MagicMock()
    mock_bed.isVisible.return_value = True
    # Bett steht bei X=500, Y=300 -> dock position (490, 235)
    mock_bed.get_dock_position.return_value = (490.0, 235.0)
    win.pet_bed = mock_bed

    # Katze startet bei X=100, Y=235
    win._px = 100.0
    win._py = 235.0
    win.state = PetState.IDLE

    # Katze soll schlafen gehen
    win.go_to_sleep()

    # Katze darf NICHT sofort teleportiert worden sein!
    assert win._going_to_bed is True
    assert win._walk_target == 490.0
    assert win.state == PetState.WALK_RIGHT
    assert win._px == 100.0  # Kein Teleport!

    # Walk schrittweise simulieren
    win._walk(0.5)  # 90 px/s * 0.5s = 45 px weiter
    assert win._px > 100.0
    assert win._px < 490.0
    assert win.state == PetState.WALK_RIGHT

    # Katze erreicht das Bett
    win._px = 489.0
    win._walk(0.1)  # step reicht um 490.0 zu erreichen
    assert win._px == 490.0
    assert win._py == 235.0
    assert win._going_to_bed is False
    assert win.state == PetState.SLEEP


def test_wake_and_drag_cancels_going_to_bed(qapp=None):
    """Testet, dass das Gehen zum Bettchen abgebrochen wird, wenn die Katze geweckt oder bewegt wird."""
    _ensure_qapp()
    cfg = Config()
    win = PetWindow(cfg, APP_DIR)
    win._going_to_bed = True

    win.wake()
    assert win._going_to_bed is False

    win._going_to_bed = True
    mock_event = MagicMock()
    mock_event.button.return_value = None
    win.mousePressEvent(mock_event)
    assert win._going_to_bed is False


def test_wallpaper_fuzzy_match():
    """Testet, dass _find_fuzzy_existing_file Umlaut- und ß/s-Varianten zuverlässig auflöst."""
    with tempfile.TemporaryDirectory() as tmpdir:
        real_file = Path(tmpdir) / "SoEinSüsesBaby.jpg"
        real_file.write_text("dummy")

        bad_path = str(Path(tmpdir) / "SoEinSüßesBaby.jpg")
        found = lively_wallpaper._find_fuzzy_existing_file(bad_path)
        assert found is not None
        assert Path(found).name == "SoEinSüsesBaby.jpg"


def test_restore_windows_wallpaper_fallback():
    """Testet den Fallback von restore_windows_wallpaper auf TranscodedWallpaper."""
    with patch("ctypes.windll.user32.SystemParametersInfoW", return_value=1) as mock_spi:
        # Ungültiger Pfad -> Fallback greift
        res = lively_wallpaper.restore_windows_wallpaper("C:/NonExistentPath/none.jpg")
        # Wenn TranscodedWallpaper existiert, wird SPI aufgerufen
        assert isinstance(res, bool)


def test_close_lively_wallpaper_command():
    """Testet, dass close_lively_wallpaper 'closewp -1' und taskkill aufruft."""
    with patch("lively_wallpaper.find_lively_exe", return_value=Path("C:/Mock/Lively.exe")), \
         patch("subprocess.run") as mock_run:
        lively_wallpaper.close_lively_wallpaper()
        assert mock_run.call_count >= 2
        args0 = mock_run.call_args_list[0][0][0]
        assert "closewp" in args0
        assert "-1" in args0
        # Prüfen, dass Player-Prozesse beendet werden
        all_taskkills = [args[0][0] for args in mock_run.call_args_list[1:]]
        assert any("Lively.Player.WebView2.exe" in tk for tk in all_taskkills)


def test_perch_levels_includes_bed_without_room_mode():
    """Testet, dass das Katzenbett auch ohne room_mode als Ebene erkannt wird."""
    _ensure_qapp()
    cfg = Config()
    cfg.set("pet.room_mode", False)
    win = PetWindow(cfg, APP_DIR)
    mock_bed = MagicMock()
    mock_bed.isVisible.return_value = True
    mock_bed.get_dock_position.return_value = (500.0, 320.0)
    win.pet_bed = mock_bed

    levels = win._perch_levels(500.0)
    assert 320.0 in levels


def test_perch_levels_horizontal_bounds():
    """Testet, dass das Bett nur dann als Ebene gilt, wenn die Katze horizontal darauf steht."""
    _ensure_qapp()
    cfg = Config()
    cfg.set("pet.room_mode", False)
    win = PetWindow(cfg, APP_DIR)
    mock_bed = MagicMock()
    mock_bed.isVisible.return_value = True
    mock_bed.get_dock_position.return_value = (200.0, 400.0)
    win.pet_bed = mock_bed

    # Bei x=200 ist das Bett vorhanden
    assert 400.0 in win._perch_levels(200.0)
    # Bei x=500 (300px weit weg) ist das Bett NICHT in levels (kein Laufen auf Luft!)
    assert 400.0 not in win._perch_levels(500.0)


def test_walk_approaching_bed_steps_up_smoothly():
    """Testet, dass die Katze beim Annähern an das Bettchen sanft in der Höhe einsteigt."""
    _ensure_qapp()
    cfg = Config()
    cfg.set("pet.room_mode", False)
    win = PetWindow(cfg, APP_DIR)
    mock_bed = MagicMock()
    mock_bed.isVisible.return_value = True
    mock_bed.get_dock_position.return_value = (400.0, 300.0)
    win.pet_bed = mock_bed

    win._going_to_bed = True
    win._walk_target = 400.0
    win._px = 350.0  # 50px vor dem Bett
    win._py = 340.0  # 40px tiefer als das Bett

    win._walk(0.1)  # Ein Schritt
    # _py muss sich sanft nach oben (300.0) bewegt haben, ohne schlagartig auf 300.0 zu springen
    assert win._py < 340.0
    assert win._py >= 300.0


def test_step_off_bed_triggers_fall():
    """Testet, dass die Katze fällt, wenn sie vom Bettrand ins Leere läuft."""
    _ensure_qapp()
    cfg = Config()
    cfg.set("pet.room_mode", False)
    win = PetWindow(cfg, APP_DIR)
    mock_bed = MagicMock()
    mock_bed.isVisible.return_value = True
    mock_bed.get_dock_position.return_value = (200.0, 400.0)
    win.pet_bed = mock_bed

    win.state = PetState.WALK_RIGHT
    win._px = 280.0  # Mehr als 70px vom Bettmittelpunkt entfernt
    win._py = 400.0  # Auf Betthöhe (viel höher als ground_y)
    win._walk_target = 450.0

    win._walk(0.05)
    # Katze muss nun PetState.FALLING sein und fallen, anstatt in der Luft weiterzulaufen
    assert win.state == PetState.FALLING
    assert win._vy > 0


def test_on_bed_moved_moves_sleeping_cat():
    """Testet, dass eine schlafende Katze synchron mit dem bewegten Bett mitwandert."""
    _ensure_qapp()
    cfg = Config()
    win = PetWindow(cfg, APP_DIR)
    mock_bed = MagicMock()
    mock_bed.isVisible.return_value = True
    mock_bed.get_dock_position.return_value = (650.0, 420.0)
    win.pet_bed = mock_bed

    win.state = PetState.SLEEP
    win._px = 200.0
    win._py = 200.0

    win.on_bed_moved(650, 420)
    assert win._px == 650.0
    assert win._py == 420.0


def test_on_bed_hidden_drops_cat():
    """Testet, dass die Katze beim Ausblenden des Betts sanft nach unten fällt."""
    _ensure_qapp()
    cfg = Config()
    win = PetWindow(cfg, APP_DIR)
    win.state = PetState.SLEEP
    win._py = win._ground_y() - 100.0  # 100px über dem Boden

    win.on_bed_hidden()
    assert win.state == PetState.FALLING
    assert win._vy > 0

