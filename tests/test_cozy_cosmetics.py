"""Rendering and availability regressions for the cozy wardrobe."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter

from accessories import ACCESSORY_NAMES
from pet_care import UNLOCK_TIERS, get_unlocked_characters
from pet_sprites import CHARACTERS, STATE_KEYS, Pose, PoseContext, compute_pose, draw_character


VARIANTS = (("animal_fox", "animal_arctic_fox"), ("animal_bunny", "animal_cocoa_bunny"))
COZY_ITEMS = ("knitted_cardigan", "earmuffs", "cozy_scarf")


def _render(char_id, pose=None):
    image = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        draw_character(painter, pose or Pose(), char_id)
    finally:
        painter.end()
    return image


def test_variants_have_distinct_fur_and_complete_localized_metadata():
    required = {"species", "desc", "sound", "pet_sounds", "ambient_lines", "task_start", "task_done", "ai_persona"}
    for original, variant in VARIANTS:
        assert variant in CHARACTERS
        info = CHARACTERS[variant]
        assert required <= info.keys()
        assert required <= info["en"].keys()
        assert info["id"] == variant
        assert info["anchors"] == CHARACTERS[original]["anchors"]
        assert info["name"] in info["ai_persona"]
        assert info["name"] in info["en"]["ai_persona"]
        assert _render(original) != _render(variant)


def test_new_characters_are_available_without_friendship_points():
    assert {"cat_mochi", "animal_arctic_fox", "animal_cocoa_bunny"} <= get_unlocked_characters()
    all_ids = [char_id for tier in UNLOCK_TIERS.values() for char_id in tier]
    assert len(all_ids) == len(set(all_ids))
    assert set(all_ids) == set(CHARACTERS)


def test_cozy_items_actually_render_for_every_character():
    for item in COZY_ITEMS:
        assert item in ACCESSORY_NAMES
        for char_id in CHARACTERS:
            assert _render(char_id) != _render(char_id, Pose(accessories=(item,))), (char_id, item)


def test_cardigan_and_scarf_can_be_worn_together():
    for _, char_id in VARIANTS:
        combined = _render(char_id, Pose(accessories=COZY_ITEMS))
        for missing in COZY_ITEMS:
            assert combined != _render(char_id, Pose(accessories=tuple(x for x in COZY_ITEMS if x != missing)))


def test_fox_and_bunny_close_their_eyes():
    for char_id in ("animal_fox", "animal_bunny", "animal_arctic_fox", "animal_cocoa_bunny"):
        for eyes in ("blink", "sleep", "closed"):
            assert _render(char_id, Pose(eyes="open")) != _render(char_id, Pose(eyes=eyes)), (char_id, eyes)


def test_variants_render_every_animation_state_with_cozy_outfit():
    for _, char_id in VARIANTS:
        for state in STATE_KEYS:
            pose = compute_pose(PoseContext(key=state, t=0.7, age=0.7))
            pose.accessories = COZY_ITEMS
            assert not _render(char_id, pose).isNull()


class _PreviewConfig:
    def __init__(self):
        self.values = {"pet.character": "animal_arctic_fox", "fun.worn": "cozy_set"}

    def get(self, key, default=None):
        return self.values.get(key, default)


def _appearance_dialog(cfg):
    from PyQt6.QtWidgets import QDialog, QTabWidget
    from settings_dialog import SettingsDialog

    class AppearanceDialog(SettingsDialog):
        def __init__(self):
            QDialog.__init__(self)
            self.cfg = cfg
            self.tabs = QTabWidget(self)
            self._build_tab_appearance()
            self._update_character_preview()

    return AppearanceDialog()


def test_settings_preview_tracks_character_and_outfit_without_saving():
    cfg = _PreviewConfig()
    initial = dict(cfg.values)
    dialog = _appearance_dialog(cfg)
    try:
        for item in (*COZY_ITEMS, "cozy_set"):
            assert dialog.worn_combo.findData(item) >= 0
        dressed = dialog.prev_image.pixmap().toImage()
        assert not dressed.isNull()
        expected = QImage(180, 180, QImage.Format.Format_ARGB32_Premultiplied)
        expected.fill(Qt.GlobalColor.transparent)
        painter = QPainter(expected)
        try:
            painter.scale(180.0 / 160.0, 180.0 / 160.0)
            draw_character(painter, Pose(accessories=("knitted_cardigan", "cozy_scarf", "earmuffs")), "animal_arctic_fox")
        finally:
            painter.end()
        assert dressed == expected
        dialog.worn_combo.setCurrentIndex(dialog.worn_combo.findData(""))
        plain = dialog.prev_image.pixmap().toImage()
        assert plain != dressed
        dialog.char_combo.setCurrentIndex(dialog.char_combo.findData("animal_cocoa_bunny"))
        assert dialog.prev_image.pixmap().toImage() != plain
        assert cfg.values == initial
    finally:
        dialog.close()


def test_cozy_preset_expands_to_wearable_items_in_pet_pose():
    from pathlib import Path
    from pet_window import PetWindow

    window = PetWindow(_PreviewConfig(), Path("."))
    try:
        pose = window._build_pose(window._t0 + 0.5)
        assert set(COZY_ITEMS) <= set(pose.accessories)
        assert "cozy_set" not in pose.accessories
    finally:
        window.close()
