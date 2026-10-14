# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Einstellungsdialog (Dark/Kawaii-Mode mit Tabs & ScrollArea) - speichert direkt in config.json."""
from __future__ import annotations

import os
import webbrowser
from typing import Optional

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSlider, QTabWidget, QVBoxLayout, QWidget,
)

import gemini
import auth_manager
import voice_tts
from paths import set_autostart


class _OAuthCustomEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, success: bool, error: str = ""):
        super().__init__(self.EVENT_TYPE)
        self.success = success
        self.error = error

try:
    from pet_sprites import CHARACTERS, get_character_info
except ImportError:
    CHARACTERS = {}
    def get_character_info(cid):
        return {"name": cid, "species": "", "desc": "", "sound": "Miau~", "emoji": "🐾"}

STYLE = """
QDialog {
    background-color: #202226;
    color: #F2F3F5;
}
QLabel {
    color: #E2E4E9;
    font: 10pt "Segoe UI";
}
QLabel#title {
    font: 700 16pt "Segoe UI";
    color: #FF8FB1;
}
QLabel#subtitle {
    color: #9AA0A6;
    font: 9pt "Segoe UI";
}
QLabel#section {
    font: 700 11pt "Segoe UI";
    color: #FFB3C6;
    margin-top: 4px;
}
QLabel#hint {
    color: #8D919B;
    font: 9pt "Segoe UI";
}
QLabel#status {
    font: 10pt "Segoe UI";
    font-weight: bold;
}
QLineEdit, QComboBox {
    background-color: #2D3036;
    color: #F2F3F5;
    border: 1px solid #484B54;
    border-radius: 8px;
    padding: 7px 10px;
    font: 10pt "Segoe UI";
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #FF8FB1;
    background-color: #33363D;
}
QComboBox QAbstractItemView {
    background: #25272D;
    color: #F2F3F5;
    selection-background-color: #FF8FB1;
    selection-color: #202226;
    border: 1px solid #484B54;
    border-radius: 6px;
    padding: 4px;
}
QCheckBox {
    color: #F2F3F5;
    font: 10pt "Segoe UI";
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #4F525C;
    background: #2D3036;
}
QCheckBox::indicator:checked {
    background: #FF8FB1;
    border: 1px solid #FF8FB1;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #383A42;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #FF8FB1;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #FFE4EC;
}
QPushButton {
    background-color: #353840;
    color: #F2F3F5;
    border: 1px solid #444750;
    border-radius: 8px;
    padding: 8px 16px;
    font: 10pt "Segoe UI";
}
QPushButton:hover {
    background-color: #434650;
    border-color: #555964;
}
QPushButton#google {
    background-color: #4285F4;
    color: #FFFFFF;
    font-weight: 600;
    border: none;
    padding: 9px 16px;
}
QPushButton#google:hover {
    background-color: #5393FF;
}
QPushButton#google:disabled {
    background-color: #333C48;
    color: #79828F;
}
QPushButton#danger {
    background-color: #4A2E35;
    color: #FF8FB1;
    border: 1px solid #633640;
}
QPushButton#danger:hover {
    background-color: #5A353E;
}
QPushButton#primary {
    background-color: #FF8FB1;
    color: #202226;
    font-weight: 700;
    border: none;
    padding: 8px 20px;
}
QPushButton#primary:hover {
    background-color: #FFA5C0;
}
QPushButton#hide_btn {
    background-color: #383442;
    color: #D8B4FE;
    border: 1px solid #5B4875;
}
QPushButton#hide_btn:hover {
    background-color: #493F5A;
}
QTabWidget::pane {
    border: 1px solid #383B44;
    background: #25282E;
    border-radius: 12px;
    padding: 4px;
}
QTabBar::tab {
    background: #1C1E22;
    color: #9AA0AA;
    padding: 10px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
    font: 600 10pt "Segoe UI";
}
QTabBar::tab:selected {
    background: #25282E;
    color: #FF8FB1;
    border: 1px solid #383B44;
    border-bottom: none;
}
QTabBar::tab:hover:!selected {
    background: #2B2E35;
    color: #F2F3F5;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: #1C1E22;
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #474A54;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #FF8FB1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QFrame#card {
    background-color: #2B2E35;
    border: 1px solid #3A3D46;
    border-radius: 10px;
    padding: 12px;
}
"""


