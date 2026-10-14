"""Onboarding-Dialog („Kennenlernen mit Kylie“): Spielerisches Erstgespraech mit animiertem Pet,
Frage-Zustandsmaschine, Schnellantwort-Chips und optionaler Gemini-Reaktion.
"""
from __future__ import annotations

import os
import random
import re
from typing import Any, Callable, Optional

from PyQt6.QtCore import QPointF, QPropertyAnimation, QRectF, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QGraphicsOpacityEffect,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

import gemini
import i18n
from i18n import tr
from pet_sprites import CHARACTERS, PoseContext, compute_pose, draw_character, get_character_info
from settings_dialog import STYLE as BASE_STYLE

FALLBACK_REACTIONS_DE = [
    "Super! 😺", "Klasse! ✨", "Alles klar! 🐾", "Schön zu wissen! 💖", "Verstanden! 😸",
    "Cool! 😺", "Toll! ✨", "Merk ich mir! 📝",
]
FALLBACK_REACTIONS_EN = [
    "Awesome! 😺", "Great! ✨", "Got it! 🐾", "Good to know! 💖", "Understood! 😸",
    "Cool! 😺", "Nice! ✨", "I'll remember that! 📝",
]


def _btn_text(label: str) -> str:
    """Qt macht aus '&' ein Tastenkuerzel und verschluckt es ('lieb & verspielt' -> 'lieb  verspielt')."""
    return label.replace("&", "&&")


def clean_free_text(text: str, max_len: int = 60) -> str:
    """Bereinigt Freitext-Eingaben: Whitespace trimmen, Zeilenumbrueche entfernen, Laenge begrenzen."""
    if not text:
        return ""
    cleaned = re.sub(r"[\r\n\t]+", " ", str(text)).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].strip()
    return cleaned


