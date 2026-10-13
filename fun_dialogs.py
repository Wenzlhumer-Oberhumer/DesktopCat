"""Dialoge für Freundschaft, Fokus-Statistik und Lernkarten (Phase 6)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from fun import (
    LEVEL_NAMES, LEVEL_REWARDS, LEVEL_THRESHOLDS, get_focus_stats,
    level_for, parse_flashcards_text, parse_gemini_flashcards_json,
)
import gemini


# ======================================================================================
#  1. Freundschafts-Dialog
# ======================================================================================
class FriendshipDialog(QDialog):
    """Zeigt Freundschafts-Level, Fortschritt und freigeschaltete Accessoires."""

    accessory_changed = pyqtSignal(str)

    def __init__(self, store, cfg, char_info: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.store = store
        self.cfg = cfg
        self.char_info = char_info

        self.setWindowTitle(f"💖 Freundschaft mit {char_info.get('name', 'Kylie')}")
        self.setFixedSize(480, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFDF9;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #2D3139;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #4B5563;
            }
        """)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header mit Avatar & Name
        head_layout = QHBoxLayout()
        emoji = self.char_info.get("emoji", "🐱")
        name = self.char_info.get("name", "Kylie")

        lbl_avatar = QLabel(emoji)
        lbl_avatar.setStyleSheet("font-size: 40px;")
        head_layout.addWidget(lbl_avatar)

        pts = self.store.get_friendship_points() if self.store else 0
        lvl, prog = level_for(pts)
        lvl_name = LEVEL_NAMES.get(lvl, "Freunde")

        info_layout = QVBoxLayout()
        lbl_title = QLabel(f"<b>{name}</b> & Du")
        lbl_title.setStyleSheet("font-size: 18px; color: #1F2937;")
        lbl_level = QLabel(f"💖 Level {lvl}: <span style='color: #EC4899;'>{lvl_name}</span>")
        lbl_level.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(lbl_title)
        info_layout.addWidget(lbl_level)
        head_layout.addLayout(info_layout, 1)

        layout.addLayout(head_layout)

        # Fortschrittsbalken
        prog_box = QGroupBox("Fortschritt zum nächsten Level")
        prog_layout = QVBoxLayout(prog_box)
        prog_layout.setSpacing(6)

        next_thresh = LEVEL_THRESHOLDS[lvl] if lvl < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1]

        self.bar = QProgressBar()
        self.bar.setFixedHeight(20)
        self.bar.setRange(0, 100)
        self.bar.setValue(int(prog * 100))
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F472B6, stop:1 #FB7185);
                border-radius: 9px;
            }
        """)
        prog_layout.addWidget(self.bar)

        if lvl < 8:
            lbl_pts = QLabel(f"{pts} / {next_thresh} Punkte ({int(prog * 100)}%) • Noch {next_thresh - pts} Punkte bis Level {lvl + 1}")
        else:
            lbl_pts = QLabel(f"{pts} Punkte • Maximales Freundschafts-Level erreicht! 🌟")
        lbl_pts.setStyleSheet("font-size: 11px; color: #6B7280;")
        prog_layout.addWidget(lbl_pts)
        layout.addWidget(prog_box)

        # Accessoires & Belohnungen
        rew_box = QGroupBox("Freigeschaltete Belohnungen & Accessoires")
        rew_layout = QVBoxLayout(rew_box)
        rew_layout.setSpacing(8)

        current_worn = str(self.cfg.get("fun.worn", "")).strip()

        for req_lvl in range(2, 9):
            title, key = LEVEL_REWARDS[req_lvl]
            row = QHBoxLayout()

            is_unlocked = lvl >= req_lvl
            lock_text = "✨" if is_unlocked else "🔒"
            lbl_item = QLabel(f"{lock_text} Level {req_lvl}: <b>{title}</b>")

            if not is_unlocked:
                lbl_item.setStyleSheet("color: #9CA3AF;")
            else:
                lbl_item.setStyleSheet("color: #1F2937;")
            row.addWidget(lbl_item, 1)

            if is_unlocked and key:
                btn = QPushButton()
                btn.setFixedWidth(90)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if current_worn == key:
                    btn.setText("✔ Ablegen")
                    btn.setStyleSheet("background-color: #FCE7F3; color: #DB2777; font-weight: bold; border-radius: 6px; padding: 4px;")
                    btn.clicked.connect(lambda _=False, k="": self._set_worn(k))
                else:
                    btn.setText("Anziehen")
                    btn.setStyleSheet("background-color: #F3F4F6; color: #374151; border-radius: 6px; padding: 4px;")
                    btn.clicked.connect(lambda _=False, k=key: self._set_worn(k))
                row.addWidget(btn)
            elif not is_unlocked:
                lbl_lock = QLabel(f"ab {LEVEL_THRESHOLDS[req_lvl-1]} Pkt.")
                lbl_lock.setStyleSheet("font-size: 11px; color: #9CA3AF;")
                row.addWidget(lbl_lock)

            rew_layout.addLayout(row)

        layout.addWidget(rew_box, 1)

        # Fusszeile
        btn_close = QPushButton("Schließen")
        btn_close.setFixedHeight(34)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #E5E7EB;
                color: #1F2937;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #D1D5DB;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _set_worn(self, key: str) -> None:
        self.cfg.set("fun.worn", key)
        self.cfg.save()
        self.accessory_changed.emit(key)
        self.accept()


# ======================================================================================
#  2. Fokus-Statistik-Dialog mit QPainter 7-Tage-Balkendiagramm
# ======================================================================================
class FocusBarChart(QWidget):
    """Zeichnet 7 Tage Fokus-Minuten als vertikale Balken."""

    def __init__(self, weekly_data: list[tuple[str, str, int, int]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.weekly = weekly_data
        self.setFixedHeight(140)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        chart_h = h - 35
        base_y = chart_h + 8

        # Max Minuten fuer Skalierung
        max_mins = max([m for _, _, m, _ in self.weekly] + [60])

        n = len(self.weekly)
        bar_w = min(36.0, (w - 40) / max(1, n) * 0.65)
        slot_w = (w - 30) / max(1, n)

        # Grundlinie
        p.setPen(QPen(QColor("#E5E7EB"), 1.0))
        p.drawLine(15, int(base_y), w - 15, int(base_y))

        for i, (date_str, label, mins, count) in enumerate(self.weekly):
            cx = 15 + i * slot_w + slot_w / 2.0
            bx = cx - bar_w / 2.0

            bh = (mins / float(max_mins)) * (chart_h - 20)
            by = base_y - bh

            # Balken
            if mins > 0:
                grad = QLinearGradient(bx, by, bx, base_y)
                grad.setColorAt(0.0, QColor("#818CF8"))
                grad.setColorAt(1.0, QColor("#6366F1"))
                p.setBrush(QBrush(grad))
                p.setPen(Qt.PenStyle.NoPen)
                path = QPainterPath()
                path.addRoundedRect(QRectF(bx, by, bar_w, bh), 5, 5)
                p.drawPath(path)

                # Minuten-Beschriftung über dem Balken
                p.setFont(QFont("Segoe UI", 8))
                p.setPen(QColor("#4F46E5"))
                p.drawText(QRectF(bx - 10, by - 16, bar_w + 20, 14), Qt.AlignmentFlag.AlignCenter, f"{mins}m")
            else:
                # Kleiner Platzhalter-Punkt
                p.setBrush(QColor("#E5E7EB"))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx, base_y - 3), 3, 3)

            # Wochentag unter der Grundlinie
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(QColor("#6B7280"))
            p.drawText(QRectF(cx - 15, base_y + 4, 30, 20), Qt.AlignmentFlag.AlignCenter, label)

        p.end()


class FocusStatsDialog(QDialog):
    """Zeigt Pomodoro- und Fokus-Statistiken, Serie und Balkendiagramm."""

    def __init__(self, store, char_info: dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.store = store
        self.char_info = char_info

        self.setWindowTitle("📊 Fokus-Statistik & Pomodoro")
        self.setFixedSize(460, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #1E293B;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                color: #475569;
            }
        """)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        stats = get_focus_stats(self.store)

        # Header Kacheln (Heute & Serie)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        # Kachel 1: Heute
        card_today = QFrame()
        card_today.setStyleSheet("background: #EEF2FF; border-radius: 10px; padding: 10px;")
        l_today = QVBoxLayout(card_today)
        l_today.addWidget(QLabel("⏱️ <b>Heute fokussiert</b>"))
        mins = stats["today_minutes"]
        cnt = stats["today_count"]
        lbl_m = QLabel(f"<span style='font-size: 22px; font-weight: bold; color: #4F46E5;'>{mins} Min.</span>")
        lbl_c = QLabel(f"{cnt} Pomodoro{'s' if cnt != 1 else ''}")
        lbl_c.setStyleSheet("color: #64748B; font-size: 11px;")
        l_today.addWidget(lbl_m)
        l_today.addWidget(lbl_c)
        cards_layout.addWidget(card_today, 1)

        # Kachel 2: Serie
        card_streak = QFrame()
        card_streak.setStyleSheet("background: #FEF3C7; border-radius: 10px; padding: 10px;")
        l_streak = QVBoxLayout(card_streak)
        l_streak.addWidget(QLabel("🔥 <b>Fokus-Serie</b>"))
        stk = stats["streak"]
        lbl_s = QLabel(f"<span style='font-size: 22px; font-weight: bold; color: #D97706;'>{stk} {('Tag' if stk == 1 else 'Tage')}</span>")
        lbl_sub = QLabel("In Folge am Ball! 💪" if stk > 0 else "Starte heute deine Serie!")
        lbl_sub.setStyleSheet("color: #78350F; font-size: 11px;")
        l_streak.addWidget(lbl_s)
        l_streak.addWidget(lbl_sub)
        cards_layout.addWidget(card_streak, 1)

        layout.addLayout(cards_layout)

        # 7-Tage-Balkendiagramm
        chart_box = QGroupBox("Vergangene 7 Tage")
        chart_layout = QVBoxLayout(chart_box)
        chart_widget = FocusBarChart(stats["weekly"], self)
        chart_layout.addWidget(chart_widget)
        layout.addWidget(chart_box)

        # Lob in Figur-Stimme
        praise_box = QFrame()
        praise_box.setStyleSheet("background: #F1F5F9; border-radius: 8px; padding: 10px;")
        praise_l = QHBoxLayout(praise_box)
        name = self.char_info.get("name", "Kylie")
        emoji = self.char_info.get("emoji", "🐾")

        if mins >= 50:
            quote = f"„Wahnsinn, du bist heute eine echte Fokus-Maschine, Boss! Weiter so!“ {emoji}"
        elif mins > 0:
            quote = f"„Gute Arbeit! Jeder Pomodoro bringt dich deinem Ziel näher.“ {emoji}"
        else:
            quote = f"„Bereit für etwas Produktivität? Sag mir einfach: 'Pomodoro starten'! ⏱️“ {emoji}"

        lbl_quote = QLabel(f"<b>{name}:</b> {quote}")
        lbl_quote.setWordWrap(True)
        lbl_quote.setStyleSheet("color: #334155; font-size: 12px;")
        praise_l.addWidget(lbl_quote)
        layout.addWidget(praise_box)

        # Schliessen Button
        btn_close = QPushButton("Fertig")
        btn_close.setFixedHeight(34)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0;
                color: #1E293B;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #CBD5E1;
            }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


