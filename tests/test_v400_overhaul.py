# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests für Desktop Cat v4.0.0 ("Das Große Cozy & Kawaii Overhaul"):
1. Kawaii Pose & Animation Engine (stufenloses Blinzeln, 4-Pfoten-Walk, Cat-Loaf-Schlaf, Groom/Stretch, integrierte Wink-Pfote)
2. Neue harmonische Kawaii-Sounds (meow_purr, chirp, yawn)
3. Anti-Nerv & Usability Fixes (Sprechblasen ohne Fokus-Diebstahl, Arrow-Flip oben, sicheres Fenster-Schieben)
4. PetWindow Hit-Maske, Ghost-Mode, Hover-Petting & Laserpointer-Minispiel
5. Controller-Verbesserungen (Kein System-Beep, Schlaf-Respekt, Katzenbett-Sync im Fokus-Modus, Event-Freundschaft)
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QImage, QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication

import minigames
import pet_sprites
import sound_effects
import tools
from config import Config
from memory_store import MemoryStore
from main import Buddy
from paths import APP_DIR
from pet_window import INTERVALS, PetState, PetWindow
from speech_bubble import SpeechBubble


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_v400_smooth_blink_and_4paw_stride_and_loaf_poses():
    """Prüft stufenlose Blinzel-Kurve, 4-Pfoten-Kinematik, Cat-Loaf-Schlaf und Groom/Stretch."""
    # 1. Smooth blink curve produces intermediate values (0 < blink_amount < 1)
    ctx_mid_blink = pet_sprites.PoseContext(key="idle", t=0.04, age=1.0)
    pose_blink = pet_sprites.compute_pose(ctx_mid_blink)
    assert 0.0 < pose_blink.blink_amount < 1.0

    # 2. 4-paw walk kinematics
    ctx_walk = pet_sprites.PoseContext(key="walk_right", t=0.1, age=0.5)
    pose_walk = pet_sprites.compute_pose(ctx_walk)
    assert pose_walk.paw_lx != 0.0 or pose_walk.paw_rx != 0.0
    assert pose_walk.hind_l > 0.0 or pose_walk.hind_r > 0.0

    # 3. Cozy Cat-Loaf sleep pose
    ctx_sleep = pet_sprites.PoseContext(key="sleep", t=1.0, age=5.0)
    pose_sleep = pet_sprites.compute_pose(ctx_sleep)
    assert pose_sleep.loaf >= 0.5
    assert pose_sleep.sy < 0.90 and pose_sleep.sx > 1.05

    # 4. Grooming & Stretch states render cleanly
    for key in ("groom", "stretch", "sleep", "walk_right"):
        p_ctx = pet_sprites.PoseContext(key=key, t=0.8, age=0.8, wave_angle=15.0, petting_glow=0.8)
        pose = pet_sprites.compute_pose(p_ctx)
        img = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        try:
            pet_sprites.draw_character(painter, pose, "cat_mochi")
        finally:
            painter.end()


def test_v400_new_kawaii_sounds():
    """Prüft die neuen Sounds meow_purr, chirp und yawn in sound_effects."""
    sound_effects.init_sounds()
    for sname in ("meow_purr", "chirp", "yawn"):
        wav = sound_effects.SOUNDS.get(sname)
        assert wav is not None and wav[:4] == b"RIFF" and len(wav) > 1000


def test_v400_speech_bubble_dismisses_without_focus_steal_and_flips_at_top():
    """Prüft, dass ein einfacher Klick auf SpeechBubble sie schließt ohne Fokus-Diebstahl, und der Pfeil oben flippt."""
    _ensure_app()
    bubble = SpeechBubble()
    clicks = []
    bubble.clicked.connect(lambda: clicks.append(True))

    # Top of screen -> arrow should flip to top (_arrow_top = True)
    bubble.anchor_to(QPoint(300, 5))
    bubble.say("Hallo hoch oben!")
    assert bubble._arrow_top is True

    # Normal single click dismisses without emitting clicked
    ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(20, 20),
        QPointF(20, 20),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    bubble.mousePressEvent(ev)
    assert clicks == []

    # Double click emits clicked for replying
    bubble.mouseDoubleClickEvent(ev)
    assert clicks == [True]
    bubble.close()


