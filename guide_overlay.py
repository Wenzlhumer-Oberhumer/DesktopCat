"""Klick-Zeiger-Overlay: transparentes, durchklickbares Vollbild-Overlay mit pulsierendem Ring und Pfeil."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPolygonF,
)
from PyQt6.QtWidgets import QWidget

ACTION_LABELS = {
    "left": "🖱️ Linksklick",
    "right": "🖱️ Rechtsklick",
    "double": "🖱️🖱️ Doppelklick",
    "type": "⌨️ Tippen",
    "scroll": "🖲️ Scrollen",
    "none": "ℹ️ Info",
}


class GuideOverlay(QWidget):
    """Durchklickbares Overlay fuer Klick-Anleitungen."""

    def __init__(self, parent=None):
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._box: Optional[QRect] = None
        self._pet_pos: Optional[QPoint] = None
        self._action = "left"
        self._target_name = ""
        self._screen_origin = QPoint(0, 0)

        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 fps
        self._timer.timeout.connect(self._on_tick)

    def set_screen_geometry(self, geom: QRect) -> None:
        """Positioniert das Overlay ueber dem gesamten Zielmonitor."""
        self._screen_origin = geom.topLeft()
        self.setGeometry(geom)

    def set_target(
        self,
        box: Optional[QRect],
        pet_pos: Optional[QPoint] = None,
        action: str = "left",
        target_name: str = "",
    ) -> None:
        """Setzt das Ziel-Rechteck (in globalen Bildschirmkoordinaten) und startet die Animation."""
        self._box = box
        self._pet_pos = pet_pos
        self._action = (action or "left").lower()
        self._target_name = target_name or ""
        if box is not None and not self._timer.isActive():
            self._timer.start()
        elif box is None and self._timer.isActive():
            self._timer.stop()
        self.update()

    def set_pet_pos(self, pet_pos: QPoint) -> None:
        self._pet_pos = pet_pos
        self.update()

    def hide_target(self) -> None:
        self._box = None
        if self._timer.isActive():
            self._timer.stop()
        self.update()

    def _on_tick(self) -> None:
        self._phase = (self._phase + 0.025) % 1.0
        self.update()

    # -- Zeichnen ----------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        if self._box is None:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Lokale Koordinaten bezueglich dieses Overlays
        b = self._box.translated(-self._screen_origin)

        # 1. Pulsierende Ringe um die Ziel-Box
        self._draw_pulsing_rings(p, b)

        # 2. Pfeil von der Figur zur Box
        if self._pet_pos is not None:
            pet_local = self._pet_pos - self._screen_origin
            self._draw_arrow(p, pet_local, b)

        # 3. Label-Pille mit Aktion und Icon
        self._draw_action_pill(p, b)

    def _draw_pulsing_rings(self, p: QPainter, b: QRect) -> None:
        r = 8.0
        # Innerer Ring (sanft atmend)
        p.setBrush(Qt.BrushStyle.NoBrush)
        inner_pulse = 2.0 + 1.5 * abs(self._phase - 0.5) * 2.0
        p.setPen(QPen(QColor(255, 143, 177, 230), inner_pulse))
        p.drawRoundedRect(QRectF(b).adjusted(-4, -4, 4, 4), r, r)

        # Äußerer expandierender Ring (ausblendend, Neon-Grün)
        d = 4.0 + 16.0 * self._phase
        alpha = int(220 * (1.0 - self._phase))
        p.setPen(QPen(QColor(90, 247, 142, alpha), 2.2))
        p.drawRoundedRect(QRectF(b).adjusted(-d, -d, d, d), r + d * 0.5, r + d * 0.5)

    def _draw_arrow(self, p: QPainter, pet_pt: QPoint, target_box: QRect) -> None:
        t_center = target_box.center()
        p1 = QPointF(pet_pt.x() + 40, pet_pt.y() + 40)
        p2 = QPointF(t_center.x(), t_center.y())

        # Richtung und Distanz
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 40:
            return

        # Sanft geschwungener Pfeil
        path = QPainterPath(p1)
        ctrl = QPointF((p1.x() + p2.x()) / 2.0, min(p1.y(), p2.y()) - 30)
        path.quadTo(ctrl, p2)

        pen = QPen(QColor(255, 143, 177, 190), 2.0, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Pfeilspitze an p2
        ux = dx / dist
        uy = dy / dist
        arrow_size = 10.0
        left_wing = QPointF(p2.x() - ux * arrow_size + uy * (arrow_size * 0.6),
                            p2.y() - uy * arrow_size - ux * (arrow_size * 0.6))
        right_wing = QPointF(p2.x() - ux * arrow_size - uy * (arrow_size * 0.6),
                             p2.y() - uy * arrow_size + ux * (arrow_size * 0.6))
        tip = QPolygonF([p2, left_wing, right_wing])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 143, 177, 230))
        p.drawPolygon(tip)

    def _draw_action_pill(self, p: QPainter, b: QRect) -> None:
        act = self._action
        base_label = ACTION_LABELS.get(act, "🖱️ Klick")
        if act == "type" and self._target_name:
            text = f"⌨️ Tippen: „{self._target_name}“"
        elif self._target_name and act != "none":
            text = f"{base_label} auf {self._target_name}"
        else:
            text = base_label

        font = QFont("Segoe UI", 10)
        font.setBold(True)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text) + 24
        th = 28

        # Oberhalb oder unterhalb der Box platzieren
        px = int(b.center().x() - tw / 2)
        if b.top() - th - 12 > 10:
            py = b.top() - th - 10
        else:
            py = b.bottom() + 10

        # Im sichtbaren Overlay-Bereich halten
        px = max(10, min(px, self.width() - tw - 10))
        py = max(10, min(py, self.height() - th - 10))

        pill_rect = QRectF(px, py, tw, th)

        # Schatten
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(pill_rect.adjusted(1, 2, 1, 2), 14, 14)

        # Hintergrund & Rand
        p.setBrush(QColor(38, 40, 44, 235))
        p.setPen(QPen(QColor(255, 143, 177, 200), 1.2))
        p.drawRoundedRect(pill_rect, 14, 14)

        # Text
        p.setPen(QColor("#F5F6F8"))
        p.drawText(pill_rect, int(Qt.AlignmentFlag.AlignCenter), text)