# ======================================================================================
#  Reine Ablauf-Logik (State Machine) ohne Qt
# ======================================================================================
class OnboardingFlow:
    """Zustandsmaschine fuer die 15 Onboarding-Schritte, komplett ohne GUI-Klassen testbar."""

    TOTAL_STEPS = 15

    def __init__(self, cfg: Any, has_key_fn: Optional[Callable[[], bool]] = None, is_update: bool = False):
        self.cfg = cfg
        self.has_key_fn = has_key_fn if has_key_fn is not None else gemini.has_key
        self.is_update = is_update
        self.step = 1
        self.answers: dict[str, Any] = {}

        if is_update and hasattr(cfg, "get"):
            self.answers["name"] = cfg.get("profile.name", "")
            self.answers["user_name"] = cfg.get("pet.user_name", "Boss")
            self.answers["character"] = cfg.get("pet.character", "cat_mochi")
            self.answers["language"] = cfg.get("language", "de")
            self.answers["interests"] = cfg.get("profile.interests", "")
            self.answers["city"] = cfg.get("profile.city", "")
            self.answers["pronouns"] = cfg.get("profile.pronouns", "")
            self.answers["tone"] = cfg.get("profile.tone", "")

    def current_step(self) -> int:
        return self.step

    def is_done(self) -> bool:
        return self.step >= self.TOTAL_STEPS

    def can_skip(self) -> bool:
        # Schritt 3 (Name) ist Pflicht, Schritt 15 ist Abschluss
        return self.step not in (3, 15)

    def skip_later(self) -> None:
        skips = int(self.cfg.get("onboarding_skips", 0)) if hasattr(self.cfg, "get") else 0
        if hasattr(self.cfg, "set"):
            self.cfg.set("onboarding_skips", skips + 1)
        if hasattr(self.cfg, "save"):
            self.cfg.save()

    def skip_current_step(self) -> bool:
        if not self.can_skip():
            return False
        # Falls von Schritt 10 weitergegangen wird und bereits ein Key da ist -> Schritt 11 ueberspringen
        if self.step == 10 and self.has_key_fn():
            self.step = 12
        else:
            self.step += 1
        if self.step > self.TOTAL_STEPS:
            self.step = self.TOTAL_STEPS
        return True

    def submit_answer(self, answer: Any) -> bool:
        """Verarbeitet eine Antwort fuer den aktuellen Schritt und schaltet weiter."""
        s = self.step

        if s == 1:
            ans_str = str(answer).strip().lower()
            if ans_str in ("later", "später", "spaeter"):
                self.skip_later()
                return False
            self.step = 2
            return True

        elif s == 2:
            ans_str = str(answer).strip().lower()
            lang = "en" if "en" in ans_str else "de"
            if hasattr(self.cfg, "set"):
                self.cfg.set("language", lang)
            i18n.set_language(lang)
            self.answers["language"] = lang
            self.step = 3
            return True

        elif s == 3:
            cleaned = clean_free_text(str(answer), 60)
            if not cleaned:
                return False  # Pflichtfeld
            if hasattr(self.cfg, "set"):
                self.cfg.set("profile.name", cleaned)
            self.answers["name"] = cleaned
            self.step = 4
            return True

        elif s == 4:
            cleaned = clean_free_text(str(answer), 60)
            u_name = cleaned or self.answers.get("name") or (self.cfg.get("profile.name") if hasattr(self.cfg, "get") else "") or "Boss"
            if hasattr(self.cfg, "set"):
                self.cfg.set("pet.user_name", u_name)
            self.answers["user_name"] = u_name
            self.step = 5
            return True

        elif s == 5:
            cleaned = clean_free_text(str(answer), 40)
            if hasattr(self.cfg, "set"):
                self.cfg.set("profile.pronouns", cleaned)
            self.answers["pronouns"] = cleaned
            self.step = 6
            return True

        elif s == 6:
            if isinstance(answer, list):
                uses = [clean_free_text(str(x), 40) for x in answer if str(x).strip()]
            elif isinstance(answer, str) and answer.strip():
                uses = [clean_free_text(x, 40) for x in answer.split(",") if x.strip()]
            else:
                uses = []
            if hasattr(self.cfg, "set"):
                self.cfg.set("profile.uses", uses)
            self.answers["uses"] = uses
            self.step = 7
            return True

        elif s == 7:
            cleaned = clean_free_text(str(answer), 200)
            if hasattr(self.cfg, "set"):
                self.cfg.set("profile.interests", cleaned)
            self.answers["interests"] = cleaned
            if cleaned:
                try:
                    from memory_store import get_memory_store
                    store = get_memory_store()
                    store.add_fact(f"Mag: {cleaned}", kind="profile", category="Hobbys")
                except Exception:
                    pass
            self.step = 8
            return True

        elif s == 8:
            cleaned = clean_free_text(str(answer), 40)
            if hasattr(self.cfg, "set"):
                self.cfg.set("profile.tone", cleaned)
            self.answers["tone"] = cleaned
            self.step = 9
            return True

        elif s == 9:
            ans_str = str(answer).lower()
            if "oft" in ans_str or "often" in ans_str:
                if hasattr(self.cfg, "set"):
                    self.cfg.set("pet.chatter", True)
                    self.cfg.set("pet.wander_min_s", 3)
                    self.cfg.set("pet.wander_max_s", 6)
            elif "nie" in ans_str or "rufst" in ans_str or "call" in ans_str or "never" in ans_str:
                if hasattr(self.cfg, "set"):
                    self.cfg.set("pet.chatter", False)
            else:
                if hasattr(self.cfg, "set"):
                    self.cfg.set("pet.chatter", True)
                    self.cfg.set("pet.wander_min_s", 5)
                    self.cfg.set("pet.wander_max_s", 10)
            self.answers["chatter"] = answer
            self.step = 10
            return True

        elif s == 10:
            cleaned = clean_free_text(str(answer), 40)
            if hasattr(self.cfg, "set"):
                self.cfg.set("profile.city", cleaned)
            self.answers["city"] = cleaned
            if self.has_key_fn():
                self.step = 12
            else:
                self.step = 11
            return True

        elif s == 11:
            self.step = 12
            return True

        elif s == 12:
            cid = str(answer).strip()
            if cid in CHARACTERS:
                if hasattr(self.cfg, "set"):
                    self.cfg.set("pet.character", cid)
                self.answers["character"] = cid
            self.step = 13
            return True

        elif s == 13:
            if isinstance(answer, dict) and hasattr(self.cfg, "set"):
                if "save_chats" in answer:
                    self.cfg.set("privacy.save_chats", bool(answer["save_chats"]))
                if "remember" in answer:
                    self.cfg.set("privacy.remember", bool(answer["remember"]))
                if "use_history" in answer:
                    self.cfg.set("privacy.use_history", bool(answer["use_history"]))
            self.step = 14
            return True

        elif s == 14:
            ans_str = str(answer).lower()
            auto = not ("nein" in ans_str or "no" in ans_str)
            if hasattr(self.cfg, "set"):
                self.cfg.set("autostart", auto)
            self.step = 15
            return True

        elif s == 15:
            self.finish()
            return True

        return False

    def finish(self) -> None:
        if hasattr(self.cfg, "set"):
            self.cfg.set("onboarding_done", True)
        if hasattr(self.cfg, "save"):
            self.cfg.save()
        self.step = 15


# ======================================================================================
#  Worker-Threads fuer Gemini-Reaktionen & Key-Validierung
# ======================================================================================
class OnboardingReactionWorker(QThread):
    reaction_ready = pyqtSignal(str)

    def __init__(self, char_id: str, profile_summary: str, question: str, user_answer: str, lang: str):
        super().__init__()
        self.char_id = char_id
        self.profile_summary = profile_summary
        self.question = question
        self.user_answer = user_answer
        self.lang = lang

    def run(self) -> None:
        cinfo = get_character_info(self.char_id)
        cname = cinfo.get("name", "Kylie")
        species = cinfo.get("species", "Katze")
        persona = cinfo.get("ai_persona", "")
        sound = cinfo.get("sound", "Miau~")

        if self.lang == "en":
            pool = FALLBACK_REACTIONS_EN
            fallback = random.choice(pool)
            prompt = (
                f"You are {cname}, a friendly {species}. Persona: {persona}. Catchphrase: '{sound}'.\n"
                f"User profile so far: {self.profile_summary}\n"
                f"You just asked: \"{self.question}\"\n"
                f"User answered: \"{self.user_answer}\"\n"
                "Reply with EXACTLY ONE short, lovely reaction in character voice (at most 1 sentence, at most 1 emoji). "
                "Do NOT ask any new questions."
            )
        else:
            pool = FALLBACK_REACTIONS_DE
            fallback = random.choice(pool)
            prompt = (
                f"Du bist {cname}, ein(e) herzliche(r) {species}. Persona: {persona}. Ausruf: '{sound}'.\n"
                f"Bisheriges Nutzer-Profil: {self.profile_summary}\n"
                f"Du hast gerade gefragt: \"{self.question}\"\n"
                f"Nutzer hat geantwortet: \"{self.user_answer}\"\n"
                "Antworte mit GENAU 1 kurzen, herzlichen Reaktion in deiner Figuren-Stimme (maximal 1 Satz, höchstens 1 Emoji). "
                "Stelle KEINE neue Frage."
            )

        try:
            res = gemini.ask(prompt, timeout_s=15)
            text = (res or "").strip().replace("\n", " ")
            if text and len(text) < 180:
                self.reaction_ready.emit(text)
                return
        except Exception:
            pass

        self.reaction_ready.emit(fallback)


