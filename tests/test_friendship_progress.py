"""Real SQLite awards must reach the tree, unlock checks and friendship screen."""
import tempfile
import datetime
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from config import Config
from memory_store import MemoryStore
from fun import add_friendship_points, level_for, LEVEL_THRESHOLDS
import pet_care


def test_awarded_points_unlock_characters_and_persist_after_restart():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)/'memory.db'
        store = MemoryStore(path)
        store.set_friendship_points(24)
        added, level_up, level = add_friendship_points(store, 'chat', '2026-10-15')
        assert (added, level_up, level) == (1, True, 2)
        restarted = MemoryStore(path)
        assert restarted.get_friendship_points() == 25
        assert pet_care.is_character_unlocked('dog_shiba', restarted)[0]
        assert 'animal_bunny' in pet_care.get_unlocked_characters(restarted)


def test_character_tree_and_friendship_screen_read_same_real_points():
    from character_tree_dialog import CharacterTreeDialog
    from fun_dialogs import FriendshipDialog
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td)/'config.json')
        store = MemoryStore(Path(td)/'memory.db')
        store.set_friendship_points(30)
        tree = CharacterTreeDialog(cfg, store)
        friend = FriendshipDialog(store, cfg, {'name': 'Kylie'})
        try:
            assert tree.lbl_level_badge.text() == 'Level 2'
            assert '30 FP' in tree.lbl_level_desc.text()
            assert tree.bar_fp.value() == friend.bar.value() == 10
            add_friendship_points(store, 'curious', '2026-10-15')
            tree.refresh_all()
            assert '33 FP' in tree.lbl_level_desc.text()
        finally:
            tree.close()
            friend.close()


def test_every_unlock_threshold_matches_level_calculation():
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        for level, threshold in enumerate(LEVEL_THRESHOLDS, 1):
            store.set_friendship_points(threshold)
            assert level_for(threshold)[0] == level
            unlocked = pet_care.get_unlocked_characters(store)
            expected = {cid for req, ids in pet_care.UNLOCK_TIERS.items() if req <= level for cid in ids}
            assert unlocked == expected


def test_concurrent_awards_cannot_lose_points_or_exceed_daily_limit():
    from concurrent.futures import ThreadPoolExecutor
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: add_friendship_points(store, 'chat', '2026-10-15'), range(30)))
        assert sum(added for added, _, _ in results) == 20
        assert store.get_daily_friendship_count('chat', '2026-10-15') == 20
        assert store.get_friendship_points() == 20


def test_award_failure_rolls_back_points_and_daily_counter():
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        store.set_friendship_points(24)
        with store._db() as db:
            db.execute("CREATE TRIGGER refuse_points BEFORE UPDATE ON friendship BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        try:
            add_friendship_points(store, 'chat', '2026-10-15')
        except Exception:
            pass
        else:
            raise AssertionError('The test database should reject the points update')
        assert store.get_friendship_points() == 24
        assert store.get_daily_friendship_count('chat', '2026-10-15') == 0


def test_tree_feed_routes_through_live_pet_once():
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from character_tree_dialog import CharacterTreeDialog
    with tempfile.TemporaryDirectory() as td:
        cfg = Config(Path(td)/'config.json')
        store = MemoryStore(Path(td)/'memory.db')
        pet = MagicMock()
        # The live pet's treat_given signal is connected to Buddy._on_treat.
        pet.give_treat.side_effect = lambda: pet_care.feed_pet(cfg, store)
        dialog = SimpleNamespace(cfg=cfg, store=store, pet=pet, refresh_all=MagicMock())
        CharacterTreeDialog._on_feed_clicked(dialog)
        assert store.get_friendship_points() == 2
        assert store.get_daily_friendship_count('treat', datetime.date.today().isoformat()) == 1


def test_trophy_pays_advertised_reward_once_without_using_treat_limit():
    import achievements
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        unlocked = achievements.record_achievement_event(store, 'bubbles_popped', 20)
        assert len(unlocked) == 1
        assert store.get_friendship_points() == unlocked[0]['fp_reward'] == 50
        assert store.get_daily_friendship_count('treat', datetime.date.today().isoformat()) == 0
        achievements.record_achievement_event(store, 'bubbles_popped', 1)
        assert store.get_friendship_points() == 50
        direct = achievements.unlock_achievement_direct(store, 'room_designer')
        assert store.get_friendship_points() == 50 + direct['fp_reward']
        assert achievements.unlock_achievement_direct(store, 'room_designer') is None
        assert store.get_friendship_points() == 50 + direct['fp_reward']


def test_parallel_trophy_events_preserve_progress_and_pay_once():
    from concurrent.futures import ThreadPoolExecutor
    import achievements
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        with ThreadPoolExecutor(max_workers=6) as pool:
            unlocked = list(pool.map(lambda _: achievements.record_achievement_event(store, 'bubbles_popped', 1), range(30)))
        assert int(store.get_stat('bubbles_popped')) == 30
        assert sum(len(batch) for batch in unlocked) == 1
        assert store.get_friendship_points() == 50
