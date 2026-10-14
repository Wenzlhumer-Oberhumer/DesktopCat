# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Regressionstests fuer die Fehler aus dem Review von v2.3-v3.0 (Flug, Effekte, Sprache, Pflege)."""
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtGui import QImage, QPainter

import pet_care
from config import Config

_REPO = Path(__file__).resolve().parent.parent


def test_fly_mode_actually_moves_the_pet():
    # Bug: der FLY-Zweig fehlte in _tick -> IT-Guide/Fehler-Doktor/Haftnotiz hingen in der Luft
    from pet_window import PetState, PetWindow
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / "c.json")
        pet = PetWindow(cfg, _REPO)
        pet.drop_in()
        start = (pet._px, pet._py)
        pet.fly_to(pet._px - 400, pet._py - 300)
        assert pet.state == PetState.FLY
        clock = [1000.0]
        with patch("pet_window.time.monotonic", side_effect=lambda: clock[0]):
            pet._last = clock[0]
            for _ in range(40):
                clock[0] += 0.05
                pet._tick()
        assert (pet._px, pet._py) != start
        pet.hide()


def test_water_and_crumbs_effects_paint_without_error():
    # Bugs: QColor("#hex", alpha) gibt es nicht; Kruemel-Schleife zeichnete nichts und rief restore() 5x
    from pet_sprites import PoseContext, compute_pose, draw_character
    pose = compute_pose(PoseContext(key="idle", t=1.0, age=1.0))
    pose.water = 0.4
    pose.crumbs = 0.3
    img = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    draw_character(p, pose, "cat_mochi")
    assert p.end()


def test_main_uses_existing_config_api_for_voice():
    src = (_REPO / "main.py").read_text(encoding="utf-8")
    assert "as_dict()" not in src                          # Config hat nur snapshot()
    assert "GetAsyncKeyState(0x20)" not in src              # PTT folgt dem eingestellten Hotkey
    assert "QTimer.singleShot(0, lambda: self._say(msg" not in src


def test_online_voice_is_opt_in():
    from config import DEFAULTS
    assert DEFAULTS["voice"]["online"] is False
    from voice_tts import TTSManager
    tts = TTSManager()
    with patch.object(TTSManager, "_fallback_sapi") as sapi, patch("voice_tts._EdgeTtsWorker") as edge:
        tts.speak("Hallo", {"voice": {"enabled": True}})
        assert sapi.called and not edge.called             # ohne Opt-in nur die lokale Windows-Stimme


def test_room_mode_and_home_default_off():
    from config import DEFAULTS
    assert DEFAULTS["pet"]["room_mode"] is False and DEFAULTS["pet"]["is_at_home"] is False
    for f in ("pet_window.py", "main.py", "character_tree_dialog.py"):
        src = (_REPO / f).read_text(encoding="utf-8")
        assert not re.search(r'"pet\.(room_mode|is_at_home)", True\)', src), f


def test_care_decay_starts_on_fresh_install():
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / "c.json")
        pet_care.get_care_stats(cfg)
        assert cfg.get("care.last_updated")
        cfg.set("care.last_updated", cfg.get("care.last_updated") - 10 * 3600)
        assert pet_care.get_care_stats(cfg)["hunger"] < 100


def test_feeding_does_not_award_points_twice():
    src = (_REPO / "main.py").read_text(encoding="utf-8")
    assert "pet_care.feed_pet(self.cfg, store)" not in src and "pet_care.wash_pet(self.cfg, store)" not in src