class SettingsDialog(QDialog):
    hide_pet_requested = pyqtSignal()

    def __init__(self, cfg, parent=None, hotkey_validator=None):
        super().__init__(parent)
        self.cfg = cfg
        self._hotkey_ok = hotkey_validator or (lambda spec: bool(spec.strip()))

        import i18n
        self.setWindowTitle(i18n.tr("settings.title"))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(650, 560)
        self.setMinimumSize(560, 460)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # -- Header -------------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        header_v = QVBoxLayout()
        header_v.setSpacing(2)
        title = QLabel("🐾  Desktop Cat – Einstellungen")
        title.setObjectName("title")
        subtitle = QLabel("Passe deine Katze, Funktionen und Gemini-KI nach deinen Wünschen an.")
        subtitle.setObjectName("subtitle")
        header_v.addWidget(title)
        header_v.addWidget(subtitle)
        top_bar.addLayout(header_v, 1)

        root.addLayout(top_bar)

        # -- Tab Widget ---------------------------------------------------------------
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # Erstelle Tabs
        self._build_tab_appearance()
        self._build_tab_behavior()
        self._build_tab_ai()
        self._build_tab_wellbeing()
        self._build_tab_system()

        # -- Footer Buttons -----------------------------------------------------------
        footer = QHBoxLayout()
        footer.setSpacing(10)

        open_cfg_btn = QPushButton(i18n.tr("settings.open_cfg"))
        open_cfg_btn.clicked.connect(self._open_cfg)
        footer.addWidget(open_cfg_btn)

        my_data_btn = QPushButton(i18n.tr("settings.my_data"))
        my_data_btn.clicked.connect(self._open_my_data)
        footer.addWidget(my_data_btn)

        footer.addStretch(1)

        cancel_btn = QPushButton(i18n.tr("settings.cancel"))
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)

        save_btn = QPushButton(i18n.tr("settings.save"))
        save_btn.setObjectName("primary")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)

        root.addLayout(footer)

        self._refresh_auth_ui()
        self._update_character_preview()

    # ==================================================================================
    #  Helper fuer scrollbare Tabs
    # ==================================================================================
    def _create_scrollable_tab(self, tab_title: str) -> QVBoxLayout:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        scroll.setWidget(container)
        self.tabs.addTab(scroll, tab_title)
        return layout

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

    # ==================================================================================
    #  Tab 1: 🎨 Aussehen & Style
    # ==================================================================================
    def _build_tab_appearance(self) -> None:
        import i18n
        lay = self._create_scrollable_tab(i18n.tr("settings.tab_appearance"))

        # Card: Charakter-Wahl & Live-Preview
        card_char = QFrame()
        card_char.setObjectName("card")
        card_char_lay = QVBoxLayout(card_char)
        card_char_lay.setSpacing(10)

        sec_lbl = QLabel("🎭  Charakter & Aussehen")
        sec_lbl.setObjectName("section")
        card_char_lay.addWidget(sec_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self.char_combo = QComboBox()
        cur_char = str(self.cfg.get("pet.character", "cat_mochi"))
        try:
            import pet_care
            from memory_store import get_memory_store
            _store = get_memory_store()
            _unlocked = lambda c: pet_care.is_character_unlocked(c, _store)
        except Exception:
            _unlocked = lambda c: (True, 1, 0)
        for cid, ci in CHARACTERS.items():
            ok, lvl, _ = _unlocked(cid)
            label = f"{ci.get('emoji', '🐾')}  {ci.get('name', cid)} ({ci.get('species', '')})"
            self.char_combo.addItem(label if ok else f"🔒 {label} – ab Level {lvl}", cid)
            if not ok:   # gesperrte Figuren nicht waehlbar (Freischalt-Baum nicht umgehen)
                self.char_combo.model().item(self.char_combo.count() - 1).setEnabled(False)
        self.char_combo.setCurrentIndex(max(0, self.char_combo.findData(cur_char)))
        self.char_combo.setEnabled(bool(CHARACTERS))
        self.char_combo.currentIndexChanged.connect(self._update_character_preview)
        form.addRow("Figur:", self.char_combo)

        # Outfit / Zubehör
        self.worn_combo = QComboBox()
        outfit_options = [
            ("", "Keines (Standard)"),
            ("bow", "🎀  Schleife"),
            ("bandana", "🧣  Halstuch"),
            ("scarf", "🧣  Winterschal"),
            ("party_hat", "🎉  Partyhut"),
            ("sunglasses", "🕶️  Sonnenbrille"),
            ("crown", "👑  Königliche Krone"),
            ("hacker_glasses", "💻  Hacker-Brille"),
            ("nightcap", "🌙  Schlafmütze"),
            ("beanie", "🧢  Beanie-Mütze"),
            ("umbrella", "☂️  Regenschirm"),
            ("gold_sparkle", "✨  Goldener Glanz"),
        ]
        cur_worn = str(self.cfg.get("fun.worn", "")).strip()
        for wid, wlabel in outfit_options:
            self.worn_combo.addItem(wlabel, wid)
        idx = self.worn_combo.findData(cur_worn)
        self.worn_combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(i18n.tr("settings.worn_accessory"), self.worn_combo)

        card_char_lay.addLayout(form)

        # Live-Vorschau Box
        self.preview_box = QFrame()
        self.preview_box.setStyleSheet("background-color: #212328; border: 1px dashed #4F525C; border-radius: 8px; padding: 10px;")
        prev_lay = QVBoxLayout(self.preview_box)
        prev_lay.setSpacing(4)
        self.prev_title = QLabel()
        self.prev_title.setStyleSheet("font-weight: bold; color: #FF8FB1; font-size: 11pt;")
        self.prev_desc = QLabel()
        self.prev_desc.setWordWrap(True)
        self.prev_desc.setStyleSheet("color: #CCD0D9; font-size: 9pt;")
        self.prev_sound = QLabel()
        self.prev_sound.setStyleSheet("color: #FFB3C6; font-style: italic; font-size: 9pt;")
        prev_lay.addWidget(self.prev_title)
        prev_lay.addWidget(self.prev_desc)
        prev_lay.addWidget(self.prev_sound)
        card_char_lay.addWidget(self.preview_box)

        lay.addWidget(card_char)

        # Card: Visuelle Anpassungen (Transparenz & Größe)
        card_vis = QFrame()
        card_vis.setObjectName("card")
        card_vis_lay = QVBoxLayout(card_vis)
        card_vis_lay.setSpacing(10)

        vis_title = QLabel("✨  Transparenz & Skalierung")
        vis_title.setObjectName("section")
        card_vis_lay.addWidget(vis_title)

        form_vis = QFormLayout()
        form_vis.setSpacing(10)

        # Deckkraft / Transparenz
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        cur_op = int(float(self.cfg.get("pet.opacity", 1.0)) * 100)
        self.opacity_slider.setValue(max(30, min(100, cur_op)))
        self.opacity_lbl = QLabel()
        form_vis.addRow(i18n.tr("settings.opacity"), self._with_label(self.opacity_slider, self.opacity_lbl, " %"))

        # Größe
        self.scale = QSlider(Qt.Orientation.Horizontal)
        self.scale.setRange(60, 180)
        self.scale.setValue(int(float(self.cfg.get("pet.scale", 1.0)) * 100))
        self.scale_lbl = QLabel()
        form_vis.addRow("Größe:", self._with_label(self.scale, self.scale_lbl, " %"))

        # Wetter-Outfits
        fun = self.cfg.get("fun", {}) if isinstance(self.cfg.get("fun"), dict) else {}
        self.weather_outfits_chk = QCheckBox("Wetter-Outfits automatisch anziehen (Regenschirm, Sonnenbrille etc.)")
        self.weather_outfits_chk.setChecked(bool(fun.get("weather_outfits", True)))
        form_vis.addRow("", self.weather_outfits_chk)

        card_vis_lay.addLayout(form_vis)
        lay.addWidget(card_vis)
        lay.addStretch(1)

    def _update_character_preview(self) -> None:
        cid = self.char_combo.currentData()
        if not cid:
            return
        info = get_character_info(str(cid))
        name = info.get("name", "Buddy")
        emoji = info.get("emoji", "🐾")
        species = info.get("species", "")
        desc = info.get("desc", "")
        sound = info.get("sound", "Miau~")
        self.prev_title.setText(f"{emoji}  {name} – {species}")
        self.prev_desc.setText(desc)
        self.prev_sound.setText(f"Typischer Spruch: „{sound}“")

    # ==================================================================================
    #  Tab 2: 🐾 Verhalten & Katze
    # ==================================================================================
    def _build_tab_behavior(self) -> None:
        import i18n
        lay = self._create_scrollable_tab(i18n.tr("settings.tab_behavior"))

        card_beh = QFrame()
        card_beh.setObjectName("card")
        card_beh_lay = QVBoxLayout(card_beh)
        card_beh_lay.setSpacing(10)

        sec_lbl = QLabel("🏃  Bewegung & Interaktion")
        sec_lbl.setObjectName("section")
        card_beh_lay.addWidget(sec_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(30, 300)
        self.speed.setValue(int(self.cfg.get("pet.speed", 90)))
        self.speed_lbl = QLabel()
        form.addRow("Laufgeschwindigkeit:", self._with_label(self.speed, self.speed_lbl, " px/s"))

        # Sprechblasen-Dauer
        self.bubble_slider = QSlider(Qt.Orientation.Horizontal)
        self.bubble_slider.setRange(2, 10)
        self.bubble_slider.setValue(int(float(self.cfg.get("pet.bubble_seconds", 4.0))))
        self.bubble_lbl = QLabel()
        form.addRow(i18n.tr("settings.bubble_seconds"), self._with_label(self.bubble_slider, self.bubble_lbl, " s"))

        self.wander = QCheckBox("Selbstständig auf dem Desktop herumlaufen & dösen")
        self.wander.setChecked(bool(self.cfg.get("pet.wander", True)))
        form.addRow("", self.wander)

        self.chatter = QCheckBox("Gelegentlich etwas sagen (Zwischenrufe & Gedanken)")
        self.chatter.setChecked(bool(self.cfg.get("pet.chatter", True)))
        form.addRow("", self.chatter)

        self.sound_enabled_chk = QCheckBox(i18n.tr("settings.sound_enabled"))
        self.sound_enabled_chk.setChecked(bool(self.cfg.get("pet.sound_enabled", True)))
        form.addRow("", self.sound_enabled_chk)

        fun = self.cfg.get("fun", {}) if isinstance(self.cfg.get("fun"), dict) else {}
        self.pc_fever_chk = QCheckBox("PC-Fieber-Reaktion bei hoher CPU-/RAM-Auslastung")
        self.pc_fever_chk.setChecked(bool(fun.get("pc_fever", True)))
        form.addRow("", self.pc_fever_chk)

        card_beh_lay.addLayout(form)
        lay.addWidget(card_beh)
        lay.addStretch(1)

    # ==================================================================================
    #  Tab 3: 🤖 Gemini-KI & Sprache
    # ==================================================================================
    # ==================================================================================
    #  Tab 3: 🤖 Gemini-KI, Dual-Login & Voice
    # ==================================================================================
    def _build_tab_ai(self) -> None:
        import i18n
        lay = self._create_scrollable_tab(i18n.tr("settings.tab_ai"))

        # Card 1: Gemini KI-Verbindung (Option A & Option C)
        card_ai = QFrame()
        card_ai.setObjectName("card")
        ai_lay = QVBoxLayout(card_ai)
        ai_lay.setSpacing(12)

        sec_lbl = QLabel("🧠  Google Gemini-Konto & Dual-Login (Option A & C)")
        sec_lbl.setObjectName("section")
        ai_lay.addWidget(sec_lbl)

        self.status_lbl = QLabel()
        self.status_lbl.setObjectName("status")
        ai_lay.addWidget(self.status_lbl)

        # -- Option C: 1-Klick Studio Key --
        opt_c_lbl = QLabel("Option C: 1-Klick Studio Key (Empfohlen für schnellen Start)")
        opt_c_lbl.setStyleSheet("font-weight: 600; color: #FF85A2;")
        ai_lay.addWidget(opt_c_lbl)

        steps = QLabel("1. „Gratis-Key holen“ klicken & mit Google-Konto anmelden\n"
                       "2. „Create API key“ wählen & Key kopieren (Free Tier reicht vollkommen aus)\n"
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
        ai_lay.addLayout(btn_box)

        # Trennlinie
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #353842;")
        ai_lay.addWidget(sep)

        # -- Option A: Google OAuth 2.0 Browser-Login --
        opt_a_lbl = QLabel("Option A: Google-Konto Browser-Login (OAuth 2.0)")
        opt_a_lbl.setStyleSheet("font-weight: 600; color: #79D279;")
        ai_lay.addWidget(opt_a_lbl)

        oauth_hint = QLabel("Melde dich mit 1 Klick im Browser mit deinem Google-Konto an.\n"
                            "Lade deine heruntergeladene JSON-Datei oder trage die Client-ID ein:")
        oauth_hint.setObjectName("hint")
        ai_lay.addWidget(oauth_hint)

        import_btn = QPushButton("📁  JSON-Datei importieren (client_secret…)")
        import_btn.clicked.connect(self._on_import_oauth_json)
        ai_lay.addWidget(import_btn)

        oauth_form = QFormLayout()
        oauth_form.setSpacing(8)

        cur_oauth = auth_manager.get_auth_manager().get_oauth_data() or {}
        self.oauth_client_id_edit = QLineEdit(cur_oauth.get("client_id", ""))
        self.oauth_client_id_edit.setPlaceholderText("z. B. 123456...apps.googleusercontent.com")
        oauth_form.addRow("Client-ID:", self.oauth_client_id_edit)

        self.oauth_client_secret_edit = QLineEdit(cur_oauth.get("client_secret", ""))
        self.oauth_client_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.oauth_client_secret_edit.setPlaceholderText("Client-Secret (optional)")
        oauth_form.addRow("Client-Secret:", self.oauth_client_secret_edit)
        ai_lay.addLayout(oauth_form)

        oauth_btn_box = QHBoxLayout()
        oauth_btn_box.setSpacing(10)
        self.oauth_login_btn = QPushButton("Mit Google im Browser anmelden")
        self.oauth_login_btn.setObjectName("primary")
        self.oauth_login_btn.clicked.connect(self._on_oauth_login)
        oauth_btn_box.addWidget(self.oauth_login_btn, 1)

        self.logout_btn = QPushButton("Abmelden / Key löschen")
        self.logout_btn.setObjectName("danger")
        self.logout_btn.clicked.connect(self._on_logout_click)
        oauth_btn_box.addWidget(self.logout_btn)
        ai_lay.addLayout(oauth_btn_box)

        self.ai_enabled = QCheckBox("KI verwenden (Gemini für smarte Befehle, Chat & Sprachinteraktion)")
        self.ai_enabled.setChecked(bool(self.cfg.get("ai.enabled", True)))
        ai_lay.addWidget(self.ai_enabled)

        lay.addWidget(card_ai)

        # Card 2: 🎙️ Sprachausgabe (TTS) & Lip-Sync (v3.0.0)
        card_voice = QFrame()
        card_voice.setObjectName("card")
        card_voice_lay = QVBoxLayout(card_voice)
        card_voice_lay.setSpacing(10)

        voice_sec = QLabel("🎙️  Sprachausgabe (TTS) & Lip-Sync (v3.0.0)")
        voice_sec.setObjectName("section")
        card_voice_lay.addWidget(voice_sec)

        voice_form = QFormLayout()
        voice_form.setSpacing(10)

        v_cfg = self.cfg.get("voice", {}) if isinstance(self.cfg.get("voice"), dict) else {}

        self.voice_enabled_chk = QCheckBox("Antworten mit Stimme vorlesen")
        self.voice_enabled_chk.setChecked(bool(v_cfg.get("enabled", True)))
        voice_form.addRow("", self.voice_enabled_chk)

        self.voice_combo = QComboBox()
        for key, p in voice_tts.VOICE_PRESETS.items():
            self.voice_combo.addItem(p["name"], p["id"])

        cur_voice = str(v_cfg.get("name", "de-DE-KatjaNeural"))
        idx = self.voice_combo.findData(cur_voice)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)
        voice_form.addRow("Stimme / Persona:", self.voice_combo)

        # Kawaii Pitch Slider (+0% bis +40%)
        cur_pitch_str = str(v_cfg.get("pitch", "+20%")).replace("+", "").replace("%", "").strip()
        try:
            cur_pitch_val = int(cur_pitch_str)
        except ValueError:
            cur_pitch_val = 20

        self.voice_pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.voice_pitch_slider.setRange(0, 40)
        self.voice_pitch_slider.setValue(cur_pitch_val)
        self.voice_pitch_lbl = QLabel()
        voice_form.addRow("Niedliche Tonhöhe (Kawaii Pitch):", self._with_label(self.voice_pitch_slider, self.voice_pitch_lbl, " %"))

        self.lipsync_chk = QCheckBox("Mundbewegungen (Lip-Sync) synchron beim Sprechen animieren")
        self.lipsync_chk.setChecked(bool(v_cfg.get("lipsync", True)))
        voice_form.addRow("", self.lipsync_chk)

        self.voice_online_chk = QCheckBox("Natürliche Online-Stimme (Microsoft Edge)")
        self.voice_online_chk.setToolTip("Klingt natürlicher, schickt aber jeden vorgelesenen Text an einen Microsoft-Dienst.\n"
                                         "Aus = eingebaute Windows-Stimme, alles bleibt auf deinem PC.")
        self.voice_online_chk.setChecked(bool(v_cfg.get("online", False)))
        voice_form.addRow("", self.voice_online_chk)

        card_voice_lay.addLayout(voice_form)
        lay.addWidget(card_voice)

        # Card 3: Sprache & Persona
        card_lang = QFrame()
        card_lang.setObjectName("card")
        card_lang_lay = QVBoxLayout(card_lang)
        card_lang_lay.setSpacing(10)

        lang_sec = QLabel("🗣️  Sprache & Anrede")
        lang_sec.setObjectName("section")
        card_lang_lay.addWidget(lang_sec)

        form = QFormLayout()
        form.setSpacing(10)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Deutsch", "de")
        self.lang_combo.addItem("English", "en")
        cur_lang = str(self.cfg.get("language", "de")).lower()
        self.lang_combo.setCurrentIndex(1 if cur_lang.startswith("en") else 0)
        form.addRow("Sprache / Language:", self.lang_combo)

        self.user_name_edit = QLineEdit(str(self.cfg.get("pet.user_name", "Boss")))
        self.user_name_edit.setPlaceholderText("Boss (Standard)")
        form.addRow("Dein Name / Anrede:", self.user_name_edit)

        card_lang_lay.addLayout(form)
        lay.addWidget(card_lang)
        lay.addStretch(1)

    # ==================================================================================
    #  Tab 4: 🌿 Wohlbefinden & Alltag
    # ==================================================================================
    def _build_tab_wellbeing(self) -> None:
        import i18n
        lay = self._create_scrollable_tab(i18n.tr("settings.tab_wellbeing"))

        card = QFrame()
        card.setObjectName("card")
        card_lay = QVBoxLayout(card)
        card_lay.setSpacing(10)

        sec_lbl = QLabel("💧  Gesundheit, Pausen & Erinnerungen")
        sec_lbl.setObjectName("section")
        card_lay.addWidget(sec_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        self.breaks = QCheckBox("Erinnerung: kurz strecken & Augen entspannen")
        self.breaks.setChecked(bool(self.cfg.get("wellbeing.breaks", True)))
        form.addRow("", self.breaks)

        self.water = QCheckBox("Erinnerung: Schluck Wasser trinken")
        self.water.setChecked(bool(self.cfg.get("wellbeing.water", True)))
        form.addRow("", self.water)

        self.break_min = QSlider(Qt.Orientation.Horizontal)
        self.break_min.setRange(10, 180)
        self.break_min.setValue(int(self.cfg.get("wellbeing.break_min", 60)))
        self.break_min_lbl = QLabel()
        form.addRow("Erinnerungs-Intervall:", self._with_label(self.break_min, self.break_min_lbl, " Min."))

        self.battery_warn = QCheckBox("Akku-Warnung unter 15 % anzeigen")
        self.battery_warn.setChecked(bool(self.cfg.get("battery_warn", True)))
        form.addRow("", self.battery_warn)

        self.night_mode = QCheckBox("Nachtmodus (23–7 Uhr: ruhig, schläfrig & unaufdringlich)")
        self.night_mode.setChecked(bool(self.cfg.get("night_mode", True)))
        form.addRow("", self.night_mode)

        daily = self.cfg.get("daily", {}) if isinstance(self.cfg.get("daily"), dict) else {}
        self.briefing_chk = QCheckBox("Guten-Morgen-Briefing beim ersten Tagesstart")
        self.briefing_chk.setChecked(bool(daily.get("briefing", True)))
        form.addRow("", self.briefing_chk)

        self.curious_chk = QCheckBox("Gelegentlich neugierige Alltags-Fragen stellen")
        self.curious_chk.setChecked(bool(daily.get("curious", True)))
        form.addRow("", self.curious_chk)

        self.bedtime_edit = QLineEdit(str(daily.get("bedtime", "23:00")))
        self.bedtime_edit.setPlaceholderText("z. B. 23:00 (leer = aus)")
        form.addRow("Schlafenszeit:", self.bedtime_edit)

        card_lay.addLayout(form)
        lay.addWidget(card)
        lay.addStretch(1)

    # ==================================================================================
    #  Tab 5: ⚙️ System & Hotkeys
    # ==================================================================================
    def _build_tab_system(self) -> None:
        import i18n
        lay = self._create_scrollable_tab(i18n.tr("settings.tab_system"))

        card_sys = QFrame()
        card_sys.setObjectName("card")
        card_sys_lay = QVBoxLayout(card_sys)
        card_sys_lay.setSpacing(10)

        sec_lbl = QLabel("💻  System & Startverhalten")
        sec_lbl.setObjectName("section")
        card_sys_lay.addWidget(sec_lbl)

        form_sys = QFormLayout()
        form_sys.setSpacing(10)

        self.autostart = QCheckBox("Automatisch mit Windows starten")
        self.autostart.setChecked(bool(self.cfg.get("autostart", True)))
        form_sys.addRow("", self.autostart)

        self.auto_update = QCheckBox("Automatisch nach neuen Updates suchen")
        self.auto_update.setChecked(bool(self.cfg.get("update.auto", True)))
        form_sys.addRow("", self.auto_update)

        self.always_on_top_chk = QCheckBox(i18n.tr("settings.always_on_top"))
        self.always_on_top_chk.setChecked(bool(self.cfg.get("pet.always_on_top", True)))
        form_sys.addRow("", self.always_on_top_chk)

        card_sys_lay.addLayout(form_sys)
        lay.addWidget(card_sys)

        # Card: Tastenkürzel
        card_keys = QFrame()
        card_keys.setObjectName("card")
        card_keys_lay = QVBoxLayout(card_keys)
        card_keys_lay.setSpacing(10)

        keys_lbl = QLabel("⌨️  Globale Tastenkürzel (Hotkeys)")
        keys_lbl.setObjectName("section")
        card_keys_lay.addWidget(keys_lbl)

        form_keys = QFormLayout()
        form_keys.setSpacing(10)

        self.hotkey_edit = QLineEdit(str(self.cfg.get("hotkey", "ctrl+alt+p")))
        self.hotkey_edit.setPlaceholderText("z. B. ctrl+alt+p")
        form_keys.addRow("Befehlseingabe / Katze rufen:", self.hotkey_edit)

        self.hotkey_explain_edit = QLineEdit(str(self.cfg.get("hotkey_explain", "ctrl+alt+e")))
        self.hotkey_explain_edit.setPlaceholderText("z. B. ctrl+alt+e")
        form_keys.addRow("Kopieren & Erklären:", self.hotkey_explain_edit)

        self.hotkey_voice_edit = QLineEdit(str(self.cfg.get("hotkey_voice", "ctrl+alt+space")))
        self.hotkey_voice_edit.setPlaceholderText("z. B. ctrl+alt+space")
        form_keys.addRow("Push-to-Talk (Sprechen & Zuhören):", self.hotkey_voice_edit)

        card_keys_lay.addLayout(form_keys)

        self.hotkey_hint = QLabel("Format: ctrl / alt / shift / win + Taste, z. B. ctrl+alt+p, ctrl+alt+e oder ctrl+alt+space")
        self.hotkey_hint.setObjectName("hint")
        card_keys_lay.addWidget(self.hotkey_hint)

        lay.addWidget(card_keys)

        # Card: Schnelle Aktionen (z. B. Katze ausblenden)
        card_act = QFrame()
        card_act.setObjectName("card")
        card_act_lay = QVBoxLayout(card_act)
        card_act_lay.setSpacing(8)

        act_lbl = QLabel("⚡  Schnell-Aktionen")
        act_lbl.setObjectName("section")
        card_act_lay.addWidget(act_lbl)

        hide_btn = QPushButton(i18n.tr("settings.hide_pet_btn"))
        hide_btn.setObjectName("hide_btn")
        hide_btn.clicked.connect(self._on_hide_pet_click)
        card_act_lay.addWidget(hide_btn)

        hide_hint = QLabel("Tipp: Du kannst die Katze jederzeit per Klick auf das Taskleisten-Icon oder per Tastenkürzel wieder aufwecken.")
        hide_hint.setObjectName("hint")
        hide_hint.setWordWrap(True)
        card_act_lay.addWidget(hide_hint)

        lay.addWidget(card_act)
        lay.addStretch(1)

    def _on_hide_pet_click(self) -> None:
        self.hide_pet_requested.emit()
        self.accept()

    # ==================================================================================
    #  Auth & Key Handling (Dual-Login Option A & C)
    # ==================================================================================
    def _set_status(self, text: str, color: str) -> None:
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {color};")

    def _refresh_auth_ui(self) -> None:
        mode = auth_manager.get_auth_manager().get_auth_mode()
        if mode == "oauth":
            self._set_status("🟢  Angemeldet mit Google-Konto (OAuth 2.0)", "#79D279")
            self.logout_btn.setVisible(True)
        elif mode == "apikey":
            self._set_status("🟢  Verbunden mit Google AI Studio Key (Option C)", "#79D279")
            self.logout_btn.setVisible(True)
        else:
            self._set_status("⚪  Offline-Modus (Noch kein Account oder Key verbunden)", "#A0A5B5")
            self.logout_btn.setVisible(False)

    def _on_save_key(self) -> None:
        key = self.key_edit.text().strip()
        self._set_status("🔄  Prüfe Key…", "#8D919B")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            gemini.validate_key(key)
            gemini.save_key(key)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"❌  {exc}", "#FF8F8F")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.key_edit.clear()
        self._refresh_auth_ui()
        parent = self.parent()
        if parent and hasattr(parent, "celebrate"):
            parent.celebrate()

    def _on_import_oauth_json(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "client_secret.json auswählen", "", "JSON-Dateien (*.json);;Alle Dateien (*.*)"
        )
        if not file_path:
            return
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            client_info = data.get("installed") or data.get("web") or data
            cid = str(client_info.get("client_id", "")).strip()
            sec = str(client_info.get("client_secret", "")).strip()
            if cid:
                self.oauth_client_id_edit.setText(cid)
            if sec:
                self.oauth_client_secret_edit.setText(sec)
            self._set_status("✅  Client-ID aus JSON erfolgreich geladen!", "#79D279")
        except Exception as exc:
            self._set_status(f"❌  Fehler beim Lesen der JSON-Datei: {exc}", "#FF8F8F")

    def _on_oauth_login(self) -> None:
        cid = self.oauth_client_id_edit.text().strip()
        sec = self.oauth_client_secret_edit.text().strip()
        if not cid:
            self._set_status("❌  Bitte zuerst eine Google Client-ID eingeben (oder Option C nutzen)", "#FF8F8F")
            return

        self._set_status("🌐  Browser wird geöffnet… Bitte dort anmelden & Zugriff erlauben", "#FFD24D")
        self.oauth_login_btn.setEnabled(False)

        def _on_success():
            QApplication.instance().postEvent(self, _OAuthCustomEvent(True))

        def _on_err(err_msg: str):
            QApplication.instance().postEvent(self, _OAuthCustomEvent(False, err_msg))

        auth_manager.get_auth_manager().start_oauth_flow_async(
            client_id=cid,
            client_secret=sec,
            on_success=_on_success,
            on_error=_on_err,
        )

    def customEvent(self, event) -> None:
        if isinstance(event, _OAuthCustomEvent):
            self.oauth_login_btn.setEnabled(True)
            if event.success:
                self._refresh_auth_ui()
                parent = self.parent()
                if parent and hasattr(parent, "celebrate"):
                    parent.celebrate()
            else:
                self._set_status(f"❌  Anmeldung fehlgeschlagen: {event.error}", "#FF8F8F")

    def _on_logout_click(self) -> None:
        gemini.clear_key()
        self._refresh_auth_ui()

    def _open_cfg(self) -> None:
        try:
            os.startfile(str(self.cfg.path))  # type: ignore[attr-defined]
        except OSError:
            pass

    def _open_my_data(self) -> None:
        from my_data_dialog import MyDataDialog
        dlg = MyDataDialog(self.cfg, parent=self)
        dlg.exec()

    # ==================================================================================
    #  Speichern
    # ==================================================================================
    def _save(self) -> None:
        c = self.cfg
        hotkey = self.hotkey_edit.text().strip().lower()
        if not self._hotkey_ok(hotkey):
            self.hotkey_hint.setText("❌  Ungültiges Tastenkürzel – Beispiel: ctrl+alt+p")
            self.hotkey_hint.setStyleSheet("color: #FF8F8F;")
            self.tabs.setCurrentIndex(4)  # springe zum System-Tab
            return
        hotkey_ex = self.hotkey_explain_edit.text().strip().lower()
        if not self._hotkey_ok(hotkey_ex):
            self.hotkey_hint.setText("❌  Ungültiges Tastenkürzel für Kopieren & Erklären – Beispiel: ctrl+alt+e")
            self.hotkey_hint.setStyleSheet("color: #FF8F8F;")
            self.tabs.setCurrentIndex(4)
            return
        hotkey_voice = self.hotkey_voice_edit.text().strip().lower()
        if not self._hotkey_ok(hotkey_voice):
            self.hotkey_hint.setText("❌  Ungültiges Tastenkürzel für Push-to-Talk – Beispiel: ctrl+alt+space")
            self.hotkey_hint.setStyleSheet("color: #FF8F8F;")
            self.tabs.setCurrentIndex(4)
            return

        c.set("hotkey", hotkey)
        c.set("hotkey_explain", hotkey_ex)
        c.set("hotkey_voice", hotkey_voice)

        # Voice & Lip-Sync Einstellungen
        c.set("voice.enabled", self.voice_enabled_chk.isChecked())
        c.set("voice.online", self.voice_online_chk.isChecked())
        c.set("voice.name", str(self.voice_combo.currentData() or "de-DE-KatjaNeural"))
        c.set("voice.pitch", f"+{self.voice_pitch_slider.value()}%")
        c.set("voice.lipsync", self.lipsync_chk.isChecked())

        char = self.char_combo.currentData()
        if char:
            c.set("pet.character", str(char))

        worn = self.worn_combo.currentData()
        c.set("fun.worn", str(worn or ""))

        cur_lang = self.lang_combo.currentData() or "de"
        c.set("language", cur_lang)
        import i18n
        i18n.set_language(cur_lang)

        c.set("pet.user_name", self.user_name_edit.text().strip() or "Boss")
        c.set("pet.opacity", self.opacity_slider.value() / 100.0)
        c.set("pet.scale", self.scale.value() / 100.0)
        c.set("pet.speed", self.speed.value())
        c.set("pet.wander", self.wander.isChecked())
        c.set("pet.chatter", self.chatter.isChecked())
        c.set("pet.bubble_seconds", float(self.bubble_slider.value()))
        c.set("pet.sound_enabled", self.sound_enabled_chk.isChecked())
        c.set("pet.always_on_top", self.always_on_top_chk.isChecked())

        c.set("fun.weather_outfits", self.weather_outfits_chk.isChecked())
        c.set("fun.pc_fever", self.pc_fever_chk.isChecked())
        c.set("ai.enabled", self.ai_enabled.isChecked())

        c.set("wellbeing.breaks", self.breaks.isChecked())
        c.set("wellbeing.water", self.water.isChecked())
        c.set("wellbeing.break_min", self.break_min.value())
        c.set("battery_warn", self.battery_warn.isChecked())
        c.set("night_mode", self.night_mode.isChecked())

        c.set("daily.briefing", self.briefing_chk.isChecked())
        c.set("daily.curious", self.curious_chk.isChecked())
        c.set("daily.bedtime", self.bedtime_edit.text().strip())

        c.set("autostart", self.autostart.isChecked())
        set_autostart(self.autostart.isChecked())
        c.set("update.auto", self.auto_update.isChecked())

        c.save()
        self.accept()
