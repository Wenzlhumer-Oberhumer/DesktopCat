"""Regression tests for the v3.2.1 usability plan."""
import datetime
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from config import Config
from memory_store import MemoryStore


def test_yarn_points_have_their_own_ten_action_limit():
    from play_coordinator import PlayCoordinator
    from fun import add_friendship_points
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        buddy = SimpleNamespace(active=True, clock=SimpleNamespace(paused=False), store=store, score=0, pet=MagicMock(), room=MagicMock(), t=lambda de,en: de)
        with patch('memory_store.get_memory_store', return_value=store):
            for _ in range(10):
                PlayCoordinator._caught(buddy)
        before = store.get_friendship_points()
        assert store.get_daily_friendship_count('yarn', datetime.date.today().isoformat()) == 10
        assert store.get_daily_friendship_count('treat', datetime.date.today().isoformat()) == 0
        assert add_friendship_points(store, 'yarn')[0] == 0
        assert add_friendship_points(store, 'treat')[0] == 2
        assert store.get_friendship_points() == before + 2


def test_manual_rounds_do_not_consume_automatic_quota():
    from main import Buddy
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        cfg = Config(Path(td)/'config.json')
        today = datetime.date.today().isoformat()
        store.set_stat('curious_date', today)
        store.set_stat('curious_count', '5')
        buddy = SimpleNamespace(cfg=cfg, _interaction_ready_at=0,
            _can_offer_interaction=lambda manual: True, _dismiss_interaction=MagicMock(),
            pet=MagicMock(), bubble=MagicMock(), interaction_card=MagicMock(),
            _interaction_watchdog=MagicMock(), char_info=lambda: {'name':'Kylie'})
        with patch('memory_store.get_memory_store', return_value=store), patch('daily.should_ask_curious', return_value=False) as eligible:
            Buddy._start_pet_interaction(buddy, manual=True)
            eligible.assert_not_called()
            assert store.get_stat('curious_count') == '5'
            assert float(store.get_stat('curious_last_ts')) > time.time()-5
            eligible.return_value = True
            Buddy._start_pet_interaction(buddy, manual=False)
            assert store.get_stat('curious_count') == '6'


def test_question_pause_persists_and_expires_without_disabling_manual_rounds():
    from main import Buddy
    from daily import should_ask_curious
    now = datetime.datetime(2026,10,15,22,30)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)/'config.json'
        buddy = SimpleNamespace(cfg=Config(path), _dismiss_interaction=MagicMock(),
            _say=MagicMock(), _update_tray_menu=MagicMock())
        with patch('main.time.time', return_value=now.timestamp()):
            Buddy.pause_pet_questions(buddy)
        reloaded = Config(path)
        assert reloaded.get('daily.interaction_pause_until') == now.timestamp()+3600
        assert not should_ask_curious(now, {}, reloaded.snapshot())
        tomorrow = datetime.datetime(2026,10,16,8)
        assert should_ask_curious(tomorrow, {}, reloaded.snapshot())
        Buddy.resume_pet_questions(buddy)
        assert buddy.cfg.get('daily.interaction_pause_until') == 0
        buddy._dismiss_interaction.assert_called_once()


def test_card_pause_is_explicit_and_never_answers():
    from interaction_card import InteractionCard
    from pet_interactions import interactions_for
    app = QApplication.instance() or QApplication([])
    card = InteractionCard()
    answers, pauses = [], []
    card.answered.connect(lambda *args: answers.append(args))
    card.pause_requested.connect(lambda: pauses.append(True))
    card.present(interactions_for()[0], 'Kylie', QPoint(400,500))
    card.pause_button.click()
    card.pause_button.click()
    assert not answers and pauses == [True]
    card.close()


def test_friendship_window_refreshes_points_and_rewards_while_open():
    from fun_dialogs import FriendshipDialog
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        dialog = FriendshipDialog(store, Config(Path(td)/'config.json'), {'name':'Kylie'})
        dialog.show()
        store.set_friendship_points(30)
        QTest.qWait(800)
        assert dialog.bar.value() == 10
        assert '2' in dialog.level_label.text()
        assert '30' in dialog.points_label.text()
        assert dialog.reward_buttons[2].isVisible()
        dialog.hide()
        assert not dialog.refresh_timer.isActive()
        dialog.close()


def test_one_level_announcement_uses_total_after_trophy_bonus():
    from main import Buddy
    from fun import add_friendship_points
    from achievements import record_achievement_event
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        store.set_friendship_points(24)
        buddy = _notification_buddy(24)
        add_friendship_points(store,'treat')
        record_achievement_event(store,'bubbles_popped',20)
        with patch('memory_store.get_memory_store',return_value=store):
            Buddy._refresh_friendship_progress(buddy)
            Buddy._refresh_friendship_progress(buddy)
        buddy._say.assert_called_once()
        assert 'Level 3' in buddy._say.call_args.args[0]
        assert buddy._last_friendship_points == 76


def _notification_buddy(points):
    buddy = SimpleNamespace(_last_friendship_points=points, pet=MagicMock(),
        _say=MagicMock(), brain=SimpleNamespace(busy=False, pending_action=None, record_assistant_message=MagicMock()),
        user_name=lambda:'Boss', input=MagicMock(), update_prompt=MagicMock(), _active_interaction=None)
    buddy.input.isVisible.return_value = False
    buddy.update_prompt.isVisible.return_value = False
    buddy.pet.isVisible.return_value = True
    return buddy


