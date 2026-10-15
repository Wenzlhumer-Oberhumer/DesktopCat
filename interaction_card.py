"""An optional, keyboard-accessible question card that never steals focus."""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from speech_bubble import FloatingCard


class InteractionCard(FloatingCard):
    answered = pyqtSignal(str, object)
    dismissed = pyqtSignal()

    def __init__(self):
        super().__init__(focusable=True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._item = None
        self._acted = True
        self.content = QWidget(self)
        self.content.setStyleSheet(
            'QLabel{color:#f5f6f8;background:transparent;font:10pt "Segoe UI";}'
            'QPushButton{color:#fff;background:#434751;border:2px solid transparent;border-radius:9px;'
            'padding:6px 10px;font:10pt "Segoe UI";}'
            'QPushButton:hover{background:#5b4655;}'
            'QPushButton:focus,QLineEdit:focus{border:2px solid #ffadd0;}'
            'QPushButton:pressed{background:#79556b;}'
            'QPushButton#primary{background:#ffadd0;color:#25262d;font-weight:600;}'
            'QLineEdit{background:#22252b;color:#fff;border:2px solid #777d8b;border-radius:8px;'
            'padding:8px;font:10pt "Segoe UI";}')
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.title = QLabel()
        self.title.setStyleSheet('color:#ffadd0;font-weight:600;')
        self.title.setWordWrap(True)
        self.question = QLabel()
        self.question.setTextFormat(Qt.TextFormat.PlainText)
        self.question.setWordWrap(True)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.question)
        self.choices = QGridLayout()
        self.choices.setSpacing(8)
        self.layout.addLayout(self.choices)
        self.choice_buttons = []
        self.tell_button = self._button('')
        self.tell_button.setObjectName('primary')
        self.tell_button.clicked.connect(self._begin_text)
        self.layout.addWidget(self.tell_button)
        self.answer_edit = QLineEdit()
        self.answer_edit.setMaxLength(280)
        self.answer_edit.setMinimumHeight(44)
        self.answer_edit.returnPressed.connect(self._send_text)
        self.layout.addWidget(self.answer_edit)
        self.error = QLabel()
        self.error.setStyleSheet('color:#ffb9bb;')
        self.layout.addWidget(self.error)
        self.footer = QHBoxLayout()
        self.send_button = self._button('')
        self.send_button.setObjectName('primary')
        self.send_button.clicked.connect(self._send_text)
        self.skip_button = self._button('')
        self.skip_button.clicked.connect(self._dismiss)
        self.footer.addWidget(self.send_button)
        self.footer.addWidget(self.skip_button)
        self.layout.addLayout(self.footer)
        self.expiry = QTimer(self)
        self.expiry.setSingleShot(True)
        self.expiry.timeout.connect(self._dismiss)

    @staticmethod
    def _button(text):
        button = QPushButton(text)
        button.setMinimumHeight(44)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def present(self, item, name, anchor, language='de'):
        self._item, self._acted = item, False
        self._english = language == 'en'
        self.title.setText(f'{name} · ' + ('A little moment together' if self._english else 'Ein kleiner Moment mit dir'))
        self.question.setText(item.question)
        self.setAccessibleName(self.title.text())
        self.setAccessibleDescription(item.question)
        self.answer_edit.clear()
        self.answer_edit.setPlaceholderText('Your answer (up to 280 characters)' if self._english else 'Deine Antwort (bis 280 Zeichen)')
        self.answer_edit.setAccessibleName('Your answer' if self._english else 'Deine Antwort')
        self.error.clear()
        self.error.hide()
        self.answer_edit.hide()
        self.send_button.hide()
        self.tell_button.setText('Tell me' if self._english else 'Erzählen')
        self.send_button.setText('Send answer' if self._english else 'Antwort senden')
        self.skip_button.setText('Skip' if self._english else 'Überspringen')
        self.tell_button.setVisible(not item.choices)
        while self.choices.count():
            old = self.choices.takeAt(0).widget()
            old.hide()
            old.deleteLater()
        self.choice_buttons = []
        # Stack choices on a narrow display rather than cropping labels.
        self.anchor_to(anchor)
        self._content_width = min(352, self._screen_geo().width() - 2*self.M - 28)
        for index, choice in enumerate(item.choices):
            button = self._button(choice.label)
            button.clicked.connect(lambda checked=False, i=index: self._answer(i))
            row, col = (0, index) if self._content_width >= 320 else (index, 0)
            self.choices.addWidget(button, row, col)
            self.choice_buttons.append(button)
        self._resize_content()
        self.show()
        self.fade_in()
        self.expiry.start(90000)

    def _resize_content(self):
        self.content.setFixedWidth(self._content_width)
        self.layout.activate()
        height = max(self.layout.totalHeightForWidth(self._content_width), self.layout.sizeHint().height())
        self.content.setFixedHeight(height)
        self.content.move(self.M+12, self.M+12)
        self.set_content_size(self._content_width+24, height+24)

    def _begin_text(self):
        if self._acted:
            return
        self.expiry.stop()
        self.tell_button.hide()
        self.answer_edit.show()
        self.send_button.show()
        self._resize_content()
        self.activateWindow()
        self.answer_edit.setFocus(Qt.FocusReason.MouseFocusReason)

    def _send_text(self):
        if self._acted or not self.answer_edit.isVisible():
            return
        text = self.answer_edit.text().strip()
        if not text:
            self.error.setText('Please enter an answer or skip.' if self._english else 'Bitte eine Antwort eingeben oder überspringen.')
            self.error.show()
            self._resize_content()
            return
        self._answer(text)

    def _answer(self, answer):
        if self._acted:
            return
        self._acted = True
        self.hide_now()
        self.answered.emit(self._item.id, answer)

    def _dismiss(self):
        if self._acted:
            return
        self._acted = True
        self.hide_now()
        self.dismissed.emit()

    def hide_now(self):
        self.expiry.stop()
        self.answer_edit.clear()
        super().hide_now()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._dismiss()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._dismiss()
        super().closeEvent(event)
