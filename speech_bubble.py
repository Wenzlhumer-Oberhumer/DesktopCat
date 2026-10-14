# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Sprechblase und Eingabeleiste: schwebende, abgerundete Dark-Mode-Karten mit Pfeil zum Pet."""
from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPalette, QPen,
)
from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QWidget

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
        self._buttons: list[QPushButton] = []
        self._action_callbacks: list[tuple[str, Callable]] = []
        self._actions_active = False

    def _clear_actions(self) -> None:
        self._actions_active = False
        self._action_callbacks.clear()
        for btn in self._buttons:
            btn.hide()
            btn.deleteLater()
        self._buttons.clear()

    def say(self, text: str, duration_ms: Optional[int] = None, persistent: bool = False) -> None:
        """Zeigt Text. persistent=True bleibt bis zur naechsten Nachricht stehen (z. B. 'Ich bin dran...')."""
        text = (text or "").strip()
        if not text:
            return
        self._clear_actions()
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

    def show_with_actions(
        self,
        text: str,
        actions: list[tuple[str, Callable]],
        duration_ms: Optional[int] = None,
    ) -> None:
        """Zeigt Text mit interaktiven Aktions-Buttons (z. B. Weiter / Nochmal / Fertig)."""
        text = (text or "").strip()
        if not text:
            return
        self._clear_actions()
        self._actions_active = True
        self.persistent = (duration_ms is None)

        fm = QFontMetrics(self.label.font())
        rect = fm.boundingRect(QRect(0, 0, max(self.MAX_TEXT_W, 280), 4000), int(Qt.TextFlag.TextWordWrap), text)
        tw, th = max(rect.width() + 6, 80), rect.height() + 4
        self.label.setText(text)

        btn_font = QFont(FONT_FAMILY)
        btn_font.setPointSizeF(9.5)
        btn_font.setBold(True)
        btn_fm = QFontMetrics(btn_font)

        btn_widths: list[int] = []
        for label, cb in actions:
            btn = QPushButton(label, self)
            btn.setFont(btn_font)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 22); border: 1px solid rgba(255, 255, 255, 45);"
                " border-radius: 9px; color: #F5F6F8; padding: 4px 10px; font-weight: 600; }"
                "QPushButton:hover { background: rgba(255, 143, 177, 50); border: 1px solid #FF8FB1; color: #FFFFFF; }"
                "QPushButton:pressed { background: rgba(255, 143, 177, 90); }"
            )
            btn.clicked.connect(lambda checked=False, callback=cb: self._on_action_clicked(callback))
            btn.show()
            self._buttons.append(btn)
            self._action_callbacks.append((label, cb))
            bw = btn_fm.horizontalAdvance(label) + 24
            btn_widths.append(bw)

        total_btn_w = sum(btn_widths) + max(0, len(btn_widths) - 1) * 8
        content_w = max(tw, total_btn_w, 200)
        btn_h = 28
        content_h = th + 12 + btn_h

        self.label.setGeometry(self.M + self.PAD_X, self.M + self.PAD_Y, content_w, th)

        # Buttons unten anordnen
        bx = self.M + self.PAD_X
        by = self.M + self.PAD_Y + th + 10
        for btn, bw in zip(self._buttons, btn_widths):
            btn.setGeometry(bx, by, bw, btn_h)
            bx += bw + 8

        self.set_content_size(content_w + 2 * self.PAD_X, content_h + 2 * self.PAD_Y)

        self._hide_timer.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self.fade_in()
        self.setFocus()
        if duration_ms is not None:
            self._hide_timer.start(duration_ms)

    def _on_action_clicked(self, callback: Callable) -> None:
        self._actions_active = False
        self._hide_timer.stop()
        self.fade_out(150)
        try:
            callback()
        except Exception:
            pass

    def keyPressEvent(self, event) -> None:
        if self._actions_active and event.key() == Qt.Key.Key_Escape:
            for label, cb in self._action_callbacks:
                low = label.lower()
                if any(k in low for k in ("fertig", "schließen", "abbrechen", "close")):
                    self._on_action_clicked(cb)
                    return
            self.fade_out(150)
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._actions_active:
            return
        self._hide_timer.stop()
        self.fade_out(150)
        self.clicked.emit()

    def on_hidden(self) -> None:
        self.persistent = False
        self._clear_actions()


