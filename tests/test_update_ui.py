from unittest.mock import patch
from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import QApplication
from unittest.mock import MagicMock
from types import SimpleNamespace


def _buddy():
    from tests.test_v307_fixes import Settings
    return SimpleNamespace(_pending_update={'version': '3.1.0'}, update_prompt=MagicMock(),
        _download_worker=None, cfg=Settings(), _awaiting_update_reply=False,
        brain=SimpleNamespace(busy=False, pending_action=None), input=MagicMock(),
        _quiz_session=None, bubble=MagicMock(), pet=MagicMock(), _say=MagicMock(),
        _offer_update=MagicMock(), _start_update_download=MagicMock())


def test_snooze_persists_exact_time_and_blocks_nested_offer():
    from main import Buddy
    buddy = _buddy()
    with patch('update_ui.SnoozeDialog') as dialog:
        instance = dialog.return_value
        instance.DialogCode.Accepted = 1
        instance.selected_time.return_value = 1800007200
        def select():
            assert buddy._choosing_update_reminder
            Buddy._offer_update(buddy)
            buddy.update_prompt.offer.assert_not_called()
            return 1
        instance.exec.side_effect = select
        Buddy._defer_update(buddy)
    assert buddy.cfg.get('update.remind_after') == 1800007200
    assert buddy.cfg.get('update.deferred_version') == '3.1.0'
    assert not buddy._choosing_update_reminder
    buddy._start_update_download.assert_not_called()


def test_stale_or_busy_update_button_never_installs():
    from main import Buddy
    buddy = _buddy()
    Buddy._install_update_offer(buddy, '3.0.9')
    buddy._start_update_download.assert_not_called()
    buddy.brain.busy = True
    Buddy._install_update_offer(buddy, '3.1.0')
    buddy._start_update_download.assert_not_called()


def test_chat_results_replace_update_card_instead_of_disappearing():
    from main import Buddy
    buddy = _buddy()
    buddy.input.isVisible.return_value = False
    buddy.update_prompt.isVisible.return_value = True
    buddy._follow = MagicMock()
    Buddy._say(buddy, 'Erledigt', 5000)
    buddy.update_prompt.hide_now.assert_called_once()
    buddy.bubble.say.assert_called_once_with('Erledigt', 5000, False)


def test_automatic_update_offer_respects_focus_and_hidden_pet():
    from main import Buddy
    buddy = _buddy()
    buddy._focus_mode = True
    Buddy._offer_update(buddy)
    buddy.update_prompt.offer.assert_not_called()
    buddy._focus_mode = False
    buddy.pet.isVisible.return_value = False
    Buddy._offer_update(buddy)
    buddy.update_prompt.offer.assert_not_called()


def test_update_buttons_require_explicit_single_click():
    from update_ui import UpdatePrompt
    app = QApplication.instance() or QApplication([])
    card = UpdatePrompt()
    installs, later = [], []
    card.install_requested.connect(installs.append)
    card.later_requested.connect(lambda: later.append(True))
    card.offer('3.1.0')
    assert not installs
    card.install_button.click()
    card.install_button.click()
    assert installs == ['3.1.0']
    card.offer('3.1.1')
    card.later_button.click()
    assert later == [True]
    card.close()


def test_snooze_presets_and_custom_time_are_future_timestamps():
    from update_ui import SnoozeDialog
    app = QApplication.instance() or QApplication([])
    with patch('update_ui.time.time', return_value=1800000000):
        dlg = SnoozeDialog()
        assert dlg.selected_time() == 1800000900
        dlg.options.setCurrentIndex(1)
        assert dlg.selected_time() == 1800003600
        dlg.options.setCurrentIndex(4)
        dlg.custom_time.setDateTime(QDateTime.fromSecsSinceEpoch(1800007200))
        assert dlg.selected_time() == 1800007200
        dlg.custom_time.setDateTime(QDateTime.fromSecsSinceEpoch(1799999900))
        dlg._confirm()
        assert dlg.result() != dlg.DialogCode.Accepted
        assert dlg.error.text()
        dlg.close()
