"""Einstellungsdialog (Dark-Mode) - speichert direkt in config.json."""
from __future__ import annotations

import os
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

import gemini
from paths import set_autostart

try:
    from pet_sprites import CHARACTERS
except ImportError:         # alte pet_sprites ohne Charakter-Registry
    CHARACTERS = {}

STYLE = """
QDialog { background: #26282C; }
QLabel { color: #F2F3F5; font: 10pt "Segoe UI"; }
QLabel#title { font: 600 15pt "Segoe UI"; color: #FF8FB1; }
QLabel#section { font: 600 11pt "Segoe UI"; color: #FFB3C6; margin-top: 6px; }
QLabel#hint { color: #8D919B; font: 9pt "Segoe UI"; }
QLabel#status { font: 10pt "Segoe UI"; font-weight: bold; }
QLineEdit, QComboBox { background: #33353B; color: #F2F3F5; border: 1px solid #55575F; border-radius: 8px;
        padding: 6px 8px; font: 10pt "Segoe UI"; }
QComboBox QAbstractItemView { background: #2B2D31; color: #F2F3F5; selection-background-color: #FF8FB1;
        selection-color: #26282C; }
QCheckBox { color: #F2F3F5; font: 10pt "Segoe UI"; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #55575F; background: #33353B; }
QCheckBox::indicator:checked { background: #FF8FB1; border: 1px solid #FF8FB1; }
QSlider::groove:horizontal { height: 6px; background: #3D3F46; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #FF8FB1; border-radius: 3px; }
QSlider::handle:horizontal { background: #FFFFFF; width: 16px; margin: -6px 0; border-radius: 8px; }
QPushButton { background: #3A3C43; color: #F2F3F5; border: none; border-radius: 10px; padding: 9px 18px;
        font: 10pt "Segoe UI"; }
QPushButton:hover { background: #474A52; }
QPushButton#google { background: #4285F4; color: #FFFFFF; font-weight: 600; padding: 10px 18px; }
QPushButton#google:hover { background: #5393FF; }
QPushButton#google:disabled { background: #384252; color: #88909D; }
QPushButton#danger { background: #4A3338; color: #FF8FB1; }
QPushButton#danger:hover { background: #5C3D44; }
QPushButton#primary { background: #FF8FB1; color: #26282C; font-weight: 600; }
QPushButton#primary:hover { background: #FFA5C0; }
"""


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None, hotkey_validator=None):
        super().__init__(parent)
        self.cfg = cfg
        self._hotkey_ok = hotkey_validator or (lambda spec: bool(spec.strip()))

        self.setWindowTitle("Einstellungen")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setMinimumWidth(480)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("\U0001F43E  Einstellungen")
        title.setObjectName("title")
        root.addWidget(title)

        # -- Gemini-Konto -------------------------------------------------------------
        sec_ai = QLabel("Gemini-KI")
        sec_ai.setObjectName("section")
        root.addWidget(sec_ai)

        ai_box = QWidget()
        ai_lay = QVBoxLayout(ai_box)
        ai_lay.setContentsMargins(0, 0, 0, 0)
        ai_lay.setSpacing(8)

        # Status
        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("status")
        ai_lay.addWidget(self.status_lbl)

        steps = QLabel("1. „Gratis-Key holen“ klicken und mit Google anmelden\n"
                       "2. „Create API key“ → Key kopieren (Free Tier reicht, KEIN Bezahlkonto nötig –\n"
                       "    Angebote für Billing, Firebase oder Guthaben einfach überspringen)\n"
                       "3. Hier einfügen → „Prüfen & speichern“")
        steps.setObjectName("hint")
        ai_lay.addWidget(steps)

        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Gemini-Key einfügen (beginnt mit AIza…)")
        self.key_edit.textChanged.connect(lambda t: self.save_key_btn.setEnabled(bool(t.strip())))
        ai_lay.addWidget(self.key_edit)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        get_key_btn = QPushButton("Gratis-Key holen")
        get_key_btn.setObjectName("google")
        get_key_btn.clicked.connect(lambda: webbrowser.open(gemini.KEY_URL))
        btn_box.addWidget(get_key_btn, 1)

        self.save_key_btn = QPushButton("Prüfen & speichern")
        self.save_key_btn.setObjectName("primary")
        self.save_key_btn.setEnabled(False)
        self.save_key_btn.clicked.connect(self._on_save_key)
        btn_box.addWidget(self.save_key_btn)

        self.logout_btn = QPushButton("Key entfernen")
        self.logout_btn.setObjectName("danger")
        self.logout_btn.clicked.connect(self._on_logout_click)
        btn_box.addWidget(self.logout_btn)
        ai_lay.addLayout(btn_box)

        # Checkbox KI verwenden
        self.ai_enabled = QCheckBox("KI verwenden (Gemini)")
        self.ai_enabled.setChecked(bool(cfg.get("ai.enabled", True)))
        ai_lay.addWidget(self.ai_enabled)

        root.addWidget(ai_box)

        hint = QLabel("Der Key ist kostenlos und bleibt sicher in der Windows-Anmeldeinformationsverwaltung. "
                      "Ohne Key arbeitet Desktop Cat im Offline-Modus.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # -- Katze / Verhalten --------------------------------------------------------
        sec_pet = QLabel("Verhalten & Aussehen")
        sec_pet.setObjectName("section")
        root.addWidget(sec_pet)

        form2 = QFormLayout()
        form2.setSpacing(10)

        self.char_combo = QComboBox()
        cur_char = str(cfg.get("pet.character", "cat_mochi"))
        for cid, ci in CHARACTERS.items():
            self.char_combo.addItem(f"{ci['emoji']}  {ci['name']} ({ci['species']})", cid)
        self.char_combo.setCurrentIndex(max(0, self.char_combo.findData(cur_char)))
        self.char_combo.setEnabled(bool(CHARACTERS))
        form2.addRow("Charakter", self.char_combo)

        self.user_name_edit = QLineEdit(str(cfg.get("pet.user_name", "Boss")))
        self.user_name_edit.setPlaceholderText("Boss (Standard)")
        form2.addRow("Dein Name / Anrede", self.user_name_edit)

        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(30, 300)
        self.speed.setValue(int(cfg.get("pet.speed", 90)))
        self.speed_lbl = QLabel()
        form2.addRow("Laufgeschwindigkeit", self._with_label(self.speed, self.speed_lbl, " px/s"))

        self.scale = QSlider(Qt.Orientation.Horizontal)
        self.scale.setRange(60, 180)
        self.scale.setValue(int(float(cfg.get("pet.scale", 1.0)) * 100))
        self.scale_lbl = QLabel()
        form2.addRow("Gr\u00f6\u00dfe", self._with_label(self.scale, self.scale_lbl, " %"))

        self.wander = QCheckBox("Selbstst\u00e4ndig herumlaufen & schlafen")
        self.wander.setChecked(bool(cfg.get("pet.wander", True)))
        form2.addRow("", self.wander)

        self.chatter = QCheckBox("Gelegentlich etwas sagen")
        self.chatter.setChecked(bool(cfg.get("pet.chatter", True)))
        form2.addRow("", self.chatter)

        self.autostart = QCheckBox("Mit Windows starten")
        self.autostart.setChecked(bool(cfg.get("autostart", True)))
        form2.addRow("", self.autostart)

        self.auto_update = QCheckBox("Automatisch nach Updates suchen")
        self.auto_update.setChecked(bool(cfg.get("update.auto", True)))
        form2.addRow("", self.auto_update)

        self.breaks = QCheckBox("Erinnerung: kurz strecken")
        self.breaks.setChecked(bool(cfg.get("wellbeing.breaks", True)))
        form2.addRow("", self.breaks)

        self.water = QCheckBox("Erinnerung: Wasser trinken")
        self.water.setChecked(bool(cfg.get("wellbeing.water", True)))
        form2.addRow("", self.water)

        self.break_min = QSlider(Qt.Orientation.Horizontal)
        self.break_min.setRange(10, 180)
        self.break_min.setValue(int(cfg.get("wellbeing.break_min", 60)))
        self.break_min_lbl = QLabel()
        form2.addRow("Erinnerung alle", self._with_label(self.break_min, self.break_min_lbl, " Min."))

        self.battery_warn = QCheckBox("Akku-Warnung unter 15 %")
        self.battery_warn.setChecked(bool(cfg.get("battery_warn", True)))
        form2.addRow("", self.battery_warn)

        self.night_mode = QCheckBox("Nachtmodus (23\u20137 Uhr: ruhig & m\u00fcde)")
        self.night_mode.setChecked(bool(cfg.get("night_mode", True)))
        form2.addRow("", self.night_mode)

        self.hotkey_edit = QLineEdit(str(cfg.get("hotkey", "ctrl+alt+p")))
        self.hotkey_edit.setPlaceholderText("z. B. ctrl+alt+p")
        form2.addRow("Tastenk\u00fcrzel", self.hotkey_edit)
        root.addLayout(form2)

        self.hotkey_hint = QLabel("Format: ctrl / alt / shift / win + Taste, z. B. ctrl+alt+p oder ctrl+shift+f5")
        self.hotkey_hint.setObjectName("hint")
        root.addWidget(self.hotkey_hint)

        # -- Dialog-Buttons -----------------------------------------------------------
        btns = QHBoxLayout()
        open_cfg = QPushButton("config.json \u00f6ffnen")
        open_cfg.clicked.connect(self._open_cfg)
        btns.addWidget(open_cfg)
        btns.addStretch(1)

        cancel = QPushButton("Abbrechen")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Speichern")
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

        self._refresh_auth_ui()

    def _set_status(self, text: str, color: str) -> None:
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {color};")

    def _refresh_auth_ui(self) -> None:
        if gemini.has_key():
            self._set_status("\u2705  Gemini-Key hinterlegt", "#79D279")
            self.logout_btn.setVisible(True)
        else:
            self._set_status("\u274c  Noch kein Gemini-Key", "#FF8F8F")
            self.logout_btn.setVisible(False)

    def _on_save_key(self) -> None:
        key = self.key_edit.text().strip()
        self._set_status("\U0001f504  Pr\u00fcfe Key\u2026", "#8D919B")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            gemini.validate_key(key)
            gemini.save_key(key)
        except Exception as exc:  # noqa: BLE001 - LLMError oder Credential-Fehler anzeigen
            self._set_status(f"\u274c  {exc}", "#FF8F8F")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.key_edit.clear()
        self._refresh_auth_ui()
        parent = self.parent()
        if parent and hasattr(parent, "celebrate"):
            parent.celebrate()

    def _on_logout_click(self) -> None:
        gemini.clear_key()
        self._refresh_auth_ui()

    @staticmethod
    def _with_label(slider: QSlider, label: QLabel, suffix: str) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        label.setMinimumWidth(64)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda v: label.setText(f"{v}{suffix}"))
        label.setText(f"{slider.value()}{suffix}")
        lay.addWidget(slider, 1)
        lay.addWidget(label)
        return box

    def _open_cfg(self) -> None:
        try:
            os.startfile(str(self.cfg.path))  # type: ignore[attr-defined]
        except OSError:
            pass

    def _save(self) -> None:
        c = self.cfg
        hotkey = self.hotkey_edit.text().strip().lower()
        if not self._hotkey_ok(hotkey):
            self.hotkey_hint.setText("\u274c  Ung\u00fcltiges Tastenk\u00fcrzel - Beispiel: ctrl+alt+p")
            self.hotkey_hint.setStyleSheet("color: #FF8F8F;")
            return
        c.set("hotkey", hotkey)
        char = self.char_combo.currentData()
        if char:
            c.set("pet.character", str(char))
        c.set("pet.user_name", self.user_name_edit.text().strip() or "Boss")
        c.set("wellbeing.breaks", self.breaks.isChecked())
        c.set("wellbeing.water", self.water.isChecked())
        c.set("wellbeing.break_min", self.break_min.value())
        c.set("battery_warn", self.battery_warn.isChecked())
        c.set("night_mode", self.night_mode.isChecked())
        c.set("ai.enabled", self.ai_enabled.isChecked())
        c.set("pet.speed", self.speed.value())
        c.set("pet.scale", self.scale.value() / 100.0)
        c.set("pet.wander", self.wander.isChecked())
        c.set("pet.chatter", self.chatter.isChecked())
        c.set("autostart", self.autostart.isChecked())
        set_autostart(self.autostart.isChecked())
        c.set("update.auto", self.auto_update.isChecked())
        c.save()
        self.accept()
