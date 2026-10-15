"""Regressions for privacy, wallpaper ownership, duplicate actions and updates."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

import gemini
import lively_wallpaper as wallpaper
from agent_brain import AgentWorker
from main import AmbientVisionWorker, Buddy
from tools import ToolResult


class Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def save(self):
        pass


def test_background_vision_requires_ai_and_explicit_consent():
    for ai, consent in [(False, True), (True, False), (False, False)]:
        worker = AmbientVisionWorker('fake-image', 'Editor', [], {
            'ai': {'enabled': ai}, 'privacy': {'auto_vision': consent}})
        with patch('gemini.has_key', return_value=True), patch('gemini.ask') as ask:
            worker._analyze()
        ask.assert_not_called()


def test_failed_followup_does_not_repeat_completed_note():
    worker = AgentWorker('notiere Milch', {
        'ai': {'enabled': True}, 'privacy': {'remember': False, 'use_history': False}}, [])
    with patch('gemini.has_key', return_value=True), patch('gemini.ask', side_effect=[
        '{"say":"","tool":{"name":"manage_notes","args":{"action":"add","text":"Milch"}}}',
        gemini.LLMError('Timeout')]), patch('tools.execute', return_value=ToolResult(True, 'Milch notiert')) as execute:
        ok, message, _ = worker._process()
    assert ok and 'Milch notiert' in message
    assert execute.call_count == 1


def test_restore_without_owned_wallpaper_changes_nothing():
    with patch('lively_wallpaper.subprocess.run') as run, patch('lively_wallpaper.restore_windows_wallpaper') as restore:
        assert wallpaper.restore_original_wallpaper(Settings()) is True
    run.assert_not_called()
    restore.assert_not_called()


def _layout(path, monitor=1):
    return {'LivelyScreen': {'Index': monitor, 'IsPrimary': monitor == 1}, 'LivelyInfoPath': str(path)}


def test_activation_checks_layout_and_refreshes_saved_background():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        room = root / 'room'
        room.mkdir()
        (room / 'LivelyInfo.json').write_text('{}')
        original = root / 'new-background.jpg'
        original.write_bytes(b'image')
        (root / 'Settings.json').write_text('{"WallpaperArrangement":0}')
        (root / 'WallpaperLayout.json').write_text('[]')
        cfg = Settings({'lively.prev_wallpaper': 'stale.jpg'})

        def activate(*args, **kwargs):
            (root / 'WallpaperLayout.json').write_text(json.dumps([_layout(room)]))
            return SimpleNamespace(returncode=0)

        with patch('lively_wallpaper.get_lively_data_dir', return_value=root), \
             patch('lively_wallpaper.find_lively_exe', return_value=Path('Lively.exe')), \
             patch('lively_wallpaper.deploy_room_to_lively_library', return_value=room), \
             patch('lively_wallpaper.get_current_windows_wallpaper', return_value=str(original)), \
             patch('lively_wallpaper.subprocess.run', side_effect=activate):
            ok, message = wallpaper.apply_lively_wallpaper(cfg)
        assert ok, message
        assert cfg.get('lively.active') is True
        assert cfg.get('lively.prev_wallpaper') == str(original)


def test_failed_wallpaper_command_does_not_report_success():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / 'WallpaperLayout.json').write_text('[]')
        cfg = Settings()
        with patch('lively_wallpaper.get_lively_data_dir', return_value=root), \
             patch('lively_wallpaper.find_lively_exe', return_value=Path('Lively.exe')), \
             patch('lively_wallpaper.deploy_room_to_lively_library', return_value=wallpaper.get_room_package_dir()), \
             patch('lively_wallpaper.subprocess.run', return_value=SimpleNamespace(returncode=1)):
            ok, _ = wallpaper.apply_lively_wallpaper(cfg)
        assert not ok
        assert not cfg.get('lively.active')


def test_restore_leaves_manually_selected_wallpaper_alone():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / 'WallpaperLayout.json').write_text(json.dumps([_layout(root / 'other-room')]))
        cfg = Settings({'lively.active': True, 'lively.room_path': str(root / 'our-room'), 'lively.monitor': 1})
        with patch('lively_wallpaper.get_lively_data_dir', return_value=root), \
             patch('lively_wallpaper.subprocess.run') as run, \
             patch('lively_wallpaper.restore_windows_wallpaper') as restore:
            assert wallpaper.restore_original_wallpaper(cfg)
        run.assert_not_called()
        restore.assert_not_called()
        assert not cfg.get('lively.active')


def test_failed_static_restore_can_be_retried_after_room_is_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        room = root / 'our-room'
        (root / 'WallpaperLayout.json').write_text(json.dumps([_layout(room)]))
        cfg = Settings({'lively.active': True, 'lively.room_path': str(room),
                        'lively.monitor': 1, 'lively.prev_wallpaper': 'original.jpg'})

        def close(*args, **kwargs):
            (root / 'WallpaperLayout.json').write_text('[]')
            return True

        with patch('lively_wallpaper.get_lively_data_dir', return_value=root), \
             patch('lively_wallpaper.close_lively_wallpaper', side_effect=close), \
             patch('lively_wallpaper.restore_windows_wallpaper', side_effect=[False, True]) as restore:
            assert not wallpaper.restore_original_wallpaper(cfg)
            assert cfg.get('lively.prev_wallpaper') == 'original.jpg'
            assert wallpaper.restore_original_wallpaper(cfg)
        assert restore.call_count == 2
        assert not cfg.get('lively.active')


def test_hidden_reminder_does_not_cancel_update_reply_while_typing():
    buddy = SimpleNamespace(_awaiting_update_reply=True, input=MagicMock())
    buddy.input.isVisible.return_value = True
    Buddy._say(buddy, 'Trink etwas Wasser')
    assert buddy._awaiting_update_reply


def test_manual_update_check_refreshes_a_previously_offered_release():
    buddy = _update_buddy()
    buddy._update_worker = None
    buddy._offer_update = MagicMock()
    buddy._on_update_checked = MagicMock()
    with patch('main.CheckUpdateWorker') as worker:
        Buddy._check_update(buddy, manual=True)
    worker.assert_called_once_with(manual=True)
    worker.return_value.start.assert_called_once()


def test_disabled_ai_blocks_explicit_cloud_entry_points():
    buddy = SimpleNamespace(cfg=Settings({'ai.enabled': False}), _say=MagicMock())
    with patch('gemini.has_key', return_value=True):
        Buddy.start_error_doctor(buddy)
        Buddy.start_it_guide(buddy, 'Help')
        Buddy._run_clipboard_action(buddy, 'explain', 'clipboard')
        Buddy._create_ai_flashcards(buddy, 'Math')
    assert buddy._say.call_count == 4


def test_disabled_ai_keeps_onboarding_answers_local():
    from onboarding import OnboardingDialog
    dialog = SimpleNamespace(_is_waiting=False, cfg=Settings({'ai.enabled': False}),
        _add_user_bubble=MagicMock(), avatar=MagicMock(), flow=MagicMock(),
        _clear_input_area=MagicMock(), _show_typing=MagicMock(),
        _render_current_step=MagicMock(), _reap_threads=MagicMock(), _threads=set())
    dialog.flow.current_step.return_value = 3
    dialog.flow.submit_answer.return_value = True
    dialog.flow.is_done.return_value = False
    with patch('gemini.has_key', return_value=True), patch('onboarding.OnboardingReactionWorker') as worker, \
         patch('onboarding.QTimer.singleShot'):
        OnboardingDialog._handle_answer(dialog, 'My name')
    worker.assert_not_called()


def test_update_bubble_click_only_opens_reply():
    buddy = SimpleNamespace(_pending_update={'version': '9.0.0'}, brain=SimpleNamespace(busy=False),
                            open_input=MagicMock(), _start_update_download=MagicMock())
    Buddy._on_bubble_clicked(buddy)
    buddy._start_update_download.assert_not_called()
    buddy.open_input.assert_called_once_with(reply_mode=True)


def _update_buddy():
    return SimpleNamespace(_pending_update={'version': '9.0.0'}, _awaiting_update_reply=True,
        _download_worker=None, _quiz_session=None, _mochi_asked_question=False,
        input=MagicMock(), brain=SimpleNamespace(pending_action=None, submit=MagicMock(return_value=True)),
        _start_update_download=MagicMock(), _say=MagicMock(), cfg=Settings(),
        _update_tray_menu=MagicMock(), char_info=lambda: {'name': 'Kylie'},
        user_name=lambda: 'Boss', pet=MagicMock(), create_sticky_note=MagicMock())


def test_yes_installs_only_offered_update_and_clears_reply_state():
    buddy = _update_buddy()
    Buddy._on_submit(buddy, 'ja')
    buddy._start_update_download.assert_called_once()
    buddy.brain.submit.assert_not_called()
    assert not buddy._awaiting_update_reply


def test_later_does_not_install_and_defers_reminder():
    buddy = _update_buddy()
    Buddy._on_submit(buddy, 'später')
    buddy._start_update_download.assert_not_called()
    buddy.brain.submit.assert_not_called()
    assert not buddy._awaiting_update_reply
    assert buddy.cfg.get('update.remind_after', 0) > 0


def test_unrelated_message_cannot_leave_stale_update_consent():
    buddy = _update_buddy()
    Buddy._on_submit(buddy, 'notiz: Milch')
    assert not buddy._awaiting_update_reply


def test_browser_handoff_copies_only_requested_text_and_opens_fixed_url():
    from gemini_browser import open_gemini_browser
    app = QApplication.instance() or QApplication([])
    app.clipboard().setText('existing clipboard')
    with patch('gemini_browser.webbrowser.open', return_value=True) as browser:
        assert open_gemini_browser('Meine Frage')
    assert app.clipboard().text() == 'Meine Frage'
    browser.assert_called_once_with('https://gemini.google.com/app')
    with patch('gemini_browser.webbrowser.open', return_value=True):
        assert open_gemini_browser()
    assert app.clipboard().text() == 'Meine Frage'
