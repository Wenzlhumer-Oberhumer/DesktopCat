# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Dialog für Eigene Python-Skripte & Routinen (v2.5.0).

Bietet eine übersichtliche Oberfläche zum Erstellen, Bearbeiten,
Testen und Planen von autonomen Skripten und Alltagsroutinen.
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

import custom_scripts

_RUNNING: list = []      # haelt laufende Worker fest, auch wenn der Dialog geschlossen wird


class _RunWorker(QThread):
    done = pyqtSignal(dict)

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def run(self) -> None:
        self.done.emit(custom_scripts.run_script(self.name))


SCHEDULE_OPTIONS = [
    ("manual", "🖐️ Nur manuell"),
    ("startup", "🚀 Beim Start von Desktop Cat"),
    ("daily_09:00", "⏰ Täglich um 09:00 Uhr"),
    ("daily_12:00", "☀️ Täglich um 12:00 Uhr"),
    ("daily_15:00", "☕ Täglich um 15:00 Uhr"),
    ("daily_18:00", "🌆 Täglich um 18:00 Uhr"),
    ("daily_21:00", "🌙 Täglich um 21:00 Uhr"),
    ("interval_30m", "⏳ Alle 30 Minuten"),
    ("interval_60m", "⏳ Jede Stunde (60 Min)"),
    ("interval_120m", "⏳ Alle 2 Stunden (120 Min)"),
]