def test_level_notification_waits_for_input_without_losing_the_award():
    from main import Buddy
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        store.set_friendship_points(26)
        buddy = _notification_buddy(24)
        buddy.input.isVisible.return_value = True
        with patch('memory_store.get_memory_store',return_value=store):
            Buddy._refresh_friendship_progress(buddy)
            buddy._say.assert_not_called()
            buddy.input.isVisible.return_value = False
            Buddy._refresh_friendship_progress(buddy)
            Buddy._refresh_friendship_progress(buddy)
        buddy._say.assert_called_once()
        assert 'Level 2' in buddy._say.call_args.args[0]


def test_progress_card_cannot_be_overwritten_by_ambient_chatter():
    from main import Buddy
    buddy = SimpleNamespace(cfg=MagicMock(), _focus_mode=False, pet=MagicMock(),
        update_prompt=MagicMock(), interaction_card=MagicMock(), _schedule_chatter=MagicMock(),
        _say=MagicMock(), brain=SimpleNamespace(busy=False), input=MagicMock(),bubble=MagicMock())
    from pet_window import PetState
    buddy.pet.state = PetState.IDLE
    buddy.pet.isVisible.return_value = True
    buddy.input.isVisible.return_value = False
    buddy.bubble.isVisible.return_value = False
    buddy.interaction_card.isVisible.return_value = False
    buddy.update_prompt.isVisible.return_value = True
    with patch('main.is_night',return_value=False):
        Buddy._on_chatter(buddy)
    buddy._say.assert_not_called()


def test_update_card_has_download_verification_and_retry_states():
    from update_ui import UpdatePrompt
    app = QApplication.instance() or QApplication([])
    card = UpdatePrompt()
    clicks=[]
    card.install_requested.connect(clicks.append)
    card.begin_download('3.2.1')
    card.set_progress(-1)
    assert card.progress.maximum() == 0
    card.set_progress(42)
    assert card.progress.value() == 42 and card.progress.maximum() == 100
    card.hide_now()
    card.set_progress(45)
    assert not card.isVisible()
    card.show()
    card.set_verifying()
    assert 'Prüfsumme' in card.message.text()
    assert not card.install_button.isEnabled()
    card.show_error('Testfehler')
    assert 'Testfehler' in card.message.text()
    assert card.install_button.isEnabled() and card.later_button.isEnabled()
    card.install_button.click()
    card.install_button.click()
    assert clicks == ['3.2.1']
    card.close()


def test_worker_unknown_size_and_hash_failure_keep_phase_order():
    import hashlib
    import io
    from updater import DownloadUpdateWorker
    app = QApplication.instance() or QApplication([])
    payload = b'isolated installer test'
    base = 'https://github.com/Wenzlhumer-Oberhumer/DesktopCat/releases/download/v3.2.1/'
    setup = base+'DesktopCat-Setup-3.2.1.exe'
    for known_size, valid_hash in ((True,True),(False,True),(False,False)):
        events=[]
        class Response(io.BytesIO):
            headers = {'Content-Length':str(len(payload))} if known_size else {}
        def open_url(req, **kwargs):
            digest = hashlib.sha256(payload).hexdigest() if valid_hash else '0'*64
            return Response(digest.encode() if req.full_url.endswith('.sha256') else payload)
        with tempfile.TemporaryDirectory() as td:
            worker = DownloadUpdateWorker(setup, setup+'.sha256', '3.2.1')
            worker.progress.connect(lambda value: events.append(('progress',value)))
            worker.verifying.connect(lambda: events.append(('verify',None)))
            worker.download_completed.connect(lambda ok, detail:events.append(('done',ok)))
            with patch('urllib.request.urlopen',side_effect=open_url),patch('updater.tempfile.gettempdir',return_value=td):
                worker.run()
            assert events[0] == ('progress',0 if known_size else -1)
            assert events[-2:] == [('verify',None),('done',valid_hash)]
            assert (Path(td)/'DesktopCat-Setup-3.2.1.exe').exists() == valid_hash


def test_retry_state_is_processed_after_the_download_thread_has_finished():
    from main import Buddy
    from updater import DownloadUpdateWorker
    app = QApplication.instance() or QApplication([])
    buddy = SimpleNamespace(_pending_update={'version':'3.2.1','setup_url':'unused','sha_url':'unused'},
        _download_worker=None, bubble=MagicMock(),pet=MagicMock(),update_prompt=MagicMock())
    results=[]
    buddy._finish_update_download = lambda: Buddy._finish_update_download(buddy)
    def completed(ok, detail):
        assert not buddy._download_worker.isRunning()
        results.append((ok,detail))
    buddy._on_update_downloaded = completed
    def failed_run(worker):
        worker.download_completed.emit(False,'simulated network failure')
    with patch.object(DownloadUpdateWorker,'run',failed_run):
        for _ in range(2):
            Buddy._start_update_download(buddy)
            assert buddy._download_worker.wait(2000)
            app.processEvents()
    assert results == [(False,'simulated network failure')]*2
