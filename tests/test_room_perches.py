from types import SimpleNamespace
from unittest.mock import patch
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QGuiApplication
from pet_window import PetWindow
from pet_sprites import FLOOR


def _pet(primary=True):
    screen = SimpleNamespace(geometry=lambda: QRect(0, 0, 1000, 800))
    pet = SimpleNamespace(_play_screen=None, cfg=SimpleNamespace(get=lambda key, default=None: True),
        _px=500, scale=1, width=lambda: 200, pet_bed=None,
        _screen_for_x=lambda x: screen, _ground_y=lambda: 800-FLOOR,
        _room_surfaces=lambda: PetWindow._room_surfaces(pet))
    pet.screen = screen
    return pet


def test_room_surfaces_match_visible_shelf_and_sill_only():
    pet = _pet()
    shelf = 800*.35-FLOOR
    sill = 800*.65-FLOOR
    with patch('pet_window.QGuiApplication.primaryScreen', return_value=pet.screen):
        assert shelf in PetWindow._perch_levels(pet, 400)  # center at500
        assert shelf not in PetWindow._perch_levels(pet, 50)
        assert sill in PetWindow._perch_levels(pet, 700)
        assert sill not in PetWindow._perch_levels(pet, 400)


def test_room_surfaces_do_not_exist_on_secondary_display():
    pet = _pet(primary=False)
    assert PetWindow._room_surfaces(pet) == []


def test_room_surfaces_accept_a_real_qscreen():
    pet = _pet()
    screen = QGuiApplication.primaryScreen()
    pet._screen_for_x = lambda x: screen
    assert len(PetWindow._room_surfaces(pet)) == 2
