# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Charakter-Baum & Tamagotchi-Care Dialog (Gamification).

Zeigt:
1. Freundschafts-Level & Fortschritt
2. Tamagotchi-Werte (Hunger 🥣, Sauberkeit 🧼, Laune 💖) mit Schnellaktionen (Füttern, Waschen, Streicheln)
3. 8-stufigen Charakter-Freischalt-Baum für alle 15 Tiere und Wesen.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from fun import LEVEL_NAMES, LEVEL_THRESHOLDS, level_for
from i18n import tr
import pet_care
from pet_sprites import CHARACTERS, get_character_info
from settings_dialog import STYLE

CARE_DIALOG_STYLE = STYLE + """
QProgressBar {
    background-color: #2D3036;
    border: 1px solid #484B54;
    border-radius: 6px;
    height: 16px;
    text-align: center;
    color: #F2F3F5;
    font-size: 8pt;
    font-weight: bold;
}
QProgressBar::chunk {
    border-radius: 5px;
}
QFrame#tierCard {
    background-color: #26282E;
    border: 1px solid #3A3D46;
    border-radius: 10px;
    padding: 10px;
}
QFrame#charCard {
    background-color: #2D3036;
    border: 1px solid #424650;
    border-radius: 8px;
    padding: 8px;
}
QFrame#charCardActive {
    background-color: #382B34;
    border: 2px solid #FF8FB1;
    border-radius: 8px;
    padding: 8px;
}
QFrame#charCardLocked {
    background-color: #222429;
    border: 1px dashed #3A3D45;
    border-radius: 8px;
    padding: 8px;
}
"""


