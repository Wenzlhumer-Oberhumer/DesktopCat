"""Fenster „Meine Daten“: Faktenverwaltung, Datenschutzeinstellungen, Loeschfunktionen und Transparenzhinweise."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from memory_store import get_memory_store
from i18n import tr


STYLE = """
QDialog { background: #26282C; }
QLabel { color: #F2F3F5; font: 10pt "Segoe UI"; }
QLabel#title { font: 600 14pt "Segoe UI"; color: #FF8FB1; }
QLabel#section { font: 600 11pt "Segoe UI"; color: #FFB3C6; margin-top: 6px; }
QLabel#hint { color: #8D919B; font: 9pt "Segoe UI"; }
QCheckBox { color: #F2F3F5; font: 10pt "Segoe UI"; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #55575F; background: #33353B; }
QCheckBox::indicator:checked { background: #FF8FB1; border: 1px solid #FF8FB1; }
QPushButton { background: #3A3C43; color: #F2F3F5; border: none; border-radius: 8px;
              padding: 8px 14px; font: 10pt "Segoe UI"; }
QPushButton:hover { background: #474A52; }
QPushButton#danger { background: #4A3338; color: #FF8FB1; font-weight: 600; }
QPushButton#danger:hover { background: #5C3D44; }
QPushButton#primary { background: #FF8FB1; color: #26282C; font-weight: 600; }
QPushButton#primary:hover { background: #FFA5C0; }
QFrame#infobox { background: #2F3136; border: 1px solid #4E515A; border-radius: 8px; padding: 10px; }
QScrollArea { background: #2B2D31; border: 1px solid #3E4148; border-radius: 8px; }
"""


MONTHS_DE = {1: "Jan.", 2: "Feb.", 3: "März", 4: "Apr.", 5: "Mai", 6: "Juni", 7: "Juli", 8: "Aug.", 9: "Sept.", 10: "Okt.", 11: "Nov.", 12: "Dez."}
MONTHS_EN = {1: "Jan", 2: "Feb", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec"}


def _human_date(d_str: str) -> str:
    """Wandelt '2026-10-20' oder '10-20' oder '03-14' in ein lesbares Datum um."""
    if not d_str:
        return ""
    d_clean = str(d_str).strip()
    parts = d_clean.split("-")
    import i18n
    m_dict = MONTHS_EN if i18n.lang() == "en" else MONTHS_DE
    try:
        if len(parts) == 3:
            _, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{d}. {m_dict.get(m, str(m))}"
        elif len(parts) == 2:
            m, d = int(parts[0]), int(parts[1])
            return f"{d}. {m_dict.get(m, str(m))}"
    except Exception:
        pass
    return d_clean


def format_fact_display(f: dict) -> str:
    """Formatiert Fakten menschenlesbar mit Emojis, ohne 'Frist' und ohne ISO-Datum."""
    text = (f.get("text") or "").strip()
    kind = f.get("kind", "fact")
    due = f.get("due_date")

    is_bday = kind == "birthday" or "geburtstag" in text.lower() or "birthday" in text.lower()
    if is_bday:
        prefix = "🎂 "
        if due and not any(ch.isdigit() for ch in text):
            return f"{prefix}{text} am {_human_date(due)}"
        return f"{prefix}{text}"

    is_date = kind in ("date", "appointment", "deadline", "event") or bool(due)
    if is_date:
        prefix = "📅 "
        if due:
            h_due = _human_date(due)
            if h_due and h_due not in text:
                return f"{prefix}{text} · {h_due}"
        return f"{prefix}{text}"

    return f"• {text}"


class MyDataDialog(QDialog):
    """Verwaltung gespeicherter Fakten, Privatsphaere-Einstellungen und Loeschungen."""

    def __init__(self, cfg, parent=None, store: Optional[object] = None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.store = store or get_memory_store()
        self.char_name = str(cfg.get("pet", {}).get("name") or "Kylie")

        self.setWindowTitle("🔒 Meine Daten")
        self.resize(740, 780)
        self.setMinimumHeight(680)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel(tr("data.title"))
        title.setObjectName("title")
        root.addWidget(title)

        # 1. Abschnitt: Was Kylie über dich weiß
        sec_facts = QLabel(tr("data.section_facts", name=self.char_name))
        sec_facts.setObjectName("section")
        root.addWidget(sec_facts)

        self.facts_scroll = QScrollArea()
        self.facts_scroll.setFixedHeight(150)
        self.facts_scroll.setWidgetResizable(True)
        self.facts_container = QWidget()
        self.facts_lay = QVBoxLayout(self.facts_container)
        self.facts_lay.setContentsMargins(8, 8, 8, 8)
        self.facts_lay.setSpacing(6)
        self.facts_scroll.setWidget(self.facts_container)
        root.addWidget(self.facts_scroll)

        # 2. Abschnitt: Datenschutzeinstellungen (Schalter)
        sec_privacy = QLabel(tr("data.section_privacy"))
        sec_privacy.setObjectName("section")
        root.addWidget(sec_privacy)

        priv = cfg.get("privacy", {}) or {}
        self.chk_save_chats = QCheckBox(tr("data.chk_save_chats"))
        self.chk_save_chats.setChecked(bool(priv.get("save_chats", True)))
        self.chk_save_chats.toggled.connect(self._on_setting_changed)
        root.addWidget(self.chk_save_chats)

        self.chk_remember = QCheckBox(tr("data.chk_remember", name=self.char_name))
        self.chk_remember.setChecked(bool(priv.get("remember", True)))
        self.chk_remember.toggled.connect(self._on_setting_changed)
        root.addWidget(self.chk_remember)

        self.chk_use_history = QCheckBox(tr("data.chk_use_history"))
        self.chk_use_history.setChecked(bool(priv.get("use_history", True)))
        self.chk_use_history.toggled.connect(self._on_setting_changed)
        root.addWidget(self.chk_use_history)

        # 3. Abschnitt: Transparenzhinweis / Info-Box (vollstaendig sichtbar & scrollbar)
        info_frame = QFrame()
        info_frame.setObjectName("infobox")
        info_lay = QVBoxLayout(info_frame)
        info_lay.setContentsMargins(12, 10, 12, 10)
        info_lay.setSpacing(6)

        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setFrameShape(QFrame.Shape.NoFrame)
        info_scroll.setStyleSheet("background: transparent; border: none;")

        info_text = tr("data.privacy_long", name=self.char_name)
        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setTextFormat(Qt.TextFormat.RichText)
        info_lbl.setStyleSheet("background: transparent; color: #F2F3F5; font: 9.5pt 'Segoe UI';")
        info_scroll.setWidget(info_lbl)
        info_lay.addWidget(info_scroll)
        root.addWidget(info_frame, 1)

        # 4. Abschnitt: Buttons
        actions_lay = QHBoxLayout()
        self.btn_del_chats = QPushButton(tr("data.btn_del_chats"))
        self.btn_del_chats.setObjectName("danger")
        self.btn_del_chats.clicked.connect(self._on_delete_all_chats)
        actions_lay.addWidget(self.btn_del_chats)

        self.btn_wipe_all = QPushButton(tr("data.btn_wipe_all"))
        self.btn_wipe_all.setObjectName("danger")
        self.btn_wipe_all.clicked.connect(self._on_wipe_everything)
        actions_lay.addWidget(self.btn_wipe_all)

        actions_lay.addStretch(1)

        self.btn_export = QPushButton(tr("data.btn_export"))
        self.btn_export.clicked.connect(self._on_export_all)
        actions_lay.addWidget(self.btn_export)

        btn_close = QPushButton(tr("common.done"))
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(self.accept)
        actions_lay.addWidget(btn_close)

        root.addLayout(actions_lay)

        self._refresh_facts()

    def _refresh_facts(self) -> None:
        while self.facts_lay.count():
            child = self.facts_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        all_facts = self.store.facts()
        if not all_facts:
            empty = QLabel(tr("data.no_facts", name=self.char_name))
            empty.setObjectName("hint")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.facts_lay.addWidget(empty)
            return

        for f in all_facts:
            row = QHBoxLayout()
            row.setContentsMargins(4, 2, 4, 2)
            dt_str = datetime.datetime.fromtimestamp(f["ts"]).strftime("%d.%m.%Y %H:%M")
            display_text = format_fact_display(f)
            txt = f"{display_text} <font color='#8D919B'>({dt_str})</font>"

            lbl = QLabel(txt)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            row.addWidget(lbl, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(30, 26)
            del_btn.setToolTip("Diesen Fakt löschen")
            del_btn.setStyleSheet("""
                QPushButton {
                    background: #3A3C43;
                    color: #F2F3F5;
                    border: 1px solid #4E515A;
                    border-radius: 6px;
                    font: 11pt 'Segoe UI';
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: #5C3D44;
                    color: #FF8FB1;
                    border-color: #FF8FB1;
                }
            """)
            del_btn.clicked.connect(lambda _=False, fid=f["id"]: self._delete_single_fact(fid))
            row.addWidget(del_btn)

            self.facts_lay.addLayout(row)

        self.facts_lay.addStretch(1)

    def _delete_single_fact(self, fact_id: int) -> None:
        self.store.delete_fact(fact_id)
        self._refresh_facts()

    def _on_setting_changed(self) -> None:
        self.cfg.set("privacy.save_chats", self.chk_save_chats.isChecked())
        self.cfg.set("privacy.remember", self.chk_remember.isChecked())
        self.cfg.set("privacy.use_history", self.chk_use_history.isChecked())
        self.cfg.save()

    def _on_delete_all_chats(self) -> None:
        ans = QMessageBox.question(
            self,
            "Alle Chats löschen",
            "Möchtest du wirklich alle gespeicherten Chat-Verläufe löschen?\nGemerkte Fakten bleiben erhalten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.store.delete_all_chats()
            QMessageBox.information(self, "Gelöscht", "Alle Chat-Verläufe wurden gelöscht. 🗑️")

    def _on_wipe_everything(self) -> None:
        ans = QMessageBox.warning(
            self,
            "Alles vergessen",
            "Wirklich alles vergessen? Das kann nicht rückgängig gemacht werden.\n"
            "Alle Chats, gemerkten Fakten und Statistiken werden unwiderruflich gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.store.wipe_everything()
            self._refresh_facts()
            QMessageBox.information(self, "Zurückgesetzt", "Alle Daten wurden vollständig gelöscht. 🧹✨")

    def _on_export_all(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Alle Daten exportieren",
            str(Path.home() / "Desktop" / "DesktopCat_AlleDaten.txt"),
            "Textdateien (*.txt);;Alle Dateien (*.*)",
        )
        if path:
            self.store.export_text(path)
            QMessageBox.information(self, "Export erfolgreich", f"Deine Daten wurden nach:\n{path}\nexportiert! 📄✨")
