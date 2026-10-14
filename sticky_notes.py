# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Haftnotizen am Desktop (Phase 6.5).

Erzeugt kleine, hübsche, rahmenlose Haftnotizen mit Segoe Print Schriftart,
Farbauswahl (Gelb, Rosa, Mint), Speicherung in der Datenbank und Interaktion.
"""
from __future__ import annotations

from typing import Optional
from PyQt6.QtCore import QPoint, QRectF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from i18n import tr


NOTE_COLORS = {
    "yellow": {
        "bg": "#FFF9C4",
        "header": "#FFF59D",
        "border": "#FBC02D",
        "text": "#3E2723",
        "accent": "#F57F17",
    },
    "pink": {
        "bg": "#F8BBD0",
        "header": "#F48FB1",
        "border": "#EC407A",
        "text": "#4A148C",
        "accent": "#C2185B",
    },
    "mint": {
        "bg": "#C8E6C9",
        "header": "#A5D6A7",
        "border": "#66BB6A",
        "text": "#1B5E20",
        "accent": "#2E7D32",
    },
}

COLOR_ORDER = ["yellow", "pink", "mint"]


def _get_note_font(size: int = 11) -> QFont:
    families = QFontDatabase.families()
    if "Segoe Print" in families:
        return QFont("Segoe Print", size)
    elif "Comic Sans MS" in families:
        return QFont("Comic Sans MS", size)
    return QFont("Segoe UI", size)


class StickyNoteWindow(QWidget):
    """Einzelnes Haftnotiz-Fenster auf dem Desktop."""

    note_done = pyqtSignal(int)
    note_deleted = pyqtSignal(int)

    def __init__(self, note_id: int, text: str, color: str, x: int, y: int, store):
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.note_id = note_id
        self.color_name = color if color in NOTE_COLORS else "yellow"
        self.store = store
        self._drag_pos: Optional[QPoint] = None

        self.resize(210, 210)
        self.move(x, y)

        self._setup_ui(text)
        self._update_colors()

    def _setup_ui(self, initial_text: str) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 10)
        self.main_layout.setSpacing(4)

        # Header bar
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(4)

        # Farbwechsler
        self.btn_color = QPushButton("🎨")
        self.btn_color.setFixedSize(22, 22)
        self.btn_color.setToolTip(tr("note.color_tooltip"))
        self.btn_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color.clicked.connect(self._cycle_color)
        self.header_layout.addWidget(self.btn_color)

        # Titel / Drag Handle
        self.lbl_title = QLabel(tr("note.window_title"))
        self.lbl_title.setFont(_get_note_font(9))
        self.header_layout.addWidget(self.lbl_title, 1)

        # Erledigt (Checkmark)
        self.btn_done = QPushButton("✔")
        self.btn_done.setFixedSize(22, 22)
        self.btn_done.setToolTip(tr("note.done_tooltip"))
        self.btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_done.clicked.connect(self._on_done)
        self.header_layout.addWidget(self.btn_done)

        # Löschen (Kreuz)
        self.btn_del = QPushButton("✖")
        self.btn_del.setFixedSize(22, 22)
        self.btn_del.setToolTip(tr("note.delete_tooltip"))
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.clicked.connect(self._on_delete)
        self.header_layout.addWidget(self.btn_del)

        self.main_layout.addLayout(self.header_layout)

        # Textfeld
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(tr("note.placeholder"))
        self.editor.setPlainText(initial_text)

        self.editor.setFont(_get_note_font(11))
        self.editor.textChanged.connect(self._on_text_changed)
        self.main_layout.addWidget(self.editor)

        # Debounce Timer fuer DB Speicherung
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_text_to_db)

    def _update_colors(self) -> None:
        c = NOTE_COLORS.get(self.color_name, NOTE_COLORS["yellow"])
        self.lbl_title.setStyleSheet(f"color: {c['text']}; font-weight: bold;")

        btn_style = (
            f"QPushButton {{ background: transparent; border: none; font-size: 11px; border-radius: 4px; color: {c['text']}; }}"
            f"QPushButton:hover {{ background: rgba(0,0,0,0.08); }}"
        )
        self.btn_color.setStyleSheet(btn_style)
        self.btn_done.setStyleSheet(btn_style)
        self.btn_del.setStyleSheet(btn_style)

        self.editor.setStyleSheet(
            f"QPlainTextEdit {{ background: transparent; border: none; color: {c['text']}; selection-background-color: {c['border']}; }}"
        )
        self.update()

    def _cycle_color(self) -> None:
        idx = (COLOR_ORDER.index(self.color_name) + 1) % len(COLOR_ORDER)
        self.color_name = COLOR_ORDER[idx]
        self._update_colors()
        if self.store:
            try:
                self.store.update_note(self.note_id, text=None)
                # Farbfeld in Tabelle notes aktualisieren falls noetig
                with self.store._db() as db:
                    db.execute("UPDATE notes SET color = ? WHERE id = ?", (self.color_name, self.note_id))
            except Exception:
                pass

    def _on_text_changed(self) -> None:
        self._save_timer.start()

    def _save_text_to_db(self) -> None:
        if self.store:
            try:
                self.store.update_note(self.note_id, text=self.editor.toPlainText())
            except Exception:
                pass

    def _on_done(self) -> None:
        if self.store:
            try:
                self.store.update_note(self.note_id, done=1)
            except Exception:
                pass
        self.note_done.emit(self.note_id)
        self.close()

    def _on_delete(self) -> None:
        if self.store:
            try:
                self.store.delete_note(self.note_id)
            except Exception:
                pass
        self.note_deleted.emit(self.note_id)
        self.close()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = NOTE_COLORS.get(self.color_name, NOTE_COLORS["yellow"])
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)

        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)

        # Zarter Schatten
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 25))
        p.drawRoundedRect(QRectF(4, 4, self.width() - 4, self.height() - 4), 10, 10)

        # Hintergrund
        p.setBrush(QColor(c["bg"]))
        p.setPen(QPen(QColor(c["border"]), 1.5))
        p.drawPath(path)

        # Header Trennlinie
        p.setPen(QPen(QColor(c["border"]), 1.0, Qt.PenStyle.DashLine))
        p.drawLine(10, 32, self.width() - 10, 32)
        p.end()

    # -- Verschieben per Drag ----------------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() <= 32:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos is not None:
            new_pos = e.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if self._drag_pos is not None:
            self._drag_pos = None
            if self.store:
                try:
                    self.store.update_note(self.note_id, x=self.x(), y=self.y())
                except Exception:
                    pass
            e.accept()
        else:
            super().mouseReleaseEvent(e)


class StickyNoteManager:
    """Verwaltet alle offenen Haftnotiz-Fenster."""

    def __init__(self, store, on_note_done_cb=None):
        self.store = store
        self.on_note_done_cb = on_note_done_cb
        self.windows: dict[int, StickyNoteWindow] = {}

    def load_notes(self) -> None:
        """Laedt alle noch nicht erledigten Notizen und zeigt sie an."""
        if not self.store:
            return
        try:
            notes = self.store.get_notes(include_done=False)
            for n in notes:
                self._open_window(n["id"], n["text"], n["color"], n["x"], n["y"])
        except Exception as exc:
            print(f"[sticky_notes] Fehler beim Laden: {exc}")

    def create_note(self, text: str = "", color: str = "yellow", x: Optional[int] = None, y: Optional[int] = None) -> tuple[int, int, int]:
        """Erstellt eine neue Notiz und platziert sie rechts am Bildschirm."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None

        if x is None or y is None:
            count = len(self.windows)
            right = avail.right() if avail else 1200
            top = avail.top() if avail else 50
            x = right - 230
            y = top + 60 + (count % 4) * 220

        color = color if color in NOTE_COLORS else "yellow"
        note_id = self.store.add_note(text=text, color=color, x=x, y=y)
        self._open_window(note_id, text, color, x, y)
        return note_id, x, y

    def _open_window(self, note_id: int, text: str, color: str, x: int, y: int) -> None:
        if note_id in self.windows:
            self.windows[note_id].show()
            self.windows[note_id].raise_()
            return

        w = StickyNoteWindow(note_id, text, color, x, y, self.store)
        w.note_done.connect(self._on_note_done)
        w.note_deleted.connect(self._on_note_deleted)
        w.show()
        self.windows[note_id] = w

    def _on_note_done(self, note_id: int) -> None:
        self.windows.pop(note_id, None)
        if callable(self.on_note_done_cb):
            self.on_note_done_cb(note_id)

    def _on_note_deleted(self, note_id: int) -> None:
        self.windows.pop(note_id, None)

    def close_all(self) -> None:
        for w in list(self.windows.values()):
            w.close()
        self.windows.clear()