class CharacterTreeDialog(QDialog):
    """Interaktiver Dialog fuer Gamification, Tamagotchi-Beduerfnisse und Charakter-Freischaltung."""

    character_selected = pyqtSignal(str)

    def __init__(self, cfg, store=None, pet=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cfg = cfg
        self.store = store
        self.pet = pet

        self.setWindowTitle(tr("care.tree_title"))
        self.resize(620, 720)
        self.setMinimumSize(540, 500)
        self.setStyleSheet(CARE_DIALOG_STYLE)

        self._setup_ui()
        self.refresh_all()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        lbl_title = QLabel(tr("care.tree_title"))
        lbl_title.setObjectName("title")
        lbl_sub = QLabel(tr("care.tree_subtitle"))
        lbl_sub.setObjectName("subtitle")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_sub)
        main_layout.addLayout(header_layout)

        # 2. Freundschaft & Tamagotchi Care Bereich (Oben fixiert)
        top_box = QFrame()
        top_box.setObjectName("tierCard")
        top_layout = QVBoxLayout(top_box)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(12, 10, 12, 10)

        # Freundschaftszeile
        friend_row = QHBoxLayout()
        self.lbl_level_badge = QLabel("Level 1")
        self.lbl_level_badge.setStyleSheet(
            "background: #FF8FB1; color: #202226; font-weight: bold; padding: 4px 10px; border-radius: 6px;"
        )
        self.lbl_level_desc = QLabel("Bekannte 🐾 (0 FP)")
        self.lbl_level_desc.setStyleSheet("color: #F2F3F5; font-weight: bold; font-size: 10pt;")
        friend_row.addWidget(self.lbl_level_badge)
        friend_row.addWidget(self.lbl_level_desc)
        friend_row.addStretch()

        self.bar_fp = QProgressBar()
        self.bar_fp.setStyleSheet("""
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF8FB1, stop:1 #FF5E8E); }
        """)
        self.bar_fp.setFixedHeight(18)
        self.bar_fp.setFixedWidth(200)
        friend_row.addWidget(self.bar_fp)
        top_layout.addLayout(friend_row)

        # Trenner
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #3A3D46;")
        top_layout.addWidget(sep)

        # Tamagotchi-Stats (Hunger, Sauberkeit, Laune)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        # Hunger
        v_hunger = QVBoxLayout()
        v_hunger.setSpacing(3)
        v_hunger.addWidget(QLabel("🥣  " + tr("care.hunger")))
        self.bar_hunger = QProgressBar()
        v_hunger.addWidget(self.bar_hunger)
        self.btn_feed = QPushButton(tr("care.feed_btn"))
        self.btn_feed.clicked.connect(self._on_feed_clicked)
        v_hunger.addWidget(self.btn_feed)
        stats_layout.addLayout(v_hunger)

        # Sauberkeit
        v_hygiene = QVBoxLayout()
        v_hygiene.setSpacing(3)
        v_hygiene.addWidget(QLabel("🧼  " + tr("care.hygiene")))
        self.bar_hygiene = QProgressBar()
        v_hygiene.addWidget(self.bar_hygiene)
        self.btn_wash = QPushButton(tr("care.wash_btn"))
        self.btn_wash.clicked.connect(self._on_wash_clicked)
        v_hygiene.addWidget(self.btn_wash)
        stats_layout.addLayout(v_hygiene)

        # Laune
        v_happy = QVBoxLayout()
        v_happy.setSpacing(3)
        v_happy.addWidget(QLabel("💖  " + tr("care.happiness")))
        self.bar_happy = QProgressBar()
        v_happy.addWidget(self.bar_happy)
        self.btn_pet = QPushButton(tr("care.pet_btn"))
        self.btn_pet.clicked.connect(self._on_pet_clicked)
        v_happy.addWidget(self.btn_pet)
        stats_layout.addLayout(v_happy)

        top_layout.addLayout(stats_layout)
        main_layout.addWidget(top_box)

        # 3. Scroll-Bereich für den Charakter-Baum
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.tree_widget = QWidget()
        self.tree_layout = QVBoxLayout(self.tree_widget)
        self.tree_layout.setContentsMargins(0, 4, 8, 4)
        self.tree_layout.setSpacing(12)
        scroll.setWidget(self.tree_widget)
        main_layout.addWidget(scroll, 1)

        # Schließen Button unten
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(120)
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        main_layout.addLayout(btn_box)

    def refresh_all(self) -> None:
        """Aktualisiert alle Anzeigen: Freundschaft, Tamagotchi-Stats und Charakter-Karten."""
        # 1. Freundschaftsdaten
        current_fp = 0
        if self.store is not None:
            try:
                current_fp = int(self.store.get_stat("friendship_points") or 0)
            except Exception:
                current_fp = 0
        lvl, pct = level_for(current_fp)
        lvl_name = LEVEL_NAMES.get(lvl, "Freunde")

        self.lbl_level_badge.setText(f"Level {lvl}")
        self.lbl_level_desc.setText(f"{lvl_name} 🐾 ({current_fp} FP)")

        cur_thresh = LEVEL_THRESHOLDS[lvl - 1] if lvl - 1 < len(LEVEL_THRESHOLDS) else 0
        next_thresh = LEVEL_THRESHOLDS[lvl] if lvl < len(LEVEL_THRESHOLDS) else cur_thresh
        span = max(1, next_thresh - cur_thresh)
        progress = max(0, min(100, int((current_fp - cur_thresh) / span * 100))) if lvl < 8 else 100

        self.bar_fp.setValue(progress)
        if lvl < 8:
            self.bar_fp.setFormat(f"{current_fp} / {next_thresh} FP")
        else:
            self.bar_fp.setFormat(f"Max Level ({current_fp} FP)")

        # 2. Tamagotchi Stats
        care = pet_care.get_care_stats(self.cfg)
        self._update_stat_bar(self.bar_hunger, care["hunger"])
        self._update_stat_bar(self.bar_hygiene, care["hygiene"])
        self._update_stat_bar(self.bar_happy, care["happiness"])

        # 3. Charakter-Baum aufbauen
        self._build_tree(lvl, current_fp)

    def _update_stat_bar(self, bar: QProgressBar, val: int) -> None:
        bar.setValue(val)
        bar.setFormat(f"{val} %")
        if val >= 60:
            color = "#4ECCA3"   # Frisches Gruen
        elif val >= 35:
            color = "#F6C90E"   # Sonnengelb
        else:
            color = "#FF6B6B"   # Warnrot
        bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)

    def _build_tree(self, user_lvl: int, user_fp: int) -> None:
        # Bestehende Widgets leeren
        while self.tree_layout.count():
            item = self.tree_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        current_char = str(self.cfg.get("pet.character", "cat_mochi"))

        # Iteriere durch die 8 Tiers
        for tier_lvl in sorted(pet_care.UNLOCK_TIERS.keys()):
            char_ids = pet_care.UNLOCK_TIERS[tier_lvl]
            req_pts = LEVEL_THRESHOLDS[tier_lvl - 1] if tier_lvl - 1 < len(LEVEL_THRESHOLDS) else 0
            is_tier_unlocked = user_lvl >= tier_lvl

            tier_frame = QFrame()
            tier_frame.setObjectName("tierCard")
            t_layout = QVBoxLayout(tier_frame)
            t_layout.setContentsMargins(10, 8, 10, 8)
            t_layout.setSpacing(8)

            # Tier Header
            th_layout = QHBoxLayout()
            tier_title = f"Stufe {tier_lvl} — {LEVEL_NAMES.get(tier_lvl, 'Stufe ' + str(tier_lvl))}"
            lbl_t_title = QLabel(tier_title)
            lbl_t_title.setStyleSheet("font-weight: bold; color: #FFB3C6; font-size: 10pt;")
            th_layout.addWidget(lbl_t_title)
            th_layout.addStretch()

            if is_tier_unlocked:
                lbl_status = QLabel("✔ Freigeschaltet")
                lbl_status.setStyleSheet("color: #4ECCA3; font-weight: bold; font-size: 9pt;")
            else:
                pts_needed = max(0, req_pts - user_fp)
                lbl_status = QLabel(f"🔒 Benötigt Level {tier_lvl} (noch {pts_needed} FP)")
                lbl_status.setStyleSheet("color: #A0A5B0; font-size: 9pt;")
            th_layout.addWidget(lbl_status)
            t_layout.addLayout(th_layout)

            # Charaktere in diesem Tier
            chars_row = QHBoxLayout()
            chars_row.setSpacing(10)

            for cid in char_ids:
                ci = get_character_info(cid)
                card = QFrame()
                is_active = (cid == current_char)

                if is_active:
                    card.setObjectName("charCardActive")
                elif is_tier_unlocked:
                    card.setObjectName("charCard")
                else:
                    card.setObjectName("charCardLocked")

                c_layout = QVBoxLayout(card)
                c_layout.setContentsMargins(8, 8, 8, 8)
                c_layout.setSpacing(4)

                # Icon & Name
                top_line = QHBoxLayout()
                lbl_em = QLabel(ci.get("emoji", "🐾"))
                lbl_em.setStyleSheet("font-size: 20pt;")
                top_line.addWidget(lbl_em)

                v_info = QVBoxLayout()
                v_info.setSpacing(1)
                lbl_cname = QLabel(ci.get("name", cid))
                lbl_cname.setStyleSheet("font-weight: bold; font-size: 10pt; color: #F2F3F5;")
                lbl_spec = QLabel(ci.get("species", ""))
                lbl_spec.setStyleSheet("color: #8D919B; font-size: 8pt;")
                v_info.addWidget(lbl_cname)
                v_info.addWidget(lbl_spec)
                top_line.addLayout(v_info)
                top_line.addStretch()
                c_layout.addLayout(top_line)

                # Beschreibung / Spruch
                lbl_desc = QLabel(ci.get("desc", ""))
                lbl_desc.setStyleSheet("color: #B0B5C0; font-size: 8pt;")
                lbl_desc.setWordWrap(True)
                lbl_desc.setMaximumHeight(36)
                c_layout.addWidget(lbl_desc)

                # Button / Status
                if is_active:
                    btn = QPushButton(tr("care.active"))
                    btn.setEnabled(False)
                    btn.setStyleSheet(
                        "background: #FF8FB1; color: #202226; font-weight: bold; border: none; border-radius: 6px; padding: 4px;"
                    )
                elif is_tier_unlocked:
                    btn = QPushButton(tr("care.activate"))
                    btn.setStyleSheet(
                        "background: #3A3D46; color: #F2F3F5; border: 1px solid #5A5E6B; border-radius: 6px; padding: 4px;"
                    )
                    btn.clicked.connect(lambda _=False, c=cid: self._select_char(c))
                else:
                    btn = QPushButton(f"🔒 Lvl {tier_lvl}")
                    btn.setEnabled(False)
                    btn.setStyleSheet(
                        "background: #25272D; color: #6C707A; border: 1px solid #363940; border-radius: 6px; padding: 4px;"
                    )
                c_layout.addWidget(btn)
                chars_row.addWidget(card, 1)

            t_layout.addLayout(chars_row)
            self.tree_layout.addWidget(tier_frame)

        self.tree_layout.addStretch()

    def _select_char(self, cid: str) -> None:
        self.cfg.set("pet.character", cid)
        self.cfg.save()
        if self.pet is not None:
            self.pet.set_character(cid)
        self.character_selected.emit(cid)
        self.refresh_all()

    def _on_feed_clicked(self) -> None:
        pet_care.feed_pet(self.cfg, self.store)
        if self.pet is not None:
            self.pet.give_treat()
        self.refresh_all()

    def _on_wash_clicked(self) -> None:
        pet_care.wash_pet(self.cfg, self.store)
        if self.pet is not None:
            self.pet.wash_pet(4.5)
        self.refresh_all()

    def _on_pet_clicked(self) -> None:
        pet_care.pet_pet(self.cfg, self.store)
        if self.pet is not None:
            self.pet.react_happy()
        self.refresh_all()
