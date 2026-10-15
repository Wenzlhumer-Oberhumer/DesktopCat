# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline, nonmodal play room. The coordinator owns rewards and arcade clocks."""
from __future__ import annotations

import random

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
                            QPushButton, QScrollArea, QVBoxLayout, QWidget)

from pet_sprites import get_character_info, render_icon


class GameRoom(QDialog):
    start_requested = pyqtSignal(str, str)
    trick_requested = pyqtSignal(str)
    closed = pyqtSignal()
    round_finished = pyqtSignal(int, int)
    reaction_requested = pyqtSignal(str)
    cancel_requested = pyqtSignal()
    throw_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()

    def __init__(self, store, cfg, parent=None):
        super().__init__(parent)
        self.store, self.cfg = store, cfg
        self.current_game, self.mode = '', 'cozy'
        self.paused = False
        self.finished = False
        self.phase = ''
        self._remaining_phase = 0
        self._closed_emitted = False
        self.phase_timer = QTimer(self)
        self.phase_timer.setSingleShot(True)
        self.phase_timer.timeout.connect(self._advance_phase)
        self.setModal(False)
        self.setWindowTitle(self._t('Spielzimmer', 'Play room'))
        self.resize(620, 760)
        self.setMinimumSize(500, 560)
        self.setStyleSheet('''
            QDialog {background:#20242e;color:#f5f1e9;}
            QWidget {color:#f5f1e9;font-family:'Segoe UI';font-size:14px;}
            QLabel {background:transparent;}
            QPushButton,QComboBox {background:#343b4c;border:1px solid #79859c;
                border-radius:10px;padding:8px 12px;color:#f5f1e9;}
            QPushButton:hover {background:#46516a;}
            QPushButton:pressed {background:#56617a;}
            QPushButton:focus,QComboBox:focus {border:2px solid #ffd290;}
            QPushButton:disabled {background:#292e39;color:#a4a9b3;border-color:#505767;}
            QScrollArea {border:0;background:transparent;}
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        avatar = QLabel()
        self.avatar = avatar
        avatar.setPixmap(render_icon(72, cfg.get('pet.character', 'cat_mochi')))
        character = cfg.get('pet.character', 'cat_mochi')
        name = cfg.get('pet.name', '') or get_character_info(character).get('name', 'Kylie')
        avatar.setAccessibleName(name)
        header.addWidget(avatar)
        title = QLabel(self._t('Spielzeit mit ', 'Playtime with ') + name)
        self.title_label = title
        title.setWordWrap(True)
        title.setStyleSheet('font-size:23px;font-weight:600;color:#ffd290;')
        header.addWidget(title, 1)
        layout.addLayout(header)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(48)
        layout.addWidget(self.status_label)
        self.clock_label = QLabel()
        layout.addWidget(self.clock_label)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll, 1)
        controls = QHBoxLayout()
        self.back_button = self._button(self._t('Zum Spielzimmer', 'Back to play room'), self._back)
        controls.addWidget(self.back_button)
        self.pause_button = self._button(self._t('Pause', 'Pause'), self._request_pause)
        controls.addWidget(self.pause_button)
        self.resume_button = self._button(self._t('Weiter', 'Resume'), self.resume_requested.emit)
        controls.addWidget(self.resume_button)
        layout.addLayout(controls)
        self.show_hub()

    def _t(self, de, en):
        return en if self.cfg.get('language', 'de') == 'en' else de

    def _button(self, text, callback):
        button = QPushButton(text)
        button.setMinimumHeight(44)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    def _page(self):
        old = self.scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self.page = QWidget()
        self.page.setStyleSheet('background:#20242e;')
        self.body = QVBoxLayout(self.page)
        self.body.setContentsMargins(0, 8, 0, 8)
        self.body.setSpacing(12)
        self.scroll.setWidget(self.page)
        return self.body

    def _stop_phase(self):
        self.phase_timer.stop()
        self._remaining_phase = 0
        self.phase = ''

    def show_hub(self):
        character = self.cfg.get('pet.character', 'cat_mochi')
        name = self.cfg.get('pet.name', '')
        if not name or (name == 'Kylie' and character != 'cat_mochi'):
            name = get_character_info(character).get('name', 'Kylie')
        self.avatar.setPixmap(render_icon(72, character))
        self.avatar.setAccessibleName(name)
        self.title_label.setText(self._t('Spielzeit mit ', 'Playtime with ') + name)
        self._stop_phase()
        self.current_game = ''
        self.paused = False
        self.finished = False
        self._closed_emitted = False
        body = self._page()
        self.update_status(self._personality())
        self.clock_label.clear()
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumHeight(44)
        self.mode_combo.addItem(self._t('Gemütlich · ohne Zeitdruck', 'Cozy · take your time'), 'cozy')
        self.mode_combo.addItem(self._t('Arcade · kleine Herausforderung', 'Arcade · a little challenge'), 'arcade')
        body.addWidget(self.mode_combo)
        grid = QGridLayout()
        self.game_buttons = {}
        games = [('yarn', 'Wollknäuel', 'Yarn chase'), ('cups', 'Hütchenspiel', 'Find the treat'),
                 ('memory', 'Memory', 'Memory pairs'), ('bubble', 'Seifenblasen', 'Bubble pop')]
        for i, (key, de, en) in enumerate(games):
            button = self._button(self._t(de, en), lambda checked=False, g=key: self.start_requested.emit(g, self.mode_combo.currentData()))
            self.game_buttons[key] = button
            grid.addWidget(button, i // 2, i % 2)
        body.addLayout(grid)
        body.addWidget(QLabel(self._t('Kleine Geschichten', 'Little stories')))
        for key, de, en in [('story_picnic', 'Ein Picknick', 'A picnic'), ('story_sock', 'Die verschwundene Socke', 'The missing sock'), ('story_stars', 'Unter den Sternen', 'Under the stars')]:
            body.addWidget(self._button(self._t(de, en), lambda checked=False, g=key: self.start_requested.emit(g, 'cozy')))
        tricks = QHBoxLayout()
        for key, de, en in [('highfive', 'High Five', 'High five'), ('wave', 'Winken', 'Wave'), ('dance', 'Tanzen', 'Dance')]:
            tricks.addWidget(self._button(self._t(de, en), lambda checked=False, k=key: self.trick_requested.emit(k)))
        body.addLayout(tricks)
        self.records_label = QLabel()
        self.records_label.setWordWrap(True)
        body.addWidget(self.records_label)
        self.preferences_label = QLabel()
        self.preferences_label.setWordWrap(True)
        body.addWidget(self.preferences_label)
        body.addWidget(self._button(self._t('Spielvorlieben zurücksetzen', 'Reset play preferences'), self._reset_preferences))
        self.refresh_records()
        body.addStretch()
        self._sync_controls()

    def _personality(self):
        char = self.cfg.get('pet.character', 'cat_mochi')
        if 'fox' in char:
            return self._t('Na, kannst du mich überlisten? Such dir ein Spiel aus!', 'Think you can outfox me? Pick a game!')
        if 'bunny' in char or 'rabbit' in char:
            return self._t('Wir spielen ganz in Ruhe. Was magst du heute?', 'Let’s play gently. What would you like today?')
        return self._t('Was versteckt sich hier? Lass uns gemeinsam spielen!', 'What’s hiding here? Let’s explore a game together!')

    def refresh_records(self):
        if not hasattr(self, 'records_label') or self.current_game:
            return
        records = self.store.get_play_records()
        badges = self.store.get_play_badges()
        prefs = self.store.get_play_preferences()
        names = self._game_names()
        lines = [self._t('Spielrekorde · separat von Freundschaftspunkten', 'Play records · separate from friendship points')]
        for record in records:
            mode = self._t('Gemütlich', 'Cozy') if record['mode'] == 'cozy' else 'Arcade'
            lines.append(f"{names.get(record['game'], record['game'])} · {mode}: {record['score']} " + self._t('Punkte', 'points') + f" · {record['turns']} " + self._t('Züge', 'turns'))
        if not records:
            lines.append(self._t('Dein erster Rekord wartet auf dich.', 'Your first record is waiting for you.'))
        badge_names = [('first_ball', 'Erster Ball', 'First ball'), ('spurnase', 'Spürnase', 'Super sleuth'),
                       ('merkmeister', 'Merkmeister', 'Memory master'), ('highfive', 'High Five', 'High five'),
                       ('adventurer', 'Abenteurer', 'Adventurer'), ('playmates', 'Spielgefährten', 'Playmates')]
        lines.append(self._t('Abzeichen', 'Badges') + f' · {len(badges)}/6')
        lines.extend(('✓ ' if key in badges else '○ ') + self._t(de, en) for key, de, en in badge_names)
        self.records_label.setText('\n'.join(lines))
        counts = [f'{names.get(game, game)}: {count}' for game, count in prefs.items()]
        self.preferences_label.setText(self._t('Deine Spielvorlieben: ', 'Your play preferences: ') + (', '.join(counts) or self._t('Noch keine.', 'None yet.')))

    def _game_names(self):
        return {key: self._t(de, en) for key, de, en in [
            ('yarn', 'Wollknäuel', 'Yarn chase'), ('cups', 'Hütchenspiel', 'Find the treat'),
            ('memory', 'Memory', 'Memory pairs'), ('bubble', 'Seifenblasen', 'Bubble pop'),
            ('story', 'Geschichten', 'Stories'),
            ('story_picnic', 'Picknick im Regen', 'Picnic in the rain'),
            ('story_sock', 'Die verschwundene Socke', 'The missing sock'),
            ('story_stars', 'Unter den Sternen', 'Under the stars')]}

    def _reset_preferences(self):
        self.store.reset_play_preferences()
        self.refresh_records()

    def _back(self):
        self.cancel_requested.emit()
        self.show_hub()

    def _request_pause(self):
        self.pause_requested.emit()

    def start_game(self, game, mode):
        if game in ('story_picnic', 'story_sock', 'story_stars'):
            self._stop_phase()
            self.current_game, self.mode = game, 'cozy'
            self.finished = self.paused = False
            self._page()
            self.action_buttons = []
            self.clock_label.clear()
            self.back_button.show()
            self.pause_button.hide()
            self.resume_button.hide()
            return
        if game not in ('yarn', 'cups', 'memory', 'bubble') or mode not in ('cozy', 'arcade'):
            return
        self._stop_phase()
        self.current_game, self.mode = game, mode
        self.finished, self.paused = False, False
        self.turns = self.score = 0
        body = self._page()
        self.clock_label.clear()
        self.hint_button = self._button(self._t('Kleiner Hinweis', 'A little hint'), self._hint)
        self.hint_button.setVisible(mode == 'cozy' and game in ('cups', 'memory'))
        self.action_buttons = []
        if game == 'cups':
            self.cup_round = 0
            self.cup_grid = QHBoxLayout()
            self.cup_buttons = []
            for i in range(3):
                button = self._button('', lambda checked=False, index=i: self._choose_cup(index))
                button.setMinimumHeight(112)
                self.cup_buttons.append(button)
                self.cup_grid.addWidget(button)
            body.addLayout(self.cup_grid)
            self.action_buttons = self.cup_buttons
            self._new_cup_round()
        elif game == 'memory':
            self.cards = list(range(6)) * 2
            random.shuffle(self.cards)
            self.open_cards, self.matched_cards, self.seen_cards = [], set(), set()
            self.card_buttons = []
            grid = QGridLayout()
            for i in range(12):
                button = self._button('?', lambda checked=False, index=i: self._choose_card(index))
                button.setMinimumHeight(76)
                self.card_buttons.append(button)
                grid.addWidget(button, i // 4, i % 4)
            self.action_buttons = self.card_buttons
            body.addLayout(grid)
            self.update_status(self._t('Finde sechs Paare. Hinweise zeigen nur bereits gesehene Karten.', 'Find six pairs. Hints only recall cards you have already seen.'))
        else:
            self.update_status(self._t('Wir spielen direkt auf deinem Desktop!', 'We’re playing right on your desktop!'))
            if game == 'yarn':
                throw = self._button(self._t('Wollknäuel werfen', 'Throw the yarn'), self.throw_requested.emit)
                self.action_buttons.append(throw)
                body.addWidget(throw)
        body.addWidget(self.hint_button)
        body.addStretch()
        self._sync_controls()

    def _schedule(self, milliseconds):
        self._remaining_phase = milliseconds
        if not self.paused:
            self.phase_timer.start(milliseconds)

    def _new_cup_round(self):
        self.cup_round += 1
        self.treat_cup = random.randrange(3)
        self.cup_positions = [0, 1, 2]
        self.shuffle_steps = 0
        self.phase = 'reveal'
        self.update_status(self._t('Merke dir das Leckerli! ', 'Watch the treat! ') + (f'{self.cup_round}/5' if self.mode == 'arcade' else ''))
        self._render_cups()
        self._schedule(1400)

    def _render_cups(self):
        for i, button in enumerate(self.cup_buttons):
            identity = self.cup_positions[i]
            text = self._t('Becher ', 'Cup ') + 'ABC'[identity]
            if self.phase == 'reveal' and identity == self.treat_cup:
                text += self._t('\nLeckerli', '\nTreat')
            button.setText(text)
            button.setEnabled(not self.paused and not self.finished and self.phase == 'guess')

    def _advance_phase(self):
        if self.paused or self.finished or not self.current_game:
            return
        if self.phase in ('reveal', 'shuffle'):
            self.phase = 'shuffle'
            if self.shuffle_steps < 5:
                a, b = random.sample(range(3), 2)
                self.cup_positions[a], self.cup_positions[b] = self.cup_positions[b], self.cup_positions[a]
                self.shuffle_steps += 1
                self.update_status(self._t('Die Becher wechseln die Plätze …', 'The cups are trading places …'))
                self._render_cups()
                self._schedule(420)
            else:
                self.phase = 'guess'
                self.update_status(self._t('Wo ist das Leckerli?', 'Where is the treat?'))
                self._render_cups()
                self._sync_controls()
        elif self.phase in ('mismatch', 'memory_hint'):
            self.open_cards.clear()
            self.phase = ''
            self._render_memory()
            self._sync_controls()

    def _choose_cup(self, index):
        if self.current_game != 'cups' or self.paused or self.finished or self.phase != 'guess' or not 0 <= index < 3:
            return
        self.turns += 1
        correct = self.cup_positions[index] == self.treat_cup
        if correct:
            self.score += 1
        self.reaction_requested.emit('success' if correct else 'curious')
        if not correct and self.mode == 'cozy':
            self.update_status(self._t('Fast! Schau noch einmal in Ruhe.', 'Almost! Take another look.'))
            return
        if self.mode == 'arcade' and self.cup_round < 5:
            self._new_cup_round()
            self._sync_controls()
        else:
            self._finish()

    def _choose_card(self, index):
        if self.current_game != 'memory' or self.paused or self.finished or self.phase or not 0 <= index < 12 or index in self.matched_cards or index in self.open_cards:
            return
        self.open_cards.append(index)
        self.seen_cards.add(index)
        if len(self.open_cards) == 2:
            self.turns += 1
            a, b = self.open_cards
            if self.cards[a] == self.cards[b]:
                self.matched_cards.update((a, b))
                self.open_cards.clear()
                self.score += 1
                self.reaction_requested.emit('success')
                if self.score == 6:
                    self._finish()
            else:
                self.phase = 'mismatch'
                self._schedule(1000)
        self._render_memory()
        self._sync_controls()

    def _render_memory(self):
        words = [self._t('🐾 Pfote', '🐾 Paw'), self._t('🥕 Karotte', '🥕 Carrot'), self._t('⭐ Stern', '⭐ Star'), self._t('🧶 Spielzeug', '🧶 Toy'), self._t('🌼 Blume', '🌼 Flower'), self._t('♥ Herz', '♥ Heart')]
        for index, button in enumerate(self.card_buttons):
            revealed = index in self.open_cards or index in self.matched_cards
            button.setText(words[self.cards[index]] if revealed else '?')
            button.setAccessibleName(f'{index + 1}: ' + button.text())
            button.setEnabled(not self.paused and not self.finished and not self.phase and index not in self.matched_cards)

    def _hint(self):
        if self.paused or self.finished or self.mode != 'cozy':
            return
        if self.current_game == 'cups' and self.phase == 'guess':
            self.update_status(self._t('Nasen-Hinweis: Schau bei Becher ', 'Nose hint: look at cup ') + 'ABC'[self.treat_cup])
            self.reaction_requested.emit('curious')
        elif self.current_game == 'memory' and not self.phase:
            known = self.seen_cards - self.matched_cards
            if not known or self.open_cards:
                self.update_status(self._t('Decke zuerst Karten auf, dann helfe ich beim Erinnern.', 'Turn over some cards first; then I can help you remember.'))
                return
            self.open_cards = sorted(known)
            self.phase = 'memory_hint'
            self._render_memory()
            self._schedule(1600)
            self._sync_controls()

    def set_paused(self, paused):
        if self.paused == bool(paused):
            return
        self.paused = bool(paused)
        if self.paused:
            self._remaining_phase = max(1, self.phase_timer.remainingTime()) if self.phase_timer.isActive() else self._remaining_phase
            self.phase_timer.stop()
            self._before_pause_status = self.status_label.text()
            self.update_status(self._t('Pause · Mit „Weiter“ geht es weiter.', 'Paused · Choose Resume when you’re ready.'))
        else:
            self.update_status(getattr(self, '_before_pause_status', ''))
            if self.phase and not self.finished:
                self.phase_timer.start(max(1, self._remaining_phase))
        self._sync_controls()

    def _sync_controls(self):
        active = bool(self.current_game)
        self.back_button.setVisible(active)
        self.pause_button.setVisible(active and not self.paused and not self.finished)
        self.resume_button.setVisible(active and self.paused and not self.finished)
        if active:
            for button in getattr(self, 'action_buttons', []):
                consumed = self.current_game == 'story' and getattr(self, '_story_chosen', False)
                button.setEnabled(not self.paused and not self.finished and not consumed)
            if self.current_game == 'cups':
                self._render_cups()
            elif self.current_game == 'memory':
                self._render_memory()
            if self.current_game in ('cups', 'memory', 'yarn', 'bubble'):
                self.hint_button.setEnabled(not self.paused and not self.finished and (not self.phase or self.phase == 'guess'))

    def tick(self, remaining):
        self.clock_label.setText('' if remaining is None else self._t('Verbleibend: ', 'Time left: ') + f'{max(0, remaining)} s')

    def update_status(self, text):
        self.status_label.setText(text)

    def finish_timeout(self):
        if self.current_game == 'memory' and self.mode == 'arcade' and not self.paused:
            self._finish()

    def _finish(self):
        if self.finished or self.current_game not in ('cups', 'memory'):
            return
        self.finished = True
        self._stop_phase()
        self.update_status(self._t('Gut gespielt! Ergebnis: ', 'Nicely played! Score: ') + str(self.score))
        self._sync_controls()
        self.round_finished.emit(self.score, self.turns)

    def show_story(self, text, choices, callback):
        self._stop_phase()
        self.current_game, self.mode = 'story', 'cozy'
        self.paused = self.finished = False
        body = self._page()
        self.update_status(text)
        self.clock_label.clear()
        self.action_buttons = []
        self._story_chosen = False
        def choose(index):
            if self._story_chosen or self.paused:
                return
            self._story_chosen = True
            for button in self.action_buttons:
                button.setEnabled(False)
            callback(index)
        for index, label in enumerate(choices):
            button = self._button(label, lambda checked=False, i=index: choose(i))
            self.action_buttons.append(button)
            body.addWidget(button)
        body.addStretch()
        self.back_button.show()
        self.pause_button.hide()
        self.resume_button.hide()

    def _close_room(self):
        self._stop_phase()
        self.finished = True
        if not self._closed_emitted:
            self._closed_emitted = True
            self.cancel_requested.emit()
            self.closed.emit()

    def reject(self):
        self._close_room()
        super().reject()

    def closeEvent(self, event):
        self._close_room()
        super().closeEvent(event)