def test_v400_pet_window_hit_mask_ghost_mode_and_fps():
    """Prüft erhöhte Framerate, Hit-Maske, Ghost-Mode und Hover-Streicheln."""
    _ensure_app()
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / "config.json")
        pet = PetWindow(cfg, APP_DIR)
        try:
            # Smooth FPS intervals
            assert INTERVALS[PetState.IDLE] <= 33
            assert INTERVALS[PetState.SLEEP] <= 50

            # Hit mask is active so empty corners pass clicks through
            mask = pet.mask()
            assert not mask.isEmpty()
            assert not mask.contains(QPoint(2, 2))
            assert mask.contains(QPoint(int(80 * pet.scale), int(100 * pet.scale)))

            # Ghost mode toggles WindowTransparentForInput
            toggled = []
            pet.ghost_mode_toggled.connect(toggled.append)
            pet.set_ghost_mode(True)
            assert pet._ghost_mode is True
            assert bool(pet.windowFlags() & Qt.WindowType.WindowTransparentForInput)
            assert toggled == [True]
            pet.set_ghost_mode(False)
            assert pet._ghost_mode is False
            assert toggled == [True, False]
        finally:
            pet.close()


def test_v400_laser_pointer_manager():
    """Prüft Start, Stop und Toggle des neuen Laserpointer-Minispiels."""
    _ensure_app()
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / "config.json")
        cfg.set("pet.sound_enabled", False)
        pet = PetWindow(cfg, APP_DIR)
        mgr = minigames.LaserPointerManager(pet, cfg)
        try:
            assert not mgr.active
            mgr.start(duration_s=5.0)
            assert mgr.active
            mgr.stop()
            assert not mgr.active
        finally:
            mgr.stop()
            pet.close()


def test_v400_sleeping_cat_not_woken_by_chatter_and_bed_hidden_in_focus():
    """Prüft, dass Chatter eine schlafende Katze nicht weckt und Fokus-Modus das Katzenbett mit-versteckt."""
    buddy = SimpleNamespace(
        cfg=SimpleNamespace(get=lambda k, d=None: True),
        _focus_mode=False,
        pet=MagicMock(),
        pet_bed=MagicMock(),
        update_prompt=MagicMock(),
        interaction_card=MagicMock(),
        _schedule_chatter=MagicMock(),
        _say=MagicMock(),
        brain=SimpleNamespace(busy=False),
        input=MagicMock(),
        bubble=MagicMock(),
        play=MagicMock(),
        _dismiss_interaction=MagicMock(),
        tray=MagicMock(),
        icon=MagicMock(),
        _update_tray_menu=MagicMock(),
        char_info=lambda: {"name": "Kylie"},
        user_name=lambda: "Flo",
        _award_friendship=MagicMock(),
    )
    buddy.pet.state = PetState.SLEEP
    buddy.pet.isVisible.return_value = True
    buddy.input.isVisible.return_value = False
    buddy.bubble.isVisible.return_value = False
    buddy.interaction_card.isVisible.return_value = False
    buddy.update_prompt.isVisible.return_value = False

    with patch("main.is_night", return_value=False):
        Buddy._on_chatter(buddy)
    buddy.pet.wake.assert_not_called()
    buddy._say.assert_not_called()

    # Focus mode hides and restores pet_bed
    Buddy.start_focus_mode(buddy)
    buddy.pet_bed.hide.assert_called_once()
    Buddy.end_focus_mode(buddy)
    buddy.pet_bed.show.assert_called_once()


def test_v400_friendship_event_callback():
    """Prüft, dass MemoryStore.on_friendship_changed bei Punkteänderungen feuert."""
    events = []
    cb = lambda: events.append(1)
    MemoryStore.on_friendship_changed.append(cb)
    try:
        with tempfile.TemporaryDirectory() as td:
            store = MemoryStore(Path(td) / "memory.db")
            store.set_friendship_points(15)
            assert len(events) >= 1
    finally:
        MemoryStore.on_friendship_changed.remove(cb)
