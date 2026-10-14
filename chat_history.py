# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Fenster „Meine Chats“: Chronologischer Verlauf, Suche, Export und Weiterreden."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSplitter,
    QVBoxLayout, QWidget,
)

import tools
from memory_store import get_memory_store
from pet_sprites import get_character_info
from i18n import tr


STYLE = """
QDialog { background: #26282C; }
QLabel { color: #F2F3F5; font: 10pt "Segoe UI"; }
QLabel#title { font: 600 14pt "Segoe UI"; color: #FF8FB1; }
QLabel#empty { font: 12pt "Segoe UI"; color: #8D919B; }
QLineEdit { background: #33353B; color: #F2F3F5; border: 1px solid #55575F; border-radius: 8px;
            padding: 7px 10px; font: 10pt "Segoe UI"; }
QListWidget { background: #2B2D31; color: #F2F3F5; border: 1px solid #3E4148; border-radius: 8px;
              padding: 4px; font: 10pt "Segoe UI"; }
QListWidget::item { border-radius: 6px; padding: 8px; margin: 2px 0; }
QListWidget::item:hover { background: #36383E; }
QListWidget::item:selected { background: #3F424A; border-left: 3px solid #FF8FB1; color: #FFFFFF; }
QScrollArea { background: #26282C; border: 1px solid #3E4148; border-radius: 8px; }
QScrollBar:vertical { background: #26282C; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #474A52; min-height: 20px; border-radius: 5px; }
QPushButton { background: #3A3C43; color: #F2F3F5; border: none; border-radius: 8px;
              padding: 8px 14px; font: 10pt "Segoe UI"; }
QPushButton:hover { background: #474A52; }
QPushButton#primary { background: #FF8FB1; color: #26282C; font-weight: 600; }
QPushButton#primary:hover { background: #FFA5C0; }
QPushButton#danger { background: #4A3338; color: #FF8FB1; }
QPushButton#danger:hover { background: #5C3D44; }
"""


def _format_date(ts: float) -> str:
    dt = datetime.datetime.fromtimestamp(ts)
    now = datetime.datetime.now()
    if dt.date() == now.date():
        return f"Heute {dt.strftime('%H:%M')}"
    if dt.date() == (now - datetime.timedelta(days=1)).date():
        return f"Gestern {dt.strftime('%H:%M')}"
    if dt.year == now.year:
        return dt.strftime("%d. %b %H:%M")
    return dt.strftime("%d.%m.%Y")


