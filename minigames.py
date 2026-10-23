# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Desktop-Minispiele (v2.4.0): Seifenblasen-Platzen & Wollknäuel-Fangen.

Interaktive Minispiele, die direkt auf dem Desktop ablaufen:
1. BubbleWidget / BubblePopGame: Klickbare, schwebende Seifenblasen mit Glanz und Plopp-Sound.
2. YarnBallWidget: Physikalischer Spielzeugball, dem die Katze hinterherjagt.
"""
from __future__ import annotations

import math
import random
import time
from typing import Optional

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QCursor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import QApplication, QWidget

from achievements import record_achievement_event
from fun import add_friendship_points
import sound_effects


# ======================================================================================
#  1. Seifenblasen-Platzen (Bubble Pop)
# ======================================================================================
class BubbleWidget(QWidget):
    """Einzelne, aufsteigende Seifenblase, die per Klick zerplatzt."""

    popped = pyqtSignal(int, int)
    cancel_requested = pyqtSignal()

    def __init__(self, x: float, y: float, size: int = 56, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.size_val = size
        self.setFixedSize(size, size)
        self.move(int(x), int(y))

        self.px = float(x)
        self.py = float(y)
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-1.8, -3.5)
        self.wobble_phase = random.uniform(0, math.tau)
        self.t0 = time.monotonic()
        self._popping = False
        self._pop_t = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.timer.start(20)

    def _pop(self) -> None:
        self.timer.stop()
        self.close()
        self.deleteLater()

    def _check_bounds(self) -> None:
        if self.py < getattr(self, 'top_edge', 0) - 80:
            self.timer.stop()
            self.close()
            self.deleteLater()

    def _step(self) -> None:
        now = time.monotonic()
        if self._popping:
            if now - self._pop_t > 0.18:
                self._pop()
            else:
                self.update()
            return

        dt = 0.02
        self.py += self.vy
        self.px += self.vx + math.sin(now * 3.0 + self.wobble_phase) * 0.7
        self.move(int(self.px), int(self.py))

        # Oben aus dem Bildschirm geflogen
        self._check_bounds()

    def mousePressEvent(self, e) -> None:
        if not self._popping:
            self._popping = True
            self._pop_t = time.monotonic()
            sound_effects.play_sound("pop")
            center = self.geometry().center()
            self.popped.emit(center.x(), center.y())
            self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        w, h = float(self.width()), float(self.height())

        if self._popping:
            # Zerplatzende Partikel
            prog = (time.monotonic() - self._pop_t) / 0.18
            alpha = int(max(0, 255 * (1.0 - prog)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(180, 230, 255, alpha))
            r = 3.5 * (1.0 - prog)
            for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                rad = math.radians(angle)
                dist = (w / 2) * prog * 1.4
                cx = w / 2 + math.cos(rad) * dist
                cy = h / 2 + math.sin(rad) * dist
                p.drawEllipse(QPointF(cx, cy), r, r)
            return

        # Schillernde Seifenblase
        grad = QRadialGradient(w * 0.35, h * 0.35, w * 0.5)
        grad.setColorAt(0.0, QColor(255, 255, 255, 140))
        grad.setColorAt(0.4, QColor(190, 240, 255, 80))
        grad.setColorAt(0.7, QColor(255, 190, 240, 70))
        grad.setColorAt(0.95, QColor(160, 220, 255, 180))
        grad.setColorAt(1.0, QColor(140, 200, 255, 0))

        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(180, 225, 255, 190), 1.6))
        p.drawEllipse(QRectF(2, 2, w - 4, h - 4))

        # Glanzfleck links oben
        p.setBrush(QColor(255, 255, 255, 220))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(w * 0.22, h * 0.20, w * 0.24, h * 0.14))
        # Kleiner Glanzpunkt
        p.drawEllipse(QRectF(w * 0.18, h * 0.36, w * 0.08, h * 0.08))


class BubblePopGameManager:
    """Verwaltet Wellen von Seifenblasen und verknuepft Punkte & Achievements."""

    def __init__(self, store=None, cfg=None):
        self.store = store
        self.cfg = cfg
        self.active_bubbles: list[BubbleWidget] = []
        self.cancel_callback = self.clear

    def spawn_wave(self, count: int = 8, screen=None) -> None:
        self.clear()
        screen = screen or QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()

        for _ in range(count):
            x = random.uniform(geom.left() + 60, geom.right() - 100)
            y = random.uniform(geom.bottom() - 40, geom.bottom() + 150)
            size = random.choice([42, 50, 58, 66])
            b = BubbleWidget(x, y, size)
            b.top_edge = geom.top()
            b.popped.connect(self._on_bubble_popped)
            b.cancel_requested.connect(lambda: self.cancel_callback())
            b.destroyed.connect(lambda _=None, bubble=b: self.active_bubbles.remove(bubble) if bubble in self.active_bubbles else None)
            b.show()
            self.active_bubbles.append(b)

    def set_paused(self, paused: bool) -> None:
        for bubble in self.active_bubbles:
            if paused:
                bubble.timer.stop()
                bubble.setEnabled(False)
                bubble.hide()
            else:
                if bubble._popping:
                    bubble._pop_t = time.monotonic()
                bubble.setEnabled(True)
                bubble.show()
                bubble.timer.start(20)

    def clear(self) -> None:
        for bubble in self.active_bubbles:
            bubble.timer.stop()
            bubble.close()
            bubble.deleteLater()
        self.active_bubbles.clear()

    def _on_bubble_popped(self, x: int, y: int) -> None:
        self.active_bubbles = [b for b in self.active_bubbles if b.isVisible()]   # zerplatzte nicht sammeln
        if self.store is not None:
            try:
                # Punkte gutschreiben
                add_friendship_points(self.store, "bubble")
                # Achievement-Fortschritt
                record_achievement_event(self.store, "bubbles_popped", 1)
                # Seasonal Quest Fortschritt
                from seasonal_events import record_quest_event
                record_quest_event(self.store, "quest_wt_bubbles", 1)
            except Exception:
                pass


# ======================================================================================
#  2. Wollknäuel-Fangen (Yarn Ball Physics Toy)
# ======================================================================================
class YarnBallWidget(QWidget):
    """Physikalischer Spielball, der geworfen werden kann und dem die Katze nachjagt."""

    kicked = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setWindowTitle("Yarn Ball")

        self.setFixedSize(50, 50)
        self.px = 400.0
        self.py = 400.0
        self.vx = 0.0
        self.vy = 0.0
        self._dragging = False
        self._drag_start = QPointF()
        self._samples: list[tuple[float, float, float]] = []
        self.play_geometry = None
        self._paused = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._physics_step)
        self.timer.start(16)

    def launch(self, x: float, y: float, vx: float = 300.0, vy: float = -200.0) -> None:
        self.px, self.py = x, y
        self.vx, self.vy = vx, vy
        self.move(int(x), int(y))
        self.show()

    def kick(self, push_vx: float = 400.0, push_vy: float = -350.0) -> None:
        """Wird aufgerufen, wenn die Katze den Ball erreicht und wegstoesst."""
        self.vx = push_vx
        self.vy = push_vy
        sound_effects.play_sound("squeak")
        self.kicked.emit()

    def _physics_step(self) -> None:
        if self._dragging or self._paused:
            return

        dt = 0.016
        # Schwerkraft & Reibung
        self.vy += 850.0 * dt
        self.vx *= (1.0 - 0.45 * dt)
        self.px += self.vx * dt
        self.py += self.vy * dt

        screen = QApplication.primaryScreen()
        if screen:
            geom = self.play_geometry if self.play_geometry is not None else screen.availableGeometry()
            ground = float(geom.bottom() + 1 - self.height())
            lo = float(geom.left())
            hi = float(geom.right() + 1 - self.width())
            if self.py < geom.top():
                self.py = float(geom.top())
                self.vy = abs(self.vy)*0.7

            # Boden-Abprall
            if self.py >= ground:
                self.py = ground
                if abs(self.vy) > 120:
                    self.vy = -self.vy * 0.65
                    self.vx *= 0.8
                    if abs(self.vy) > 220:
                        sound_effects.play_sound("squeak")
                else:
                    self.vy = 0.0
                    self.vx *= 0.85

            # Wand-Abprall
            if self.px <= lo:
                self.px = lo
                self.vx = -self.vx * 0.7
            elif self.px >= hi:
                self.px = hi
                self.vx = -self.vx * 0.7

        self.move(int(self.px), int(self.py))

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self._dragging = False
        self._samples.clear()
        self.setEnabled(not paused)
        if paused:
            self.timer.stop()
            self.hide()
        else:
            self.show()
            self.timer.start(16)

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.cancel_requested.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._drag_start = e.globalPosition() - QPointF(self.pos())
            self._samples = [(time.monotonic(), e.globalPosition().x(), e.globalPosition().y())]

    def mouseMoveEvent(self, e) -> None:
        if self._dragging:
            target = e.globalPosition() - self._drag_start
            self.px = float(target.x())
            self.py = float(target.y())
            self.move(int(self.px), int(self.py))
            self._samples.append((time.monotonic(), e.globalPosition().x(), e.globalPosition().y()))
            if len(self._samples) > 20:
                self._samples.pop(0)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            # Schwung berechnen
            now = time.monotonic()
            recent = [s for s in self._samples if now - s[0] < 0.12]
            if len(recent) >= 2:
                dt = max(0.01, recent[-1][0] - recent[0][0])
                self.vx = (recent[-1][1] - recent[0][1]) / dt
                self.vy = (recent[-1][2] - recent[0][2]) / dt
            sound_effects.play_sound("squeak")

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        w, h = float(self.width()), float(self.height())

        # Schatten
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(QRectF(4, h - 10, w - 8, 8))

        # Roter Wollknäuel
        grad = QRadialGradient(w * 0.38, h * 0.38, w * 0.45)
        grad.setColorAt(0.0, QColor(255, 120, 130))
        grad.setColorAt(0.7, QColor(230, 50, 70))
        grad.setColorAt(1.0, QColor(160, 20, 35))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(140, 15, 30), 1.5))
        p.drawEllipse(QRectF(3, 3, w - 6, h - 6))

        # Wollfäden-Linien
        p.setPen(QPen(QColor(255, 170, 180, 180), 2.0))
        p.drawArc(QRectF(8, 8, w - 16, h - 16), 30 * 16, 120 * 16)
        p.drawArc(QRectF(10, 12, w - 20, h - 22), 180 * 16, 110 * 16)
        p.drawArc(QRectF(14, 6, w - 26, h - 18), 270 * 16, 90 * 16)

        # Heraushängender Wollfaden
        path = QPainterPath()
        path.moveTo(w - 8, h - 12)
        path.quadTo(w + 6, h - 4, w + 12, h - 16)
        p.setPen(QPen(QColor(230, 50, 70), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(path)


# ======================================================================================
#  3. Laserpointer-Spiel (LaserPointerWidget & LaserPointerManager)
# ======================================================================================
class LaserPointerWidget(QWidget):
    """32x32 rahmenloser, durchklickbarer Leuchtpunkt fuer den Laserpointer."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(32, 32)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        cx, cy = 16.0, 16.0

        # Weicher, strahlender Laser-Halo (Rosa / Rot)
        halo = QRadialGradient(cx, cy, 14.0)
        halo.setColorAt(0.0, QColor(255, 50, 90, 230))
        halo.setColorAt(0.25, QColor(255, 30, 80, 160))
        halo.setColorAt(0.60, QColor(255, 20, 60, 60))
        halo.setColorAt(1.0, QColor(255, 10, 40, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(QPointF(cx, cy), 14.0, 14.0)

        # Intensiver, heisser Laser-Kern (Weiss mit pinkem Schein)
        core = QRadialGradient(cx, cy, 4.0)
        core.setColorAt(0.0, QColor(255, 255, 255, 255))
        core.setColorAt(0.55, QColor(255, 180, 200, 240))
        core.setColorAt(1.0, QColor(255, 40, 80, 0))
        p.setBrush(QBrush(core))
        p.drawEllipse(QPointF(cx, cy), 4.5, 4.5)


class LaserPointerManager(QObject):
    """Verwaltet das Laserpointer-Minispiel, fuehrt den roten Laserpunkt und animiert die Katze."""

    def __init__(self, pet_window, cfg=None):
        super().__init__()
        self.pet_window = pet_window
        self.cfg = cfg
        self._active: bool = False
        self._laser_widget: Optional[LaserPointerWidget] = None
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._step)
        self._last_sound_t = 0.0
        self._end_time = 0.0

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, val: bool) -> None:
        self._active = bool(val)

    def start(self, duration_s: float = 25.0) -> None:
        """Startet den Laserpointer fuer die angegebene Dauer."""
        self._active = True
        self._end_time = time.monotonic() + duration_s
        self._last_sound_t = 0.0

        if self._laser_widget is None:
            self._laser_widget = LaserPointerWidget()

        pos = QCursor.pos()
        self._laser_widget.move(pos.x() - 16, pos.y() - 16)
        self._laser_widget.show()

        sound_effects.play_sound("chirp", self.cfg)

        if self.pet_window is not None:
            self.pet_window._ball_target_x = pos.x()
            if hasattr(self.pet_window, "chase_mouse"):
                self.pet_window.chase_mouse(duration_s)

        self._timer.start(16)

    def stop(self) -> None:
        """Stoppt den Laserpointer, raeumt das Widget auf und beendet die Verfolgung."""
        self._active = False
        self._timer.stop()

        if self._laser_widget is not None:
            self._laser_widget.hide()
            self._laser_widget.close()
            self._laser_widget.deleteLater()
            self._laser_widget = None

        if self.pet_window is not None:
            self.pet_window._ball_target_x = None
            if hasattr(self.pet_window, "stop_ball_chase"):
                self.pet_window.stop_ball_chase()
            elif hasattr(self.pet_window, "calm"):
                self.pet_window.calm()

    def toggle(self) -> None:
        """Schaltet den Laserpointer an oder aus."""
        if self._active:
            self.stop()
        else:
            self.start()

    def _step(self) -> None:
        if not self._active:
            return

        now = time.monotonic()
        if now >= self._end_time:
            self.stop()
            return

        pos = QCursor.pos()
        cur_x, cur_y = pos.x(), pos.y()

        if self._laser_widget is not None:
            self._laser_widget.move(cur_x - 16, cur_y - 16)

        if self.pet_window is not None:
            self.pet_window._ball_target_x = cur_x

            # Pruefe Distanz Katze zu Laserpointer X
            pet_w = float(self.pet_window.width()) if hasattr(self.pet_window, "width") else 128.0
            pet_px = float(getattr(self.pet_window, "_px", 0.0))
            cat_center_x = pet_px + pet_w / 2.0
            dist_x = abs(cat_center_x - cur_x)

            if dist_x <= 35.0:
                # Niedliche Hopser/Sprung-Reaktion (Pounce)
                if hasattr(self.pet_window, "_hop_t"):
                    self.pet_window._hop_t = now
                    if hasattr(self.pet_window, "_anim_timer") and not self.pet_window._anim_timer.isActive():
                        self.pet_window._anim_timer.start(16)

                # Sound mit 2.5s Cooldown
                if now - self._last_sound_t > 2.5:
                    self._last_sound_t = now
                    snd = random.choice(["squeak", "meow_purr"])
                    sound_effects.play_sound(snd, self.cfg)
                    if hasattr(self.pet_window, "store") and self.pet_window.store is not None:
                        try:
                            add_friendship_points(self.pet_window.store, "laser_pounce")
                        except Exception:
                            pass
