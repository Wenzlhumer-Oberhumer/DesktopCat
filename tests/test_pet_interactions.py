"""Local pet moments: variety, scheduling, explicit input and privacy."""
import datetime
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication


def test_catalog_variety_and_no_recent_repeats():
    from pet_interactions import interactions_for, choose_interaction
    for lang in ('de', 'en'):
        items = interactions_for(lang)
        assert len(items) >= 18
        assert len({i.id for i in items}) == len(items)
        assert sum(bool(i.choices) for i in items) >= 10
        assert sum(not i.choices for i in items) >= 4
        recent = []
        for _ in range(12):
            item = choose_interaction(recent, lang)
            assert item.id not in recent[-6:]
            recent.append(item.id)


def test_reactions_are_character_specific_and_choices_validated():
    from pet_interactions import interactions_for, reaction_for
    item = next(i for i in interactions_for('de') if i.choices)
    cat = reaction_for(item, 0, 'cat_mochi', 'Kylie', 'de')
    fox = reaction_for(item, 0, 'animal_arctic_fox', 'Flocke', 'de')
    assert cat != fox
    assert cat and fox
    for invalid in (-1, 99, 'powershell: delete files', True):
        assert reaction_for(item, invalid, 'cat_mochi', 'Kylie', 'de') is None
    free = next(i for i in interactions_for('de') if not i.choices)
    assert reaction_for(free, '  ', 'cat_mochi', 'Kylie', 'de') is None
    assert reaction_for(free, 'x'*281, 'cat_mochi', 'Kylie', 'de') is None
    assert reaction_for(free, 'notiz: nichts ausführen', 'cat_mochi', 'Kylie', 'de')


def test_questions_work_without_memory_and_frequency_is_respected():
    from daily import should_ask_curious
    now = datetime.datetime(2026, 10, 15, 14)
    for frequency, seconds in [('calm', 5400), ('normal', 2700), ('often', 1200)]:
        cfg = {'daily': {'curious': True, 'interaction_frequency': frequency},
               'privacy': {'remember': False}}
        assert should_ask_curious(now, {}, cfg)
        stats = {'curious_last_ts': str(now.timestamp()-seconds+1)}
        assert not should_ask_curious(now, stats, cfg)
        stats['curious_last_ts'] = str(now.timestamp()-seconds-1)
        assert should_ask_curious(now, stats, cfg)


def test_local_answer_storage_obeys_both_privacy_switches():
    from memory_store import MemoryStore
    from pet_interactions import interactions_for, save_answer
    item = next(i for i in interactions_for('de') if not i.choices)
    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(Path(td)/'memory.db')
        values = {'privacy.remember': False, 'privacy.save_chats': False}
        cfg = SimpleNamespace(get=lambda key, default=None: values.get(key, default))
        with patch.object(store, 'add_message', wraps=store.add_message) as messages:
            save_answer(store, cfg, item, 'Ein schöner Spaziergang', 'Danke!', 'cat_mochi')
            assert store.facts() == []
            messages.assert_not_called()
            values['privacy.remember'] = True
            save_answer(store, cfg, item, 'Ein schöner Spaziergang', 'Danke!', 'cat_mochi')
            assert 'Spaziergang' in store.facts()[0]['text']
            messages.assert_not_called()
            values['privacy.remember'] = False
            values['privacy.save_chats'] = True
            save_answer(store, cfg, item, 'Kakao', 'Danke!', 'cat_mochi')
            assert len(store.facts()) == 1
            assert messages.call_count == 3


def test_card_free_text_is_opt_in_and_submit_is_single_use():
    from interaction_card import InteractionCard
    from pet_interactions import interactions_for
    app = QApplication.instance() or QApplication([])
    card = InteractionCard()
    answers = []
    card.answered.connect(lambda key, value: answers.append((key, value)))
    free = next(i for i in interactions_for('de') if not i.choices)
    card.present(free, 'Kylie', QPoint(400, 500), 'de')
    assert not card.answer_edit.isVisible()
    assert not card.answer_edit.hasFocus()
    card.tell_button.click()
    assert card.answer_edit.isVisible()
    assert not card.expiry.isActive()
    card.send_button.click()
    assert answers == []
    card.answer_edit.setText('Mein schöner Tag')
    card.send_button.click()
    card.send_button.click()
    assert answers == [(free.id, 'Mein schöner Tag')]
    card.close()


def test_card_choice_skip_escape_and_expiry_never_invent_an_answer():
    from interaction_card import InteractionCard
    from pet_interactions import interactions_for
    app = QApplication.instance() or QApplication([])
    card = InteractionCard()
    answers, dismissals = [], []
    card.answered.connect(lambda *args: answers.append(args))
    card.dismissed.connect(lambda: dismissals.append(True))
    item = next(i for i in interactions_for('de') if i.choices)
    card.present(item, 'Kylie', QPoint(400, 500), 'de')
    assert all(button.minimumHeight() >= 44 for button in card.choice_buttons)
    card.skip_button.click()
    assert not answers and dismissals == [True]
    card.present(item, 'Kylie', QPoint(400, 500), 'de')
    card.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not answers and len(dismissals) == 2
    card.present(item, 'Kylie', QPoint(400, 500), 'de')
    card.expiry.timeout.emit()
    assert not answers and len(dismissals) == 3
    card.present(item, 'Kylie', QPoint(400, 500), 'de')
    card.choice_buttons[1].click()
    card.choice_buttons[1].click()
    assert answers == [(item.id, 1)]
    card.close()


