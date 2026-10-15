# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer pet_care.py (Tamagotchi-Care & Charakter-Baum)."""
import time
from unittest.mock import MagicMock

from config import Config
import pet_care
from pet_sprites import CHARACTERS


class DummyConfig:
    def __init__(self, data=None):
        self._d = data or {}

    def get(self, key, default=None):
        return self._d.get(key, default)

    def set(self, key, val):
        self._d[key] = val

    def save(self):
        pass


def test_unlock_tiers_cover_all_characters():
    all_tier_chars = set()
    for chars in pet_care.UNLOCK_TIERS.values():
        all_tier_chars.update(chars)
    assert all_tier_chars == set(CHARACTERS.keys())
    assert len(all_tier_chars) == 17


def test_kylie_always_unlocked():
    store = MagicMock()
    store.get_stat.return_value = "0"
    unlocked, lvl, pts = pet_care.is_character_unlocked("cat_mochi", store)
    assert unlocked is True
    assert lvl == 1
    assert pts == 0


def test_tier_unlock_progression():
    store = MagicMock()
    # 0 FP -> Level 1 -> Kylie und die beiden neuen Kuschelfiguren
    store.get_stat.return_value = "0"
    unlocked_chars = pet_care.get_unlocked_characters(store)
    assert unlocked_chars == {"cat_mochi", "animal_arctic_fox", "animal_cocoa_bunny"}

    # 30 FP -> Level 2 -> Kylie + Hachi (dog_shiba) + Mimi (animal_bunny)
    store.get_stat.return_value = "30"
    unlocked_chars = pet_care.get_unlocked_characters(store)
    assert "dog_shiba" in unlocked_chars
    assert "animal_bunny" in unlocked_chars
    assert "cat_luna" not in unlocked_chars

    # 1300 FP -> Level 8 -> alle 17 Charaktere freigeschaltet
    store.get_stat.return_value = "1300"
    unlocked_chars = pet_care.get_unlocked_characters(store)
    assert len(unlocked_chars) == 17
    assert set(CHARACTERS.keys()) == unlocked_chars


def test_care_stats_immortal_clamped():
    """Prueft, dass Werte selbst nach Monaten Abwesenheit niemals unter 15 % fallen (unsterblich!)."""
    old_time = time.time() - 3600 * 24 * 30  # 30 Tage her
    cfg = DummyConfig({
        "care": {
            "hunger": 100,
            "hygiene": 100,
            "happiness": 100,
            "last_updated": old_time,
        }
    })
    stats = pet_care.get_care_stats(cfg)
    assert stats["hunger"] == pet_care.MIN_STAT
    assert stats["hygiene"] == pet_care.MIN_STAT
    assert stats["happiness"] == pet_care.MIN_STAT
    assert stats["hunger"] >= 15


def test_feed_pet():
    cfg = DummyConfig({
        "care": {
            "hunger": 30,
            "hygiene": 50,
            "happiness": 40,
            "last_updated": time.time(),
        }
    })
    stats, _ = pet_care.feed_pet(cfg)
    assert stats["hunger"] == 100
    assert stats["happiness"] == 55
    saved_care = cfg.get("care")
    assert saved_care["hunger"] == 100


def test_wash_pet():
    cfg = DummyConfig({
        "care": {
            "hunger": 80,
            "hygiene": 25,
            "happiness": 40,
            "last_updated": time.time(),
        }
    })
    stats, _ = pet_care.wash_pet(cfg)
    assert stats["hygiene"] == 100
    assert stats["happiness"] == 55
    saved_care = cfg.get("care")
    assert saved_care["hygiene"] == 100


def test_pet_pet():
    cfg = DummyConfig({
        "care": {
            "hunger": 70,
            "hygiene": 70,
            "happiness": 50,
            "last_updated": time.time(),
        }
    })
    stats = pet_care.pet_pet(cfg)
    assert stats["happiness"] == 70
