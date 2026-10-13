"""Sprechblase und Eingabeleiste: schwebende, abgerundete Dark-Mode-Karten mit Pfeil zum Pet."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPalette, QPen,
)
from PyQt6.QtWidgets import QLabel, QLineEdit, QWidget

FONT_FAMILY = "Segoe UI"
BG_TOP = QColor("#35373D")
BG_BOTTOM = QColor("#26282C")
ACCENT = QColor("#FF8FB1")
TEXT = QColor("#F5F6F8")
MUTED = QColor("#8D919B")


class FloatingCard(QWidget):
    """Basisklasse: rahmenloses, transparentes Top-Level-Fenster mit weichem Schatten + Pfeil nach unten."""

    M = 18          # Rand fuer den Schatten
    ARROW_H = 11
    RADIUS = 18

    def __init__(self, focusable: bool = False):
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        if not focusable:
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if not focusable:
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._anchor = QPoint(0, 0)
        self._arrow_x = 40.0
        self._fading_out = False
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.finished.connect(self._on_fade_finished)
        self.setWindowOpacity(0.0)

    # -- Geometrie -------------------------------------------------------------------
    def body_rect(self) -> QRectF:
        return QRectF(self.M, self.M, self.width() - 2 * self.M, self.height() - 2 * self.M - self.ARROW_H)

    def set_content_size(self, cw: int, ch: int) -> None:
        self.resize(int(cw + 2 * self.M), int(ch + 2 * self.M + self.ARROW_H))
        self._reposition()

    def anchor_to(self, point: QPoint) -> None:
        """point = Stelle ueber dem Kopf des Pets, auf die der Pfeil zeigen soll (globale Koordinaten)."""
        self._anchor = QPoint(point)
        self._reposition()

    def _screen_geo(self) -> QRect:
        screen = QGuiApplication.screenAt(self._anchor) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _reposition(self) -> None:
        if self.width() <= 0:
            return
        geo = self._screen_geo()
        w, h = self.width(), self.height()
        left = self._anchor.x() - w // 2
        left = max(geo.left() + 2, min(left, geo.right() - w - 2))
        top = self._anchor.y() - (h - self.M)
        top = max(geo.top() + 2, top)
        self._arrow_x = float(max(self.M + self.RADIUS + 8, min(self._anchor.x() - left, w - self.M - self.RADIUS - 8)))
        if self.pos() != QPoint(left, top):
            self.move(left, top)
        self.update()

    # -- Fade ------------------------------------------------------------------------
    def fade_in(self, ms: int = 170) -> None:
        self._fading_out = False
        self._fade.stop()
        self._fade.setDuration(ms)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.start()

    def fade_out(self, ms: int = 550) -> None:
        if not self.isVisible():
            return
        self._fading_out = True
        self._fade.stop()
        self._fade.setDuration(ms)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self) -> None:
        if self._fading_out:
            self._fading_out = False
            self.hide()
            self.on_hidden()

    def on_hidden(self) -> None:  # Hook
        pass

    def hide_now(self) -> None:
        self._fade.stop()
        self._fading_out = False
        self.setWindowOpacity(0.0)
        if self.isVisible():
            self.hide()
            self.on_hidden()

    # -- Zeichnen --------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = self.body_rect()
        r = self.RADIUS

        # weicher Schatten (konzentrische, ausfadende Ringe)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(1, self.M):
            alpha = int(30 * (1 - i / self.M) ** 2)
            if alpha <= 0:
                continue
            p.setPen(QPen(QColor(0, 0, 0, alpha), 1.6))
            p.drawRoundedRect(body.adjusted(-i, -i + 4, i, i + 4), r + i, r + i)

        path = QPainterPath()
        path.addRoundedRect(body, r, r)
        ax, b = self._arrow_x, body.bottom()
        arrow = QPainterPath(QPointF(ax - 11, b - 1))
        arrow.quadTo(QPointF(ax - 2.5, b + 1.5), QPointF(ax, b + self.ARROW_H))
        arrow.quadTo(QPointF(ax + 2.5, b + 1.5), QPointF(ax + 11, b - 1))
        arrow.closeSubpath()
        path = path.united(arrow)

        grad = QLinearGradient(0, body.top(), 0, body.bottom())
        grad.setColorAt(0, BG_TOP)
        grad.setColorAt(1, BG_BOTTOM)
        p.setBrush(grad)
        p.setPen(QPen(QColor(255, 255, 255, 34), 1.0))
        p.drawPath(path)
        self.paint_content(p, body)

    def paint_content(self, p: QPainter, body: QRectF) -> None:  # Hook
        pass


class SpeechBubble(FloatingCard):
    """Schwebende Sprechblase; blendet sich nach ein paar Sekunden mit Fade-Out aus. Klick oeffnet Eingabe."""

    clicked = pyqtSignal()
    MAX_TEXT_W = 280
    PAD_X = 16
    PAD_Y = 11

    def __init__(self, cfg=None):
        super().__init__(focusable=False)
        self._cfg = cfg
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        font = QFont(FONT_FAMILY)
        font.setPointSizeF(10.5)
        self.label.setFont(font)
        self.label.setStyleSheet("color: #F5F6F8; background: transparent;")
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(lambda: self.fade_out())
        self.persistent = False

    def say(self, text: str, duration_ms: Optional[int] = None, persistent: bool = False) -> None:
        """Zeigt Text. persistent=True bleibt bis zur naechsten Nachricht stehen (z. B. 'Ich bin dran...')."""
        text = (text or "").strip()
        if not text:
            return
        self.persistent = persistent
        fm = QFontMetrics(self.label.font())
        rect = fm.boundingRect(QRect(0, 0, self.MAX_TEXT_W, 4000), int(Qt.TextFlag.TextWordWrap), text)
        tw, th = max(rect.width() + 6, 60), rect.height() + 4
        self.label.setText(text)
        self.label.setGeometry(self.M + self.PAD_X, self.M + self.PAD_Y, tw, th)
        self.set_content_size(tw + 2 * self.PAD_X, th + 2 * self.PAD_Y)

        self._hide_timer.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self.fade_in()
        if not persistent:
            if duration_ms is None:
                base = 4000
                if self._cfg is not None:
                    base = int(float(self._cfg.get("pet.bubble_seconds", 4.0)) * 1000)
                # lange Texte bekommen etwas mehr Lesezeit
                duration_ms = base + max(0, len(text) - 60) * 45
            self._hide_timer.start(min(duration_ms, 14000))

    def mousePressEvent(self, event) -> None:
        self._hide_timer.stop()
        self.fade_out(150)
        self.clicked.emit()

    def on_hidden(self) -> None:
        self.persistent = False


class _Line(QLineEdit):
    escaped = pyqtSignal()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
            return
        super().keyPressEvent(event)


class InputBar(FloatingCard):
    """Schlankes Eingabefeld ueber dem Pet. Enter = senden, Escape = schliessen."""

    submitted = pyqtSignal(str)
    closed = pyqtSignal()

    BAR_W = 390
    BAR_H = 54

    def __init__(self):
        super().__init__(focusable=True)
        self._was_active = False
        self.line = _Line(self)
        self.line.setPlaceholderText("Was soll ich tun? \U0001F43E")
        self.line.setFrame(False)
        font = QFont(FONT_FAMILY)
        font.setPointSizeF(11)
        self.line.setFont(font)
        self.line.setStyleSheet(
            "QLineEdit { background: transparent; border: none; color: #F5F6F8;"
            " selection-background-color: #FF8FB1; selection-color: #26282C; }"
        )
        pal = self.line.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, MUTED)
        self.line.setPalette(pal)
        self.line.returnPressed.connect(self._submit)
        self.line.escaped.connect(self.dismiss)
        self.history: list[str] = []
        self._hist_idx = 0
        self.line.installEventFilter(self)

        self.set_content_size(self.BAR_W, self.BAR_H)
        self.line.setGeometry(self.M + 50, self.M + 9, self.BAR_W - 50 - 56, self.BAR_H - 18)

    # -- Verhalten -------------------------------------------------------------------
    def popup(self, anchor: QPoint, placeholder: Optional[str] = None) -> None:
        self.line.clear()
        self._hist_idx = len(self.history)
        self._was_active = False
        if placeholder:
            self.line.setPlaceholderText(placeholder)
        else:
            self.line.setPlaceholderText("Was soll ich tun? \U0001F43E")
        self.anchor_to(anchor)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.fade_in(140)
        self.activateWindow()
        self._force_foreground()
        self.line.setFocus(Qt.FocusReason.PopupFocusReason)

    def _force_foreground(self) -> None:
        """Windows gibt Fremdfenstern nicht immer sofort den Fokus - mit pywin32 nachhelfen."""
        try:
            import win32api, win32gui, win32process
            hwnd = int(self.winId())
            fg = win32gui.GetForegroundWindow()
            if fg and fg != hwnd:
                tid_fg = win32process.GetWindowThreadProcessId(fg)[0]
                tid_me = win32api.GetCurrentThreadId()
                if tid_fg != tid_me:
                    win32process.AttachThreadInput(tid_me, tid_fg, True)
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                    finally:
                        win32process.AttachThreadInput(tid_me, tid_fg, False)
                else:
                    win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _submit(self) -> None:
        text = self.line.text().strip()
        self.dismiss()
        if text:
            if not self.history or self.history[-1] != text:
                self.history.append(text)
                self.history = self.history[-30:]
            self.submitted.emit(text)

    def dismiss(self) -> None:
        if self.isVisible() and not self._fading_out:
            self.fade_out(130)

    def on_hidden(self) -> None:
        self.closed.emit()

    def eventFilter(self, obj, event) -> bool:  # Pfeil hoch/runter = Verlauf
        from PyQt6.QtCore import QEvent
        if obj is self.line and event.type() == QEvent.Type.KeyPress and self.history:
            if event.key() == Qt.Key.Key_Up and self._hist_idx > 0:
                self._hist_idx -= 1
                self.line.setText(self.history[self._hist_idx])
                return True
            if event.key() == Qt.Key.Key_Down and self._hist_idx < len(self.history):
                self._hist_idx += 1
                self.line.setText(self.history[self._hist_idx] if self._hist_idx < len(self.history) else "")
                return True
        return super().eventFilter(obj, event)

    def event(self, e) -> bool:
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.WindowActivate:
            self._was_active = True
        elif e.type() == QEvent.Type.WindowDeactivate and self._was_active:
            QTimer.singleShot(0, self.dismiss)   # Klick daneben schliesst die Leiste
        return super().event(e)

    # -- Zeichnen --------------------------------------------------------------------
    def paint_content(self, p: QPainter, body: QRectF) -> None:
        cy = body.center().y()
        cx = body.left() + 28
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ACCENT)
        p.drawEllipse(QPointF(cx, cy + 3.5), 7.2, 5.6)
        for dx, dy in ((-8.6, -3.6), (-3.2, -8.2), (3.2, -8.2), (8.6, -3.6)):
            p.drawEllipse(QPointF(cx + dx, cy + dy), 2.7, 3.3)
        # Enter-Badge
        badge = QRectF(body.right() - 40, cy - 11, 28, 22)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawRoundedRect(badge, 7, 7)
        p.setPen(MUTED)
        f = QFont(FONT_FAMILY)
        f.setPointSizeF(10)
        p.setFont(f)
        p.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), "\u21B5")