# ======================================================================================
#  3. Lernkarten-Dialog (Flashcards Verwaltung & KI Generator)
# ======================================================================================
class GeminiCardWorker(QThread):
    """Fragt Gemini im Hintergrund nach Lernkarten als JSON-Liste."""

    success = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, topic: str):
        super().__init__()
        self.topic = topic

    @pyqtSlot()
    def run(self) -> None:
        try:
            prompt = (
                f"Erstelle 10 Lernkarten zum Thema '{self.topic}'. "
                "Gib ausschließlich ein valides JSON-Array zurück im Format: "
                '[{"front": "Frage oder Begriff", "back": "Antwort oder Erklärung"}]. '
                "Kein Begleittext, keine Markdown-Formatierung um das JSON."
            )
            raw = gemini.ask(prompt, timeout_s=40)
            cards = parse_gemini_flashcards_json(raw)
            if not cards:
                self.failed.emit("Konnte keine gültigen Karten aus der KI-Antwort parsen.")
            else:
                self.success.emit(cards)
        except Exception as exc:
            self.failed.emit(str(exc))


class FlashcardsDialog(QDialog):
    """Verwaltet Lernkarten-Decks, Import, KI-Karten und Quiz-Start."""

    quiz_requested = pyqtSignal(str)

    def __init__(self, store, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.store = store
        self._gemini_worker: Optional[GeminiCardWorker] = None

        self.setWindowTitle("📚 Lernkarten & Vokabel-Trainer")
        self.resize(600, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #2D3748;
            }
            QTableWidget {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                gridline-color: #EDF2F7;
            }
            QHeaderView::section {
                background-color: #F7FAFC;
                padding: 4px;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #E2E8F0;
            }
        """)

        self._setup_ui()
        self._reload_decks()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Deck-Auswahlzeile
        deck_layout = QHBoxLayout()
        deck_layout.addWidget(QLabel("<b>Aktuelles Deck:</b>"))

        self.cb_decks = QComboBox()
        self.cb_decks.setMinimumWidth(180)
        self.cb_decks.currentTextChanged.connect(self._on_deck_changed)
        deck_layout.addWidget(self.cb_decks, 1)

        btn_new_deck = QPushButton("➕ Neues Deck")
        btn_new_deck.clicked.connect(self._create_deck)
        deck_layout.addWidget(btn_new_deck)

        layout.addLayout(deck_layout)

        # Tabelle fuer Karten
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Vorderseite (Frage)", "Rückseite (Antwort)", "Box"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        # Schnell-Hinzufügen Zeile
        add_layout = QHBoxLayout()
        self.edit_front = QLineEdit()
        self.edit_front.setPlaceholderText("Vorderseite / Wort")
        self.edit_back = QLineEdit()
        self.edit_back.setPlaceholderText("Rückseite / Übersetzung")
        btn_add = QPushButton("Hinzufügen")
        btn_add.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; border-radius: 4px; padding: 5px 12px;")
        btn_add.clicked.connect(self._add_card)

        add_layout.addWidget(self.edit_front, 1)
        add_layout.addWidget(self.edit_back, 1)
        add_layout.addWidget(btn_add)
        layout.addLayout(add_layout)

        # Aktionen (Import, KI-Karten, Löschen, Quiz starten)
        act_layout = QHBoxLayout()

        btn_import = QPushButton("📥 Text-Import")
        btn_import.setToolTip("Format: Zeilenweise 'Wort = Übersetzung'")
        btn_import.clicked.connect(self._open_import_dialog)
        act_layout.addWidget(btn_import)

        btn_ai = QPushButton("✨ KI-Karten (Gemini)")
        btn_ai.clicked.connect(self._generate_ai_cards)
        act_layout.addWidget(btn_ai)

        btn_del = QPushButton("🗑️ Karte löschen")
        btn_del.clicked.connect(self._delete_selected_card)
        act_layout.addWidget(btn_del)

        act_layout.addStretch()

        self.btn_quiz = QPushButton("▶ Quiz starten")
        self.btn_quiz.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_quiz.clicked.connect(self._start_quiz)
        act_layout.addWidget(self.btn_quiz)

        layout.addLayout(act_layout)

    def _reload_decks(self) -> None:
        if not self.store:
            return
        decks = self.store.get_decks()
        if not decks:
            decks = ["Allgemein"]

        self.cb_decks.blockSignals(True)
        self.cb_decks.clear()
        for d in decks:
            self.cb_decks.addItem(d)
        self.cb_decks.blockSignals(False)

        self._load_cards_for_current_deck()

    def _on_deck_changed(self, _deck: str) -> None:
        self._load_cards_for_current_deck()

    def _load_cards_for_current_deck(self) -> None:
        deck = self.cb_decks.currentText() or "Allgemein"
        cards = self.store.get_cards(deck) if self.store else []

        self.table.setRowCount(len(cards))
        for row, c in enumerate(cards):
            item_f = QTableWidgetItem(c["front"])
            item_f.setData(Qt.ItemDataRole.UserRole, c["id"])
            item_b = QTableWidgetItem(c["back"])
            item_box = QTableWidgetItem(f"Box {c['box']}")
            item_box.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_f)
            self.table.setItem(row, 1, item_b)
            self.table.setItem(row, 2, item_box)

        self.btn_quiz.setEnabled(len(cards) > 0)

    def _create_deck(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Neues Deck", "Name des neuen Decks:")
        if ok and name.strip():
            deck = name.strip()
            if self.cb_decks.findText(deck) == -1:
                self.cb_decks.addItem(deck)
            self.cb_decks.setCurrentText(deck)

    def _add_card(self) -> None:
        f = self.edit_front.text().strip()
        b = self.edit_back.text().strip()
        if not f or not b:
            return
        deck = self.cb_decks.currentText() or "Allgemein"
        if self.store:
            self.store.add_card(deck, f, b)
        self.edit_front.clear()
        self.edit_back.clear()
        self._load_cards_for_current_deck()

    def _delete_selected_card(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        card_id = item.data(Qt.ItemDataRole.UserRole)
        if card_id and self.store:
            self.store.delete_card(card_id)
        self._load_cards_for_current_deck()

    def _open_import_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Lernkarten aus Text importieren")
        dlg.resize(400, 320)
        l = QVBoxLayout(dlg)
        l.addWidget(QLabel("Füge hier deine Karten ein (eine pro Zeile, z. B. <i>Hund = dog</i>):"))

        edit = QTextEdit()
        edit.setPlaceholderText("Guten Tag = Hello\nKatze = Cat\nApfel = Apple")
        l.addWidget(edit, 1)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("Importieren")
        btn_ok.setStyleSheet("background-color: #4F46E5; color: white; font-weight: bold; border-radius: 4px; padding: 6px;")
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        l.addLayout(btn_row)

        def _do_import():
            parsed = parse_flashcards_text(edit.toPlainText())
            if not parsed:
                QMessageBox.warning(dlg, "Import", "Keine gültigen Zeilen im Format 'Vorderseite = Rückseite' gefunden.")
                return
            deck = self.cb_decks.currentText() or "Allgemein"
            if self.store:
                for front, back in parsed:
                    self.store.add_card(deck, front, back)
            QMessageBox.information(dlg, "Import erfolgreich", f"{len(parsed)} Karten zum Deck '{deck}' hinzugefügt! 🎉")
            dlg.accept()
            self._load_cards_for_current_deck()

        btn_ok.clicked.connect(_do_import)
        dlg.exec()

    def _generate_ai_cards(self) -> None:
        if not gemini.has_key():
            QMessageBox.warning(
                self,
                "Gemini-Key fehlt",
                "Für KI-generierte Lernkarten wird ein kostenloser Gemini-Key benötigt.\n"
                "Klicke mit der rechten Maustaste auf Kylie -> 'Gemini-Key eintragen'.",
            )
            return

        from PyQt6.QtWidgets import QInputDialog
        topic, ok = QInputDialog.getText(
            self,
            "KI-Lernkarten generieren",
            "Zu welchem Thema möchtest du 10 Lernkarten?\n(z. B. 'Englisch Vokabeln Restaurant' oder 'Photosynthese'):",
        )
        if not ok or not topic.strip():
            return

        self._ai_topic = topic.strip()
        self._gemini_worker = GeminiCardWorker(self._ai_topic)
        self._gemini_worker.success.connect(self._on_ai_cards_generated)
        self._gemini_worker.failed.connect(lambda err: QMessageBox.warning(self, "KI-Fehler", f"Konnte keine Karten erstellen:\n{err}"))
        self._gemini_worker.start()

    def _on_ai_cards_generated(self, cards: list) -> None:
        deck = self.cb_decks.currentText() or "Allgemein"
        if self.store:
            for front, back in cards:
                self.store.add_card(deck, front, back)
        QMessageBox.information(self, "Lernkarten erstellt", f"{len(cards)} Lernkarten zum Thema '{self._ai_topic}' hinzugefügt! ✨")
        self._load_cards_for_current_deck()

    def _start_quiz(self) -> None:
        deck = self.cb_decks.currentText() or "Allgemein"
        self.quiz_requested.emit(deck)
        self.accept()
