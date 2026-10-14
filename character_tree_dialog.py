# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Charakter-Baum, Trophäen & Minispiele Dialog (v2.4.0).

Bietet 3 Tabs:
1. 🌳 Charakter-Baum: 8-stufige Freischaltung aller 15 Gefährten & Tamagotchi-Pflege
2. 🏆 Trophäen & Quests: 12 freischaltbare Achievements & saisonale Feiertags-Quests
3. 🎮 Minispiele & Zimmer: Seifenblasen, Wollknäuel, Katzenbett & Lively Wallpaper
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from achievements import get_achievement_status, get_all_achievements
from fun import LEVEL_NAMES, LEVEL_THRESHOLDS, level_for
from i18n import tr
import lively_wallpaper
import pet_care
from pet_sprites import CHARACTERS, get_character_info
from seasonal_events import get_current_event, get_quest_status
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
QFrame#achCardUnlocked {
    background-color: #26332E;
    border: 1px solid #4ECCA3;
    border-radius: 8px;
    padding: 10px;
}
QFrame#achCardLocked {
    background-color: #26282E;
    border: 1px solid #3A3D46;
    border-radius: 8px;
    padding: 10px;
}
"""


class CharacterTreeDialog(QDialog):
    """Interaktiver Dialog fuer Gamification, Tamagotchi-Care, Trophäen und Minispiele."""

    character_selected = pyqtSignal(str)
    bubble_game_requested = pyqtSignal()
    yarn_game_requested = pyqtSignal()
    wallpaper_requested = pyqtSignal()
    bed_toggled = pyqtSignal(bool)
    home_mode_toggled = pyqtSignal(bool)
    scripts_requested = pyqtSignal()

    def __init__(self, cfg, store=None, pet=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cfg = cfg
        self.store = store
        self.pet = pet

        self.setWindowTitle(tr("care.tree_title"))
        self.resize(680, 750)
        self.setMinimumSize(580, 520)
        self.setStyleSheet(CARE_DIALOG_STYLE)

        self._setup_ui()
        self.refresh_all()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

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
        top_layout.setSpacing(8)
        top_layout.setContentsMargins(12, 8, 12, 8)

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
        stats_layout.setSpacing(14)

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

        # 3. Tabs: Charakter-Baum, Trophäen & Quests, Minispiele & Zimmer
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #3A3D46; background: #202226; border-radius: 8px; }
            QTabBar::tab { background: #26282E; color: #A0A5B0; padding: 8px 18px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
            QTabBar::tab:selected { background: #FF8FB1; color: #202226; }
        """)

        # Tab 1: Charakter-Baum
        scroll_tree = QScrollArea()
        scroll_tree.setWidgetResizable(True)
        scroll_tree.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.tree_widget = QWidget()
        self.tree_layout = QVBoxLayout(self.tree_widget)
        self.tree_layout.setContentsMargins(4, 8, 8, 8)
        self.tree_layout.setSpacing(10)
        scroll_tree.setWidget(self.tree_widget)
        self.tabs.addTab(scroll_tree, tr("care.tab_tree"))

        # Tab 2: Trophäen & Quests
        scroll_trophies = QScrollArea()
        scroll_trophies.setWidgetResizable(True)
        scroll_trophies.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.trophies_widget = QWidget()
        self.trophies_layout = QVBoxLayout(self.trophies_widget)
        self.trophies_layout.setContentsMargins(4, 8, 8, 8)
        self.trophies_layout.setSpacing(10)
        scroll_trophies.setWidget(self.trophies_widget)
        self.tabs.addTab(scroll_trophies, tr("care.tab_trophies"))

        # Tab 3: Minispiele & Zimmer
        scroll_games = QScrollArea()
        scroll_games.setWidgetResizable(True)
        scroll_games.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.games_widget = QWidget()
        self.games_layout = QVBoxLayout(self.games_widget)
        self.games_layout.setContentsMargins(4, 8, 8, 8)
        self.games_layout.setSpacing(10)
        scroll_games.setWidget(self.games_widget)
        self.tabs.addTab(scroll_games, tr("care.tab_games"))

        main_layout.addWidget(self.tabs, 1)

        # Schließen Button unten
        btn_close = QPushButton("Schließen")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(120)
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        main_layout.addLayout(btn_box)

    def refresh_all(self) -> None:
        """Aktualisiert Freundschaft, Tamagotchi-Stats, Baum, Trophäen und Minispiele."""
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

        care = pet_care.get_care_stats(self.cfg)
        self._update_stat_bar(self.bar_hunger, care["hunger"])
        self._update_stat_bar(self.bar_hygiene, care["hygiene"])
        self._update_stat_bar(self.bar_happy, care["happiness"])

        self._build_tree(lvl, current_fp)
        self._build_trophies()
        self._build_games()

    def _update_stat_bar(self, bar: QProgressBar, val: int) -> None:
        bar.setValue(val)
        bar.setFormat(f"{val} %")
        color = "#4ECCA3" if val >= 60 else ("#F6C90E" if val >= 35 else "#FF6B6B")
        bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 5px; }}")

    def _build_tree(self, user_lvl: int, user_fp: int) -> None:
        while self.tree_layout.count():
            item = self.tree_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        current_char = str(self.cfg.get("pet.character", "cat_mochi"))

        for tier_lvl in sorted(pet_care.UNLOCK_TIERS.keys()):
            char_ids = pet_care.UNLOCK_TIERS[tier_lvl]
            req_pts = LEVEL_THRESHOLDS[tier_lvl - 1] if tier_lvl - 1 < len(LEVEL_THRESHOLDS) else 0
            is_tier_unlocked = user_lvl >= tier_lvl

            tier_frame = QFrame()
            tier_frame.setObjectName("tierCard")
            t_layout = QVBoxLayout(tier_frame)
            t_layout.setContentsMargins(10, 8, 10, 8)
            t_layout.setSpacing(8)

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

                lbl_desc = QLabel(ci.get("desc", ""))
                lbl_desc.setStyleSheet("color: #B0B5C0; font-size: 8pt;")
                lbl_desc.setWordWrap(True)
                lbl_desc.setMaximumHeight(36)
                c_layout.addWidget(lbl_desc)

                if is_active:
                    btn = QPushButton(tr("care.active"))
                    btn.setEnabled(False)
                    btn.setStyleSheet("background: #FF8FB1; color: #202226; font-weight: bold; border: none; border-radius: 6px; padding: 4px;")
                elif is_tier_unlocked:
                    btn = QPushButton(tr("care.activate"))
                    btn.setStyleSheet("background: #3A3D46; color: #F2F3F5; border: 1px solid #5A5E6B; border-radius: 6px; padding: 4px;")
                    btn.clicked.connect(lambda _=False, c=cid: self._select_char(c))
                else:
                    btn = QPushButton(f"🔒 Lvl {tier_lvl}")
                    btn.setEnabled(False)
                    btn.setStyleSheet("background: #25272D; color: #6C707A; border: 1px solid #363940; border-radius: 6px; padding: 4px;")
                c_layout.addWidget(btn)
                chars_row.addWidget(card, 1)

            t_layout.addLayout(chars_row)
            self.tree_layout.addWidget(tier_frame)

        self.tree_layout.addStretch()

    def _build_trophies(self) -> None:
        """Erstellt die Ansicht für saisonale Quests und die 12 Achievements."""
        while self.trophies_layout.count():
            item = self.trophies_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 1. Saisonale Feiertags-Quest
        event = get_current_event()
        event_card = QFrame()
        event_card.setObjectName("tierCard")
        e_layout = QVBoxLayout(event_card)
        e_layout.setContentsMargins(12, 10, 12, 10)
        e_layout.setSpacing(6)

        lbl_ev_title = QLabel(event["title"])
        lbl_ev_title.setStyleSheet("font-weight: bold; color: #FFD166; font-size: 11pt;")
        lbl_ev_sub = QLabel(event["subtitle"])
        lbl_ev_sub.setStyleSheet("color: #A0A5B0; font-size: 9pt;")
        e_layout.addWidget(lbl_ev_title)
        e_layout.addWidget(lbl_ev_sub)

        for quest in event.get("quests", []):
            cur, tgt, done = get_quest_status(self.store, quest)
            q_box = QHBoxLayout()
            lbl_q = QLabel(f"🎯 {quest['title']} ({quest['desc']})")
            lbl_q.setStyleSheet("color: #F2F3F5; font-size: 9pt;")
            q_box.addWidget(lbl_q)
            q_box.addStretch()

            bar_q = QProgressBar()
            bar_q.setMaximum(tgt)
            bar_q.setValue(cur)
            bar_q.setFormat(f"{cur}/{tgt}" if not done else "✔ Erledigt!")
            bar_q.setFixedWidth(130)
            bar_q.setFixedHeight(18)
            q_box.addWidget(bar_q)
            e_layout.addLayout(q_box)

        self.trophies_layout.addWidget(event_card)

        # 2. Die 12 Achievements
        lbl_ach_title = QLabel("🏆 Ruhmeshalle & Meilensteine")
        lbl_ach_title.setStyleSheet("font-weight: bold; color: #FFB3C6; font-size: 11pt; margin-top: 6px;")
        self.trophies_layout.addWidget(lbl_ach_title)

        for ach in get_all_achievements():
            cur, tgt, unlocked = get_achievement_status(self.store, ach)
            card = QFrame()
            card.setObjectName("achCardUnlocked" if unlocked else "achCardLocked")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(10, 8, 10, 8)
            c_layout.setSpacing(10)

            lbl_ic = QLabel(ach["icon"])
            lbl_ic.setStyleSheet("font-size: 20pt;")
            c_layout.addWidget(lbl_ic)

            v_txt = QVBoxLayout()
            v_txt.setSpacing(2)
            lbl_at = QLabel(ach["title"])
            lbl_at.setStyleSheet("font-weight: bold; font-size: 10pt; color: #F2F3F5;")
            lbl_ad = QLabel(f"{ach['desc']} (+{ach['fp_reward']} FP)")
            lbl_ad.setStyleSheet("color: #8D919B; font-size: 8pt;")
            v_txt.addWidget(lbl_at)
            v_txt.addWidget(lbl_ad)
            c_layout.addLayout(v_txt, 1)

            bar_a = QProgressBar()
            bar_a.setMaximum(tgt)
            bar_a.setValue(cur)
            bar_a.setFixedWidth(120)
            bar_a.setFixedHeight(18)
            if unlocked:
                bar_a.setFormat("✔ Erreicht")
                bar_a.setStyleSheet("QProgressBar::chunk { background-color: #4ECCA3; border-radius: 5px; }")
            else:
                bar_a.setFormat(f"{cur}/{tgt}")
                bar_a.setStyleSheet("QProgressBar::chunk { background-color: #FF8FB1; border-radius: 5px; }")
            c_layout.addWidget(bar_a)

            self.trophies_layout.addWidget(card)

        self.trophies_layout.addStretch()

    def _build_games(self) -> None:
        """Erstellt die Ansicht fuer Minispiele, Katzenbett und Lively Wallpaper."""
        while self.games_layout.count():
            item = self.games_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # 1. Lively Wallpaper: Katzenzimmer (Empfohlen ⭐)
        room_card = QFrame()
        room_card.setObjectName("tierCard")
        r_layout = QVBoxLayout(room_card)
        r_layout.setContentsMargins(12, 10, 12, 10)
        r_layout.setSpacing(8)

        lbl_rw = QLabel(tr("lively.title"))
        lbl_rw.setStyleSheet("font-weight: bold; color: #FFD166; font-size: 11pt;")
        lbl_rd = QLabel(tr("lively.desc"))
        lbl_rd.setStyleSheet("color: #A0A5B0; font-size: 9pt;")
        r_layout.addWidget(lbl_rw)
        r_layout.addWidget(lbl_rd)

        is_at_home = bool(self.cfg.get("pet.is_at_home", True))
        home_btn_text = "🏠  Katze ist ZU HAUSE im Zimmer (Klick: Rausgehen)" if is_at_home else "🌿  Katze ist DRAUSSEN auf dem Desktop (Klick: Nach Hause)"
        btn_home_mode = QPushButton(home_btn_text)
        btn_home_mode.setStyleSheet("background: #4ECCA3; color: #121316; font-weight: bold; border-radius: 6px; padding: 8px;" if is_at_home else "background: #3A3D46; color: #F2F3F5; font-weight: bold; border-radius: 6px; padding: 8px;")
        btn_home_mode.clicked.connect(self._on_home_mode_clicked)
        r_layout.addWidget(btn_home_mode)

        self.chk_auto_lively = QCheckBox(tr("lively.auto_sync_label"))
        self.chk_auto_lively.setChecked(bool(self.cfg.get("lively.auto_sync", True)))
        self.chk_auto_lively.toggled.connect(self._on_auto_lively_toggled)
        r_layout.addWidget(self.chk_auto_lively)

        btn_act_lively = QPushButton(tr("lively.activate_btn"))
        btn_act_lively.setStyleSheet("background: #FF8FB1; color: #202226; font-weight: bold; border-radius: 6px; padding: 7px;")
        btn_act_lively.clicked.connect(self._on_activate_lively)
        r_layout.addWidget(btn_act_lively)
        self.games_layout.addWidget(room_card)

        # 2. Seifenblasen-Minispiel
        bubble_card = QFrame()
        bubble_card.setObjectName("charCard")
        b_layout = QVBoxLayout(bubble_card)
        b_layout.setContentsMargins(12, 10, 12, 10)
        b_layout.setSpacing(6)
        lbl_bt = QLabel(tr("game.bubble_title"))
        lbl_bt.setStyleSheet("font-weight: bold; color: #6EC5E9; font-size: 10pt;")
        lbl_bd = QLabel(tr("game.bubble_desc"))
        lbl_bd.setStyleSheet("color: #8D919B; font-size: 8pt;")
        btn_start_bubble = QPushButton(tr("game.bubble_btn"))
        btn_start_bubble.setStyleSheet("background: #3A3D46; color: #F2F3F5; border-radius: 6px; padding: 6px;")
        btn_start_bubble.clicked.connect(self.bubble_game_requested.emit)
        b_layout.addWidget(lbl_bt)
        b_layout.addWidget(lbl_bd)
        b_layout.addWidget(btn_start_bubble)
        self.games_layout.addWidget(bubble_card)

        # 3. Wollknäuel-Minispiel
        yarn_card = QFrame()
        yarn_card.setObjectName("charCard")
        y_layout = QVBoxLayout(yarn_card)
        y_layout.setContentsMargins(12, 10, 12, 10)
        y_layout.setSpacing(6)
        lbl_yt = QLabel(tr("game.yarn_title"))
        lbl_yt.setStyleSheet("font-weight: bold; color: #FF9AA2; font-size: 10pt;")
        lbl_yd = QLabel(tr("game.yarn_desc"))
        lbl_yd.setStyleSheet("color: #8D919B; font-size: 8pt;")
        btn_start_yarn = QPushButton(tr("game.yarn_btn"))
        btn_start_yarn.setStyleSheet("background: #3A3D46; color: #F2F3F5; border-radius: 6px; padding: 6px;")
        btn_start_yarn.clicked.connect(self.yarn_game_requested.emit)
        y_layout.addWidget(lbl_yt)
        y_layout.addWidget(lbl_yd)
        y_layout.addWidget(btn_start_yarn)
        self.games_layout.addWidget(yarn_card)

        # 4. Kuscheliges Katzenbett
        bed_card = QFrame()
        bed_card.setObjectName("charCard")
        bd_layout = QVBoxLayout(bed_card)
        bd_layout.setContentsMargins(12, 10, 12, 10)
        bd_layout.setSpacing(6)
        lbl_bdt = QLabel(tr("furniture.bed_title"))
        lbl_bdt.setStyleSheet("font-weight: bold; color: #FFB7B2; font-size: 10pt;")
        lbl_bdd = QLabel(tr("furniture.bed_desc"))
        lbl_bdd.setStyleSheet("color: #8D919B; font-size: 8pt;")
        self.chk_bed = QCheckBox(tr("furniture.bed_btn"))
        self.chk_bed.setChecked(bool(self.cfg.get("furniture.bed_visible", True)))
        self.chk_bed.toggled.connect(self._on_bed_toggled)
        bd_layout.addWidget(lbl_bdt)
        bd_layout.addWidget(lbl_bdd)
        bd_layout.addWidget(self.chk_bed)
        self.games_layout.addWidget(bed_card)

        # 5. Eigene Skripte & Routinen
        scripts_card = QFrame()
        scripts_card.setObjectName("charCard")
        sc_layout = QVBoxLayout(scripts_card)
        sc_layout.setContentsMargins(12, 10, 12, 10)
        sc_layout.setSpacing(6)
        lbl_sct = QLabel("🤖  Eigene Python-Skripte & Routinen")
        lbl_sct.setStyleSheet("font-weight: bold; color: #79C0FF; font-size: 10pt;")
        lbl_scd = QLabel("Erstelle, bearbeite und plane eigene Python-Skripte und tägliche Alltags-Routinen.")
        lbl_scd.setStyleSheet("color: #8D919B; font-size: 8pt;")
        btn_open_scripts = QPushButton("🤖  Skripte & Routinen verwalten")
        btn_open_scripts.setStyleSheet("background: #3A3D46; color: #F2F3F5; border-radius: 6px; padding: 6px;")
        btn_open_scripts.clicked.connect(self.scripts_requested.emit)
        sc_layout.addWidget(lbl_sct)
        sc_layout.addWidget(lbl_scd)
        sc_layout.addWidget(btn_open_scripts)
        self.games_layout.addWidget(scripts_card)

        self.games_layout.addStretch()

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

    def _on_home_mode_clicked(self) -> None:
        new_state = not bool(self.cfg.get("pet.is_at_home", True))
        self.cfg.set("pet.is_at_home", new_state)
        self.cfg.save()
        self.home_mode_toggled.emit(new_state)
        self.refresh_all()

    def _on_auto_lively_toggled(self, checked: bool) -> None:
        self.cfg.set("lively.auto_sync", checked)
        self.cfg.save()

    def _on_activate_lively(self) -> None:
        lively_wallpaper.apply_lively_wallpaper(self.cfg, self.store)
        self.wallpaper_requested.emit()

    def _on_bed_toggled(self, checked: bool) -> None:
        self.cfg.set("furniture.bed_visible", checked)
        self.cfg.save()
        self.bed_toggled.emit(checked)
