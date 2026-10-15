"""One local play session owns the pet, desktop toys and paused game clock."""
from __future__ import annotations

import math
import time
import uuid
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QGuiApplication
import i18n


class PlayClock:
    def __init__(self, duration=None, now=None):
        self.duration = duration
        self.elapsed = 0.0
        self.started = time.monotonic() if now is None else now
        self.paused = False

    def pause(self, now=None):
        if not self.paused:
            now = time.monotonic() if now is None else now
            self.elapsed += max(0, now - self.started)
            self.paused = True

    def resume(self, now=None):
        if self.paused:
            self.started = time.monotonic() if now is None else now
            self.paused = False

    def remaining(self, now=None):
        if self.duration is None:
            return None
        now = time.monotonic() if now is None else now
        elapsed = self.elapsed + (0 if self.paused else max(0, now-self.started))
        return max(0, math.ceil(self.duration-elapsed))


class ContactLatch:
    def __init__(self):
        self.touching = False

    def touch(self, contact):
        fresh = contact and not self.touching
        self.touching = contact
        return fresh


class PlayCoordinator(QObject):
    def __init__(self, buddy, store):
        super().__init__(buddy)
        self.buddy, self.pet, self.store = buddy, buddy.pet, store
        self.room = None
        self.active = False
        self.ball = None
        self.story = None
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self._tick)
        self.buddy.bubble_mgr.cancel_callback = self._back_to_hub
        QGuiApplication.instance().screenRemoved.connect(self._screen_removed)

    def t(self, de, en):
        return en if i18n.lang() == 'en' else de

    def open(self):
        if self.room is None:
            from game_room import GameRoom
            self.room = GameRoom(self.store, self.buddy.cfg)
            self.room.start_requested.connect(self.start)
            self.room.trick_requested.connect(self.trick)
            self.room.closed.connect(self.cancel)
            self.room.cancel_requested.connect(self.cancel)
            self.room.pause_requested.connect(self.pause)
            self.room.resume_requested.connect(self.resume)
            self.room.throw_requested.connect(self.throw)
            self.room.round_finished.connect(self.finish)
            self.room.reaction_requested.connect(self.react)
        if not self.active:
            self.room.show_hub()
        self.room.show()
        self.room.raise_()
        self.room.activateWindow()

    def blocked(self):
        from PyQt6.QtWidgets import QApplication
        from main import _is_fullscreen_foreground
        b = self.buddy
        return (b._focus_mode or not self.pet.isVisible() or b.brain.busy
                or b.brain.pending_action or b._settings_open or b.input.isVisible()
                or QApplication.activeModalWidget() is not None or _is_fullscreen_foreground())

    def start(self, game, mode='cozy'):
        if game not in ('yarn', 'bubble', 'cups', 'memory', 'story_picnic', 'story_sock', 'story_stars'):
            return
        if self.blocked():
            return
        self.cancel()
        self.open()
        self.buddy._dismiss_interaction()
        self.buddy.bubble.hide_now()
        self.buddy.update_prompt.hide_now()
        self.active = True
        self.game, self.mode = game, 'arcade' if mode == 'arcade' else 'cozy'
        self.session_id = uuid.uuid4().hex
        self.score = 0
        self.screen = self.pet.screen()
        self.pet._play_screen = self.screen
        self.contact = ContactLatch()
        self.clock = PlayClock(60 if self.mode == 'arcade' and game in ('yarn', 'memory') else None)
        self.pet.wake()
        self.pet.calm()
        self.pet.freeze(game != 'yarn')
        self.room.start_game(game, self.mode)
        if game == 'yarn':
            from minigames import YarnBallWidget
            self.ball = YarnBallWidget()
            self.ball.play_geometry = self.screen.availableGeometry()
            self.ball.kicked.connect(self._caught)
            self.ball.cancel_requested.connect(self._back_to_hub)
            # Desktop play always takes place on this monitor's floor.
            self.pet._py = float(self.pet._ground_y())
            self.pet.move(int(self.pet._px), int(self.pet._py))
            self.throw()
        elif game == 'bubble':
            self.buddy.bubble_mgr.spawn_wave(14, self.screen)
        elif game.startswith('story_'):
            from play_stories import StorySession
            self.story = StorySession(game, i18n.lang(), self.pet.character)
            self._show_story()
        self.timer.start()

    def throw(self):
        if self.active and self.game == 'yarn' and not self.clock.paused:
            g = self.screen.availableGeometry()
            x = max(g.left(), min(g.right()-50, self.pet.x()+self.pet.width()/2+120))
            self.ball.launch(x, g.bottom()-150, -240 if x > self.pet.x()+self.pet.width()/2 else 240, -260)
            self.pet.chase_ball(self.ball.geometry().center().x())

    def _caught(self):
        if not self.active or self.clock.paused:
            return
        from fun import add_friendship_points
        from achievements import record_achievement_event
        add_friendship_points(self.store, 'yarn')
        record_achievement_event(self.store, 'yarn_catches', 1)
        self.store.unlock_play_badge('first_ball')
        self.score += 1
        self.pet.react_happy()
        self.room.update_status(self.t(f'Gefangen! {self.score} echte Ballkontakte 🐾', f'Caught! {self.score} real ball contacts 🐾'))

    def _tick(self):
        if not self.active:
            return
        if self.screen not in QGuiApplication.screens():
            self.cancel()
            return
        if self.blocked():
            self.pause()
        if self.clock.paused:
            return
        remaining = self.clock.remaining()
        self.room.tick(remaining)
        if remaining == 0:
            if self.game == 'memory':
                self.room.finish_timeout()
            else:
                self.finish(self.score, 0)
            return
        if self.ball:
            center = self.ball.geometry().center()
            self.pet.chase_ball(center.x())
            # Full body rectangle is deliberately excluded: only the floor paws count.
            paw_x = self.pet.x()+self.pet.width()/2
            paw_y = self.pet.y()+148*self.pet.scale
            touching = (not self.ball._dragging and abs(center.x()-paw_x) < self.ball.width()/2+24*self.pet.scale
                        and abs(center.y()-paw_y) < self.ball.height()/2+18*self.pet.scale)
            if self.contact.touch(touching):
                direction = 1 if center.x() >= paw_x else -1
                self.ball.kick(direction*320, -250)
        elif self.game == 'bubble':
            live = [b for b in self.buddy.bubble_mgr.active_bubbles if b.isVisible()]
            if not live:
                self.finish(0, 0)

    def pause(self):
        if not self.active or self.clock.paused:
            return
        self.clock.pause()
        self.pet.stop_ball_chase()
        if not self.buddy.brain.busy:
            self.pet.freeze(True)
        if self.ball:
            self.ball.set_paused(True)
        self.buddy.bubble_mgr.set_paused(True)
        self.room.set_paused(True)

    def resume(self):
        if self.active and self.clock.paused and not self.blocked():
            self.clock.resume()
            self.room.set_paused(False)
            self.pet.calm()
            self.pet.freeze(self.game != 'yarn')
            if self.ball:
                self.ball.set_paused(False)
            self.buddy.bubble_mgr.set_paused(False)

    def _show_story(self):
        self.room.show_story(self.story.text, list(self.story.choices), self._choose_story)

    def _choose_story(self, index):
        if self.active and not self.clock.paused and self.story and not self.story.finished:
            self.react(self.story.choose(index))
            self._show_story()
            if self.story.finished:
                ending = self.story.text
                self.finish(1, 0)
                self.room.show_story(ending, [], lambda _: None)

    def react(self, action):
        if action == 'dance':
            self.pet.dance(2)
        elif action == 'stretch':
            self.pet.wake_with_stretch()
        else:
            self.pet.react_happy()

    def trick(self, name):
        if self.active or self.blocked() or name not in ('highfive', 'wave', 'dance'):
            return
        self.buddy._dismiss_interaction()
        if name == 'dance':
            self.pet.dance(3)
        else:
            self.pet.perform_trick(name)
        if name == 'highfive':
            self.store.unlock_play_badge('highfive')
        self.room.update_status(self.t('Ein Pfötchen nur für dich! 🐾', 'A little paw just for you! 🐾'))
        self.room.refresh_records()

    def finish(self, score=0, turns=0):
        if not self.active or self.clock.paused:
            return
        result = self.store.finish_play_session(self.session_id, self.game, self.mode, score,
                    completed=True, remember=bool(self.buddy.cfg.get('privacy.remember', True)), turns=turns)
        self.cancel()
        self.room.show_hub()
        self.room.update_status(self.t(f'Zusammen geschafft! +{result["awarded"]} Freundschaftspunkte',
                                      f'We did it together! +{result["awarded"]} friendship points'))
        self.room.refresh_records()

    def cancel(self):
        if not self.active:
            return
        # Cancellation never writes a completed round or a reward.
        self.active = False
        self.timer.stop()
        self.pet.stop_ball_chase()
        self.pet._play_screen = None
        if self.ball:
            self.ball.close()
            self.ball.deleteLater()
            self.ball = None
        self.buddy.bubble_mgr.clear()
        self.story = None
        if not self.buddy.brain.busy and not self.buddy.input.isVisible():
            self.pet.freeze(False)

    def _screen_removed(self, screen):
        if self.active and screen == self.screen:
            self.cancel()
            self.room.show_hub()

    def _back_to_hub(self):
        if not self.active:
            return
        self.cancel()
        if self.room:
            self.room.show_hub()
