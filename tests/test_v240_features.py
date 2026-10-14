# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Unit-Tests für Desktop Cat v2.4.0 Features:
- Sound-Effekte (prozedurale RIFF/WAVE Synthese)
- Trophäen & Meilensteine (Achievements)
- Saisonale Mini-Events & Quests
- Lively Wallpaper Raum-Paket & Erkennung
- Katzenbett-Möbel (PetBedWidget)
- Interaktive Minispiele (BubblePop & YarnBall)
"""
import datetime
from pathlib import Path
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

import achievements
import furniture
import lively_wallpaper
import minigames
import seasonal_events
import sound_effects


class DummyConfig:
    def __init__(self, data=None):
        self._d = data or {}

    def get(self, key, default=None):
        return self._d.get(key, default)

    def set(self, key, val):
        self._d[key] = val

    def save(self):
        pass


class DummyMemoryStore:
    def __init__(self):
        self._stats = {}

    def get_stat(self, key, default="0"):
        return self._stats.get(key, default)

    def set_stat(self, key, val):
        self._stats[key] = str(val)


# ==============================================================================
#  1. Sound-Effekte
# ==============================================================================
def test_sound_effects_synthesis():
    """Prüft, dass alle 6 Sounds valide RIFF/WAVE Header und Bytes generieren."""
    sound_effects.init_sounds()
    expected_sounds = ["meow", "purr", "pop", "chomp", "water", "squeak"]
    for name in expected_sounds:
        data = sound_effects.SOUNDS.get(name)
        assert data is not None, f"Sound {name} fehlt im Cache"
        assert len(data) > 200, f"Sound {name} ist verdächtig kurz"
        assert data[:4] == b"RIFF", f"Sound {name} hat keinen RIFF-Header"
        assert b"WAVE" in data[:16], f"Sound {name} ist kein WAV-Format"

    # Deaktivierter Sound wird nicht abgespielt
    cfg = DummyConfig({"pet.sound_enabled": False})
    res = sound_effects.play_sound("meow", cfg)
    assert res is False


# ==============================================================================
#  2. Trophäen & Meilensteine (Achievements)
# ==============================================================================
def test_achievements_structure():
    """Prüft die Definition und Struktur aller 12 Achievements."""
    achs = achievements.get_all_achievements()
    assert len(achs) == 12
    ids = set()
    for ach in achs:
        assert "id" in ach
        assert "title" in ach
        assert "desc" in ach
        assert "icon" in ach
        assert "stat" in ach
        assert "target" in ach
        assert "fp_reward" in ach
        assert ach["id"] not in ids, f"Doppelte Achievement-ID: {ach['id']}"
        ids.add(ach["id"])


def test_achievements_progress_and_unlock():
    """Testet Fortschrittszählung und Freischaltung via MemoryStore."""
    store = DummyMemoryStore()

    # Vor dem Event: 0 Blasen geplatzt
    bubble_ach = next(a for a in achievements.ACHIEVEMENTS if a["id"] == "bubble_king")
    cur, target, unlocked = achievements.get_achievement_status(store, bubble_ach)
    assert cur == 0
    assert target == 20
    assert unlocked is False

    # 10 Blasen platzen
    newly = achievements.record_achievement_event(store, "bubbles_popped", 10)
    assert len(newly) == 0
    cur, _, unlocked = achievements.get_achievement_status(store, bubble_ach)
    assert cur == 10
    assert unlocked is False

    # Weitere 10 Blasen -> Ziel erreicht!
    newly = achievements.record_achievement_event(store, "bubbles_popped", 10)
    assert len(newly) == 1
    assert newly[0]["id"] == "bubble_king"
    cur, _, unlocked = achievements.get_achievement_status(store, bubble_ach)
    assert cur == 20
    assert unlocked is True


def test_achievements_direct_unlock():
    """Testet die direkte Freischaltung (z.B. für Event-Quests)."""
    store = DummyMemoryStore()
    ach = achievements.unlock_achievement_direct(store, "room_designer")
    assert ach is not None
    assert ach["id"] == "room_designer"
    # Nochmalige Freischaltung liefert None (bereits freigeschaltet)
    assert achievements.unlock_achievement_direct(store, "room_designer") is None


# ==============================================================================
#  3. Saisonale Mini-Events & Quests
# ==============================================================================
def test_seasonal_events_detection():
    """Prüft die korrekte Erkennung der Feiertage nach Datum."""
    # Halloween: 31. Oktober
    dt_hl = datetime.datetime(2026, 10, 31, 12, 0)
    ev_hl = seasonal_events.get_current_event(dt_hl)
    assert ev_hl["id"] == "halloween"
    assert "🎃" in ev_hl["icon"]

    # Winter: 24. Dezember
    dt_wt = datetime.datetime(2026, 12, 24, 18, 0)
    ev_wt = seasonal_events.get_current_event(dt_wt)
    assert ev_wt["id"] == "winter"
    assert "🎄" in ev_wt["icon"]

    # Frühling: 20. April
    dt_sp = datetime.datetime(2026, 4, 20, 10, 0)
    ev_sp = seasonal_events.get_current_event(dt_sp)
    assert ev_sp["id"] == "spring"

    # Sommer: 15. Juli
    dt_sm = datetime.datetime(2026, 7, 15, 14, 0)
    ev_sm = seasonal_events.get_current_event(dt_sm)
    assert ev_sm["id"] == "summer"


def test_seasonal_quest_progression():
    """Testet Quest-Fortschritt im aktuellen Event."""
    store = DummyMemoryStore()
    event = seasonal_events.get_current_event()
    quest = event["quests"][0]

    cur, target, done = seasonal_events.get_quest_status(store, quest)
    assert cur == 0
    assert done is False

    # Event-Zähler erhöhen
    completed = seasonal_events.record_quest_event(store, quest["stat"], quest["target"])
    assert len(completed) >= 1
    assert completed[0]["id"] == quest["id"]
    cur, target, done = seasonal_events.get_quest_status(store, quest)
    assert cur == target
    assert done is True


# ==============================================================================
#  4. Lively Wallpaper Paket & Erkennung
# ==============================================================================
def test_lively_wallpaper_room_package_structure():
    """Prüft, dass das HTML5/Canvas-Katzenzimmer vollständig und gültig ist."""
    room_dir = lively_wallpaper.get_room_package_dir()
    assert room_dir.is_dir(), f"Verzeichnis existiert nicht: {room_dir}"
    assert (room_dir / "LivelyInfo.json").is_file(), "LivelyInfo.json fehlt"
    assert (room_dir / "index.html").is_file(), "index.html fehlt"
    assert (room_dir / "style.css").is_file(), "style.css fehlt"
    assert (room_dir / "script.js").is_file(), "script.js fehlt"
    assert (room_dir / "preview.png").is_file(), "preview.png fehlt"

    # Windows Wallpaper Registry-Abfrage wirft keinen Fehler
    wp = lively_wallpaper.get_current_windows_wallpaper()
    assert isinstance(wp, str)


# ==============================================================================
#  5. Katzenbett (PetBedWidget)
# ==============================================================================
def test_furniture_pet_bed_widget():
    """Prüft das verschiebbare Katzenbett-Widget und Dock-Koordinaten."""
    app = QApplication.instance() or QApplication([])
    cfg = DummyConfig({"furniture.bed_pos": [350, 450]})
    bed = furniture.PetBedWidget(cfg)
    assert bed.pos().x() == 350
    assert bed.pos().y() == 450

    dock_x, dock_y = bed.get_dock_position()
    assert isinstance(dock_x, float)
    assert isinstance(dock_y, float)
    assert dock_x == 350 - 10
    assert dock_y == 450 - 65

    # Neue Position speichern
    bed.move(500, 600)
    bed.save_position()
    assert cfg.get("furniture.bed_pos") == [500, 600]
    bed.close()


# ==============================================================================
#  6. Minispiele: BubbleWidget & YarnBallWidget
# ==============================================================================
def test_minigames_bubble_widget():
    """Testet Seifenblasen-Widget und Zerplatzen."""
    app = QApplication.instance() or QApplication([])
    bubble = minigames.BubbleWidget(200, 300, 50)
    assert bubble.size_val == 50
    assert bubble.px == 200.0
    assert bubble.py == 300.0

    popped_coords = []
    bubble.popped.connect(lambda x, y: popped_coords.append((x, y)))

    # Simulierter Mausklick
    mock_event = MagicMock()
    mock_event.button.return_value = minigames.Qt.MouseButton.LeftButton
    bubble.mousePressEvent(mock_event)

    assert bubble._popping is True
    assert len(popped_coords) == 1
    bubble.timer.stop()
    bubble.close()


def test_minigames_yarn_ball_widget():
    """Testet das physikalische Wollknäuel-Spielzeug."""
    app = QApplication.instance() or QApplication([])
    yarn = minigames.YarnBallWidget()
    yarn.launch(150, 250, 200, -150)
    assert yarn.px == 150.0
    assert yarn.py == 250.0
    assert yarn.vx == 200.0
    assert yarn.vy == -150.0

    kicked = [False]
    yarn.kicked.connect(lambda: kicked.__setitem__(0, True))
    yarn.kick(350, -280)
    assert yarn.vx == 350.0
    assert yarn.vy == -280.0
    assert kicked[0] is True
    yarn.timer.stop()
    yarn.close()
