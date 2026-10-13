"""Einstellungsdialog (Dark-Mode) - speichert direkt in config.json."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

STYLE = """
QDialog { background: #26282C; }
QLabel { color: #F2F3F5; font: 10pt "Segoe UI"; }
QLabel#title { font: 600 15pt "Segoe UI"; color: #FF8FB1; }
QLabel#hint { color: #8D919B; font: 9pt "Segoe UI"; }
QLineEdit, QComboBox { background: #33353B; color: #F2F3F5; border: 1px solid #44464D; border-radius: 8px;
        padding: 6px 10px; font: 10pt "Segoe UI"; selection-background-color: #FF8FB1; selection-color: #26282C; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #FF8FB1; }
QComboBox QAbstractItemView { background: #33353B; color: #F2F3F5; selection-background-color: #FF8FB1;
        selection-color: #26282C; border: 1px solid #44464D; outline: none; }
QCheckBox { color: #F2F3F5; font: 10pt "Segoe UI"; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #55575F; background: #33353B; }
QCheckBox::indicator:checked { background: #FF8FB1; border: 1px solid #FF8FB1; }
QSlider::groove:horizontal { height: 6px; background: #3D3F46; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #FF8FB1; border-radius: 3px; }
QSlider::handle:horizontal { background: #FFFFFF; width: 16px; margin: -6px 0; border-radius: 8px; }
QPushButton { background: #3A3C43; color: #F2F3F5; border: none; border-radius: 10px; padding: 9px 18px;
        font: 10pt "Segoe UI"; }
QPushButton:hover { background: #474A52; }
QPushButton#primary { background: #FF8FB1; color: #26282C; font-weight: 600; }
QPushButton#primary:hover { background: #FFA5C0; }
"""


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
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

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.provider = QComboBox()
        self.provider.addItems(["auto", "gemini", "openai", "offline"])
        self.provider.setCurrentText(str(cfg.get("ai.provider", "auto")))
        form.addRow("KI-Anbieter", self.provider)

        # Gemini API Key & Direct Link
        gem_box = QWidget()
        gem_lay = QHBoxLayout(gem_box)
        gem_lay.setContentsMargins(0, 0, 0, 0)
        gem_lay.setSpacing(6)
        self.gem_key = self._secret(cfg.get("ai.gemini_api_key", ""))
        gem_btn = QPushButton("🔑 Key holen")
        gem_btn.setToolTip("Öffnet Google AI Studio im Browser, um kostenlos einen Gemini API-Key zu erstellen")
        gem_btn.clicked.connect(self._open_gemini_link)
        gem_lay.addWidget(self.gem_key, 1)
        gem_lay.addWidget(gem_btn)
        form.addRow("Gemini API-Key", gem_box)

        # Gemini Modelle (editable QComboBox)
        self.gem_model = QComboBox()
        self.gem_model.setEditable(True)
        gem_models = [
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-3.8-flash",
            "gemini-pro-latest",
            "gemini-2.5-flash",
        ]
        self.gem_model.addItems(gem_models)
        cur_model = str(cfg.get("ai.gemini_model", "gemini-3.5-flash"))
        idx = self.gem_model.findText(cur_model)
        if idx >= 0:
            self.gem_model.setCurrentIndex(idx)
        else:
            self.gem_model.setEditText(cur_model)
        form.addRow("Gemini-Modell", self.gem_model)

        self.oai_key = self._secret(cfg.get("ai.openai_api_key", ""))
        form.addRow("OpenAI API-Key", self.oai_key)
        self.oai_model = QComboBox()
        self.oai_model.setEditable(True)
        self.oai_model.addItems(["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "o3-mini"])
        self.oai_model.setEditText(str(cfg.get("ai.openai_model", "gpt-4o-mini")))
        form.addRow("OpenAI-Modell", self.oai_model)
        self.oai_url = QLineEdit(str(cfg.get("ai.openai_base_url", "")))
        form.addRow("OpenAI Base-URL", self.oai_url)
        root.addLayout(form)

        hint = QLabel("💡 Mochi beherrscht 15 Tools! Bei Rate-Limits probiert er automatisch Ersatz-Modelle oder arbeitet nahtlos offline.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(hint)


        form2 = QFormLayout()
        form2.setSpacing(10)
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
        root.addLayout(form2)

        hk = QLabel(f"Tastenk\u00fcrzel zum Eingeben: {str(cfg.get('hotkey', 'ctrl+alt+p')).upper()} "
                    "(\u00e4nderbar in config.json, Neustart n\u00f6tig)")
        hk.setObjectName("hint")
        root.addWidget(hk)

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

    @staticmethod
    def _secret(value: str) -> QLineEdit:
        edit = QLineEdit(str(value or ""))
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setPlaceholderText("nicht gesetzt")
        return edit

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

    def _open_gemini_link(self) -> None:
        try:
            os.startfile("https://aistudio.google.com/app/apikey")
        except OSError:
            pass

    def _open_cfg(self) -> None:
        try:
            os.startfile(str(self.cfg.path))  # type: ignore[attr-defined]
        except OSError:
            pass

    def _save(self) -> None:
        c = self.cfg
        c.set("ai.provider", self.provider.currentText())
        c.set("ai.gemini_api_key", self.gem_key.text().strip())
        c.set("ai.gemini_model", self.gem_model.currentText().strip() or "gemini-3.5-flash")
        c.set("ai.openai_api_key", self.oai_key.text().strip())
        c.set("ai.openai_model", self.oai_model.currentText().strip() or "gpt-4o-mini")
        c.set("ai.openai_base_url", self.oai_url.text().strip() or "https://api.openai.com/v1")
        c.set("pet.speed", self.speed.value())
        c.set("pet.scale", self.scale.value() / 100.0)
        c.set("pet.wander", self.wander.isChecked())
        c.set("pet.chatter", self.chatter.isChecked())
        c.save()
        self.accept()

