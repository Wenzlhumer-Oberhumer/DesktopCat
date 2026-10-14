# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer pet_sprites: Charakter-Registry und Zeichnen aller Figuren auf ein QImage."""
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt

import pet_sprites
from pet_sprites import CHARACTERS, PoseContext, compute_pose, draw_character, get_character_info

EXPECTED_IDS = {
    "cat_mochi", "cat_luna", "dog_shiba", "dog_balu", "fantasy_drago",
    "fantasy_byte", "fantasy_spooky", "fantasy_axolotl", "animal_penguin",
}
REQUIRED_KEYS = {"id", "name", "species", "emoji", "desc", "drawer", "sound", "pet_sounds", "ambient_lines", "ai_persona"}


def _default_pose():
    return compute_pose(PoseContext(key="idle", t=1.0, age=1.0))


def test_registry_has_exactly_the_nine_ids():
    assert set(CHARACTERS) == EXPECTED_IDS
    assert len(CHARACTERS) == 9


def test_every_character_has_required_keys():
    for cid, info in CHARACTERS.items():
        missing = REQUIRED_KEYS - set(info)
        assert not missing, f"{cid} fehlt: {missing}"
        assert info["id"] == cid


def test_cat_mochi_drawer_is_draw_cat():
    assert CHARACTERS["cat_mochi"]["drawer"] is pet_sprites.draw_cat


def test_unknown_id_falls_back_to_cat_mochi():
    info = get_character_info("unknown")
    assert info["id"] == "cat_mochi"
    assert info["name"] == "Kylie"


def test_known_id_returns_its_own_info():
    assert get_character_info("dog_balu")["id"] == "dog_balu"


def test_every_character_draws_without_error():
    pose = _default_pose()
    for cid in CHARACTERS:
        img = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        try:
            draw_character(p, pose, cid)
        finally:
            p.end()
        # Die Figur muss mindestens einen sichtbaren Pixel setzen
        visible = any(
            img.pixelColor(x, y).alpha() > 0
            for y in range(0, 160, 2) for x in range(0, 160, 2)
        )
        assert visible, f"{cid} hat nichts gezeichnet"
