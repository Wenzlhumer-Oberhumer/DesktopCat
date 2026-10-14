# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Fenster „Meine Daten“: Faktenverwaltung, Datenschutzeinstellungen, Loeschfunktionen und Transparenzhinweise."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import tools
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

        # 0. Abschnitt: Dein Profil
        sec_profile = QLabel(tr("data.section_profile"))
        sec_profile.setObjectName("section")
        root.addWidget(sec_profile)

        prof_frame = QFrame()
        prof_frame.setObjectName("infobox")
        prof_grid = QGridLayout(prof_frame)
        prof_grid.setContentsMargins(12, 10, 12, 10)
        prof_grid.setHorizontalSpacing(12)
        prof_grid.setVerticalSpacing(8)

        # Name & Spitzname
        lbl_p_name = QLabel(tr("data.profile_name"))
        lbl_p_name.setStyleSheet("color: #8D919B; font-size: 9.5pt;")
        self.edit_p_name = QLineEdit(str(cfg.get("profile.name", "")))
        self.edit_p_name.setPlaceholderText("z. B. Florian")
        self.edit_p_name.textChanged.connect(self._on_profile_field_changed)

        lbl_p_nick = QLabel(tr("data.profile_nickname"))
        lbl_p_nick.setStyleSheet("color: #8D919B; font-size: 9.5pt;")
        self.edit_p_nick = QLineEdit(str(cfg.get("pet.user_name", "Boss")))
        self.edit_p_nick.setPlaceholderText("z. B. Flo oder Boss")
        self.edit_p_nick.textChanged.connect(self._on_profile_field_changed)

        prof_grid.addWidget(lbl_p_name, 0, 0)
        prof_grid.addWidget(self.edit_p_name, 0, 1)
        prof_grid.addWidget(lbl_p_nick, 0, 2)
        prof_grid.addWidget(self.edit_p_nick, 0, 3)

        # Pronomen & Stadt
        lbl_p_pro = QLabel(tr("data.profile_pronouns"))
        lbl_p_pro.setStyleSheet("color: #8D919B; font-size: 9.5pt;")
        self.edit_p_pro = QLineEdit(str(cfg.get("profile.pronouns", "")))
        self.edit_p_pro.setPlaceholderText("er / sie / they")
        self.edit_p_pro.textChanged.connect(self._on_profile_field_changed)

        lbl_p_city = QLabel(tr("data.profile_city"))
        lbl_p_city.setStyleSheet("color: #8D919B; font-size: 9.5pt;")
        self.edit_p_city = QLineEdit(str(cfg.get("profile.city", "")))
        self.edit_p_city.setPlaceholderText("z. B. Berlin")
        self.edit_p_city.textChanged.connect(self._on_profile_field_changed)

        prof_grid.addWidget(lbl_p_pro, 1, 0)
        prof_grid.addWidget(self.edit_p_pro, 1, 1)
        prof_grid.addWidget(lbl_p_city, 1, 2)
        prof_grid.addWidget(self.edit_p_city, 1, 3)

        # Hobbys & Ton
        lbl_p_int = QLabel(tr("data.profile_interests"))
        lbl_p_int.setStyleSheet("color: #8D919B; font-size: 9.5pt;")
        self.edit_p_int = QLineEdit(str(cfg.get("profile.interests", "")))
        self.edit_p_int.setPlaceholderText("Gitarre, Katzen, Python...")
        self.edit_p_int.textChanged.connect(self._on_profile_field_changed)

        lbl_p_tone = QLabel(tr("data.profile_tone"))
        lbl_p_tone.setStyleSheet("color: #8D919B; font-size: 9.5pt;")
        self.edit_p_tone = QLineEdit(str(cfg.get("profile.tone", "")))
        self.edit_p_tone.setPlaceholderText("frech & witzig, lieb...")
        self.edit_p_tone.textChanged.connect(self._on_profile_field_changed)

        prof_grid.addWidget(lbl_p_int, 2, 0)
        prof_grid.addWidget(self.edit_p_int, 2, 1)
        prof_grid.addWidget(lbl_p_tone, 2, 2)
        prof_grid.addWidget(self.edit_p_tone, 2, 3)

        # Profile Buttons
        prof_btn_row = QHBoxLayout()
        self.btn_repeat_onboarding = QPushButton(tr("data.btn_onboarding_repeat"))
        self.btn_repeat_onboarding.clicked.connect(self._on_repeat_onboarding)
        prof_btn_row.addWidget(self.btn_repeat_onboarding)

        self.btn_del_profile = QPushButton(tr("data.btn_profile_delete"))
        self.btn_del_profile.setObjectName("danger")
        self.btn_del_profile.clicked.connect(self._on_delete_profile)
        prof_btn_row.addWidget(self.btn_del_profile)
        prof_btn_row.addStretch()

        prof_grid.addLayout(prof_btn_row, 3, 0, 1, 4)
        root.addWidget(prof_frame)

        # 1. Abschnitt: Was Kylie über dich weiß
        sec_facts = QLabel(tr("data.section_facts", name=self.char_name))
        sec_facts.setObjectName("section")
        root.addWidget(sec_facts)

        self.facts_scroll = QScrollArea()
        self.facts_scroll.setFixedHeight(120)
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
            tr("data.del_chats_title"),
            tr("data.del_chats_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.store.delete_all_chats()
            QMessageBox.information(self, tr("data.deleted_title"), tr("data.deleted_text"))

    def _on_wipe_everything(self) -> None:
        ans = QMessageBox.warning(
            self,
            tr("data.wipe_title"),
            tr("data.wipe_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.store.wipe_everything()
            self.cfg.set("profile", {"name": "", "pronouns": "", "uses": [], "interests": "", "tone": "", "city": ""})
            self.cfg.set("onboarding_done", False)
            self.cfg.save()
            self._refresh_profile_fields()
            self._refresh_facts()
            QMessageBox.information(self, tr("data.reset_title"), tr("data.reset_text"))

    def _on_export_all(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("data.export_title"),
            str(tools.desktop_dir() / "DesktopCat_AlleDaten.txt"),
            tr("common.file_filter_txt"),
        )
        if path:
            self.store.export_text(path)
            QMessageBox.information(self, tr("common.export_ok_title"), tr("common.export_ok_text", path=path))

    def _on_profile_field_changed(self) -> None:
        self.cfg.set("profile.name", self.edit_p_name.text().strip())
        self.cfg.set("pet.user_name", self.edit_p_nick.text().strip() or "Boss")
        self.cfg.set("profile.pronouns", self.edit_p_pro.text().strip())
        self.cfg.set("profile.city", self.edit_p_city.text().strip())
        self.cfg.set("profile.interests", self.edit_p_int.text().strip())
        self.cfg.set("profile.tone", self.edit_p_tone.text().strip())
        self.cfg.save()

    def _on_repeat_onboarding(self) -> None:
        try:
            from onboarding import OnboardingDialog
            dlg = OnboardingDialog(self.cfg, parent=self, is_update=True)
            dlg.exec()
            self._refresh_profile_fields()
            self._refresh_facts()
        except Exception as e:
            QMessageBox.warning(self, tr("common.error_title"), tr("data.onboarding_failed", e=e))

    def _on_delete_profile(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(tr("data.btn_profile_delete"))
        box.setText(tr("data.confirm_delete_profile"))
        box.setIcon(QMessageBox.Icon.Question)
        btn_yes = box.addButton(tr("data.btn_delete"), QMessageBox.ButtonRole.YesRole)
        box.addButton(tr("data.btn_cancel"), QMessageBox.ButtonRole.NoRole)
        box.exec()
        if box.clickedButton() == btn_yes:
            self.cfg.set("profile", {"name": "", "pronouns": "", "uses": [], "interests": "", "tone": "", "city": ""})
            self.cfg.save()
            self._refresh_profile_fields()

    def _refresh_profile_fields(self) -> None:
        self.edit_p_name.setText(str(self.cfg.get("profile.name", "")))
        self.edit_p_nick.setText(str(self.cfg.get("pet.user_name", "Boss")))
        self.edit_p_pro.setText(str(self.cfg.get("profile.pronouns", "")))
        self.edit_p_city.setText(str(self.cfg.get("profile.city", "")))
        self.edit_p_int.setText(str(self.cfg.get("profile.interests", "")))
        self.edit_p_tone.setText(str(self.cfg.get("profile.tone", "")))