class CustomScriptsDialog(QDialog):
    """Verwaltungs- und Editor-Dialog für Skripte & Routinen."""

    script_executed = pyqtSignal(str, str)   # script_name, stdout

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("🤖 Eigene Python-Skripte & Routinen")
        self.setMinimumSize(860, 600)
        self.resize(920, 640)

        self._current_script_name: Optional[str] = None

        self._setup_style()
        self._setup_ui()
        self._load_scripts_list()

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #202226;
                color: #F2F3F5;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
            QLabel {
                color: #F2F3F5;
            }
            QListWidget {
                background-color: #26282E;
                border: 1px solid #363940;
                border-radius: 8px;
                color: #F2F3F5;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 6px;
                margin-bottom: 3px;
            }
            QListWidget::item:selected {
                background-color: #FF8FB1;
                color: #202226;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #26282E;
                border: 1px solid #3A3D46;
                border-radius: 6px;
                color: #F2F3F5;
                padding: 6px 10px;
                font-size: 9pt;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #FF8FB1;
            }
            QPlainTextEdit {
                background-color: #1A1C20;
                border: 1px solid #363940;
                border-radius: 8px;
                color: #79C0FF;
                padding: 8px;
                selection-background-color: #388BFD;
            }
            QTextEdit {
                background-color: #121316;
                border: 1px solid #2D3037;
                border-radius: 6px;
                color: #A6E22E;
                padding: 6px;
            }
            QPushButton {
                background-color: #363942;
                color: #F2F3F5;
                border: none;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #454954;
            }
            QPushButton#btnRun {
                background-color: #4ECCA3;
                color: #121316;
            }
            QPushButton#btnRun:hover {
                background-color: #5FE2B7;
            }
            QPushButton#btnSave {
                background-color: #FF8FB1;
                color: #202226;
            }
            QPushButton#btnSave:hover {
                background-color: #FFA5C0;
            }
            QPushButton#btnDelete {
                background-color: #4A282D;
                color: #FF7B89;
            }
            QPushButton#btnDelete:hover {
                background-color: #633238;
            }
            QCheckBox {
                color: #F2F3F5;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Header
        top_bar = QHBoxLayout()
        lbl_head = QLabel("🤖 Eigene Python-Skripte & Alltags-Routinen")
        lbl_head.setStyleSheet("font-size: 13pt; font-weight: bold; color: #FF8FB1;")
        lbl_sub = QLabel("Desktop Cat kann eigene Skripte schreiben, testen und automatisch als Routine ausführen.")
        lbl_sub.setStyleSheet("color: #8D919B; font-size: 8.5pt;")

        head_v = QVBoxLayout()
        head_v.addWidget(lbl_head)
        head_v.addWidget(lbl_sub)
        top_bar.addLayout(head_v)
        top_bar.addStretch()

        btn_open_folder = QPushButton("📂 Skript-Ordner")
        btn_open_folder.clicked.connect(self._on_open_folder)
        top_bar.addWidget(btn_open_folder)

        main_layout.addLayout(top_bar)

        # Splitter: Links Liste, Rechts Editor & Konsole
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Linker Bereich
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        left_lbl = QLabel("Deine Skripte:")
        left_lbl.setStyleSheet("font-weight: bold; color: #A0A5B0;")
        left_layout.addWidget(left_lbl)

        self.list_scripts = QListWidget()
        self.list_scripts.itemClicked.connect(self._on_item_clicked)
        left_layout.addWidget(self.list_scripts, 1)

        btn_new = QPushButton("➕ Neues Skript")
        btn_new.clicked.connect(self._on_new_script)
        left_layout.addWidget(btn_new)

        splitter.addWidget(left_widget)

        # Rechter Bereich
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(8)

        # Metadaten-Zeile
        meta_grid = QHBoxLayout()
        meta_grid.setSpacing(8)

        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Titel des Skripts (z. B. Morgen-Routine)")
        meta_grid.addWidget(self.edit_title, 2)

        self.edit_filename = QLineEdit()
        self.edit_filename.setPlaceholderText("Dateiname.py")
        meta_grid.addWidget(self.edit_filename, 1)

        right_layout.addLayout(meta_grid)

        # Zeitplan & Routine-Zeile
        schedule_bar = QHBoxLayout()
        schedule_bar.setSpacing(8)

        lbl_sched = QLabel("Ausführen:")
        lbl_sched.setStyleSheet("color: #A0A5B0; font-size: 8.5pt;")
        schedule_bar.addWidget(lbl_sched)

        self.combo_schedule = QComboBox()
        for key, text in SCHEDULE_OPTIONS:
            self.combo_schedule.addItem(text, key)
        schedule_bar.addWidget(self.combo_schedule, 1)

        self.chk_enabled = QCheckBox("Aktiv")
        self.chk_enabled.setChecked(True)
        schedule_bar.addWidget(self.chk_enabled)

        right_layout.addLayout(schedule_bar)

        # Code-Editor
        code_lbl = QLabel("Python-Code:")
        code_lbl.setStyleSheet("color: #A0A5B0; font-size: 8.5pt;")
        right_layout.addWidget(code_lbl)

        self.code_edit = QPlainTextEdit()
        font = QFont("Consolas, Courier New, monospace", 10)
        self.code_edit.setFont(font)
        self.code_edit.setTabStopDistance(self.code_edit.fontMetrics().horizontalAdvance(" ") * 4)
        right_layout.addWidget(self.code_edit, 3)

        # Aktions-Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_run = QPushButton("▶ Jetzt ausführen")
        self.btn_run.setObjectName("btnRun")
        self.btn_run.clicked.connect(self._on_run_script)
        btn_bar.addWidget(self.btn_run)

        self.btn_save = QPushButton("💾 Speichern & freigeben")
        self.btn_save.setToolTip("Erst nach dem Freigeben darf das Skript laufen oder als Routine starten.")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self._on_save_script)
        btn_bar.addWidget(self.btn_save)

        self.btn_delete = QPushButton("🗑️ Löschen")
        self.btn_delete.setObjectName("btnDelete")
        self.btn_delete.clicked.connect(self._on_delete_script)
        btn_bar.addWidget(self.btn_delete)

        btn_bar.addStretch()
        right_layout.addLayout(btn_bar)

        # Konsole / Ausgaben
        out_lbl = QLabel("Ausgabe & Terminal-Log:")
        out_lbl.setStyleSheet("color: #A0A5B0; font-size: 8.5pt;")
        right_layout.addWidget(out_lbl)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(font)
        self.console_output.setMaximumHeight(140)
        right_layout.addWidget(self.console_output, 1)

        splitter.addWidget(right_widget)
        splitter.setSizes([260, 600])

        main_layout.addWidget(splitter, 1)

        # Fußleiste
        foot = QHBoxLayout()
        self.lbl_status = QLabel("Bereit.")
        self.lbl_status.setStyleSheet("color: #8D919B; font-size: 8pt;")
        foot.addWidget(self.lbl_status)
        foot.addStretch()

        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(100)
        foot.addWidget(btn_close)

        main_layout.addLayout(foot)

    def _load_scripts_list(self) -> None:
        self.list_scripts.clear()
        scripts = custom_scripts.list_scripts()

        for s in scripts:
            name = s.get("name", "unbekannt.py")
            title = s.get("title") or name
            sched = s.get("schedule", "manual")
            enabled = s.get("enabled", True)

            sched_badge = "🖐️"
            if sched == "startup":
                sched_badge = "🚀"
            elif sched.startswith("daily_"):
                sched_badge = "⏰ " + sched.replace("daily_", "")
            elif sched.startswith("interval_"):
                sched_badge = "⏳ " + sched.replace("interval_", "")

            status_sym = "●" if enabled else "○"
            lock = "" if custom_scripts.is_approved(s) else "  🔒 noch nicht freigegeben"
            item_text = f"{status_sym} {title}{lock}\n    {sched_badge} ({name})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, name)
            if not enabled:
                item.setForeground(QColor(140, 145, 155))
            self.list_scripts.addItem(item)

        if self.list_scripts.count() > 0:
            target_idx = 0
            if self._current_script_name:
                for i in range(self.list_scripts.count()):
                    if self.list_scripts.item(i).data(Qt.ItemDataRole.UserRole) == self._current_script_name:
                        target_idx = i
                        break
            self.list_scripts.setCurrentRow(target_idx)
            self._on_item_clicked(self.list_scripts.item(target_idx))
        else:
            self._on_new_script()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        data = custom_scripts.get_script(name)
        if not data:
            return

        self._current_script_name = name
        self.edit_filename.setText(name)
        self.edit_title.setText(data.get("title", ""))
        self.chk_enabled.setChecked(bool(data.get("enabled", True)))
        self.code_edit.setPlainText(data.get("code", ""))

        target_sched = data.get("schedule", "manual")
        idx = self.combo_schedule.findData(target_sched)
        if idx >= 0:
            self.combo_schedule.setCurrentIndex(idx)
        else:
            self.combo_schedule.setCurrentIndex(0)

        last_res = data.get("last_result")
        if last_res:
            ok = last_res.get("ok", True)
            summary = last_res.get("summary", "")
            dur = last_res.get("duration_s", 0.0)
            status_text = f"Zuletzt ausgeführt ({dur}s): {'✅ Erfolgreich' if ok else '❌ Fehler'}\n{summary}"
            self.console_output.setPlainText(status_text)
        else:
            self.console_output.clear()

        self.lbl_status.setText(f"Geladen: {name}")

    def _on_new_script(self) -> None:
        self._current_script_name = None
        self.edit_filename.setText("mein_skript.py")
        self.edit_title.setText("Neues Skript")
        self.chk_enabled.setChecked(True)
        self.combo_schedule.setCurrentIndex(0)
        template = '''# Neues Skript für Desktop Cat 🐾
import sys

def main():
    print("Hallo! Mein Skript läuft erfolgreich! 🐾✨")

if __name__ == "__main__":
    main()
'''
        self.code_edit.setPlainText(template)
        self.console_output.clear()
        self.lbl_status.setText("Neues Skript vorbereitet.")

    def _on_save_script(self) -> None:
        name = self.edit_filename.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte einen Dateinamen angeben!")
            return
        if not name.endswith(".py"):
            name += ".py"

        title = self.edit_title.text().strip() or name[:-3]
        code = self.code_edit.toPlainText()
        schedule = self.combo_schedule.currentData() or "manual"
        enabled = self.chk_enabled.isChecked()

        ok, msg, meta = custom_scripts.save_script(
            name=name,
            code=code,
            title=title,
            schedule=schedule,
            enabled=enabled,
            approved=True,          # der Nutzer hat den Code hier vor sich und speichert ihn bewusst
        )

        if not ok:
            QMessageBox.critical(self, "Syntax- oder Speicherfehler", msg)
            return

        self._current_script_name = name
        self.lbl_status.setText(f"✅ {msg}")
        self._load_scripts_list()

    def _on_delete_script(self) -> None:
        if not self._current_script_name:
            return
        res = QMessageBox.question(
            self,
            "Skript löschen",
            f"Möchtest du das Skript '{self._current_script_name}' wirklich unwiderruflich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            custom_scripts.delete_script(self._current_script_name)
            self._current_script_name = None
            self._load_scripts_list()

    def _on_run_script(self) -> None:
        # Erst automatisch speichern
        self._on_save_script()
        if not self._current_script_name:
            return

        self.btn_run.setEnabled(False)
        self.lbl_status.setText(f"Führe {self._current_script_name} aus...")
        self.console_output.setPlainText("Ausführung gestartet...\n")

        self._run_worker = _RunWorker(self._current_script_name)     # bis 30 s - nicht im UI-Thread
        self._run_worker.done.connect(self._on_run_done)
        _RUNNING[:] = [w for w in _RUNNING if not w.isFinished()] + [self._run_worker]
        self._run_worker.start()

    def _on_run_done(self, res: dict) -> None:
        self.btn_run.setEnabled(True)

        ok = res["ok"]
        dur = res["duration_s"]
        stdout = res["stdout"]
        stderr = res["stderr"]

        log_lines = []
        if stdout:
            log_lines.append(stdout)
        if stderr:
            log_lines.append(f"[STDERR / Fehler]\n{stderr}")
        log_lines.append(f"\n--- Beendet mit Code {res['exit_code']} in {dur}s ({'OK ✅' if ok else 'FEHLER ❌'}) ---")

        self.console_output.setPlainText("\n".join(log_lines))
        self.lbl_status.setText(f"{'✅ Erfolgreich' if ok else '❌ Fehlgeschlagen'} in {dur}s")

        self.script_executed.emit(self._current_script_name, stdout or stderr)

    def _on_open_folder(self) -> None:
        scripts_dir = custom_scripts.get_scripts_dir()
        try:
            if os.name == "nt":
                os.startfile(str(scripts_dir))
            else:
                subprocess.Popen(["xdg-open", str(scripts_dir)])
        except Exception as exc:
            QMessageBox.information(self, "Skript-Ordner", f"Pfad:\n{scripts_dir}\n\nFehler beim Öffnen: {exc}")
