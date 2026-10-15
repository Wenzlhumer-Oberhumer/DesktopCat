"""Bed context menu, persistent visibility and sleeping on the desktop floor."""
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtWidgets import QApplication, QMenu

from config import Config
from furniture import PetBedWidget
from main import Buddy
from paths import APP_DIR
from pet_window import PetState, PetWindow


def test_right_click_bed_offers_hide_and_requests_it():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as td:
        bed = PetBedWidget(Config(Path(td) / 'config.json'))
        requests = []
        bed.hide_requested.connect(lambda: requests.append(False))
        bed.show()
        selected = []

        def choose_hide(menu, position):
            action = menu.actions()[0]
            selected.append(action.text())
            action.trigger()

        # Exercise the real action and signal without entering a native menu loop.
        with patch.object(QMenu, 'exec', choose_hide):
            bed.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse,
                                QPoint(40, 40), bed.mapToGlobal(QPoint(40, 40))))
        assert selected
        assert requests == [False]
        bed.close()


def test_visibility_toggle_is_persistent_and_can_restore_bed():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / 'config.json'
        cfg = Config(path)
        bed = PetBedWidget(cfg)
        pet = PetWindow(cfg, APP_DIR)
        pet.pet_bed = bed
        buddy = SimpleNamespace(cfg=cfg, pet_bed=bed, pet=pet, _say=MagicMock(),
                                _update_tray_menu=MagicMock())
        pet.pet_bed_requested.connect(lambda: Buddy.toggle_pet_bed(buddy))
        bed.show()
        Buddy.toggle_pet_bed(buddy, False)
        assert not bed.isVisible()
        assert Config(path).get('furniture.bed_visible') is False
        from i18n import tr
        menu = pet.build_menu()
        show_action = next(action for action in menu.actions() if action.text() == tr('menu.show_bed'))
        show_action.trigger()
        assert bed.isVisible()
        assert Config(path).get('furniture.bed_visible') is True
        bed.close()
        pet.close()


def _fall_until_sleep(pet):
    for _ in range(300):
        if pet.state == PetState.SLEEP:
            return
        assert pet.state == PetState.FALLING
        pet._fall(0.02)
    raise AssertionError('Cat did not resume sleeping on the floor')


def test_hiding_bed_lets_cat_sleep_on_floor_at_same_horizontal_position():
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / 'config.json')
        cfg.set('pet.room_mode', True)
        pet = PetWindow(cfg, APP_DIR)
        bed = PetBedWidget(cfg)
        pet.pet_bed = bed
        bed.show()
        pet._px, pet._py = 230.0, pet._ground_y() - 180.0
        pet.state = PetState.SLEEP
        bed.hide()
        pet.on_bed_hidden()
        _fall_until_sleep(pet)
        assert pet._px == 230.0
        assert pet._py == pet._ground_y()
        assert not pet._going_to_bed
        pet.close()
        bed.close()


def test_hidden_bed_allows_sleep_anywhere_on_floor():
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / 'config.json')
        pet = PetWindow(cfg, APP_DIR)
        bed = PetBedWidget(cfg)
        pet.pet_bed = bed
        bed.hide()
        for x in (100.0, 350.0, 600.0):
            pet.wake()
            pet._px, pet._py = x, pet._ground_y()
            pet.go_to_sleep()
            assert pet.state == PetState.SLEEP
            assert pet._px == x
            assert not pet._going_to_bed
        pet.close()
        bed.close()


def test_hiding_bed_on_the_way_to_it_preserves_sleep_request():
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / 'config.json')
        pet = PetWindow(cfg, APP_DIR)
        bed = PetBedWidget(cfg)
        pet.pet_bed = bed
        bed.show()
        pet._px, pet._py = 100.0, pet._ground_y()
        pet.go_to_sleep()
        assert pet._going_to_bed
        bed.hide()
        pet.on_bed_hidden()
        assert pet.state == PetState.SLEEP
        assert pet._px == 100.0
        pet.close()
        bed.close()


def test_showing_and_moving_bed_does_not_teleport_floor_sleeping_cat():
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / 'config.json')
        pet = PetWindow(cfg, APP_DIR)
        bed = PetBedWidget(cfg)
        pet.pet_bed = bed
        bed.hide()
        pet._px, pet._py = 150.0, pet._ground_y()
        pet.go_to_sleep()
        original = (pet._px, pet._py)
        bed.show()
        bed.move(400, 250)
        pet.on_bed_moved(400, 250)
        assert (pet._px, pet._py) == original
        assert pet.state == PetState.SLEEP
        pet.close()
        bed.close()


def test_wake_cancels_sleep_after_fall():
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td) / 'config.json')
        pet = PetWindow(cfg, APP_DIR)
        pet._py = pet._ground_y() - 100
        pet.go_to_sleep()
        assert pet.state == PetState.FALLING
        pet.wake()
        for _ in range(200):
            if pet.state != PetState.FALLING:
                break
            pet._fall(0.02)
        assert pet.state == PetState.IDLE
        pet.close()
