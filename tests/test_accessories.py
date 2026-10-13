"""Unit-Tests fuer Phase 4 (Accessoires, Anker, Wetter, Saison, PC-Fieber und Fliegen)."""
from __future__ import annotations

import datetime
from pathlib import Path

from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication

from accessories import (
    ACCESSORY_NAMES,
    calculate_cpu_percent,
    fly_position,
    seasonal_accessory,
    weather_accessories,
    weather_accessory,
)
from pet_sprites import (
    CHARACTERS,
    PoseContext,
    compute_pose,
    draw_character,
)
from pet_window import PetState, PetWindow


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_every_character_draws_every_accessory():
    """Jede Figur muss jedes Accessoire ohne Exception sauber zeichnen."""
    _ensure_app()
    img = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)

    for char_id in CHARACTERS:
        for acc in ACCESSORY_NAMES:
            img.fill(0)
            p = QPainter(img)
            try:
                pose = compute_pose(PoseContext(key="idle", t=0.5, age=0.5))
                pose.accessories = (acc,)
                draw_character(p, pose, char_id)
            finally:
                p.end()

        # Auch Kombination aus Wolke + Hackerbrille + Partyhut (Slot-Filterung pruefen)
        img.fill(0)
        p = QPainter(img)
        try:
            pose = compute_pose(PoseContext(key="fly", t=0.5, age=0.5))
            pose.accessories = ("cloud", "hacker_glasses", "party_hat", "scarf", "umbrella")
            draw_character(p, pose, char_id)
        finally:
            p.end()


def test_seasonal_accessory():
    """Saisonale Zubehoer-Erkennung fuer bestimmte Kalendertage."""
    assert seasonal_accessory(datetime.date(2026, 10, 20)) == "pumpkin_hat"
    assert seasonal_accessory(datetime.date(2026, 10, 31)) == "pumpkin_hat"
    assert seasonal_accessory(datetime.date(2026, 12, 24)) == "santa_hat"
    assert seasonal_accessory(datetime.date(2026, 12, 6)) == "santa_hat"
    assert seasonal_accessory(datetime.date(2026, 12, 31)) == "new_year"
    assert seasonal_accessory(datetime.date(2026, 1, 1)) == "new_year"
    assert seasonal_accessory(datetime.date(2026, 7, 15)) is None
    assert seasonal_accessory(datetime.date(2026, 4, 1)) is None


def test_weather_accessory():
    """Wetter-Zubehoer fuer Regen, Schnee, Hitze, Kaelte und mildes Wetter."""
    # Regen
    assert weather_accessory(14.0, "Leichter Regen") == "umbrella"
    assert weather_accessory(18.0, "Regenschauer mit Gewitter") == "umbrella"
    # Schnee
    assert weather_accessory(-1.0, "Schneefall") == "beanie"
    # Hitze
    assert weather_accessory(29.0, "Sonnig") == "sunglasses"
    # Kaelte ohne Schnee
    assert weather_accessory(1.0, "Klar") == "scarf"
    # Mild
    assert weather_accessory(19.0, "Heiter") is None

    # Mehrere Accessoires
    snow_accs = weather_accessories(-2.0, "Dichter Schneefall")
    assert "scarf" in snow_accs
    assert "beanie" in snow_accs

    rain_accs = weather_accessories(12.0, "Regen")
    assert rain_accs == ["umbrella"]


def test_cpu_calculation():
    """CPU-Lastberechnung aus zwei Messungen (GetSystemTimes)."""
    # 90 % Last: 100 Idle von 1000 Gesamtzeit
    t1 = (1000, 2000, 1000)
    t2 = (1100, 2500, 1500)
    assert calculate_cpu_percent(t1, t2) == 90.0

    # 0 % Last: 1000 Idle von 1000 Gesamtzeit
    t3 = (1000, 1000, 0)
    t4 = (2000, 2000, 0)
    assert calculate_cpu_percent(t3, t4) == 0.0

    # 100 % Last: 0 Idle von 1000 Gesamtzeit
    t5 = (1000, 1000, 1000)
    t6 = (1000, 1500, 1500)
    assert calculate_cpu_percent(t5, t6) == 100.0


def test_fly_position_within_screen():
    """fly_position muss die Figur neben dem Ziel platzieren und im Bildschirm halten."""
    screen = (0.0, 0.0, 1920.0, 1080.0)
    pet_size = (160.0, 160.0)

    # Ziel in der Bildschirmmitte (960, 540) -> rechts daneben (960 + 24 = 984)
    fx, fy = fly_position((960.0, 540.0), pet_size, screen)
    assert fx >= 960.0
    assert fx + 160.0 <= 1920.0
    assert 0.0 <= fy <= 1080.0 - 160.0

    # Ziel am rechten Rand (1900, 500) -> links neben das Ziel
    fx2, fy2 = fly_position((1900.0, 500.0), pet_size, screen)
    assert fx2 + 160.0 <= 1920.0
    assert fx2 < 1900.0

    # Ziel oben links (-50, -50) geklemmt
    fx3, fy3 = fly_position((-50.0, -50.0), pet_size, screen)
    assert fx3 >= 0.0
    assert fy3 >= 0.0


class _FakeConfig:
    def __init__(self):
        self._d = {"pet": {"scale": 1.0, "speed": 90, "character": "cat_mochi"}, "animations": {}}
    def get(self, k, default=None):
        return self._d.get(k, default)
    def set(self, k, v):
        self._d[k] = v
    def save(self):
        pass


def test_pet_window_accessory_and_flying():
    """PetWindow Methoden fuer Accessoires, Fliegen und Landen."""
    _ensure_app()
    cfg = _FakeConfig()
    win = PetWindow(cfg, Path("."))

    # Accessoires setzen und entfernen
    win.set_accessory("party_hat", True)
    assert "party_hat" in win._accessories
    win.set_accessory("party_hat", False)
    assert "party_hat" not in win._accessories

    # Temporaeres Accessoire
    win.set_accessory("fan", True, until=1.0) # laengst abgelaufen
    pose = win._build_pose(now=2.0)
    assert "fan" not in win._accessories
    assert "fan" not in pose.accessories

    # fly_to
    win.fly_to(500, 300)
    assert win.state == PetState.FLY
    assert "cloud" in win._accessories
    assert win._fly_target is not None

    # land
    win.land()
    assert win.state in (PetState.FALLING, PetState.IDLE)
    assert "cloud" not in win._accessories
    assert win._fly_target is None
