"""Explicit update consent and a persisted, user-selected reminder time."""
from __future__ import annotations

import datetime
import time
from PyQt6.QtCore import QDateTime, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)
from speech_bubble import FloatingCard


class UpdatePrompt(FloatingCard):
    install_requested = pyqtSignal(str)
    later_requested = pyqtSignal()

    def __init__(self):
        super().__init__(focusable=True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.version = ''
        self._acted = False
        content = QWidget(self)
        content.setGeometry(self.M + 14, self.M + 12, 332, 166)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel('Ein neues Update ist da!')
        self.title.setStyleSheet('font-size:16px;font-weight:600;color:#fff;')
        layout.addWidget(self.title)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setStyleSheet('color:#eef0f4;font-size:13px;')
        layout.addWidget(self.message)
        row = QHBoxLayout()
        self.install_button = QPushButton('Ja, installieren')
        self.later_button = QPushButton('Später…')
        for button in (self.install_button, self.later_button):
            button.setMinimumHeight(42)
            button.setStyleSheet('QPushButton{background:#444852;color:#fff;border:2px solid transparent;'
                                'border-radius:8px;padding:6px;} QPushButton:focus{border-color:#fff;}'
                                'QPushButton:hover{background:#606572;}')
            row.addWidget(button)
        self.install_button.setStyleSheet(self.install_button.styleSheet() +
                                         'QPushButton{background:#ff9fbd;color:#24262b;font-weight:600;}')
        self.install_button.clicked.connect(self._install)
        self.later_button.clicked.connect(self._later)
        layout.addLayout(row)
        self.set_content_size(360, 190)

    def offer(self, version: str):
        self.version = version
        self._acted = False
        self.install_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.message.setText(f'Hey, Version {version} ist bereit. Soll ich das Update jetzt herunterladen und installieren?')
        self.show()
        self.fade_in()

    def _install(self):
        if self._acted:
            return
        self._acted = True
        self.install_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.install_requested.emit(self.version)

    def _later(self):
        if not self._acted:
            self._acted = True
            self.later_requested.emit()


class SnoozeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from settings_dialog import STYLE
        self.setStyleSheet(STYLE)
        self.setWindowTitle('Wann soll ich dich erinnern?')
        self.setMinimumWidth(370)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Update später installieren – erinnere mich:'))
        self.options = QComboBox()
        self.options.addItems(['In 15 Minuten', 'In einer Stunde', 'In vier Stunden',
                               'Morgen um 09:00', 'Datum und Uhrzeit wählen…'])
        self.options.setMinimumHeight(40)
        layout.addWidget(self.options)
        self.custom_time = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.custom_time.setCalendarPopup(True)
        self.custom_time.setDisplayFormat('dd.MM.yyyy HH:mm')
        self.custom_time.setMinimumHeight(40)
        self.custom_time.hide()
        layout.addWidget(self.custom_time)
        self.options.currentIndexChanged.connect(lambda i: self.custom_time.setVisible(i == 4))
        self.error = QLabel()
        self.error.setStyleSheet('color:#ffb0b0;')
        layout.addWidget(self.error)
        row = QHBoxLayout()
        cancel = QPushButton('Zurück')
        cancel.clicked.connect(self.reject)
        confirm = QPushButton('Erinnerung setzen')
        confirm.setObjectName('primary')
        confirm.clicked.connect(self._confirm)
        for button in (cancel, confirm):
            button.setMinimumHeight(42)
            row.addWidget(button)
        layout.addLayout(row)

    def selected_time(self) -> float:
        index = self.options.currentIndex()
        if index < 3:
            return time.time() + (900, 3600, 14400)[index]
        if index == 3:
            tomorrow = datetime.datetime.fromtimestamp(time.time()).date() + datetime.timedelta(days=1)
            return datetime.datetime.combine(tomorrow, datetime.time(9)).timestamp()
        return float(self.custom_time.dateTime().toSecsSinceEpoch())

    def _confirm(self):
        if self.selected_time() < time.time() + 60:
            self.error.setText('Bitte einen Zeitpunkt in der Zukunft wählen.')
            return
        self.accept()