class BriefingCard(FloatingCard):
    """Guten-Morgen-Briefing als freundliche Karte neben der Figur."""

    clicked = pyqtSignal()
    CARD_W = 320

    def __init__(self, parent=None):
        super().__init__(focusable=False)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        font = QFont(FONT_FAMILY)
        font.setPointSizeF(10)
        self.label.setFont(font)
        self.label.setStyleSheet("color: #F5F6F8; background: transparent;")
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(lambda: self.fade_out())

    def show_briefing(self, title: str, lines: list[str], anchor: QPoint, duration_ms: int = 12000) -> None:
        content_html = f"<div style='font-weight:600; font-size:12pt; color:#FF8FB1; margin-bottom:6px;'>{title}</div>"
        for line in lines:
            content_html += f"<div style='margin-bottom:4px; font-size:10pt; color:#F5F6F8;'>{line}</div>"
        self.label.setText(content_html)

        th = max(50, 36 + len(lines) * 26)
        tw = self.CARD_W
        self.label.setGeometry(self.M + 16, self.M + 12, tw, th)
        self.set_content_size(tw + 32, th + 24)
        self.anchor_to(anchor)

        self._hide_timer.stop()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self.fade_in()
        self._hide_timer.start(duration_ms)

    def mousePressEvent(self, event) -> None:
        self._hide_timer.stop()
        self.fade_out(150)
        self.clicked.emit()


class ExplainCard(FloatingCard):
    """Ergebnis-Karte fuer 'Kopieren & Erklaeren' mit Kopieren-Button und Dark-Mode Styling."""

    CARD_W = 340

    def __init__(self, parent=None):
        super().__init__(focusable=True)
        self._full_text = ""

        self.title_label = QLabel(self)
        font_title = QFont(FONT_FAMILY)
        font_title.setPointSizeF(11)
        font_title.setBold(True)
        self.title_label.setFont(font_title)
        self.title_label.setStyleSheet("color: #FF8FB1; background: transparent;")

        self.text_label = QLabel(self)
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        font_text = QFont(FONT_FAMILY)
        font_text.setPointSizeF(10)
        self.text_label.setFont(font_text)
        self.text_label.setStyleSheet("color: #F5F6F8; background: transparent;")

        btn_style = (
            "QPushButton { background: rgba(255, 255, 255, 22); border: 1px solid rgba(255, 255, 255, 45);"
            " border-radius: 9px; color: #F5F6F8; padding: 4px 10px; font-weight: 600; font-family: 'Segoe UI'; font-size: 9.5pt; }"
            "QPushButton:hover { background: rgba(255, 143, 177, 50); border: 1px solid #FF8FB1; color: #FFFFFF; }"
            "QPushButton:pressed { background: rgba(255, 143, 177, 90); }"
        )
        self.copy_btn = QPushButton("📋 Kopieren", self)
        self.close_btn = QPushButton("✖ Schließen", self)
        self.copy_btn.setStyleSheet(btn_style)
        self.close_btn.setStyleSheet(btn_style)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.close_btn.clicked.connect(lambda: self.fade_out(150))

    def _copy_to_clipboard(self) -> None:
        if self._full_text:
            QGuiApplication.clipboard().setText(self._full_text)
            self.copy_btn.setText("Kopiert! ✨")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Kopieren"))

    def show_result(self, title: str, text: str, anchor: QPoint) -> None:
        self._full_text = text.strip()
        self.title_label.setText(title)
        self.text_label.setText(self._full_text)

        fm = QFontMetrics(self.text_label.font())
        rect = fm.boundingRect(QRect(0, 0, self.CARD_W - 32, 4000), int(Qt.TextFlag.TextWordWrap), self._full_text)
        th = max(rect.height() + 8, 40)
        cw = self.CARD_W
        title_h = 24
        btn_h = 28
        total_h = title_h + 6 + th + 12 + btn_h

        self.title_label.setGeometry(self.M + 16, self.M + 12, cw - 32, title_h)
        self.text_label.setGeometry(self.M + 16, self.M + 12 + title_h + 6, cw - 32, th)

        by = self.M + 12 + title_h + 6 + th + 10
        self.copy_btn.setGeometry(self.M + 16, by, 110, btn_h)
        self.close_btn.setGeometry(self.M + 16 + 118, by, 100, btn_h)

        self.set_content_size(cw, total_h)
        self.anchor_to(anchor)

        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self.fade_in()
        self.setFocus()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.fade_out(150)
            return
        super().keyPressEvent(event)


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