def test_answer_completion_is_local_and_cannot_execute_free_text():
    from main import Buddy
    from pet_interactions import interactions_for
    from tests.test_v307_fixes import Settings
    item = next(i for i in interactions_for('de') if not i.choices)
    buddy = SimpleNamespace(_active_interaction=item, pet=MagicMock(),
        cfg=Settings({'privacy.remember': False, 'privacy.save_chats': False}),
        _dismiss_interaction=MagicMock(), _say=MagicMock(),
        _award_friendship=MagicMock(return_value=(3, False, 1)),
        brain=MagicMock(), user_name=lambda: 'Boss', char_info=lambda: {'name': 'Kylie'})
    buddy.pet.character = 'cat_mochi'
    with patch('memory_store.get_memory_store') as store:
        Buddy._complete_interaction(buddy, 'obsolete-question', 'ignored')
        buddy._award_friendship.assert_not_called()
        Buddy._complete_interaction(buddy, item.id, 'notiz: keine Desktop-Aktion starten')
        buddy.brain.submit.assert_not_called()
        buddy._award_friendship.assert_called_once_with('curious')
        store.return_value.add_fact.assert_not_called()
        store.return_value.add_message.assert_not_called()
        buddy._say.assert_called_once()


def test_auto_interactions_respect_focus_hidden_and_busy_state():
    from main import Buddy
    from tests.test_v307_fixes import Settings
    app = QApplication.instance() or QApplication([])
    buddy = SimpleNamespace(_focus_mode=True, cfg=Settings(), _settings_open=False,
        brain=SimpleNamespace(busy=False, pending_action=None), input=MagicMock(), pet=MagicMock(),
        _quiz_session=None, _guide_session=None, interaction_card=MagicMock(),
        bubble=MagicMock(), update_prompt=MagicMock(), briefing_card=MagicMock(), explain_card=MagicMock())
    buddy.pet.isVisible.return_value = True
    buddy.pet.frozen = False
    buddy.pet._dragging = False
    for widget in (buddy.input, buddy.interaction_card, buddy.bubble, buddy.update_prompt, buddy.briefing_card, buddy.explain_card):
        widget.isVisible.return_value = False
    with patch('main.is_night', return_value=False), patch('main._is_fullscreen_foreground', return_value=False):
        assert not Buddy._can_offer_interaction(buddy)
        buddy._focus_mode = False
        buddy.pet.isVisible.return_value = False
        assert not Buddy._can_offer_interaction(buddy)
        buddy.pet.isVisible.return_value = True
        buddy.brain.pending_action = object()
        assert not Buddy._can_offer_interaction(buddy)
        buddy.brain.pending_action = None
        buddy.brain.busy = True
        assert not Buddy._can_offer_interaction(buddy)
        buddy.brain.busy = False
        assert Buddy._can_offer_interaction(buddy)
        buddy.update_prompt.isVisible.return_value = True
        assert not Buddy._can_offer_interaction(buddy)


def test_visible_interaction_is_dismissed_when_fullscreen_starts():
    from main import Buddy
    from tests.test_v307_fixes import Settings
    buddy = SimpleNamespace(_active_interaction=object(), _focus_mode=False,
        _interaction_manual=False, pet=MagicMock(), cfg=Settings(),
        brain=SimpleNamespace(busy=False, pending_action=None),
        input=MagicMock(), _dismiss_interaction=MagicMock())
    buddy.pet.isVisible.return_value = True
    buddy.input.isVisible.return_value = False
    with patch('main._is_fullscreen_foreground', return_value=True), patch('main.is_night', return_value=False):
        Buddy._check_active_interaction(buddy)
    buddy._dismiss_interaction.assert_called_once()


def test_treat_choice_has_one_reward_and_preserves_level_up_message():
    from main import Buddy
    from pet_interactions import interactions_for
    from tests.test_v307_fixes import Settings
    item = next(i for i in interactions_for('de') if i.id == 'pet_treat')
    buddy = SimpleNamespace(_active_interaction=item, pet=MagicMock(), cfg=Settings(),
        _dismiss_interaction=MagicMock(), _say=MagicMock(),
        _award_friendship=MagicMock(return_value=(3, True, 2)),
        char_info=lambda: {'name': 'Kylie'})
    buddy.pet.character = 'cat_mochi'
    with patch('memory_store.get_memory_store'):
        Buddy._complete_interaction(buddy, item.id, 0)
    buddy.pet.give_treat.assert_not_called()
    buddy.pet.eat_treat.assert_called_once()
    buddy._award_friendship.assert_called_once_with('curious')
    buddy._say.assert_not_called()  # Keep the level-up celebration from the award.