class ChatHistoryDialog(QDialog):
    """Zeigt alle gespeicherten Unterhaltungen und erlaubt das Wiederaufnehmen."""

    resume_requested = pyqtSignal(list)   # Liste aus [("user"|"assistant", text)]

    def __init__(self, cfg, parent=None, store: Optional[object] = None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.store = store or get_memory_store()
        self.char_name = str(cfg.get("pet", {}).get("name") or "Kylie")
        self.char_id = str(cfg.get("pet", {}).get("character") or "cat_mochi")
        self.char_info = get_character_info(self.char_id)

        self.setWindowTitle(tr("chats.title_with_name", name=self.char_name))
        self.resize(840, 560)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header: Titel & Suchfeld
        header = QHBoxLayout()
        title_lbl = QLabel(tr("chats.title_with_name", name=self.char_name))
        title_lbl.setObjectName("title")
        header.addWidget(title_lbl)
        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("chats.search_placeholder"))

        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(220)
        self.search_edit.textChanged.connect(self._on_search_changed)
        header.addWidget(self.search_edit)
        root.addLayout(header)

        # Splitter: Links Liste, Rechts Nachrichten
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linke Seite: Gespraeche
        left_widget = QWidget()
        left_lay = QVBoxLayout(left_widget)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)

        self.conv_list = QListWidget()
        self.conv_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.conv_list.currentRowChanged.connect(self._on_conv_selected)
        left_lay.addWidget(self.conv_list)
        splitter.addWidget(left_widget)

        # Rechte Seite: Chatverlauf & Leerzustand
        right_widget = QWidget()
        right_lay = QVBoxLayout(right_widget)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(8)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background: transparent;")
        self.messages_lay = QVBoxLayout(self.messages_container)
        self.messages_lay.setContentsMargins(12, 12, 12, 12)
        self.messages_lay.setSpacing(10)
        self.messages_lay.addStretch(1)
        self.scroll_area.setWidget(self.messages_container)
        right_lay.addWidget(self.scroll_area)

        self.empty_label = QLabel(tr("chats.empty", emoji=self.char_info.get('emoji', '🐾'), name=self.char_name))
        self.empty_label.setObjectName("empty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_lay.addWidget(self.empty_label)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)
        splitter.setSizes([270, 530])
        self.splitter = splitter
        root.addWidget(splitter, 1)

        # Buttons unten
        btns = QHBoxLayout()
        self.del_btn = QPushButton(tr("chats.delete_conv"))
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._on_delete_conv)
        btns.addWidget(self.del_btn)

        btns.addStretch(1)

        self.export_btn = QPushButton(tr("chats.export"))
        self.export_btn.clicked.connect(self._on_export)
        btns.addWidget(self.export_btn)

        self.resume_btn = QPushButton(tr("chats.resume"))
        self.resume_btn.setObjectName("primary")
        self.resume_btn.clicked.connect(self._on_resume)
        btns.addWidget(self.resume_btn)

        close_btn = QPushButton(tr("common.close"))
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)


        root.addLayout(btns)

        self._current_convs: list[dict] = []
        self._refresh_conversations()

    def _refresh_conversations(self, search: str = "") -> None:
        self.conv_list.clear()
        self._current_convs = self.store.conversations(search)

        if not self._current_convs:
            self.empty_label.setVisible(True)
            self.scroll_area.setVisible(False)
            self.del_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            return

        self.empty_label.setVisible(False)
        self.scroll_area.setVisible(True)
        self.del_btn.setEnabled(True)
        self.resume_btn.setEnabled(True)

        for c in self._current_convs:
            dt_str = _format_date(c["started"])
            c_info = get_character_info(c.get("character", "cat_mochi"))
            emoji = c_info.get("emoji", "🐾")
            title = c["title"] or "Gespräch"
            item_text = f"{emoji} {title}\n  📅 {dt_str} ({c.get('msg_count', 0)} Nachrichten)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.conv_list.addItem(item)

        self.conv_list.setCurrentRow(0)

    def _on_search_changed(self, text: str) -> None:
        self._refresh_conversations(text)

    def _selected_conv_id(self) -> Optional[int]:
        row = self.conv_list.currentRow()
        if 0 <= row < len(self._current_convs):
            return self._current_convs[row]["id"]
        return None

    def _on_conv_selected(self, row: int) -> None:
        # Bestehende Bubbles leeren
        while self.messages_lay.count() > 1:
            child = self.messages_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if row < 0 or row >= len(self._current_convs):
            return

        conv_id = self._current_convs[row]["id"]
        msgs = self.store.messages(conv_id)

        for m in msgs:
            is_user = m["role"] == "user"
            bubble_box = QHBoxLayout()
            bubble_box.setContentsMargins(0, 2, 0, 2)

            lbl = QLabel(m["text"])
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            time_str = datetime.datetime.fromtimestamp(m["ts"]).strftime("%H:%M")
            lbl.setToolTip(time_str)

            if is_user:
                bubble_box.addStretch(1)
                lbl.setStyleSheet("""
                    background: #5E364A;
                    color: #FFFFFF;
                    border: 1px solid #78435E;
                    border-radius: 12px;
                    padding: 9px 13px;
                    font: 10pt "Segoe UI";
                    max-width: 370px;
                """)
                bubble_box.addWidget(lbl)
            else:
                c_info = get_character_info(self._current_convs[row].get("character", "cat_mochi"))
                emo = c_info.get("emoji", "🐾")
                emo_lbl = QLabel(emo)
                emo_lbl.setStyleSheet("font-size: 15pt; background: transparent; margin-right: 4px;")
                emo_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
                bubble_box.addWidget(emo_lbl)

                lbl.setStyleSheet("""
                    background: #36383E;
                    color: #F2F3F5;
                    border: 1px solid #45474F;
                    border-radius: 12px;
                    padding: 9px 13px;
                    font: 10pt "Segoe UI";
                    max-width: 370px;
                """)
                bubble_box.addWidget(lbl)
                bubble_box.addStretch(1)

            self.messages_lay.insertLayout(self.messages_lay.count() - 1, bubble_box)

        # Nach unten scrollen
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if hasattr(self, "splitter"):
            self.splitter.setSizes([270, 530])

    def _on_delete_conv(self) -> None:
        cid = self._selected_conv_id()
        if cid is None:
            return
        ans = QMessageBox.question(
            self,
            tr("chats.delete_conv"),
            tr("chats.confirm_delete_conv"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if ans == QMessageBox.StandardButton.Yes:
            self.store.delete_conversation(cid)
            self._refresh_conversations(self.search_edit.text())

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("chats.export_title"),
            str(tools.desktop_dir() / "DesktopCat_Chats.txt"),
            tr("common.file_filter_txt"),
        )
        if path:
            self.store.export_text(path)
            QMessageBox.information(self, tr("common.export_ok_title"), tr("common.export_ok_text", path=path))

    def _on_resume(self) -> None:
        cid = self._selected_conv_id()
        if cid is None:
            return
        msgs = self.store.messages(cid)
        history = [(m["role"], m["text"]) for m in msgs[-18:]]
        self.resume_requested.emit(history)
        self.accept()
