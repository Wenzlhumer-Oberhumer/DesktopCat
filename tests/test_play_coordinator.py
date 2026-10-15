import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from play_coordinator import PlayClock, ContactLatch


class PlayClockTests(unittest.TestCase):
    def test_pause_excludes_time_and_requires_resume(self):
        c = PlayClock(60, now=10)
        self.assertEqual(c.remaining(20), 50)
        c.pause(20)
        self.assertEqual(c.remaining(200), 50)
        c.resume(200)
        self.assertEqual(c.remaining(210), 40)
        c.pause(211)
        c.pause(300)
        self.assertEqual(c.remaining(500), 39)

    def test_contact_needs_separation(self):
        latch = ContactLatch()
        self.assertTrue(latch.touch(True))
        self.assertFalse(latch.touch(True))
        self.assertFalse(latch.touch(False))
        self.assertTrue(latch.touch(True))

    def test_ball_bounds_use_negative_monitor_and_close_stops_timer(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QRect
        from minigames import YarnBallWidget
        app = QApplication.instance() or QApplication([])
        ball = YarnBallWidget()
        ball.play_geometry = QRect(-1920, -200, 1920, 1040)
        ball.launch(-2200, 1200, -100, 10)
        ball._physics_step()
        self.assertGreaterEqual(ball.x(), -1920)
        self.assertLessEqual(ball.y()+ball.height(), 840)
        ball.set_paused(True)
        before = (ball.px, ball.py)
        ball._physics_step()
        self.assertEqual((ball.px, ball.py), before)
        ball.set_paused(False)
        ball.close()
        self.assertFalse(ball.timer.isActive())

    def test_finish_once_and_cancel_has_no_round_reward(self):
        from play_coordinator import PlayCoordinator
        c = SimpleNamespace(active=True, clock=SimpleNamespace(paused=False),
            store=MagicMock(), session_id='round', game='cups', mode='cozy',
            buddy=SimpleNamespace(cfg=SimpleNamespace(get=lambda k,d:d)), room=MagicMock(),
            t=lambda de,en:de)
        c.store.finish_play_session.return_value = {'awarded':3}
        c.cancel = lambda: setattr(c, 'active', False)
        PlayCoordinator.finish(c, 1, 1)
        PlayCoordinator.finish(c, 1, 1)
        c.store.finish_play_session.assert_called_once()

    def test_minimum_scale_can_touch_fixed_size_ball(self):
        from play_coordinator import PlayCoordinator
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        ball = MagicMock()
        ball.geometry.return_value = QRect(23, 98, 50, 50)
        ball.width.return_value = ball.height.return_value = 50
        ball._dragging = False
        pet = SimpleNamespace(x=lambda:0, y=lambda:60, width=lambda:96, scale=0.6, chase_ball=MagicMock())
        c = SimpleNamespace(active=True, screen=QGuiApplication.primaryScreen(), blocked=lambda:False,
            clock=SimpleNamespace(paused=False,remaining=lambda:None), room=MagicMock(),
            ball=ball, pet=pet, contact=ContactLatch())
        PlayCoordinator._tick(c)
        ball.kick.assert_called_once()

    def test_session_monitor_overrides_ambiguous_stacked_x(self):
        from pet_window import PetWindow
        first, second = MagicMock(), MagicMock()
        p = SimpleNamespace(_play_screen=second)
        with patch('pet_window.QGuiApplication.screens',return_value=[first,second]):
            self.assertIs(PetWindow._screen_for_x(p, 200),second)

    def test_desktop_toys_accept_escape(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QApplication
        from minigames import YarnBallWidget, BubbleWidget
        app = QApplication.instance() or QApplication([])
        for toy in (YarnBallWidget(), BubbleWidget(0, 0)):
            cancelled = []
            toy.cancel_requested.connect(lambda:cancelled.append(True))
            toy.show()
            QTest.keyClick(toy, Qt.Key.Key_Escape)
            self.assertEqual(cancelled, [True])
            toy.close()
