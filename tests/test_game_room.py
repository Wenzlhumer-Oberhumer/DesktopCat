"""Game Room mechanics and lifecycle regression tests."""
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication, QPushButton


def room():
    from game_room import GameRoom
    app = QApplication.instance() or QApplication([])
    values = {'language': 'en', 'pet.name': 'Mochi', 'pet.character': 'cat_mochi'}
    store = SimpleNamespace(get_play_records=lambda: {}, get_play_badges=lambda: [],
                            get_play_preferences=lambda: {}, reset_play_preferences=lambda: None)
    result = GameRoom(store, SimpleNamespace(get=lambda key, default=None: values.get(key, default)))
    result._test_app = app
    return result


def settle_cups(r):
    while r.phase in ('reveal', 'shuffle'):
        r.phase_timer.stop()
        r._advance_phase()


def test_cups_retry_and_paused_shuffle():
    r = room()
    r.start_game('cups', 'cozy')
    r.set_paused(True)
    before = (r.phase, r.cup_positions[:])
    r._advance_phase()
    assert (r.phase, r.cup_positions) == before
    r.set_paused(False)
    settle_cups(r)
    correct = r.cup_positions.index(r.treat_cup)
    r._choose_cup((correct + 1) % 3)
    assert not r.finished
    assert r.phase == 'guess'
    r._choose_cup(correct)
    assert r.finished
    r.close()


def test_memory_mismatch_freezes_input_and_pause_freezes_callback():
    r = room()
    r.start_game('memory', 'cozy')
    r.cards = [0, 1, 0, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    r._choose_card(0)
    r._choose_card(1)
    r._choose_card(2)
    assert r.open_cards == [0, 1]
    r.set_paused(True)
    r._advance_phase()
    assert r.open_cards == [0, 1]
    assert not r.phase_timer.isActive()
    r.set_paused(False)
    r.phase_timer.stop()
    r._advance_phase()
    assert r.open_cards == []
    assert r.seen_cards == {0, 1}
    r.close()


def test_memory_hint_never_exposes_unseen_cards_and_finish_is_once():
    r = room()
    r.start_game('memory', 'cozy')
    r.cards = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    r._hint()
    assert r.open_cards == []
    done = []
    r.round_finished.connect(lambda score, turns: done.append((score, turns)))
    for index in range(12):
        r._choose_card(index)
    r.finish_timeout()
    r._choose_card(0)
    assert done == [(6, 6)]
    r.close()


def test_arcade_cups_five_rounds_no_hints_and_single_completion():
    r = room()
    r.start_game('cups', 'arcade')
    done = []
    r.round_finished.connect(lambda score, turns: done.append((score, turns)))
    for _ in range(5):
        settle_cups(r)
        assert not r.hint_button.isVisible()
        r._choose_cup(r.cup_positions.index(r.treat_cup))
    r.finish_timeout()
    assert done == [(5, 5)]
    r.close()


def test_hub_navigation_signals_and_close_cancel_timers():
    r = room()
    started, closed, cancelled = [], [], []
    r.start_requested.connect(lambda game, mode: started.append((game, mode)))
    r.closed.connect(lambda: closed.append(True))
    r.cancel_requested.connect(lambda: cancelled.append(True))
    r.game_buttons['memory'].click()
    assert started == [('memory', 'cozy')]
    assert all(b.minimumHeight() >= 44 for b in r.findChildren(QPushButton))
    r.start_game('memory', 'arcade')
    r.tick(0)
    r.finish_timeout()
    assert r.finished
    r.close()
    assert closed == [True]
    assert cancelled == [True]
    assert not r.phase_timer.isActive()

def test_cups_hint_points_to_treat_only_after_shuffle():
    r = room()
    r.start_game('cups', 'cozy')
    settle_cups(r)
    r._hint()
    assert 'ABC'[r.treat_cup] in r.status_label.text()
    assert 'hint' in r.status_label.text().lower()
    r.close()


def test_memory_hint_reveals_only_seen_cards_and_does_not_count_turn():
    r = room()
    r.start_game('memory', 'cozy')
    r.cards = [0, 1, 0, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    r._choose_card(0)
    r._choose_card(1)
    r.phase_timer.stop()
    r._advance_phase()
    r._hint()
    assert r.open_cards == [0, 1]
    assert r.turns == 1
    r._choose_card(2)
    assert r.open_cards == [0, 1]
    r.close()

def test_story_pause_does_not_reactivate_consumed_choices_or_deleted_hints():
    r = room()
    r.start_game('memory', 'cozy')
    choices = []
    r.show_story('A picnic', ['Tea', 'Cake'], choices.append)
    r.action_buttons[0].click()
    r.set_paused(True)
    r.set_paused(False)
    assert choices == [0]
    assert all(not b.isEnabled() for b in r.action_buttons)
    r.close()

def test_completed_signal_can_return_to_hub_without_accepting_stale_input():
    r = room()
    r.start_game('memory', 'cozy')
    r.cards = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    finished = []
    r.round_finished.connect(lambda score, turns: (finished.append(score), r.show_hub()))
    for index in range(12):
        r._choose_card(index)
    r._choose_card(0)
    r._finish()
    assert finished == [6]
    assert r.current_game == ''
    r.close()
