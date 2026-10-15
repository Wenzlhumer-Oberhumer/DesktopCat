"""Play completions commit once, including their rewards and local records."""
import datetime
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from memory_store import MemoryStore


class PlayStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'play.db'
        self.store = MemoryStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_completion_persists_once_after_restart(self):
        self.store.set_friendship_points(17)
        result = self.store.finish_play_session('one', 'cups', 'cozy', 5)
        self.assertEqual(result, dict(duplicate=False, awarded=3, record=True, badges=['spurnase']))
        restarted = MemoryStore(self.path)
        self.assertTrue(restarted.finish_play_session('one', 'cups', 'cozy', 99)['duplicate'])
        self.assertEqual(restarted.get_friendship_points(), 20)
        self.assertEqual(restarted.get_play_records()[0]['score'], 5)
        self.assertEqual(restarted.get_play_records()[0]['completed_rounds'], 1)

    def test_concurrent_completions_share_cap_and_do_not_lose_existing_points(self):
        self.store.set_friendship_points(20)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: self.store.finish_play_session(str(n),
                ('cups', 'memory', 'story')[n % 3], 'cozy', n, turns=12), range(24)))
        self.assertEqual(sum(r['awarded'] for r in results), 30)
        self.assertEqual(self.store.get_friendship_points(), 50)
        self.assertEqual(self.store.get_daily_friendship_count('play', datetime.date.today().isoformat()), 10)
        self.assertEqual(sum(r['completed_rounds'] for r in self.store.get_play_records()), 24)
        self.assertIn('playmates', self.store.get_play_badges())

    def test_concurrent_duplicate_only_rewards_once(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.finish_play_session('same', 'story', 'cozy', 1), range(12)))
        self.assertEqual(sum(r['awarded'] for r in results), 3)
        self.assertEqual(sum(not r['duplicate'] for r in results), 1)

    def test_records_compare_per_mode_and_cozy_memory_uses_fewer_turns(self):
        self.store.finish_play_session('a', 'cups', 'cozy', 10)
        self.assertFalse(self.store.finish_play_session('b', 'cups', 'cozy', 8)['record'])
        self.assertTrue(self.store.finish_play_session('c', 'cups', 'challenge', 8)['record'])
        self.store.finish_play_session('d', 'memory', 'cozy', 99, turns=12)
        self.assertTrue(self.store.finish_play_session('e', 'memory', 'cozy', 1, turns=10)['record'])
        self.assertFalse(self.store.finish_play_session('f', 'memory', 'cozy', 999, turns=14)['record'])
        records = {(r['game'], r['mode']): r for r in self.store.get_play_records()}
        self.assertEqual(records['cups', 'cozy']['score'], 10)
        self.assertEqual(records['memory', 'cozy']['turns'], 10)

    def test_preferences_are_explicit_and_never_become_ai_facts(self):
        self.store.finish_play_session('a', 'cups', 'cozy', 1)
        self.assertEqual(self.store.get_play_preferences(), {})
        self.store.finish_play_session('b', 'cups', 'cozy', 1, remember=True)
        self.store.finish_play_session('c', 'story', 'cozy', 1, remember=True)
        self.assertEqual(self.store.get_play_preferences(), {'cups': 1, 'story': 1})
        self.assertEqual(self.store.facts(), [])
        self.store.reset_play_preferences()
        self.assertEqual(MemoryStore(self.path).get_play_preferences(), {})
        self.assertEqual(len(self.store.get_play_records()), 2)

    def test_cancelled_round_never_creates_reward_record_preference_or_badge(self):
        result = self.store.finish_play_session('cancel', 'memory', 'cozy', 100, completed=False, remember=True)
        self.assertEqual(result, dict(duplicate=False, awarded=0, record=False, badges=[]))
        self.assertEqual(self.store.get_play_records(), [])
        self.assertEqual(self.store.get_play_preferences(), {})
        self.assertEqual(self.store.get_play_badges(), [])
        self.assertTrue(self.store.finish_play_session('cancel', 'memory', 'cozy', 100)['duplicate'])

    def test_contact_games_never_receive_completion_fp_and_badges_unlock_once(self):
        for game in ('ball', 'bubbles', 'tricks'):
            self.assertEqual(self.store.finish_play_session(game, game, 'cozy', 7)['awarded'], 0)
        self.assertEqual(self.store.get_play_badges(), [])
        self.assertTrue(self.store.unlock_play_badge('first_ball'))
        self.assertFalse(self.store.unlock_play_badge('first_ball'))
        self.assertTrue(self.store.unlock_play_badge('highfive'))
        self.assertEqual(self.store.get_friendship_points(), 0)

    def test_reward_failure_rolls_back_session_record_preferences_and_badges(self):
        self.store.set_friendship_points(4)
        with self.store._db() as db:
            db.execute("CREATE TRIGGER reject_play BEFORE UPDATE ON friendship BEGIN SELECT RAISE(ABORT, 'fail'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.finish_play_session('retry', 'cups', 'cozy', 4, remember=True)
        self.assertEqual(self.store.get_play_records(), [])
        self.assertEqual(self.store.get_play_preferences(), {})
        self.assertEqual(self.store.get_play_badges(), [])
        with self.store._db() as db:
            db.execute('DROP TRIGGER reject_play')
        self.assertFalse(self.store.finish_play_session('retry', 'cups', 'cozy', 4)['duplicate'])

    def test_wipe_removes_all_play_state_and_legacy_rewards_keep_their_caps(self):
        from fun import add_friendship_points
        self.store.finish_play_session('a', 'cups', 'cozy', 1, remember=True)
        self.store.wipe_everything()
        self.assertEqual(self.store.get_play_records(), [])
        self.assertEqual(self.store.get_play_preferences(), {})
        self.assertEqual(self.store.get_play_badges(), [])
        self.assertFalse(self.store.finish_play_session('a', 'cups', 'cozy', 1)['duplicate'])
        self.assertEqual(sum(add_friendship_points(self.store, 'yarn')[0] for _ in range(15)), 20)
        self.assertEqual(sum(add_friendship_points(self.store, 'bubble')[0] for _ in range(20)), 15)

    def test_invalid_inputs_do_not_mutate_state(self):
        for args in [('', 'cups', 'cozy', 1), ('a', 'unknown', 'cozy', 1),
                     ('b', 'cups', '', 1), ('c', 'cups', 'cozy', -1)]:
            with self.assertRaises(ValueError):
                self.store.finish_play_session(*args)
        with self.assertRaises(ValueError):
            self.store.unlock_play_badge('unknown')
        self.assertEqual(self.store.get_friendship_points(), 0)
        self.assertEqual(self.store.get_play_records(), [])

    def test_play_reward_configuration_uses_same_daily_allowance(self):
        from fun import add_friendship_points
        today = datetime.date.today().isoformat()
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        for _ in range(10):
            self.store.award_friendship('play', yesterday, 10, 3)
        self.assertEqual(add_friendship_points(self.store, 'play')[0], 3)
        for n in range(12):
            self.store.finish_play_session(str(n), 'cups', 'cozy', n)
        self.assertEqual(self.store.get_daily_friendship_count('play', today), 10)
        self.assertEqual(self.store.get_friendship_points(), 60)

    def test_concurrent_badge_contacts_unlock_once(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.unlock_play_badge('first_ball'), range(12)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(MemoryStore(self.path).get_play_badges(), ['first_ball'])

    def test_real_story_ids_reward_and_unlock_adventurer(self):
        for game in ('story_picnic', 'story_sock', 'story_stars'):
            result = self.store.finish_play_session(game, game, 'cozy', 1)
            self.assertEqual(result['awarded'], 3)
            self.assertTrue(result['record'])
        self.assertEqual(self.store.get_play_badges(), ['adventurer'])
        self.assertEqual([r['game'] for r in self.store.get_play_records()],
                         ['story_picnic', 'story_sock', 'story_stars'])

    def test_live_contact_game_ids_have_records_without_completion_rewards(self):
        for game in ('yarn', 'bubble'):
            result = self.store.finish_play_session(game, game, 'arcade', 3)
            self.assertEqual(result['awarded'], 0)
            self.assertTrue(result['record'])

    def test_memory_timeout_earns_round_reward_but_master_badge_requires_six_pairs(self):
        result = self.store.finish_play_session('timeout', 'memory', 'arcade', 5, turns=12)
        self.assertEqual(result['awarded'], 3)
        self.assertEqual(result['badges'], [])
        result = self.store.finish_play_session('solved', 'memory', 'arcade', 6, turns=14)
        self.assertEqual(result['awarded'], 3)
        self.assertEqual(result['badges'], ['merkmeister'])
