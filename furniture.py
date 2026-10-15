# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Desktop-Moebel & Habitate (v2.4.0): Kuscheliges Katzenbett / Schlafkorb.

Ein frei am Desktop verschiebbares, transparentes Moebelstueck,
in das sich die Katze im Schlafmodus (PetState.SLEEP) oder Fokus-Modus hineinkuschelt.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import QApplication, QMenu, QWidget


class PetBedWidget(QWidget):
    """Transparentes, verschiebbares Katzenbettchen."""

    bed_moved = pyqtSignal(int, int)
    hide_requested = pyqtSignal()

    def __init__(self, cfg, parent: Optional[QWidget] = None):
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        # Möbelstück bleibt standardmäßig auf dem Desktop, anstatt Arbeitsfenster zu verdecken
        if bool(cfg.get("furniture.always_on_top", False)):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWindowTitle("Desktop Cat Bed")

        self.cfg = cfg
        self.setFixedSize(140, 90)

        self._dragging = False
        self._drag_start = QPoint()

        # Position aus Config laden oder unten rechts platzieren
        self._restore_position()

    def set_always_on_top(self, on: bool) -> None:
        """Passt die Always-on-Top Eigenschaft synchron zur Katze an."""
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        if self.isVisible():
            self.show()

    def _restore_position(self) -> None:
        saved_pos = self.cfg.get("furniture.bed_pos")
        if isinstance(saved_pos, list) and len(saved_pos) == 2:
            self.move(int(saved_pos[0]), int(saved_pos[1]))
        else:
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                self.move(geom.right() - 200, geom.bottom() - 100)
            else:
                self.move(500, 500)

    def save_position(self) -> None:
        pos = self.pos()
        self.cfg.set("furniture.bed_pos", [pos.x(), pos.y()])
        self.cfg.save()
        self.bed_moved.emit(pos.x(), pos.y())

    def get_dock_position(self) -> tuple[float, float]:
        """Gibt die Ziel-Koordinaten zurueck, an die die Katze laeuft, um im Bettchen zu schlafen."""
        p = self.pos()
        # Katze sitzt mittig im Koerbchen
        return float(p.x() - 10), float(p.y() - 65)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e) -> None:
        if self._dragging:
            new_pos = e.globalPosition().toPoint() - self._drag_start
            self.move(new_pos)
            self.bed_moved.emit(new_pos.x(), new_pos.y())

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self.save_position()

    def contextMenuEvent(self, event) -> None:
        from i18n import tr
        from pet_window import style_menu
        menu = style_menu(QMenu(self))
        menu.addAction(tr('menu.hide_bed')).triggered.connect(self.hide_requested.emit)
        menu.exec(event.globalPos())
        event.accept()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        w, h = float(self.width()), float(self.height())

        # 1. Weicher Bodenschatten
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 45))
        p.drawEllipse(QRectF(10, h - 22, w - 20, 18))

        # 2. Äußeres Weidenkörbchen / Plüsch-Schale
        basket_grad = QLinearGradient(0, 25, 0, h - 8)
        basket_grad.setColorAt(0.0, QColor(210, 160, 120))
        basket_grad.setColorAt(1.0, QColor(145, 100, 70))
        p.setBrush(QBrush(basket_grad))
        p.setPen(QPen(QColor(110, 70, 45), 2.0))
        p.drawRoundedRect(QRectF(8, 25, w - 16, h - 35), 24, 24)

        # 3. Weiches Innenkissen (Plüsch-Rosa/Creme)
        cushion_grad = QLinearGradient(0, 32, 0, h - 14)
        cushion_grad.setColorAt(0.0, QColor(255, 230, 235))
        cushion_grad.setColorAt(1.0, QColor(255, 195, 210))
        p.setBrush(QBrush(cushion_grad))
        p.setPen(QPen(QColor(230, 165, 180), 1.5))
        p.drawRoundedRect(QRectF(16, 32, w - 32, h - 46), 18, 18)

        # 4. Kleine Pfoten-Stickerei in der Mitte
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(220, 140, 165, 180))
        # Hauptballen
        p.drawEllipse(QRectF(w / 2 - 8, h / 2 - 4, 16, 12))
        # 3 kleine Zehen
        p.drawEllipse(QRectF(w / 2 - 11, h / 2 - 11, 6, 6))
        p.drawEllipse(QRectF(w / 2 - 3, h / 2 - 13, 6, 6))
        p.drawEllipse(QRectF(w / 2 + 5, h / 2 - 11, 6, 6))