class KeyValidationWorker(QThread):
    validation_done = pyqtSignal(bool, str)

    def __init__(self, key: str):
        super().__init__()
        self.key = (key or "").strip()

    def run(self) -> None:
        try:
            ok, msg = gemini.validate_key(self.key)
            if ok:
                gemini.save_key(self.key)
            self.validation_done.emit(ok, msg)
        except Exception as e:
            self.validation_done.emit(False, str(e))


# ======================================================================================
#  Großes, animiertes Pet-Widget (Links ~40%)
# ======================================================================================
class PetAvatarWidget(QWidget):
    """Zeigt die gewaehlte Figur gross (ca. 1.8x) mit Pose-Animation, Herzchen und Konfetti."""

    def __init__(self, character_id: str = "cat_mochi", parent=None):
        super().__init__(parent)
        self.character_id = character_id
        self.pose_key = "idle"
        self.happy = False
        self.accessories: list[str] = []
        self._frame = 0
        self._hearts: list[dict] = []
        self._confetti: list[dict] = []
        self.setFixedWidth(270)
        self.setMinimumHeight(480)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

    def set_character(self, character_id: str) -> None:
        self.character_id = character_id
        self.update()

    def set_pose_state(self, pose_key: str = "idle", accessories: Optional[list[str]] = None, happy: bool = False) -> None:
        self.pose_key = pose_key
        self.happy = happy
        if accessories is not None:
            self.accessories = list(accessories)
        self.update()

    def pop_hearts(self) -> None:
        self.happy = True
        QTimer.singleShot(600, lambda: setattr(self, "happy", False))
        for _ in range(6):
            self._hearts.append({
                "x": random.uniform(100, 170),
                "y": random.uniform(220, 260),
                "vx": random.uniform(-1.2, 1.2),
                "vy": random.uniform(-2.5, -4.5),
                "alpha": 255,
                "size": random.uniform(14, 22),
            })

    def pop_confetti(self) -> None:
        self.pose_key = "dance"
        self.happy = True
        colors = [QColor("#FF8FB1"), QColor("#FFD166"), QColor("#06D6A0"), QColor("#118AB2"), QColor("#F72585"), QColor("#FFFFFF")]
        for _ in range(35):
            self._confetti.append({
                "x": random.uniform(20, 250),
                "y": random.uniform(10, 100),
                "vx": random.uniform(-2.0, 2.0),
                "vy": random.uniform(2.5, 6.0),
                "color": random.choice(colors),
                "w": random.uniform(6, 11),
                "h": random.uniform(4, 8),
                "angle": random.uniform(0, 360),
                "va": random.uniform(-6, 6),
                "life": 120,
            })

    def _tick(self) -> None:
        self._frame += 1

        # Herzen updaten
        alive_hearts = []
        for h in self._hearts:
            h["x"] += h["vx"]
            h["y"] += h["vy"]
            h["alpha"] = max(0, h["alpha"] - 7)
            if h["alpha"] > 0:
                alive_hearts.append(h)
        self._hearts = alive_hearts

        # Konfetti updaten
        alive_confetti = []
        for c in self._confetti:
            c["x"] += c["vx"]
            c["y"] += c["vy"]
            c["angle"] += c["va"]
            c["life"] -= 1
            if c["life"] > 0 and c["y"] < self.height() + 20:
                alive_confetti.append(c)
        self._confetti = alive_confetti

        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Sanfter Hintergrund-Kreis hinter dem Pet
        painter.setPen(Qt.PenStyle.NoPen)
        glow_grad = QBrush(QColor(46, 48, 54, 180))
        painter.setBrush(glow_grad)
        painter.drawEllipse(QRectF(w / 2 - 110, h / 2 - 60, 220, 220))

        # Pet groß zeichnen (ca. 1.85x skaliert)
        painter.save()
        scale = 1.85
        cx = (w - 128 * scale) / 2
        cy = (h - 128 * scale) / 2 + 10
        painter.translate(cx, cy)
        painter.scale(scale, scale)

        p_ctx = PoseContext(
            key=self.pose_key,
            t=self._frame * 0.033,
            age=self._frame * 0.033,
            happy=self.happy,
            look=(0.3, 0.0),
        )
        current_pose = compute_pose(p_ctx)

        draw_character(
            painter,
            current_pose,
            self.character_id,
        )
        painter.restore()

        # Herzen rendern
        for hrt in self._hearts:
            painter.save()
            font = QFont("Segoe UI Emoji", int(hrt["size"]))
            painter.setFont(font)
            col = QColor(255, 143, 177, int(hrt["alpha"]))
            painter.setPen(col)
            painter.drawText(QPointF(hrt["x"], hrt["y"]), "💖")
            painter.restore()

        # Konfetti rendern
        for c in self._confetti:
            painter.save()
            painter.translate(c["x"], c["y"])
            painter.rotate(c["angle"])
            painter.setBrush(c["color"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(-c["w"] / 2, -c["h"] / 2, c["w"], c["h"]))
            painter.restore()


# ======================================================================================
#  Haupt-Dialog OnboardingDialog
# ======================================================================================
class OnboardingDialog(QDialog):
    """Rahmenloses, freundliches Onboarding-Fenster mit Chatverlauf und Live-Pet."""

    def __init__(self, cfg: Any, parent=None, is_update: bool = False):
        super().__init__(parent)
        self.cfg = cfg
        self.is_update = is_update
        self.flow = OnboardingFlow(cfg, is_update=is_update)

        self._threads: set[QThread] = set()
        self._typing_bubble: Optional[QWidget] = None
        self._is_waiting = False

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.resize(760, 530)
        self.setMinimumSize(740, 510)
        self.setStyleSheet(BASE_STYLE)

        # Sanftes Einblenden & Transparenz (nur auf echtem Desktop, nicht offscreen)
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._opacity_effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(self._opacity_effect)
            self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
            self._anim.setDuration(240)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        else:
            self.setStyleSheet("QDialog { background-color: #26282C; } " + BASE_STYLE)

        self._build_ui()
        self._center_on_screen()

        # Ersten Schritt anzeigen
        self._render_current_step()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        margins = 0 if os.environ.get("QT_QPA_PLATFORM") == "offscreen" else 8
        outer.setContentsMargins(margins, margins, margins, margins)

        # Hauptkarte mit 16 px Radius
        self.card = QFrame(self)
        self.card.setObjectName("main_card")
        self.card.setStyleSheet("""
            QFrame#main_card {
                background-color: #26282C;
                border: 1px solid #3E4148;
                border-radius: 16px;
            }
        """)
        outer.addWidget(self.card)

        card_lay = QHBoxLayout(self.card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(14)

        # Links: Pet-Avatar
        cur_char = str(self.cfg.get("pet.character", "cat_mochi"))
        self.avatar = PetAvatarWidget(cur_char, self)
        card_lay.addWidget(self.avatar, 0)

        # Trennlinie
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #33353B; max-width: 1px;")
        card_lay.addWidget(sep)

        # Rechts: Chat & Interaktionsbereich
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(4, 2, 4, 4)
        right_panel.setSpacing(8)

        # Header: Pfoten-Fortschritt & Schließen
        hdr = QHBoxLayout()
        self.lbl_progress = QLabel("🐾◦◦◦◦◦◦◦◦◦◦◦◦◦◦")
        self.lbl_progress.setStyleSheet("font-size: 11pt; color: #FF8FB1; font-weight: bold;")
        hdr.addWidget(self.lbl_progress)
        hdr.addStretch(1)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip(tr("onboarding.q1_chip_later"))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: #33353B; color: #8D919B; border-radius: 14px;
                font-size: 11pt; font-weight: bold; padding: 0px;
            }
            QPushButton:hover { background: #4A3338; color: #FF8FB1; }
        """)
        self.btn_close.clicked.connect(self._on_later_clicked)
        hdr.addWidget(self.btn_close)
        right_panel.addLayout(hdr)

        # Chatverlauf
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background: transparent; border: none;")
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_lay = QVBoxLayout(self.chat_container)
        self.chat_lay.setContentsMargins(4, 4, 4, 4)
        self.chat_lay.setSpacing(8)
        self.chat_lay.addStretch(1)
        self.chat_scroll.setWidget(self.chat_container)
        right_panel.addWidget(self.chat_scroll, 1)

        # Interaktionsbereich unten
        self.input_container = QWidget()
        self.input_lay = QVBoxLayout(self.input_container)
        self.input_lay.setContentsMargins(0, 0, 0, 0)
        self.input_lay.setSpacing(8)
        right_panel.addWidget(self.input_container, 0)

        card_lay.addLayout(right_panel, 1)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)

    def _update_progress(self) -> None:
        step = self.flow.current_step()
        total = self.flow.TOTAL_STEPS
        # ohne Leerzeichen: 15 Pfoten passen neben den Schliessen-Button
        self.lbl_progress.setText("🐾" * step + "◦" * (total - step))

    def _add_pet_bubble(self, text: str) -> None:
        cinfo = get_character_info(self.avatar.character_id)
        emo = cinfo.get("emoji", "😺")

        row_w = QWidget(self.chat_container)
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)

        lbl_emo = QLabel(emo, row_w)
        lbl_emo.setStyleSheet("font-size: 14pt; background: transparent;")
        lbl_emo.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(lbl_emo)

        bubble = QLabel(text, row_w)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(360)
        bubble.setStyleSheet("""
            QLabel {
                background-color: #33353B;
                color: #F2F3F5;
                font-size: 10pt;
                border-radius: 12px;
                padding: 10px 14px;
            }
        """)
        row.addWidget(bubble)
        row.addStretch(1)

        count = self.chat_lay.count()
        self.chat_lay.insertWidget(count - 1, row_w)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _add_user_bubble(self, text: str) -> None:
        row_w = QWidget(self.chat_container)
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)
        row.addStretch(1)

        bubble = QLabel(text, row_w)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(360)
        bubble.setStyleSheet("""
            QLabel {
                background-color: #5E364A;
                color: #FFF0F5;
                font-size: 10pt;
                font-weight: 500;
                border-radius: 12px;
                padding: 10px 14px;
            }
        """)
        row.addWidget(bubble)

        count = self.chat_lay.count()
        self.chat_lay.insertWidget(count - 1, row_w)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _show_typing(self) -> None:
        self._hide_typing()
        cinfo = get_character_info(self.avatar.character_id)
        emo = cinfo.get("emoji", "😺")

        row_w = QWidget(self.chat_container)
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(8)

        lbl_emo = QLabel(emo, row_w)
        lbl_emo.setStyleSheet("font-size: 14pt; background: transparent;")
        row.addWidget(lbl_emo)

        lbl_typing = QLabel("••• " + tr("onboarding.typing"), row_w)
        lbl_typing.setStyleSheet("""
            background-color: #2F3136;
            color: #FF8FB1;
            font-size: 9.5pt;
            font-style: italic;
            border-radius: 10px;
            padding: 6px 12px;
        """)
        row.addWidget(lbl_typing)
        row.addStretch(1)

        count = self.chat_lay.count()
        self.chat_lay.insertWidget(count - 1, row_w)
        self._typing_bubble = row_w
        self._scroll_to_bottom()

    def _hide_typing(self) -> None:
        if self._typing_bubble is not None:
            self._typing_bubble.hide()
            self._typing_bubble.setParent(None)
            self._typing_bubble.deleteLater()
            self._typing_bubble = None

    def _scroll_to_bottom(self) -> None:
        sb = self.chat_scroll.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _clear_input_area(self) -> None:
        while self.input_lay.count():
            child = self.input_lay.takeAt(0)
            w = child.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    sw = sub.widget()
                    if sw:
                        sw.hide()
                        sw.setParent(None)
                        sw.deleteLater()

    def _clear_chat(self) -> None:
        while self.chat_lay.count() > 1:
            child = self.chat_lay.takeAt(0)
            w = child.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    sw = sub.widget()
                    if sw:
                        sw.hide()
                        sw.setParent(None)
                        sw.deleteLater()

    # -- Schritt-Darstellung -----------------------------------------------------------
    def _render_current_step(self) -> None:
        self._hide_typing()
        self._clear_input_area()
        self._update_progress()

        step = self.flow.current_step()
        cinfo = get_character_info(self.avatar.character_id)
        cname = cinfo.get("name", "Kylie")
        u_name = self.flow.answers.get("user_name") or self.cfg.get("pet.user_name", "Boss")

        # Pose & Accessoires anpassen
        if step == 11:
            self.avatar.set_pose_state("working", accessories=["glasses_hacker"])
        elif step == 15:
            self.avatar.pop_confetti()
        else:
            self.avatar.set_pose_state("idle", accessories=[])

        # Texte je Schritt
        if step == 1:
            if self.is_update:
                q_text = tr("onboarding.q1_welcome_update", user_name=u_name)
            else:
                q_text = tr("onboarding.q1_welcome", name=cname)
            self._add_pet_bubble(q_text)
            self._render_chips([
                (tr("onboarding.q1_chip_yes"), "ok"),
                (tr("onboarding.q1_chip_later"), "later"),
            ])

        elif step == 2:
            self._add_pet_bubble(tr("onboarding.q2_language"))
            self._render_chips([
                (tr("onboarding.q2_chip_de"), "de"),
                (tr("onboarding.q2_chip_en"), "en"),
            ])

        elif step == 3:
            self._add_pet_bubble(tr("onboarding.q3_name"))
            self._render_text_input(
                placeholder=tr("onboarding.q3_placeholder"),
                default_text=self.flow.answers.get("name", ""),
                can_skip=False,
            )

        elif step == 4:
            self._add_pet_bubble(tr("onboarding.q4_nickname"))
            name = self.flow.answers.get("name", "Boss")
            chips = [(name, name)]
            if len(name) > 3:
                chips.append((name[:3], name[:3]))
            chips.extend([("Boss", "Boss"), ("Chef", "Chef")])
            self._render_text_input_with_chips(
                placeholder=tr("onboarding.q4_placeholder"),
                chips=chips,
                can_skip=True,
            )

        elif step == 5:
            self._add_pet_bubble(tr("onboarding.q5_pronouns"))
            self._render_chips([
                (tr("onboarding.q5_chip_he"), "er / ihm"),
                (tr("onboarding.q5_chip_she"), "sie / ihr"),
                (tr("onboarding.q5_chip_they"), "they / them"),
                (tr("onboarding.q5_chip_name_only"), "name"),
            ], can_skip=True)

        elif step == 6:
            self._add_pet_bubble(tr("onboarding.q6_uses"))
            uses_options = [
                tr("onboarding.q6_chip_school"),
                tr("onboarding.q6_chip_work"),
                tr("onboarding.q6_chip_coding"),
                tr("onboarding.q6_chip_gaming"),
                tr("onboarding.q6_chip_creative"),
                tr("onboarding.q6_chip_surfing"),
            ]
            self._render_multi_chips(uses_options)

        elif step == 7:
            self._add_pet_bubble(tr("onboarding.q7_interests"))
            self._render_text_input(
                placeholder=tr("onboarding.q7_placeholder"),
                default_text=self.flow.answers.get("interests", ""),
                can_skip=True,
            )

        elif step == 8:
            self._add_pet_bubble(tr("onboarding.q8_tone"))
            self._render_chips([
                (tr("onboarding.q8_chip_sweet"), "lieb"),
                (tr("onboarding.q8_chip_cheeky"), "frech"),
                (tr("onboarding.q8_chip_calm"), "ruhig"),
                (tr("onboarding.q8_chip_smart"), "schlau"),
            ], can_skip=True)

        elif step == 9:
            self._add_pet_bubble(tr("onboarding.q9_chatter"))
            self._render_chips([
                (tr("onboarding.q9_chip_often"), "oft"),
                (tr("onboarding.q9_chip_sometimes"), "ab und zu"),
                (tr("onboarding.q9_chip_rare"), "nie"),
            ], can_skip=True)

        elif step == 10:
            self._add_pet_bubble(tr("onboarding.q10_city"))
            self._render_text_input(
                placeholder=tr("onboarding.q10_placeholder"),
                default_text=self.flow.answers.get("city", ""),
                can_skip=True,
            )

        elif step == 11:
            self._add_pet_bubble(tr("onboarding.q11_key"))
            self._render_key_input()

        elif step == 12:
            self._add_pet_bubble(tr("onboarding.q12_character"))
            self._render_character_gallery()

        elif step == 13:
            self._add_pet_bubble(tr("onboarding.q13_privacy"))
            self._render_privacy_toggles()

        elif step == 14:
            self._add_pet_bubble(tr("onboarding.q14_autostart"))
            self._render_chips([
                (tr("onboarding.q14_chip_yes"), "ja"),
                (tr("onboarding.q14_chip_no"), "nein"),
            ], can_skip=True)

        elif step == 15:
            self._add_pet_bubble(tr("onboarding.q15_done", user_name=u_name))
            self._render_done_button()

    # -- UI-Generatoren fuer Eingabe-Elemente -------------------------------------------
    def _render_chips(self, chips: list[tuple[str, Any]], can_skip: bool = False) -> None:
        # Raster statt einer Zeile: lange Chips ("🥰 lieb & verspielt") wurden sonst zusammengequetscht
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        cols = 2 if len(chips) > 2 else len(chips)
        for i, (label, val) in enumerate(chips):
            btn = QPushButton(_btn_text(label))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #3A3C43; color: #F2F3F5; border-radius: 14px;
                    padding: 9px 16px; font-size: 10pt; font-weight: 500; border: none;
                }
                QPushButton:hover { background: #FF8FB1; color: #26282C; }
            """)
            btn.setMinimumWidth(btn.sizeHint().width())
            btn.clicked.connect(lambda _=False, v=val, l=label: self._handle_answer(v, l))
            grid.addWidget(btn, i // cols, i % cols)
        self.input_lay.addLayout(grid)

        if can_skip:
            self.input_lay.addLayout(self._skip_row())

    def _skip_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)
        btn_skip = QPushButton(tr("onboarding.btn_skip"))
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.setStyleSheet("background: transparent; color: #8D919B; font-size: 9.5pt; padding: 4px 8px;")
        btn_skip.setMinimumWidth(btn_skip.sizeHint().width())
        btn_skip.clicked.connect(self._handle_skip)
        row.addWidget(btn_skip)
        return row

    def _render_text_input(self, placeholder: str, default_text: str = "", can_skip: bool = False) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)

        edit = QLineEdit(default_text)
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet("""
            QLineEdit {
                background: #33353B; color: #F2F3F5; border: 1px solid #55575F;
                border-radius: 10px; padding: 8px 12px; font-size: 10pt;
            }
            QLineEdit:focus { border: 1px solid #FF8FB1; }
        """)

        btn_send = QPushButton(tr("onboarding.btn_send"))
        btn_send.setObjectName("primary")
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.clicked.connect(lambda: self._handle_answer(edit.text().strip(), edit.text().strip()))
        edit.returnPressed.connect(btn_send.click)

        row.addWidget(edit, 1)
        row.addWidget(btn_send)

        if can_skip:
            row.addLayout(self._skip_row())

        self.input_lay.addLayout(row)
        QTimer.singleShot(50, edit.setFocus)

    def _render_text_input_with_chips(self, placeholder: str, chips: list[tuple[str, Any]], can_skip: bool = True) -> None:
        chip_row = QHBoxLayout()
        chip_row.setSpacing(6)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet("""
            QLineEdit {
                background: #33353B; color: #F2F3F5; border: 1px solid #55575F;
                border-radius: 10px; padding: 8px 12px; font-size: 10pt;
            }
            QLineEdit:focus { border: 1px solid #FF8FB1; }
        """)

        for label, val in chips:
            btn = QPushButton(_btn_text(label))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #33353B; color: #F2F3F5; border: 1px solid #4E525C;
                    border-radius: 12px; padding: 5px 12px; font-size: 9.5pt; font-weight: 500;
                }
                QPushButton:hover { background: #FF8FB1; color: #26282C; border: 1px solid #FF8FB1; }
            """)
            btn.clicked.connect(lambda _=False, v=val, l=label: self._handle_answer(v, l))
            chip_row.addWidget(btn)

        chip_row.addStretch(1)
        self.input_lay.addLayout(chip_row)

        row = QHBoxLayout()
        row.setSpacing(8)

        btn_send = QPushButton(tr("onboarding.btn_send"))
        btn_send.setObjectName("primary")
        btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send.clicked.connect(lambda: self._handle_answer(edit.text().strip(), edit.text().strip()))
        edit.returnPressed.connect(btn_send.click)

        row.addWidget(edit, 1)
        row.addWidget(btn_send)

        if can_skip:
            row.addLayout(self._skip_row())

        self.input_lay.addLayout(row)
        QTimer.singleShot(50, edit.setFocus)

    def _render_multi_chips(self, options: list[str]) -> None:
        grid = QGridLayout()
        grid.setSpacing(6)
        selected_buttons: dict[str, QPushButton] = {}

        for i, opt in enumerate(options):
            btn = QPushButton(_btn_text(opt))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #3A3C43; color: #F2F3F5; border-radius: 12px;
                    padding: 6px 14px; font-size: 9.5pt;
                }
                QPushButton:checked {
                    background: #FF8FB1; color: #26282C; font-weight: bold;
                }
            """)
            btn.setMinimumWidth(btn.sizeHint().width())
            selected_buttons[opt] = btn
            grid.addWidget(btn, i // 3, i % 3)

        self.input_lay.addLayout(grid)

        def _on_next():
            sel = [opt for opt, b in selected_buttons.items() if b.isChecked()]
            disp = ", ".join(sel) if sel else "Keine"
            self._handle_answer(sel, disp)

        btn_row = QHBoxLayout()
        btn_next = QPushButton(tr("onboarding.btn_next"))
        btn_next.setObjectName("primary")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(_on_next)
        btn_row.addWidget(btn_next)
        btn_row.addStretch(1)

        btn_row.addLayout(self._skip_row())

        self.input_lay.addLayout(btn_row)

    def _render_key_input(self) -> None:
        top_row = QHBoxLayout()
        btn_get_key = QPushButton(tr("onboarding.q11_get_key"))
        btn_get_key.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_get_key.setStyleSheet("background: #2D3748; color: #90CDF4; border-radius: 8px; padding: 6px 12px; font-size: 9pt;")
        btn_get_key.clicked.connect(lambda: __import__("webbrowser").open("https://aistudio.google.com/app/apikey"))
        top_row.addWidget(btn_get_key)
        top_row.addStretch(1)
        self.input_lay.addLayout(top_row)

        row = QHBoxLayout()
        row.setSpacing(8)

        edit = QLineEdit()
        edit.setPlaceholderText(tr("onboarding.q11_placeholder"))
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setStyleSheet("""
            QLineEdit {
                background: #33353B; color: #F2F3F5; border: 1px solid #55575F;
                border-radius: 10px; padding: 8px 12px; font-size: 10pt;
            }
            QLineEdit:focus { border: 1px solid #FF8FB1; }
        """)

        btn_check = QPushButton(tr("onboarding.q11_btn_check"))
        btn_check.setObjectName("primary")
        btn_check.setCursor(Qt.CursorShape.PointingHandCursor)

        def _do_validate():
            key = edit.text().strip()
            if not key:
                return
            btn_check.setEnabled(False)
            btn_check.setText("...")
            thread = KeyValidationWorker(key)
            thread.validation_done.connect(lambda ok, msg: self._on_key_validated(ok, msg, thread, key))
            thread.finished.connect(self._reap_threads)
            self._threads.add(thread)
            thread.start()

        btn_check.clicked.connect(_do_validate)
        edit.returnPressed.connect(btn_check.click)

        row.addWidget(edit, 1)
        row.addWidget(btn_check)

        btn_skip = QPushButton(tr("onboarding.q11_skip"))
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.setStyleSheet("background: transparent; color: #8D919B; font-size: 9.5pt;")
        btn_skip.clicked.connect(self._handle_skip)
        row.addWidget(btn_skip)

        self.input_lay.addLayout(row)
        QTimer.singleShot(50, edit.setFocus)

    def _on_key_validated(self, ok: bool, msg: str, thread: QThread, key: str) -> None:
        thread.quit()
        if ok:
            self.avatar.pop_hearts()
            self._add_user_bubble("🔑 [API-Key eingegeben]")
            self._add_pet_bubble(tr("onboarding.q11_success"))
            self.flow.submit_answer(key)
            QTimer.singleShot(800, self._render_current_step)
        else:
            self._add_pet_bubble(tr("onboarding.q11_invalid"))
            self._clear_input_area()
            self._render_key_input()

    def _render_character_gallery(self) -> None:
        scroll = QScrollArea()
        scroll.setFixedHeight(68)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:horizontal {
                background: #1E1F24; height: 6px; margin: 0px 4px; border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #4E525C; min-width: 24px; border-radius: 3px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #FF8FB1;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        cont = QWidget()
        cont.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(cont)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        active_cid = self.avatar.character_id

        for cid, info in CHARACTERS.items():
            btn = QPushButton(f"{info.get('emoji', '')} {info.get('name', cid)}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = (cid == active_cid)
            bg = "#FF8FB1" if is_active else "#33353B"
            fg = "#26282C" if is_active else "#F2F3F5"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; color: {fg}; border-radius: 10px;
                    padding: 8px 12px; font-size: 9.5pt; font-weight: 500;
                }}
                QPushButton:hover {{ background: #FFA5C0; color: #26282C; }}
            """)

            def _choose(_=False, c=cid):
                self.avatar.set_character(c)
                self.avatar.pop_hearts()
                self._clear_input_area()
                self._render_character_gallery()

            btn.clicked.connect(_choose)
            lay.addWidget(btn)

        lay.addStretch(1)
        scroll.setWidget(cont)
        self.input_lay.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_keep = QPushButton(tr("onboarding.q12_btn_keep"))
        btn_keep.setObjectName("primary")
        btn_keep.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_keep.clicked.connect(lambda: self._handle_answer(self.avatar.character_id, get_character_info(self.avatar.character_id).get("name", "Kylie")))
        btn_row.addWidget(btn_keep)
        btn_row.addStretch(1)
        self.input_lay.addLayout(btn_row)

    def _render_privacy_toggles(self) -> None:
        priv = self.cfg.get("privacy", {}) or {}
        chk_save = QCheckBox(tr("data.chk_save_chats"))
        chk_save.setChecked(bool(priv.get("save_chats", True)))

        cname = get_character_info(self.avatar.character_id).get("name", "Kylie")
        chk_rem = QCheckBox(tr("data.chk_remember", name=cname))
        chk_rem.setChecked(bool(priv.get("remember", True)))

        chk_hist = QCheckBox(tr("data.chk_use_history"))
        chk_hist.setChecked(bool(priv.get("use_history", True)))

        self.input_lay.addWidget(chk_save)
        self.input_lay.addWidget(chk_rem)
        self.input_lay.addWidget(chk_hist)

        def _on_next():
            data = {
                "save_chats": chk_save.isChecked(),
                "remember": chk_rem.isChecked(),
                "use_history": chk_hist.isChecked(),
            }
            self._handle_answer(data, "Datenschutz bestätigt ✓")

        btn_row = QHBoxLayout()
        btn_next = QPushButton(tr("onboarding.btn_next"))
        btn_next.setObjectName("primary")
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(_on_next)
        btn_row.addWidget(btn_next)
        btn_row.addStretch(1)
        self.input_lay.addLayout(btn_row)

    def _render_done_button(self) -> None:
        btn_row = QHBoxLayout()
        btn_start = QPushButton(tr("onboarding.btn_start"))
        btn_start.setObjectName("primary")
        btn_start.setMinimumHeight(42)
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.setStyleSheet("""
            QPushButton#primary {
                background: #FF8FB1; color: #26282C; font-size: 11pt; font-weight: bold;
                border-radius: 12px; padding: 10px 28px;
            }
            QPushButton#primary:hover { background: #FFA5C0; }
        """)
        btn_start.clicked.connect(self._on_finish_clicked)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_start)
        btn_row.addStretch(1)
        self.input_lay.addLayout(btn_row)

    # -- Antwortverarbeitung & Gemini-Reaktion -----------------------------------------
    def _handle_answer(self, value: Any, display_text: str = "") -> None:
        if self._is_waiting:
            return

        disp = display_text or str(value)
        self._add_user_bubble(disp)
        self.avatar.pop_hearts()

        # Pruefen, ob Schritt valide
        step_before = self.flow.current_step()
        ok = self.flow.submit_answer(value)
        if not ok and step_before == 1 and str(value).lower() == "later":
            self.accept()
            return
        if not ok:
            return

        # Bei Schritt 15 oder wenn kein Key da ist: direkt weiter
        if self.flow.is_done() or not gemini.has_key() or step_before in (1, 2, 11, 13, 14, 15):
            self._clear_input_area()
            self._show_typing()
            QTimer.singleShot(450, self._render_current_step)
            return

        # Mit Gemini-Key: kurze dynamische Reaktion einholen
        self._is_waiting = True
        self._clear_input_area()
        self._show_typing()

        prof_summary = f"Name: {self.flow.answers.get('name', '')}, Hobbys: {self.flow.answers.get('interests', '')}, Ton: {self.flow.answers.get('tone', '')}"
        worker = OnboardingReactionWorker(
            self.avatar.character_id,
            prof_summary,
            question=str(step_before),
            user_answer=str(value),
            lang=i18n.lang(),
        )
        worker.reaction_ready.connect(lambda reply: self._on_reaction_received(reply, worker))
        worker.finished.connect(self._reap_threads)
        self._threads.add(worker)
        worker.start()

    def _on_reaction_received(self, reply: str, worker: QThread) -> None:
        worker.quit()
        self._is_waiting = False
        self._hide_typing()
        self._add_pet_bubble(reply)
        QTimer.singleShot(550, self._render_current_step)

    def _handle_skip(self) -> None:
        if self._is_waiting:
            return
        self._add_user_bubble(f"({tr('onboarding.btn_skip')})")
        self.flow.skip_current_step()
        self._clear_input_area()
        self._show_typing()
        QTimer.singleShot(400, self._render_current_step)

    def _on_later_clicked(self) -> None:
        self.flow.skip_later()
        self.reject()

    def _on_finish_clicked(self) -> None:
        self.flow.finish()
        self.accept()

    def _reap_threads(self) -> None:
        dead = {t for t in self._threads if t.isFinished()}
        for t in dead:
            t.wait()
            self._threads.remove(t)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._on_later_clicked()
        else:
            super().keyPressEvent(event)
