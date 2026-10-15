"""Manual handoff to the user's Gemini browser session; no credentials or API calls."""
import webbrowser

from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QTextEdit, QVBoxLayout


def open_gemini_browser(prompt: str = '') -> bool:
    if prompt.strip():
        QApplication.clipboard().setText(prompt)
    return webbrowser.open('https://gemini.google.com/app')


def show_browser_dialog(parent=None, prompt: str = '') -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle('Gemini im Browser')
    dialog.resize(480, 340)
    layout = QVBoxLayout(dialog)
    hint = QLabel('Nutze dein eigenes Google-Konto und Gemini-Abo direkt im Browser.\n'
                  'Die Anfrage wird kopiert. Füge sie dort mit Strg+V ein und sende sie ab.\n'
                  'Antworten und Desktop-Aktionen werden nicht automatisch übernommen.')
    hint.setWordWrap(True)
    layout.addWidget(hint)
    editor = QTextEdit()
    editor.setPlaceholderText('Deine Anfrage an Gemini (optional) …')
    editor.setPlainText(prompt)
    layout.addWidget(editor)
    status = QLabel('')
    layout.addWidget(status)
    button = QPushButton('Anfrage kopieren & Gemini öffnen')

    def open_browser():
        if open_gemini_browser(editor.toPlainText()):
            status.setText('Gemini geöffnet. Deine Anfrage kannst du dort mit Strg+V einfügen.'
                           if editor.toPlainText().strip() else 'Gemini geöffnet.')
        else:
            status.setText('Browser konnte nicht geöffnet werden. Öffne https://gemini.google.com/app manuell.')

    button.clicked.connect(open_browser)
    layout.addWidget(button)
    dialog.exec()
