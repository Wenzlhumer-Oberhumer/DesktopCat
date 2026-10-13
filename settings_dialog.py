"""Einstellungsdialog (Dark-Mode) - speichert direkt in config.json."""
from __future__ import annotations

import os
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QVBoxLayout, QWidget,
)

import gemini_cli
from paths import set_autostart

STYLE = """
QDialog { background: #26282C; }
QLabel { color: #F2F3F5; font: 10pt "Segoe UI"; }
QLabel#title { font: 600 15pt "Segoe UI"; color: #FF8FB1; }
QLabel#section { font: 600 11pt "Segoe UI"; color: #FFB3C6; margin-top: 6px; }
QLabel#hint { color: #8D919B; font: 9pt "Segoe UI"; }
QLabel#status { font: 10pt "Segoe UI"; font-weight: bold; }
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
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._login_proc = None
        self._login_start_time = 0.0

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
        sec_ai = QLabel("Gemini-Konto")
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

        # Buttons (Login & Logout)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        self.login_btn = QPushButton("Mit Google anmelden")
        self.login_btn.setObjectName("google")
        self.login_btn.clicked.connect(self._on_login_click)
        btn_box.addWidget(self.login_btn, 1)

        self.logout_btn = QPushButton("Abmelden")
        self.logout_btn.setObjectName("danger")
        self.logout_btn.clicked.connect(self._on_logout_click)
        btn_box.addWidget(self.logout_btn)
        ai_lay.addLayout(btn_box)

        # Checkbox KI verwenden
        self.ai_enabled = QCheckBox("KI verwenden (Gemini)")
        self.ai_enabled.setChecked(bool(cfg.get("ai.enabled", True)))
        ai_lay.addWidget(self.ai_enabled)

        root.addWidget(ai_box)

        hint = QLabel("Mochi nutzt die offizielle Gemini CLI \u00fcber dein Google-Konto. "
                      "Ohne Anmeldung arbeitet er im Offline-Modus.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # -- Katze / Verhalten --------------------------------------------------------
        sec_pet = QLabel("Verhalten & Aussehen")
        sec_pet.setObjectName("section")
        root.addWidget(sec_pet)

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

        self.autostart = QCheckBox("Mit Windows starten")
        self.autostart.setChecked(bool(cfg.get("autostart", True)))
        form2.addRow("", self.autostart)
        root.addLayout(form2)

        hk = QLabel(f"Tastenk\u00fcrzel zum Eingeben: {str(cfg.get('hotkey', 'ctrl+alt+p')).upper()} "
                    "(\u00e4nderbar in config.json, Neustart n\u00f6tig)")
        hk.setObjectName("hint")
        root.addWidget(hk)

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

        # Timer fuer Login-Polling
        self._login_timer = QTimer(self)
        self._login_timer.setInterval(1000)
        self._login_timer.timeout.connect(self._poll_login)

        self._refresh_auth_ui()

    def _refresh_auth_ui(self) -> None:
        cmd = gemini_cli.cli_command()
        if not cmd:
            self.status_lbl.setText("\u26a0\ufe0f  Gemini-Komponente fehlt (Node/CLI nicht gefunden)")
            self.status_lbl.setStyleSheet("color: #FFB347;")
            self.login_btn.setEnabled(False)
            self.logout_btn.setVisible(False)
            return

        if gemini_cli.is_logged_in():
            email = gemini_cli.get_logged_in_email()
            account_text = f" ({email})" if email else ""
            self.status_lbl.setText(f"\u2705  Angemeldet{account_text}")
            self.status_lbl.setStyleSheet("color: #79D279;")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Konto wechseln")
            self.logout_btn.setVisible(True)
        else:
            self.status_lbl.setText("\u274c  Nicht angemeldet")
            self.status_lbl.setStyleSheet("color: #FF8F8F;")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Mit Google anmelden")
            self.logout_btn.setVisible(False)

    def _on_login_click(self) -> None:
        try:
            self._login_proc = gemini_cli.start_login()
            self._login_start_time = time.time()
            self.login_btn.setEnabled(False)
            self.login_btn.setText("Warte auf Browser-Login\u2026")
            self.status_lbl.setText("\U0001f504  Bitte im ge\u00f6ffneten Browser anmelden\u2026")
            self.status_lbl.setStyleSheet("color: #8D919B;")
            self._login_timer.start()
        except Exception as exc:
            self.status_lbl.setText(f"\u274c  Login-Fehler: {exc}")
            self.status_lbl.setStyleSheet("color: #FF8F8F;")

    def _poll_login(self) -> None:
        if gemini_cli.is_logged_in():
            self._login_timer.stop()
            if self._login_proc:
                try:
                    self._login_proc.terminate()
                except Exception:
                    pass
                self._login_proc = None
            self._refresh_auth_ui()
            # Wenn das Hauptfenster verfuegbar ist, Mochi sprechen lassen
            parent = self.parent()
            if parent and hasattr(parent, "celebrate"):
                try:
                    parent.celebrate()
                except Exception:
                    pass
            return

        # Pruefen, ob der Konsolenprozess vorzeitig geschlossen wurde
        if self._login_proc and self._login_proc.poll() is not None:
            self._login_timer.stop()
            self._login_proc = None
            self.status_lbl.setText("\u274c  Anmeldung abgebrochen")
            self.status_lbl.setStyleSheet("color: #FF8F8F;")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Mit Google anmelden")
            return

        # 5 Minuten Timeout
        if time.time() - self._login_start_time > 300:
            self._login_timer.stop()
            if self._login_proc:
                try:
                    self._login_proc.terminate()
                except Exception:
                    pass
                self._login_proc = None
            self.status_lbl.setText("\u274c  Zeit\u00fcberschreitung beim Login")
            self.status_lbl.setStyleSheet("color: #FF8F8F;")
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Mit Google anmelden")

    def _on_logout_click(self) -> None:
        gemini_cli.logout()
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
        c.set("ai.enabled", self.ai_enabled.isChecked())
        c.set("pet.speed", self.speed.value())
        c.set("pet.scale", self.scale.value() / 100.0)
        c.set("pet.wander", self.wander.isChecked())
        c.set("pet.chatter", self.chatter.isChecked())
        c.set("autostart", self.autostart.isChecked())
        set_autostart(self.autostart.isChecked())
        c.save()
        self.accept()
