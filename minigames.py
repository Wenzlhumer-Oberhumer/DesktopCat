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

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient,
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

    def __init__(self, x: float, y: float, size: int = 56, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
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

    def _step(self) -> None:
        now = time.monotonic()
        if self._popping:
            if now - self._pop_t > 0.18:
                self.timer.stop()
                self.close()
                self.deleteLater()
            else:
                self.update()
            return

        dt = 0.02
        self.py += self.vy
        self.px += self.vx + math.sin(now * 3.0 + self.wobble_phase) * 0.7
        self.move(int(self.px), int(self.py))

        # Oben aus dem Bildschirm geflogen
        if self.py < -80:
            self.timer.stop()
            self.close()
            self.deleteLater()

    def mousePressEvent(self, e) -> None:
        if not self._popping:
            self._popping = True
            self._pop_t = time.monotonic()
            sound_effects.play_sound("pop")
            center = self.geometry().center()
            self.popped.emit(center.x(), center.y())
            self.update()

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

    def spawn_wave(self, count: int = 12) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()

        for _ in range(count):
            x = random.uniform(geom.left() + 60, geom.right() - 100)
            y = random.uniform(geom.bottom() - 40, geom.bottom() + 150)
            size = random.choice([42, 50, 58, 66])
            b = BubbleWidget(x, y, size)
            b.popped.connect(self._on_bubble_popped)
            b.show()
            self.active_bubbles.append(b)

    def _on_bubble_popped(self, x: int, y: int) -> None:
        if self.store is not None:
            try:
                # Punkte gutschreiben
                add_friendship_points(self.store, "treat")
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
        if self._dragging:
            return

        dt = 0.016
        # Schwerkraft & Reibung
        self.vy += 850.0 * dt
        self.vx *= (1.0 - 0.45 * dt)
        self.px += self.vx * dt
        self.py += self.vy * dt

        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            ground = float(geom.bottom() - self.height())
            lo = float(geom.left())
            hi = float(geom.right() - self.width())

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
