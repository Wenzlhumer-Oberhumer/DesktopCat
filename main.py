# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Einstiegspunkt: baut Pet, Sprechblase, Eingabeleiste, Gehirn und Tray-Icon zusammen."""
from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import datetime
import os
import random
import sys
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

from paths import APP_DIR, DATA_DIR, FROZEN, set_autostart
from updater import CheckUpdateWorker, DownloadUpdateWorker, launch_installer
from version import __version__
import i18n
from i18n import tr


# Sicherstellen, dass Module aus APP_DIR importiert werden koennen, auch nach os.chdir(DATA_DIR)
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

_is_test_mode = bool(
    os.environ.get("DESKTOPCAT_TEST")
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    or os.environ.get("PYTEST_CURRENT_TEST")
    or "unittest" in sys.modules
    or "pytest" in sys.modules
    or any("test" in arg.lower() for arg in sys.argv)
)

if not _is_test_mode:
    os.chdir(DATA_DIR)

# Unter pythonw.exe gibt es keine Konsole -> stdout/stderr in Logdatei umleiten
# Logdatei bei > 2 MB beim Start nach buddy.log.1 rotieren (nur im normalen Betrieb, nie in Tests)
if not _is_test_mode and not os.environ.get("DESKTOPCAT_NO_LOG"):
    log_path = DATA_DIR / "buddy.log"
    try:
        if log_path.exists() and log_path.stat().st_size > 2 * 1024 * 1024:
            backup = DATA_DIR / "buddy.log.1"
            if backup.exists():
                backup.unlink()
            log_path.rename(backup)
    except Exception:
        pass

    class _TeeStream:
        """Schreibt Ausgaben sowohl in die Konsole (falls vorhanden) als auch in buddy.log."""

        def __init__(self, console_stream, log_file):
            self._console = console_stream
            self._file = log_file

        def write(self, data):
            if self._console:
                try:
                    self._console.write(data)
                except Exception:
                    pass
            if self._file:
                try:
                    self._file.write(data)
                except Exception:
                    pass

        def flush(self):
            if self._console:
                try:
                    self._console.flush()
                except Exception:
                    pass
            if self._file:
                try:
                    self._file.flush()
                except Exception:
                    pass

    try:
        _log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = _TeeStream(sys.stdout, _log_file)
        sys.stderr = _TeeStream(sys.stderr, _log_file)
    except Exception:
        pass

import gemini
from PyQt6.QtCore import (
    QAbstractNativeEventFilter, QBuffer, QObject, QPoint, QRect, QStandardPaths,
    QThread, QTimer, pyqtSignal, pyqtSlot,
)
from PyQt6.QtGui import QAction, QGuiApplication, QIcon, QScreen
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from agent_brain import AgentBrain, name_reaction
from config import Config
from pet_sprites import render_icon
try:
    from pet_sprites import get_character_info
except ImportError:         # alte pet_sprites ohne Charakter-Registry
    def get_character_info(char_id):
        return {}
from pet_window import PetState, PetWindow, is_night, style_menu
from settings_dialog import SettingsDialog
from speech_bubble import BriefingCard, ExplainCard, InputBar, SpeechBubble
import tools
from accessories import (
    calculate_cpu_percent,
    get_ram_load_percent,
    get_system_times,
    seasonal_accessory,
    weather_accessories,
)
from guide_overlay import GuideOverlay
from it_guide import GuideSession, GuideWorker, pixmap_to_b64
import voice_recorder
import voice_tts

class WeatherWorker(QThread):
    finished_with_result = pyqtSignal(object)

    def run(self) -> None:
        try:
            res = tools.get_weather()
            self.finished_with_result.emit(res)
        except Exception:
            pass


class ErrorDoctorWorker(QThread):
    finished_with_result = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, image_b64: str):
        super().__init__()
        self.image_b64 = image_b64

    def run(self) -> None:
        try:
            prompt = (
                "Du bist ein geduldiger und kompetenter IT-Helfer. Schau dir den Screenshot an.\n"
                "Findest du eine Fehlermeldung oder ein technisches Problem?\n"
                "Erkläre die sichtbare Fehlermeldung in einfachen, verständlichen Worten auf Deutsch (2–3 Sätze).\n"
                "Gib danach 1–3 konkrete Lösungsschritte an.\n"
                "Wenn keine Fehlermeldung oder Problem sichtbar ist, erkläre freundlich, dass du keinen Fehler siehst."
            )
            ans = gemini.ask(prompt, timeout_s=45.0, image_b64=self.image_b64)
            self.finished_with_result.emit(ans)
        except Exception as exc:
            self.failed.emit(str(exc))


class ClipboardExplainWorker(QThread):
    finished_with_result = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, mode: str, text: str):
        super().__init__()
        self.mode = mode
        self.text = text

    def run(self) -> None:
        try:
            if self.mode == "explain":
                title = "💡 Erklärung"
                prompt = f"Erkläre folgenden Text einfach und verständlich auf Deutsch:\n\n{self.text}"
            elif self.mode == "translate":
                title = "🌍 Übersetzung"
                prompt = (
                    "Übersetze folgenden Text. Wenn er deutsch ist, übersetze auf Englisch. "
                    f"Wenn er englisch oder in einer anderen Sprache ist, übersetze auf Deutsch:\n\n{self.text}"
                )
            elif self.mode == "summarize":
                title = "📝 Zusammenfassung"
                prompt = f"Fasse folgenden Text kurz und prägnant in Stichpunkten zusammen:\n\n{self.text}"
            elif self.mode == "improve":
                title = "✍️ Verbessert"
                prompt = f"Verbessere folgenden Text stilistisch und grammatikalisch auf Deutsch:\n\n{self.text}"
            else:
                title = "💡 Text"
                prompt = f"Erkläre folgenden Text:\n\n{self.text}"

            ans = gemini.ask(prompt, timeout_s=40.0)
            self.finished_with_result.emit(title, ans)
        except Exception as exc:
            self.failed.emit(str(exc))

APP_ID = "MochiDesktopBuddy"
HOTKEY_ID = 0xB0B0
EXPLAIN_HOTKEY_ID = 0xB0B1
VOICE_HOTKEY_ID = 0xB0B2
WM_HOTKEY = 0x0312


class VoiceWorker(QThread):
    """Verarbeitet Sprachaufnahmen multimodul per Gemini Flash in 16kHz WAV."""

    finished_with_result = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, audio_path: str, cfg: dict):
        super().__init__()
        self.audio_path = audio_path
        self.cfg = cfg

    def run(self) -> None:
        try:
            user = str(self.cfg.get("pet", {}).get("user_name", "Boss")).strip() or "Boss"
            cinfo = get_character_info(self.cfg.get("pet", {}).get("character", "cat_mochi"))
            who = cinfo.get("ai_persona") or "Du bist Kylie, ein extrem neugieriger, süßer Katzen-Buddy."
            prompt = (
                f"{who} Der Nutzer ('{user}') spricht gerade direkt mit dir per Sprache. "
                f"Höre dir die Audio-Aufnahme genau an. Verstehe die Frage, Bemerkung oder den Wunsch "
                f"und antworte kurz, liebenswert und charmant auf Deutsch (maximal 1-3 Sätze). "
                f"Nenne den Nutzer gerne '{user}'. "
                f"Verwende keine langen Aufzählungen oder Formatierungen, da deine Antwort auch laut mit Stimme vorgelesen wird."
            )
            ans = gemini.ask_audio(self.audio_path, prompt=prompt, timeout_s=45.0)
            self.finished_with_result.emit(ans)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if os.path.exists(self.audio_path):
                try:
                    os.remove(self.audio_path)
                except OSError:
                    pass


class AmbientVisionWorker(QObject):
    """Analysiert im Hintergrund den Bildschirm und das aktive Fenster per Gemini Vision oder Kontext."""

    finished = pyqtSignal(str)

    def __init__(self, b64_img: str, top_window: str, open_apps: list[str], cfg: dict):
        super().__init__()
        self.b64_img = b64_img
        self.top_window = top_window
        self.open_apps = open_apps
        self.cfg = cfg

    @pyqtSlot()
    def run(self) -> None:
        try:
            comment = self._analyze()
        except Exception:
            comment = ""
        user = str(self.cfg.get("pet", {}).get("user_name", "Boss")).strip() or "Boss"
        self.finished.emit((comment or "").replace("Boss", user))

    def _analyze(self) -> str:
        top = self.top_window or ""
        top_low = top.lower()
        apps_str = ", ".join(self.open_apps[:6])
        user = str(self.cfg.get("pet", {}).get("user_name", "Boss")).strip() or "Boss"
        cinfo = get_character_info(self.cfg.get("pet", {}).get("character", "cat_mochi"))
        who = cinfo.get("ai_persona") or "Du bist Kylie, ein extrem neugieriger, süßer Katzen-Buddy."

        # Schritt 1: Cloud-Vision ueber die Gemini API, falls ein Key hinterlegt ist
        if (self.cfg.get('ai', {}).get('enabled', True)
                and self.cfg.get('privacy', {}).get('auto_vision', False)
                and gemini.has_key() and self.b64_img):
            try:
                prompt = (
                    f"{who} Du lebst als Desktop-Buddy auf dem Windows-Desktop des Nutzers ('{user}'). "
                    f"Aktives Fenster von {user}: '{top}'. Offene Programme: {apps_str}.\n"
                    f"Schau dir den Screenshot und das aktive Fenster genau an. Was macht {user} gerade (z. B. Coden in Angular/Python/React, Dokumente schreiben, Recherche, Surfen, Design)?\n"
                    "Reagiere spontan, lebensfroh und liebenswert darauf:\n"
                    "- Sag kurz, wie du es findest,\n"
                    "- ODER biete ihm charmant deine Hilfe an bzw. stelle eine neugierige Frage dazu.\n"
                    "WICHTIG:\n"
                    "- Maximal 1-2 kurze Sätze auf Deutsch.\n"
                    "- Höchstens ein Emoji.\n"
                    f"- Nenne den Nutzer gern '{user}'.\n"
                    "- Sei niemals belehrend, sondern sympathisch und neugierig."
                )
                comment = gemini.ask(prompt, timeout_s=45, image_b64=self.b64_img)
                if comment:
                    return comment
            except Exception:
                pass

        # Schritt 2: Intelligenter heuristischer Kontext (falls Offline oder API Rate-Limit)
        if "angular" in top_low:
            return random.choice([
                "Schön, was du da in Angular programmierst, Boss! 🅰️✨ Brauchst du Tipps für Routing, Signals oder Services?",
                "Angular-Code sieht super strukturiert aus! 🐾 Soll ich dir Notizen oder ein Testskript anlegen?",
                "Fleißig am Angular-Projekt! 💻 Sieht spannend aus, soll ich dir bei Komponenten helfen?",
            ])
        elif any(k in top_low for k in ("react", "next.js", "nextjs", "vue", "vite")):
            return random.choice([
                "Frontend-Magie mit React/Vue am Start! ⚛️✨ Sieht richtig modern aus, Boss!",
                "Coole Komponenten! 🐾 Sag Bescheid, wenn du Hilfe bei Props, Hooks oder State brauchst.",
            ])
        elif any(k in top_low for k in ("python", ".py", "pytest")):
            return random.choice([
                "Fleißig am Python-Coden, Boss! 🐍🐾 Sieht nach einem spannenden Skript aus, soll ich was testen?",
                "Python-Power am Start! 🐍✨ Brauchst du Hilfe bei Bibliotheken oder Datenstrukturen?",
            ])
        elif any(k in top_low for k in (".ts", ".js", "typescript", "javascript")):
            return "Sauberer TypeScript-Code! 💻✨ Typen sitzen, alles läuft stabil!"
        elif any(k in top_low for k in ("code", "antigravity", "visual studio", "pycharm", "webstorm")):
            app_name = top.split(" - ")[-1] if " - " in top else "deinem Editor"
            return random.choice([
                f"Voller Fokus beim Programmieren in {app_name}! 💻🐾 Sieht spannend aus, Boss!",
                "Fleißig am Tippen! ⌨️✨ Soll ich dir bei irgendwas zur Hand gehen?",
            ])
        elif any(k in top_low for k in ("powershell", "cmd.exe", "terminal")):
            return "Kommandozeilen-Profi am Werk! ⚡ Sag Bescheid, wenn ich einen Befehl ausführen soll."
        elif any(k in top_low for k in ("chrome", "vivaldi", "firefox", "edge", "github", "stack overflow")):
            if "stack overflow" in top_low or "github" in top_low:
                return "Spannende Recherche auf Entwickler-Seiten! 🌐🐾 Wenn du eine Doku zusammenfassen sollst, frag mich einfach!"
            return "Auf Recherche-Tour im Web, Boss? 🌐🔍 Sieht interessant aus!"

        return ""

CLICK_LINES = [
    "Miau~ \U0001F496", "Schnurr schnurr \U0001F63A", "Hihi, das kitzelt! \U0001F6B8", "Nyaa~ \u2728",
    "Streicheln erlaubt! \U0001F43E", "Pfoten-High-Five! \U0001F43E",
    "Mehr Kraulen, bitte~ \U0001F63B",
]
CHATTER_LINES = [
    "Brauchst du was? Doppelklick auf mich! \U0001F43E", "Ich pass auf deinen Desktop auf \U0001F440",
    "Ein bisschen Wasser trinken waere gut, Boss \U0001F4A7", "Sitzt du gut? Kurz strecken! \U0001F638",
    "Soll ich den Desktop aufraeumen? \U0001F9F9", "*gaehn* ... ich bin wach! \U0001F63A",
]

_MODS = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}


def parse_hotkey(spec: str):
    """'ctrl+alt+p' -> (modifiers, vk) oder None."""
    mods, vk = 0, None
    for part in (spec or "").lower().replace(" ", "").split("+"):
        if part in _MODS:
            mods |= _MODS[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif part.startswith("f") and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            vk = 0x70 + int(part[1:]) - 1
        elif part == "space":
            vk = 0x20
    return (mods, vk) if vk else None


class HotkeyFilter(QAbstractNativeEventFilter):
    """Globales Tastenkuerzel (RegisterHotKey) - unterstuetzt mehrere Hotkeys (z. B. Eingabeleiste & Kopieren/Erklaeren)."""

    def __init__(self, callback=None):
        super().__init__()
        self._cbs: dict[int, Callable] = {}
        if callback is not None:
            self._cbs[HOTKEY_ID] = callback
        self.registered_ids: set[int] = set()

    def register(self, spec: str, hotkey_id: int = HOTKEY_ID, callback=None) -> bool:
        parsed = parse_hotkey(spec)
        if not parsed:
            return False
        mods, vk = parsed
        if callback is not None:
            self._cbs[hotkey_id] = callback
        try:
            ok = bool(ctypes.windll.user32.RegisterHotKey(None, hotkey_id, mods | 0x4000, vk))  # MOD_NOREPEAT
            if ok:
                self.registered_ids.add(hotkey_id)
            return ok
        except Exception:
            return False

    def unregister(self, hotkey_id: Optional[int] = None) -> None:
        try:
            if hotkey_id is not None:
                if hotkey_id in self.registered_ids:
                    ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
                    self.registered_ids.discard(hotkey_id)
            else:
                for hid in list(self.registered_ids):
                    ctypes.windll.user32.UnregisterHotKey(None, hid)
                self.registered_ids.clear()
        except Exception:
            pass

    def nativeEventFilter(self, eventType, message):
        try:
            if bytes(eventType) == b"windows_generic_MSG":
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam in self._cbs:
                    cb = self._cbs[msg.wParam]
                    QTimer.singleShot(0, cb)
        except Exception:
            pass
        return False, 0


def _is_fullscreen_foreground() -> bool:
    """True, wenn ein Vollbild-Fenster (Praesentation, Video, Spiel) im Vordergrund ist."""
    try:
        u32 = ctypes.windll.user32
        hwnd = u32.GetForegroundWindow()
        if not hwnd:
            return False
        cls = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(hwnd, cls, 64)
        if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
            return False
        r = ctypes.wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        return any(r.left <= g.left() and r.top <= g.top() and r.right >= g.right() + 1 and r.bottom >= g.bottom() + 1
                   for g in (s.geometry() for s in QGuiApplication.screens()))
    except Exception:
        return False


class _PowerStatus(ctypes.Structure):
    _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("percent", ctypes.c_ubyte),
                ("sys", ctypes.c_ubyte), ("life", ctypes.c_ulong), ("full", ctypes.c_ulong)]


def _battery() -> tuple[int, bool]:
    """(Prozent, am Netzteil); (-1, True) wenn kein Akku/unbekannt."""
    try:
        st = _PowerStatus()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)) and st.percent <= 100 and st.flag != 128:
            return int(st.percent), st.ac == 1
    except Exception:
        pass
    return -1, True


class Buddy(QObject):
    """Verdrahtet alle Module miteinander."""

    timer_expired = pyqtSignal(str, int, str)      # kommt aus einem Hintergrund-Thread (tools-Timer)
    data_wiped = pyqtSignal()
    routine_message = pyqtSignal(str)              # aus dem Routinen-Thread -> Sprechblase im Main-Thread                      # "Alles vergessen" - evtl. aus dem Agent-Thread

    def __init__(self, app: QApplication, cfg: Config):
        super().__init__()
        self.app, self.cfg = app, cfg
        i18n.set_language(str(cfg.get("language", "de")))
        self.pet = PetWindow(cfg, APP_DIR)

        self.bubble = SpeechBubble(cfg)
        self.briefing_card = BriefingCard()
        self.input = InputBar()
        from interaction_card import InteractionCard
        self.interaction_card = InteractionCard()
        self._active_interaction = None
        self._interaction_ready_at = time.time() + 180
        self._interaction_watchdog = QTimer(self)
        self._interaction_watchdog.timeout.connect(self._check_active_interaction)
        self.brain = AgentBrain(cfg)
        self._settings_open = False

        # Tray-Icon (auch Quelle fuer Windows-Benachrichtigungen)
        self.icon = QIcon(render_icon(64))
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip(tr("tray.tooltip"))
        self.tray_menu = style_menu(QMenu())
        self.tray_menu.aboutToShow.connect(self._update_tray_menu)
        self._update_tray_menu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray)
        self.tray.show()

        # Signale
        self.timer_expired.connect(self._on_timer_expired)
        try:
            tools.register_timer_callback(lambda label, sec, u: self.timer_expired.emit(label, int(sec), u or ""))
        except AttributeError:      # tools.py ohne Timer-Unterstuetzung
            pass
        self.pet.moved.connect(self._follow)
        self.pet.character_changed.connect(self._on_character_changed)
        self.pet.treat_given.connect(self._on_treat)
        self.pet.petted.connect(self._on_petted)
        self.pet.command_requested.connect(self._on_submit)
        self.pet.input_requested.connect(self.open_input)
        self.pet.chats_requested.connect(self.open_chat_history)
        self.pet.data_requested.connect(self.open_my_data)
        self.pet.settings_requested.connect(self.open_settings)
        self.pet.quit_requested.connect(self.quit)
        self.bubble.clicked.connect(self._on_bubble_clicked)
        self.input.submitted.connect(self._on_submit)
        self.input.closed.connect(self._on_input_closed)
        self.interaction_card.answered.connect(self._complete_interaction)
        self.interaction_card.dismissed.connect(self._dismiss_interaction)
        self.interaction_card.pause_requested.connect(self.pause_pet_questions)
        self.pet.interaction_requested.connect(self.start_pet_interaction)
        self.brain.started.connect(self._on_task_started)
        self.brain.finished.connect(self._on_task_finished)
        self.brain.it_guide_requested.connect(self.start_it_guide)
        self.pet.error_doctor_requested.connect(self.start_error_doctor)
        self.pet.friendship_requested.connect(self.open_friendship_dialog)
        self.pet.focus_stats_requested.connect(self.open_focus_stats_dialog)
        self.pet.flashcards_requested.connect(self.open_flashcards_dialog)
        self.pet.photobox_requested.connect(self.start_photobox)
        self.pet.new_note_requested.connect(lambda: self.create_sticky_note())
        self.pet.onboarding_requested.connect(lambda: self._open_onboarding(is_update=True))
        self.pet.wash_requested.connect(self._on_wash)
        self.pet.character_tree_requested.connect(self.open_character_tree)
        self.pet.bubble_game_requested.connect(self.start_bubble_game)
        self.pet.yarn_game_requested.connect(self.start_yarn_game)
        self.pet.wallpaper_requested.connect(self.activate_lively_wallpaper)
        self.pet.restore_wallpaper_requested.connect(self.restore_desktop_wallpaper)
        self.pet.pet_bed_requested.connect(self.toggle_pet_bed)
        self.pet.scripts_requested.connect(self.open_scripts_dialog)
        self.pet.home_mode_toggled.connect(self.set_home_mode)
        self.pet.hide_requested.connect(self.hide_pet)
        self.pet.focus_mode_requested.connect(self.start_focus_mode)
        self.tray.messageClicked.connect(self._on_tray_message_clicked)
        self._focus_mode: bool = False

        from sticky_notes import StickyNoteManager
        from memory_store import get_memory_store
        self.note_manager = StickyNoteManager(get_memory_store(), on_note_done_cb=self._on_note_completed)
        from memory_store import MemoryStore
        MemoryStore.on_wipe.append(self.data_wiped.emit)
        self.routine_message.connect(self._on_routine_message)
        self.data_wiped.connect(self._on_data_wiped)
        self._quiz_session: Optional[dict] = None
        self._last_photo_folder: Optional[str] = None

        # v2.4.0: Möbel (Katzenbett) & Minispiele
        from furniture import PetBedWidget
        self.pet_bed = PetBedWidget(cfg)
        self.pet.pet_bed = self.pet_bed
        self.pet_bed.bed_moved.connect(self.pet.on_bed_moved)
        self.pet_bed.hide_requested.connect(lambda: self.toggle_pet_bed(False))
        self.pet_bed.bed_moved.connect(lambda *_: self.pet.raise_())
        if bool(cfg.get("furniture.bed_visible", True)):
            self.pet_bed.show()
            self.pet.raise_()
        else:
            self.pet_bed.hide()

        from minigames import BubblePopGameManager, YarnBallWidget
        self.bubble_mgr = BubblePopGameManager(get_memory_store(), cfg)
        self.yarn_ball: Optional[YarnBallWidget] = None

        self._wallpaper_worker = None
        if bool(cfg.get("lively.auto_sync", False)):
            QTimer.singleShot(1000, self.activate_lively_wallpaper)
        elif cfg.get('lively.active', False):
            QTimer.singleShot(1000, self.restore_desktop_wallpaper)

        self.explain_card = ExplainCard()
        self.guide_overlay: Optional[GuideOverlay] = None
        self._guide_session: Optional[GuideSession] = None
        self._guide_workers: set[QThread] = set()
        self._explain_workers: set[QThread] = set()
        self._error_doctor_workers: set[QThread] = set()

        self._last_ambient_comment = ""
        self._mochi_asked_question = False
        self._last_friendship_points = get_memory_store().get_friendship_points()
        self._pending_friendship_level = None
        self._friendship_timer = QTimer(self)
        self._friendship_timer.timeout.connect(self._refresh_friendship_progress)
        self._friendship_timer.start(500)
        self._vision_threads: set[QThread] = set()
        self._pending_update: dict | None = None
        from update_ui import UpdatePrompt
        self.update_prompt = UpdatePrompt()
        self.update_prompt.install_requested.connect(self._install_update_offer)
        self.update_prompt.later_requested.connect(self._defer_update)
        self._awaiting_update_reply = False
        self._update_worker: QThread | None = None
        self._download_worker: QThread | None = None
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(lambda: self._check_update(manual=False))
        self._update_timer.start(60 * 1000)

        # Globales Tastenkuerzel
        self.hotkey = HotkeyFilter(self._hotkey_pressed)
        self.app.installNativeEventFilter(self.hotkey)
        self._hotkey_ok = self.hotkey.register(cfg.get("hotkey", "ctrl+alt+p"))
        self._hotkey_explain_ok = self.hotkey.register(
            cfg.get("hotkey_explain", "ctrl+alt+e"),
            EXPLAIN_HOTKEY_ID,
            self._explain_hotkey_pressed,
        )

        # v3.0.0: Voice Interaktion, Lip-Sync & Push-to-Talk
        self._is_recording_voice = False
        self._is_processing_voice = False
        self._voice_worker: Optional[QThread] = None

        self._ptt_poll_timer = QTimer(self)
        self._ptt_poll_timer.timeout.connect(self._on_ptt_poll)

        tts = voice_tts.get_tts()
        tts.speaking_started.connect(lambda: self.pet.set_speaking(bool(self.cfg.get("voice.lipsync", True))))
        tts.speaking_finished.connect(lambda: self.pet.set_speaking(False))

        self._hotkey_voice_ok = self.hotkey.register(
            cfg.get("hotkey_voice", "ctrl+alt+space"),
            VOICE_HOTKEY_ID,
            self._voice_hotkey_pressed,
        )

        self._chatter = QTimer(self)
        self._chatter.setSingleShot(True)
        self._chatter.timeout.connect(self._on_chatter)

        # Wohlfuehl-Erinnerungen und Akku-Warnung
        self._wellbeing = QTimer(self)
        self._wellbeing.timeout.connect(self._on_wellbeing)
        self._wellbeing_water = False
        self._battery_timer = QTimer(self)
        self._battery_timer.timeout.connect(self._check_battery)
        self._battery_warned = False

        # Autonome Screen- und Coding-Beobachtung alle paar Minuten
        self._vision_timer = QTimer(self)
        self._vision_timer.setSingleShot(True)
        self._vision_timer.timeout.connect(self._on_autonomous_vision)

        # Phase 3: Neugier-Fragen, Fakten-Erinnerungen und Schlafenszeit
        self._curious_timer = QTimer(self)
        self._curious_timer.timeout.connect(self._on_curious_check)
        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._on_reminders_check)
        self._bedtime_timer = QTimer(self)
        self._bedtime_timer.timeout.connect(self._on_bedtime_check)

        # Phase 4: Zubehoer, Wetter-Outfits und PC-Fieber
        self._active_workers: list[QThread] = []
        self._last_system_times = get_system_times()
        self._high_cpu_count = 0
        self._last_fever_alert = 0.0
        self._weather_timer = QTimer(self)
        self._weather_timer.timeout.connect(self._check_weather_outfit)
        self._pc_fever_timer = QTimer(self)
        self._pc_fever_timer.timeout.connect(self._check_pc_fever)

        # v2.5.0: Autonome Routinen-Engine
        import custom_scripts
        custom_scripts.init_default_scripts()
        self._routines_timer = QTimer(self)
        self._routines_timer.timeout.connect(self._check_custom_routines)
        self._routines_timer.start(60 * 1000)
        QTimer.singleShot(3000, self._check_startup_routines)

    def user_name(self) -> str:
        return str(self.cfg.get("pet.user_name", "Boss")).strip() or "Boss"

    def char_info(self) -> dict:
        return get_character_info(self.pet.character)

    def _update_tray_menu(self) -> None:
        self.tray_menu.clear()
        cname = self.char_info().get("name", "Kylie")

        if getattr(self, "_focus_mode", False):
            self._act(self.tray_menu, tr("menu.end_focus_mode"), self.end_focus_mode)
            self.tray_menu.addSeparator()
            self._act(self.tray_menu, tr("menu.settings"), self.open_settings)
            self._act(self.tray_menu, tr("menu.quit"), self.quit)
            return

        if not gemini.has_key():
            self._act(self.tray_menu, tr("menu.enter_key"), self.open_settings)
            self.tray_menu.addSeparator()
        self._act(self.tray_menu, tr("menu.input"), self.open_input)
        self._act(self.tray_menu, '🐾  Time together' if i18n.lang() == 'en' else '🐾  Zeit miteinander', self.start_pet_interaction)
        pause_until = float(self.cfg.get('daily.interaction_pause_until', 0))
        if pause_until > time.time():
            stamp = datetime.datetime.fromtimestamp(pause_until).strftime('%H:%M')
            self._act(self.tray_menu, f'Fragen bis {stamp} pausiert – Pause beenden', self.resume_pet_questions)
        else:
            self._act(self.tray_menu, 'Fragen 1 Std. pausieren', self.pause_pet_questions)
        self._act(self.tray_menu, tr("menu.feed_pet", name=cname), self.pet.give_treat)
        if self.pet.isVisible():
            self._act(self.tray_menu, tr("menu.hide_pet", name=cname), self.hide_pet)
        else:
            self._act(self.tray_menu, tr("menu.show_pet", name=cname), self.show_pet)
        self._act(self.tray_menu, tr("menu.focus_mode"), self.start_focus_mode)
        is_home = bool(self.cfg.get("pet.is_at_home", False))
        home_text = tr("home.outside") if is_home else tr("home.at_home")
        self._act(self.tray_menu, home_text, lambda: self.set_home_mode(not is_home))
        bed_visible = bool(getattr(self, 'pet_bed', None) and self.pet_bed.isVisible())
        self._act(self.tray_menu, tr('menu.hide_bed' if bed_visible else 'menu.show_bed'), self.toggle_pet_bed)
        self.tray_menu.addSeparator()

        self._act(self.tray_menu, tr("menu.scripts"), self.open_scripts_dialog)
        self._act(self.tray_menu, "🖼️ Hintergrundbild wiederherstellen", self.restore_desktop_wallpaper)
        self._act(self.tray_menu, tr("menu.character_tree"), self.open_character_tree)
        self._act(self.tray_menu, tr("menu.friendship"), self.open_friendship_dialog)
        self._act(self.tray_menu, tr("menu.focus_stats"), self.open_focus_stats_dialog)
        self._act(self.tray_menu, tr("menu.flashcards"), self.open_flashcards_dialog)
        self._act(self.tray_menu, tr("menu.photo", name=cname), self.start_photobox)
        self._act(self.tray_menu, tr("menu.new_note"), lambda: self.create_sticky_note())
        self._act(self.tray_menu, tr("menu.error_doctor"), self.start_error_doctor)
        self._act(self.tray_menu, tr("menu.chats"), self.open_chat_history)
        self._act(self.tray_menu, tr("menu.data"), self.open_my_data)
        self._act(self.tray_menu, tr("menu.onboarding"), lambda: self._open_onboarding(is_update=True))
        self._act(self.tray_menu, tr("menu.watch_screen"), lambda: self._on_submit("was mache ich gerade"))
        self._act(self.tray_menu, tr("menu.create_word"), lambda: self._on_submit("erstelle ein word dokument am desktop"))
        self._act(self.tray_menu, tr("menu.reset_taskbar"), self.pet.reset_to_taskbar)
        voice_on = bool(self.cfg.get("voice.enabled", True))
        voice_text = "🔊 Sprachausgabe: Ein" if voice_on else "🔇 Sprachausgabe: Aus"
        self._act(self.tray_menu, voice_text, self._toggle_voice_output)
        self.tray_menu.addSeparator()
        if getattr(self, "_pending_update", None):
            ver = self._pending_update.get("version", "")
            state = self.update_prompt.state
            caption = (f'Update {ver}: Fehler ansehen' if state == 'error' else
                       f'Update {ver}: Fortschritt anzeigen' if state in ('download', 'verify', 'install') else
                       tr('menu.install_update', version=ver))
            self._act(self.tray_menu, caption, self._show_update_status)
        self._act(self.tray_menu, tr("menu.check_updates"), lambda: self._check_update(manual=True))
        self._act(self.tray_menu, tr("menu.settings"), self.open_settings)
        self._act(self.tray_menu, tr("menu.about", version=__version__), self._about)
        self._act(self.tray_menu, tr("menu.quit"), self.quit)


    @staticmethod
    def _act(menu: QMenu, text: str, slot) -> QAction:
        act = menu.addAction(text)
        act.triggered.connect(lambda _=False: slot())
        return act

    # -- Start / Ende ------------------------------------------------------------------
    def start(self) -> None:
        set_autostart(bool(self.cfg.get("autostart", True)))
        self.pet.drop_in()

        # Phase 10: Onboarding-Check
        if not _is_test_mode and not self.cfg.get("onboarding_done", False):
            skips = int(self.cfg.get("onboarding_skips", 0))
            if skips < 3:
                is_up = bool(self.cfg.get("first_run_done", False) or self.cfg.get("rename_intro_done", False))
                QTimer.singleShot(500, lambda: self._open_onboarding(is_update=is_up))

        first_run = not self.cfg.get("first_run_done", False)
        rename_intro = not self.cfg.get("rename_intro_done", False)
        if rename_intro:
            self.cfg.set("rename_intro_done", True)
            self.cfg.save()
            self.pet.celebrate_confetti(5.0)
            hint = f"Hi {self.user_name()}! Ich heiße jetzt Kylie – und wohne in Desktop Cat 🎉"
        elif first_run:
            self.cfg.set("first_run_done", True)
            self.cfg.save()
            if not gemini.has_key():
                hint = "Hi! Klick mich rechts \u2192 Gemini-Key eintragen, dann werde ich schlau \U0001f9e0"
            else:
                hk = str(self.cfg.get("hotkey", "ctrl+alt+p")).upper().replace("CTRL", "Strg")
                hint = f"Hallo {self.user_name()}! Ich bin {self.char_info().get('name', 'Kylie')} \U0001F43E Doppelklick oder {hk} = Befehl"
        else:
            hk = str(self.cfg.get("hotkey", "ctrl+alt+p")).upper().replace("CTRL", "Strg")
            hint = f"Hallo {self.user_name()}! Ich bin {self.char_info().get('name', 'Kylie')} \U0001F43E Doppelklick oder {hk} = Befehl"
            if not self._hotkey_ok:
                hint = f"Hallo {self.user_name()}! Ich bin {self.char_info().get('name', 'Kylie')} \U0001F43E Doppelklick auf mich = Befehl"

        QTimer.singleShot(1500, lambda: self._say(hint, 7000 if rename_intro else 6000))

        # Phase 2: Privacy-Hinweis beim ersten Start
        priv = self.cfg.get("privacy", {}) or {}
        if not priv.get("intro_shown", False):
            def _show_privacy_intro():
                self.cfg.set("privacy.intro_shown", True)
                self.cfg.save()
                p_msg = (
                    "Kleiner Hinweis: Ich speichere unsere Chats und Dinge, die du mir erzählst, "
                    "nur hier auf deinem PC 🔒 Rechtsklick → ‚Meine Daten‘ zeigt alles und löscht es mit einem Klick."
                )
                self._say(p_msg, 9000)
            delay = 9000 if rename_intro else 8000
            QTimer.singleShot(delay, _show_privacy_intro)

        self._schedule_chatter()
        self._schedule_vision(initial_delay_s=50)
        self._schedule_wellbeing()
        self._battery_timer.start(60000)
        self._curious_timer.start(60000)
        self._reminder_timer.start(900000)
        self._bedtime_timer.start(300000)
        self._weather_timer.start(3600000)
        self._pc_fever_timer.start(15000)
        QTimer.singleShot(4000, self._check_birthday_and_briefing)
        QTimer.singleShot(5000, self._check_seasonal_accessory)
        QTimer.singleShot(15000, self._on_reminders_check)
        QTimer.singleShot(20000, self._check_weather_outfit)
        QTimer.singleShot(30000, lambda: self._check_update(manual=False))
        self.note_manager.load_notes()

    def _on_data_wiped(self) -> None:
        self._dismiss_interaction()
        self.brain.clear_history()          # sonst geht der alte Verlauf bei der naechsten KI-Frage noch mit
        self.note_manager.close_all()
        # Auch die laufende Config zuruecksetzen - sonst ueberschreibt sie beim naechsten Speichern das Loeschen
        c = self.cfg
        c.set("profile", {"name": "", "pronouns": "", "uses": [], "interests": "", "tone": "", "city": ""})
        c.set("onboarding_done", False)
        c.set("care", {})
        c.set("treats", 0)
        c.set("fun.worn", "")
        c.set("lively.prev_wallpaper", "")
        try:
            import pet_care
            if not pet_care.is_character_unlocked(str(c.get("pet.character", "cat_mochi")))[0]:
                c.set("pet.character", "cat_mochi")      # Freundschaft ist weg -> gesperrte Figur nicht behalten
                self.pet.apply_config()
        except Exception:
            pass
        c.save()

    def _about(self) -> None:
        self._say(tr("about.text", version=__version__), 6000)

    def quit(self) -> None:
        self._dismiss_interaction()
        if getattr(self, '_wallpaper_worker', None) and self._wallpaper_worker.isRunning():
            self._say('Der Hintergrund wird noch umgestellt. Bitte kurz warten.', 4000)
            QTimer.singleShot(1000, self.quit)
            return
        if self.cfg.get('lively.active', False):
            try:
                import lively_wallpaper
                lively_wallpaper.restore_original_wallpaper(self.cfg)
                self.cfg.set("pet.is_at_home", False)
                self.cfg.set("pet.room_mode", False)
                self.cfg.save()
            except Exception:
                pass
        self.note_manager.close_all()
        self.hotkey.unregister()
        self.tray.hide()
        self.app.quit()

    # -- Auto-Update -------------------------------------------------------------------
    def _check_update(self, manual: bool = False) -> None:
        if self._update_worker is not None and self._update_worker.isRunning():
            return
        if not manual:
            if not FROZEN or not self.cfg.get("update.auto", True):
                return
            last_check = float(self.cfg.get("update.last_check", 0.0))
            if time.time() - last_check < 21600:
                self._offer_update()
                return
        if manual:
            self._say(tr("say.update_checking"), 3000)

        self._update_worker = CheckUpdateWorker(manual=manual)
        self._update_worker.check_completed.connect(self._on_update_checked)
        self._update_worker.start()

    def _on_update_checked(self, res: dict) -> None:
        status = res.get("status")
        manual = res.get("manual", False)
        if status == "update_available":
            if not self._pending_update or self._pending_update.get('version') != res.get('version'):
                self._awaiting_update_reply = False
            self._pending_update = res
            if self.cfg.get('update.deferred_version', res.get('version')) != res.get('version'):
                self.cfg.set('update.remind_after', 0)
            self._offer_update(force=manual)
            self._update_tray_menu()
        elif status == "up_to_date":
            self._pending_update = None
            self._awaiting_update_reply = False
            self.update_prompt.hide_now()
            self._update_tray_menu()
            if manual:
                self._say(tr("say.update_latest"), 5000)
        elif status == "error" and manual:
            self._say(tr("say.update_check_failed"), 5000)
        if status != 'error':
            self.cfg.set('update.last_check', time.time())
            self.cfg.save()

    def _offer_update(self, force: bool = False) -> None:
        if getattr(self, '_choosing_update_reminder', False) or QApplication.activeModalWidget() is not None:
            return
        if not force and (getattr(self, '_focus_mode', False) or not self.pet.isVisible()):
            return
        if getattr(self, '_active_interaction', None):
            if not force:
                return
            self._dismiss_interaction()
        if not self._pending_update or self.update_prompt.isVisible():
            return
        if self._download_worker is not None and self._download_worker.isRunning():
            return
        if not force and (not self.cfg.get('update.auto', True)
                          or time.time() < self.cfg.get('update.remind_after', 0)):
            return
        if self.brain.busy or self.brain.pending_action or self.input.isVisible() or self._quiz_session:
            return
        self.bubble.hide_now()
        self.update_prompt.anchor_to(self.pet.head_anchor())
        self.update_prompt.offer(self._pending_update['version'])
        self._awaiting_update_reply = True

    def _install_update_offer(self, version: str) -> None:
        if not self._pending_update or self._pending_update.get('version') != version:
            self.update_prompt.hide_now()
            self._offer_update(force=True)
            return
        if (self.brain.busy or self.brain.pending_action or self.input.isVisible()
                or self._quiz_session or QApplication.activeModalWidget() is not None):
            self.update_prompt.offer(version)
            self.update_prompt.message.setText('Bitte zuerst das aktuelle Gespräch oder die Aktion abschließen.')
            return
        self._start_update_download()

    def _defer_update(self) -> None:
        if getattr(self, '_choosing_update_reminder', False):
            return
        from update_ui import SnoozeDialog
        import datetime
        self.update_prompt.hide_now()
        dialog = SnoozeDialog(self.pet)
        version = self._pending_update.get('version') if self._pending_update else None
        self._choosing_update_reminder = True
        try:
            accepted = dialog.exec() == dialog.DialogCode.Accepted
        finally:
            self._choosing_update_reminder = False
        if accepted and self._pending_update and self._pending_update.get('version') == version:
            self.update_prompt.hide_now()
            remind_at = dialog.selected_time()
            self.cfg.set('update.remind_after', remind_at)
            self.cfg.set('update.deferred_version', self._pending_update['version'])
            self.cfg.save()
            self._awaiting_update_reply = False
            stamp = datetime.datetime.fromtimestamp(remind_at).strftime('%d.%m. um %H:%M')
            self._say(f'Okay, ich erinnere dich am {stamp} an das Update. 🐾', 5000)
        else:
            self._offer_update(force=True)

    def _start_update_download(self) -> None:
        if not getattr(self, "_pending_update", None):
            return
        if self._download_worker is not None and self._download_worker.isRunning():
            return
        self._awaiting_update_reply = False
        self.bubble.hide_now()
        self.update_prompt.anchor_to(self.pet.head_anchor())
        self.update_prompt.begin_download(self._pending_update['version'])
        self._download_worker = DownloadUpdateWorker(
            self._pending_update["setup_url"],
            self._pending_update["sha_url"],
            self._pending_update["version"],
        )
        self._update_download_result = None
        self._download_worker.download_completed.connect(
            lambda ok, detail: setattr(self, '_update_download_result', (ok, detail)))
        self._download_worker.finished.connect(self._finish_update_download)
        self._download_worker.progress.connect(self.update_prompt.set_progress)
        self._download_worker.verifying.connect(self.update_prompt.set_verifying)
        self._download_worker.start()

    def _finish_update_download(self) -> None:
        result = self._update_download_result or (False, 'Download wurde unerwartet beendet.')
        self._on_update_downloaded(*result)

    def _show_update_status(self) -> None:
        if self.update_prompt.state in ('download', 'verify', 'install', 'error'):
            self.update_prompt.anchor_to(self.pet.head_anchor())
            self.update_prompt.show()
            self.update_prompt.fade_in()
        else:
            self._offer_update(force=True)

    def _on_update_downloaded(self, ok: bool, path_or_err: str) -> None:
        if ok:
            self.update_prompt.set_installing()
            QTimer.singleShot(1500, lambda: self._apply_update(path_or_err))
        else:
            self.update_prompt.show_error(path_or_err)

    def _apply_update(self, setup_exe: str) -> None:
        launch_installer(setup_exe)
        self.quit()

    # -- Sprechblase / Eingabe ---------------------------------------------------------
    def _follow(self) -> None:
        a = self.pet.head_anchor()
        self.bubble.anchor_to(a)
        if hasattr(self, 'interaction_card'):
            self.interaction_card.anchor_to(a)
        if hasattr(self, 'update_prompt'):
            self.update_prompt.anchor_to(a)
        self.briefing_card.anchor_to(a)
        if hasattr(self, "explain_card") and self.explain_card.isVisible():
            self.explain_card.anchor_to(a)
        self.input.anchor_to(a)
        if getattr(self, "guide_overlay", None) and self.guide_overlay.isVisible():
            self.guide_overlay.set_pet_pos(self.pet.pos())

    def _say(self, text: str, duration_ms=None, persistent: bool = False) -> None:
        if self.input.isVisible():
            return
        if getattr(self, '_active_interaction', None):
            self._dismiss_interaction()
        self._follow()
        if hasattr(self, 'update_prompt') and self.update_prompt.isVisible():
            self.update_prompt.hide_now()
        self._awaiting_update_reply = False
        self.bubble.say(text, duration_ms, persistent)

    def open_input(self, reply_mode: bool = False) -> None:
        self._dismiss_interaction()
        self.update_prompt.hide_now()
        self._awaiting_update_reply = False
        if self.input.isVisible():
            self.input.dismiss()
            return
        if self.brain.busy:
            self._say(tr("say.still_busy"), 2500)
            return
        self.bubble.hide_now()
        self.pet.freeze(True)
        self.pet.wake()
        placeholder = (f"Antworte {self.char_info().get('name', 'Kylie')}... \U0001F43E" if (reply_mode or getattr(self, "_mochi_asked_question", False))
                       else f"Was soll ich tun, {self.user_name()}? \U0001F43E")
        self.input.popup(self.pet.head_anchor(), placeholder)

    def _on_bubble_clicked(self) -> None:
        """A bubble click opens input; installation requires an explicit reply."""
        if not self.brain.busy:
            self.open_input(reply_mode=True)

    def _on_input_closed(self) -> None:
        if not self.brain.busy:
            self.pet.freeze(False)

    def _hotkey_pressed(self) -> None:
        if getattr(self, "_focus_mode", False):
            self.end_focus_mode()
            return
        if not self.pet.isVisible():
            self.show_pet()
        self.open_input()

    def _on_submit(self, text: str) -> None:
        awaiting_update = self._awaiting_update_reply
        self._awaiting_update_reply = False
        if awaiting_update and self._pending_update and not self.brain.pending_action:
            answer = text.strip().lower().strip(' .!?')
            if answer in {'ja', 'yes', 'update installieren'}:
                self.input.hide_now()
                self._start_update_download()
                return
            if answer in {'später', 'spaeter', 'later', 'nein', 'no'}:
                self.input.hide_now()
                self._defer_update()
                return
        was_question = getattr(self, "_mochi_asked_question", False)
        self._mochi_asked_question = False
        self.input.hide_now()       # sofort weg, damit die "Ich bin dran"-Blase erscheinen darf

        if was_question:
            self._award_friendship("curious")

        if self._quiz_session:
            self._handle_quiz_answer(text)
            return

        low_txt = text.strip().lower()
        if any(k in low_txt for k in ("was bedeutet diese fehlermeldung", "was heißt dieser fehler", "was heisst dieser fehler", "fehlermeldung erklären", "fehlermeldung erklaeren")):
            self.start_error_doctor()
            return

        if low_txt.startswith("merk dir:") or low_txt.startswith("notiz:"):
            content = text.split(":", 1)[1].strip()
            self.create_sticky_note(content)
            return
        elif low_txt.startswith("merk dir ") or low_txt.startswith("notiz "):
            content = text.split(" ", 2)[-1].strip() if low_txt.startswith("merk dir ") else text.split(" ", 1)[1].strip()
            self.create_sticky_note(content)
            return

        if any(k in low_txt for k in ("frag mich vokabeln ab", "quiz starten", "lernkarten quiz", "starte quiz")):
            self.start_flashcard_quiz()
            return
        elif low_txt in ("lernkarten", "vokabeln"):
            self.open_flashcards_dialog()
            return

        if any(k in low_txt for k in ("skripte", "routinen", "skript manager", "meine routinen", "zeige skripte", "öffne skripte", "custom scripts")):
            self.open_scripts_dialog()
            return

        if any(k in low_txt for k in ("geh nach hause", "ab nach hause", "geh ins zimmer", "katze zuhause", "katze ins zimmer", "go home")):
            self.set_home_mode(True)
            return
        elif any(k in low_txt for k in ("geh raus", "geh auf den desktop", "katze draußen", "katze draussen", "rausgehen", "go outside")):
            self.set_home_mode(False)
            return

        import re
        m_cards = re.search(r"(?:mach|erstelle)\s+(?:mir\s+)?(?:(\d+)\s+)?lernkarten\s+zu\s+(.+)", low_txt)
        if m_cards:
            count_str, topic = m_cards.group(1), m_cards.group(2).strip()
            count = int(count_str) if count_str else 10
            self._create_ai_flashcards(topic, count)
            return

        char_name = str(self.char_info().get("name", "Kylie"))
        nr = name_reaction(text, char_name, self.user_name())
        if nr:
            if self.pet.state == PetState.SLEEP:
                self.pet.wake_with_stretch()
                msg = "Mrrrp… ich bin wach! 😽"
                self._say(msg, 4000)
                self.brain.record_assistant_message(msg)
                if nr.kind == "call":
                    return
            else:
                self.pet.react_happy()
            if nr.kind == "call":
                self._say(nr.reply or f"Ja? 😺 Was gibt's, {self.user_name()}?", 4000)
                self.brain.record_assistant_message(nr.reply or f"Ja? 😺 Was gibt's, {self.user_name()}?")
                return
            elif nr.kind == "who":
                self._say(nr.reply or f"Ich bin {char_name}! 🐾", 5000)
                self.brain.record_assistant_message(nr.reply or f"Ich bin {char_name}! 🐾")
                return
            elif nr.kind == "prefix" and nr.rest:
                text = nr.rest
            elif nr.hearts:
                self.pet.react_happy()

        if not self.brain.submit(text):
            self._say(tr("say.still_busy"), 2500)

    # -- Aufgaben-Lebenszyklus --------------------------------------------------------------
    def _on_task_started(self, _text: str) -> None:
        self.pet.freeze(True)
        self.pet.set_working()
        self._say(tr("say.working"), persistent=True)

    def _on_task_finished(self, ok: bool, message: str, notify: str) -> None:
        self.pet.freeze(False)
        self._award_friendship("chat")
        low = (message or "").lower()
        if "💃" in message or "tanz" in low:
            self.pet.dance(6.0)
        elif "🕶️" in message or "cool" in low:
            self.pet.be_cool(6.0)
        elif "💤" in message or "schlaf" in low:
            self.pet.go_to_sleep()
        elif ok:
            self.pet.celebrate()
        else:
            self.pet.sad()
        self.bubble.hide_now()
        self._say(("Fertig! \u2728  " if ok and notify else "") + message)
        if bool(self.cfg.get("voice.read_answers", False)):
            voice_tts.get_tts().speak(message, self.cfg.snapshot())
        if notify:
            self.tray.showMessage(notify, message, self.icon, 6000)
        if "?" in message:
            self._mochi_asked_question = True
        if "ich öffne deine chats" in low or "meine chats für dich" in low:
            QTimer.singleShot(600, self.open_chat_history)
        if "ich öffne deine skripte" in low or "skripte-manager" in low or "skript-manager" in low:
            QTimer.singleShot(600, self.open_scripts_dialog)
        if "willkommen zuhause" in low or "mach das zimmer an" in low:
            self.set_home_mode(True)
        elif "raus auf den desktop" in low or "wir gehen raus" in low:
            self.set_home_mode(False)


    def _on_timer_expired(self, label: str, duration_s: int, u_name: str) -> None:
        self.pet.wake()
        self.pet.celebrate(4.0)
        cinfo = self.char_info()
        mins = duration_s // 60
        time_hint = f"{mins} Min." if mins > 0 else f"{duration_s} Sek."
        msg = f"\u23F0 {cinfo.get('sound', 'Ring, ring')}, {u_name or self.user_name()}! Dein Timer f\u00fcr \u201e{label}\u201c ({time_hint}) ist abgelaufen! {cinfo.get('emoji', '')}"
        self.bubble.hide_now()
        self._say(msg, 7000)
        self.tray.showMessage(f"\u23F0 Timer abgelaufen: {label}", f"Die Zeit f\u00fcr \u201e{label}\u201c ({time_hint}) ist um!", self.icon, 7000)
        self.brain.record_assistant_message(msg)

        # Phase 6: Pomodoro / Fokus zählen & Freundschaftspunkte
        low_label = (label or "").lower()
        if any(k in low_label for k in ("pomodoro", "fokus")):
            from fun import record_focus_session
            from memory_store import get_memory_store
            try:
                store = get_memory_store()
                record_focus_session(store, max(1, mins or 25))
                self._award_friendship("pomodoro")
            except Exception as exc:
                print(f"[focus] Fehler beim Zählen: {exc}")

    def _on_character_changed(self, _cid: str) -> None:
        self._dismiss_interaction()
        ci = self.char_info()
        self._say(tr("say.i_am", sound=ci.get('sound', ''), name=ci.get('name', 'Kylie'), emoji=ci.get('emoji', '')), 3000)

    def _on_treat(self) -> None:
        import pet_care
        from memory_store import get_memory_store
        try:
            store = get_memory_store()
        except Exception:
            store = None
        pet_care.feed_pet(self.cfg, None)       # Punkte vergibt _award_friendship (sonst doppelt + kein Level-up-Jubel)
        n = int(self.cfg.get("treats", 0))
        ci = self.char_info()
        self._say(tr("say.treat_thanks", sound=ci.get('sound', 'Mjam!'), name=self.user_name(), n=n), 4000)
        self._award_friendship("treat")
        from achievements import record_achievement_event
        from seasonal_events import record_quest_event
        record_achievement_event(store, "treats_given", 1)
        record_quest_event(store, "quest_hl_treats", 1)

    def _on_wash(self) -> None:
        import pet_care
        from memory_store import get_memory_store
        try:
            store = get_memory_store()
        except Exception:
            store = None
        pet_care.wash_pet(self.cfg, None)       # Punkte vergibt _award_friendship (sonst doppelt)
        self.pet.wash_pet(4.5)
        self._play_pet_sound()
        if hasattr(self, "bubble_mgr") and self.bubble_mgr:
            self.bubble_mgr.spawn_wave(8)
        from achievements import record_achievement_event
        from seasonal_events import record_quest_event
        record_achievement_event(store, "washes_given", 1)
        record_quest_event(store, "quest_sp_washes", 1)
        ci = self.char_info()
        cname = ci.get("name", "Kylie")
        lines = [
            f"Bubbly fresh! 🫧 {cname} glänzt wieder wie neu!",
            f"Ooh wie das herrlich duftet! 🧼 Danke {self.user_name()}!",
            f"Blubb blubb... Seifenblasen! 🫧 Klicke sie an, um sie platzen zu lassen!",
        ]
        self._say(random.choice(lines), 4500)
        self._award_friendship("wash")

    # -- Phase 3: Alltag, Neugier, Briefing, Geburtstag, Schlafenszeit -----------------
    def _check_birthday_and_briefing(self) -> None:
        try:
            from memory_store import get_memory_store
            store = get_memory_store()
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # 1. Geburtstag
            facts = store.facts()
            for f in facts:
                if f.get("kind") == "birthday" and f.get("due_date") == today_str:
                    bday_stat = f"birthday_greeted_{today_str}"
                    if not store.get_stat(bday_stat):
                        store.set_stat(bday_stat, "1")
                        self.pet.wake()
                        self.pet.celebrate_confetti(6.0)
                        self._say(tr("say.birthday", name=self.user_name()), 10000)
                        return

            # 2. Guten-Morgen-Briefing
            daily_cfg = self.cfg.get("daily", {}) if isinstance(self.cfg.get("daily"), dict) else {}
            if not daily_cfg.get("briefing", True):
                return
            last_briefing = store.get_stat("last_briefing")
            from daily import should_brief
            if should_brief(now, last_briefing):
                store.set_stat("last_briefing", today_str)
                self._show_morning_briefing(store, now)
        except Exception:
            pass

    def _show_morning_briefing(self, store, now: datetime.datetime) -> None:
        try:
            w_res = tools.get_weather()
            w_text = w_res.message.split("\n")[0] if w_res.ok else "Einen wunderbaren Tag dir!"
        except Exception:
            w_text = "Einen wunderbaren Tag dir!"

        lines = [f"🌤️ {w_text}"]
        today = now.date()
        tmrw = today + datetime.timedelta(days=1)
        t_str = today.strftime("%Y-%m-%d")
        tm_str = tmrw.strftime("%Y-%m-%d")

        facts = store.facts()
        events = [f["text"] for f in facts if f.get("due_date") == t_str]
        tmrw_events = [f["text"] for f in facts if f.get("due_date") == tm_str]

        if events:
            lines.append(f"📅 Heute: {', '.join(events[:2])}")
        if tmrw_events:
            lines.append(f"🗓️ Morgen: {', '.join(tmrw_events[:2])}")

        ci = self.char_info()
        sound = ci.get("sound", "")
        quotes = [
            f"{sound} Auf einen produktiven Tag, {self.user_name()}! ✨",
            f"{sound} Wir schaffen heute alles, was ansteht! 🐾",
            f"{sound} Schön, dass du da bist, {self.user_name()}! 💖",
        ]
        lines.append(f"🐾 {random.choice(quotes)}")

        self.briefing_card.show_briefing(
            f"☀️ Guten Morgen, {self.user_name()}!",
            lines,
            self.pet.head_anchor(),
            duration_ms=12000,
        )

    def _on_curious_check(self) -> None:
        self._start_pet_interaction(manual=False)

    def start_pet_interaction(self) -> None:
        if getattr(self, '_focus_mode', False):
            return
        if not self.pet.isVisible():
            self.show_pet()
        if self.interaction_card.isVisible():
            self.interaction_card.raise_()
            return
        self._start_pet_interaction(manual=True)

    def _can_offer_interaction(self, manual: bool = False) -> bool:
        if (getattr(self, '_focus_mode', False) or not self.pet.isVisible()
                or self.brain.busy or self.brain.pending_action or self._settings_open
                or self._quiz_session or self._guide_session
                or self.pet.frozen or self.pet._dragging
                or QApplication.activeModalWidget() is not None
                or _is_fullscreen_foreground()):
            return False
        cards = [self.input, self.update_prompt, self.interaction_card, self.explain_card, self.briefing_card]
        if any(card.isVisible() for card in cards):
            return False
        if not manual and (is_night(self.cfg) or self.bubble.isVisible()
                           or QApplication.activePopupWidget() is not None):
            return False
        return True

    def _start_pet_interaction(self, manual: bool = False) -> None:
        if not self._can_offer_interaction(manual):
            return
        if not manual and time.time() < self._interaction_ready_at:
            return
        try:
            import json
            from daily import should_ask_curious
            from pet_interactions import choose_interaction
            from memory_store import get_memory_store
            store = get_memory_store()
            now = datetime.datetime.now()
            stats = {key: store.get_stat(key, default) for key, default in (
                ('curious_date', ''), ('curious_count', '0'), ('curious_last_ts', '0'))}
            if not manual and not should_ask_curious(now, stats, self.cfg.snapshot()):
                return
            try:
                recent = json.loads(store.get_stat('curious_recent', '[]'))
                if not isinstance(recent, list):
                    recent = []
            except (ValueError, TypeError):
                recent = []
            item = choose_interaction(recent, i18n.lang())
            try:
                count = int(stats['curious_count']) if stats['curious_date'] == now.date().isoformat() else 0
            except (ValueError, TypeError):
                count = 0
            if not manual:
                store.set_stat('curious_date', now.date().isoformat())
                store.set_stat('curious_count', str(count+1))
            store.set_stat('curious_last_ts', str(now.timestamp()))
            store.set_stat('curious_recent', json.dumps((recent+[item.id])[-6:]))
            self.bubble.hide_now()
            self._mochi_asked_question = False
            self.pet.wake()
            self.pet.freeze(True)
            self._active_interaction = item
            self._interaction_manual = manual
            self.interaction_card.present(item, self.char_info().get('name', 'Kylie'), self.pet.head_anchor(), i18n.lang())
            self._interaction_watchdog.start(2000)
        except Exception as exc:
            self._dismiss_interaction()
            print(f'[pet] Kleine Interaktion konnte nicht gestartet werden: {exc}')

    def _check_active_interaction(self) -> None:
        if self._active_interaction is None:
            return
        if (self._focus_mode or not self.pet.isVisible() or self.brain.busy
                or self.brain.pending_action or self.input.isVisible()
                or QApplication.activeModalWidget() is not None
                or _is_fullscreen_foreground()
                or (not self._interaction_manual and is_night(self.cfg))):
            self._dismiss_interaction()

    def pause_pet_questions(self) -> None:
        deadline = time.time() + 3600
        self.cfg.set('daily.interaction_pause_until', deadline)
        self.cfg.save()
        self._dismiss_interaction()
        stamp = datetime.datetime.fromtimestamp(deadline).strftime('%H:%M')
        self._say(f'Okay, bis {stamp} stelle ich keine automatischen Fragen. Du kannst jederzeit selbst eine Runde starten. 🐾', 7000)
        self._update_tray_menu()

    def resume_pet_questions(self) -> None:
        self.cfg.set('daily.interaction_pause_until', 0)
        self.cfg.save()
        self._say('Die Fragenpause ist beendet. Ich warte wie gewohnt auf einen ruhigen Moment. 🐾', 5000)
        self._update_tray_menu()

    def _dismiss_interaction(self) -> None:
        if getattr(self, '_active_interaction', None) is None:
            return
        self._active_interaction = None
        self._interaction_watchdog.stop()
        self.interaction_card.hide_now()
        if not self.brain.busy:
            self.pet.freeze(False)

    def _complete_interaction(self, key: str, answer) -> None:
        from pet_interactions import reaction_for, save_answer
        item = self._active_interaction
        if item is None or item.id != key:
            return
        result = reaction_for(item, answer, self.pet.character, self.char_info().get('name', 'Kylie'), i18n.lang())
        if result is None:
            return
        reply, action = result
        self._dismiss_interaction()
        try:
            from memory_store import get_memory_store
            save_answer(get_memory_store(), self.cfg, item, answer, reply, self.pet.character)
        except Exception as exc:
            print(f'[pet] Antwort konnte nicht lokal gespeichert werden: {exc}')
        actions = {
            'happy': self.pet.react_happy, 'dance': self.pet.dance,
            'stretch': self.pet.wake_with_stretch, 'sleep': self.pet.go_to_sleep,
            'celebrate': self.pet.celebrate_confetti, 'treat': self.pet.eat_treat,
        }
        if action == 'treat':
            import pet_care
            pet_care.feed_pet(self.cfg)
        actions[action]()
        added, level_up, _ = self._award_friendship('curious')
        if not level_up:
            points = (f'  +{added} friendship' if i18n.lang() == 'en' else f'  +{added} Freundschaft') if added else ''
            self._say(reply+points, 9000)

    def _on_reminders_check(self) -> None:
        if is_night(self.cfg) or _is_fullscreen_foreground() or self.brain.busy:
            return
        try:
            from memory_store import get_memory_store
            from daily import due_reminders
            store = get_memory_store()
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            facts = store.facts()
            stats_dict = {
                f"remind_{f['id']}_{sfx}_{today_str}": store.get_stat(f"remind_{f['id']}_{sfx}_{today_str}")
                for f in facts for sfx in ("eve", "day", "after")
            }
            rems = due_reminders(facts, now, stats_dict)
            if rems:
                _, msg, stat_key = rems[0]
                store.set_stat(stat_key, "1")
                self.pet.wake()
                self._say(msg, duration_ms=9000)
                self.tray.showMessage("Erinnerung 🐾", msg, self.icon, 7000)
                self.brain.record_assistant_message(msg)
        except Exception:
            pass

    def _on_bedtime_check(self) -> None:
        try:
            daily_cfg = self.cfg.get("daily", {}) if isinstance(self.cfg.get("daily"), dict) else {}
            bedtime = str(daily_cfg.get("bedtime", "23:00") or "").strip()
            if not bedtime:
                return
            from memory_store import get_memory_store
            from daily import bedtime_due
            store = get_memory_store()
            now = datetime.datetime.now()
            last_shown_str = store.get_stat("bedtime_last_ts")
            last_shown = float(last_shown_str) if last_shown_str else None
            due, is_second = bedtime_due(now, bedtime, last_shown)
            if due and not self.brain.busy and not self.input.isVisible():
                store.set_stat("bedtime_last_ts", str(now.timestamp()))
                self.pet.wake_with_stretch(4.0)
                self.pet.set_accessory("nightcap", True, until=time.monotonic() + 1800.0)
                if is_second:
                    self._say(tr("say.late_night_1", name=self.user_name()), 9000)
                else:
                    self._say(tr("say.late_night_2", name=self.user_name()), 9000)
        except Exception:
            pass

    # -- Phase 4: Zubehoer, Wetter & PC-Fieber -----------------------------------------
    def _reap_worker(self) -> None:
        self._active_workers = [w for w in self._active_workers if not w.isFinished()]

    def _check_seasonal_accessory(self) -> None:
        try:
            acc = seasonal_accessory(datetime.date.today())
            if acc:
                self.pet.set_accessory(acc, True)
        except Exception:
            pass

    def _check_weather_outfit(self) -> None:
        if not self.cfg.get("fun.weather_outfits", True):
            return
        worker = WeatherWorker(self.pet)
        worker.finished_with_result.connect(self._on_weather_outfit_result)
        worker.finished.connect(self._reap_worker)
        self._active_workers.append(worker)
        worker.start()

    def _on_weather_outfit_result(self, res) -> None:
        if getattr(res, "ok", False) and getattr(res, "data", None):
            outfits = weather_accessories(res.data.get("temp_c"), res.data.get("desc", ""))
            for w_acc in ("umbrella", "sunglasses", "scarf", "beanie"):
                self.pet.set_accessory(w_acc, False)
            for o in outfits:
                self.pet.set_accessory(o, True)

    def _check_pc_fever(self) -> None:
        try:
            cur_times = get_system_times()
            cpu = 0.0
            if self._last_system_times and cur_times:
                cpu = calculate_cpu_percent(self._last_system_times, cur_times)
            self._last_system_times = cur_times
            ram = get_ram_load_percent()

            if cpu > 90.0:
                self._high_cpu_count += 1
            else:
                self._high_cpu_count = 0

            if not self.cfg.get("fun.pc_fever", True):
                return

            is_fever = (self._high_cpu_count >= 2) or (ram > 92.0)
            now = time.monotonic()
            if is_fever:
                self.pet.set_accessory("fan", True, until=now + 180.0)
                if now - self._last_fever_alert > 3600.0:
                    self._last_fever_alert = now
                    self.brain.pending_action = ("system_info", {})   # "ja" fuehrt es aus
                    self._say(tr("say.pc_hot"), 8000)
        except Exception:
            pass

    # -- Wohlfuehl-Erinnerungen & Akku ---------------------------------------------------------
    def _schedule_wellbeing(self) -> None:
        self._wellbeing.stop()
        wb = self.cfg.get("wellbeing", {}) or {}
        if wb.get("breaks", True) or wb.get("water", True):
            self._wellbeing.start(max(1, int(wb.get("break_min", 60))) * 60000)

    def _on_wellbeing(self) -> None:
        wb = self.cfg.get("wellbeing", {}) or {}
        if getattr(self, "_focus_mode", False) or not self.pet.isVisible() or is_night(self.cfg) or _is_fullscreen_foreground() or self.brain.busy or self.input.isVisible():
            return
        kinds = [k for k, on in (("break", wb.get("breaks", True)), ("water", wb.get("water", True))) if on]
        if not kinds:
            return
        self._wellbeing_water = not self._wellbeing_water       # abwechseln
        kind = "water" if (self._wellbeing_water and "water" in kinds) or kinds == ["water"] else "break"
        ci = self.char_info()
        u = self.user_name()
        if kind == "water":
            self.pet.drink_water(5.0)
            text = f"{ci.get('sound', '')} {u}, Wasser trinken! 💧 Ich trinke auch gleich einen Schluck mit dir! *schlürf schlürf* 🥣💧"
        else:
            text = f"{ci.get('sound', '')} {u}, kurz strecken? 🤸"
        self.pet.wake()
        self._say(text.strip(), 7000)

    def _check_battery(self) -> None:
        pct, ac = _battery()
        if pct < 0 or ac or pct >= 20:
            self._battery_warned = False       # erst wieder warnen, wenn zwischenzeitlich geladen wurde
            return
        if pct < 15 and not self._battery_warned and self.cfg.get("battery_warn", True):
            self._battery_warned = True
            self.pet.wake()
            self.pet.sad(3.0)
            self._say(tr("say.battery_low", pct=pct, name=self.user_name()), 9000)
            self.tray.showMessage("Akku fast leer", f"Nur noch {pct} % Akku.", self.icon, 7000)

    # -- Interaktion & Sichtbarkeit -----------------------------------------------------------
    def _on_petted(self) -> None:
        if self.brain.busy:
            return
        import pet_care
        pet_care.pet_pet(self.cfg)
        if bool(self.cfg.get("pet.sound_enabled", True)):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
        u = self.user_name()
        lines = self.char_info().get("pet_sounds") or CLICK_LINES + [f"Du bist der Beste, {u}! 💖"]
        self._say(random.choice(lines), 2500)

    def hide_pet(self) -> None:
        self._dismiss_interaction()
        self.pet.hide()
        self.update_prompt.hide_now()
        self._awaiting_update_reply = False
        self.bubble.hide_now()
        self.input.hide_now()
        cname = self.char_info().get("name", "Kylie")
        hotkey = str(self.cfg.get("hotkey", "ctrl+alt+p"))
        self.tray.showMessage(
            f"🙈 {cname} macht ein Päuschen",
            tr("tray.pet_hidden_notify", name=cname, hotkey=hotkey),
            self.icon,
            5000,
        )
        self._update_tray_menu()

    def show_pet(self) -> None:
        if getattr(self, "_focus_mode", False):
            self.end_focus_mode()
            return
        self.pet.show()
        self.pet.wake()
        self.pet.react_happy()
        self._update_tray_menu()

    def start_focus_mode(self) -> None:
        self._dismiss_interaction()
        self._focus_mode = True
        self.update_prompt.hide_now()
        self._awaiting_update_reply = False
        self.pet.hide()
        self.bubble.hide_now()
        self.input.hide_now()
        cname = self.char_info().get("name", "Kylie")
        self.tray.setToolTip(f"{cname} – Fokus-Modus aktiv (Klicke zum Beenden)")
        self.tray.showMessage(
            "🎯 Fokus-Modus aktiviert",
            f"{cname} hat sich schlafen gelegt, damit du ungestört arbeiten kannst. Klicke auf das Katzen-Icon in der Taskleiste (^), um den Fokus-Modus zu beenden!",
            self.icon,
            6000,
        )
        self._update_tray_menu()

    def end_focus_mode(self) -> None:
        self._focus_mode = False
        self.tray.setToolTip(tr("tray.tooltip"))
        self.pet.show()
        self.pet.wake()
        self.pet.react_happy()
        self._update_tray_menu()
        u = self.user_name()
        self._say(f"🎯 Fokus-Modus beendet! Super konzentriert gearbeitet, {u}! ✨🐾", 4500)
        self._award_friendship("pomodoro")

    def _on_tray(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if getattr(self, "_focus_mode", False):
                self.end_focus_mode()
                return
            if not self.pet.isVisible():
                self.show_pet()
            else:
                self.open_input()

    def open_settings(self) -> None:
        self._dismiss_interaction()
        if self._settings_open:
            return
        self._settings_open = True
        try:
            old_spec = str(self.cfg.get("hotkey", "ctrl+alt+p"))
            old_ex_spec = str(self.cfg.get("hotkey_explain", "ctrl+alt+e"))
            old_voice_spec = str(self.cfg.get("hotkey_voice", "ctrl+alt+space"))
            dlg = SettingsDialog(self.cfg, hotkey_validator=lambda spec: parse_hotkey(spec) is not None)
            dlg.hide_pet_requested.connect(self.hide_pet)
            dlg.setWindowIcon(self.icon)
            if dlg.exec():
                self.pet.apply_config()
                self._schedule_chatter()
                self._schedule_wellbeing()
                spec = str(self.cfg.get("hotkey", "ctrl+alt+p"))
                if spec != old_spec:
                    self.hotkey.unregister(HOTKEY_ID)
                    if not self.hotkey.register(spec, HOTKEY_ID, self._hotkey_pressed):
                        self.cfg.set("hotkey", old_spec)
                        self.cfg.save()
                        self._hotkey_ok = self.hotkey.register(old_spec, HOTKEY_ID, self._hotkey_pressed)
                        self._say(tr("say.hotkey_taken"), 4500)
                        return
                ex_spec = str(self.cfg.get("hotkey_explain", "ctrl+alt+e"))
                if ex_spec != old_ex_spec:
                    self.hotkey.unregister(EXPLAIN_HOTKEY_ID)
                    if not self.hotkey.register(ex_spec, EXPLAIN_HOTKEY_ID, self._explain_hotkey_pressed):
                        self.cfg.set("hotkey_explain", old_ex_spec)
                        self.cfg.save()
                        self.hotkey.register(old_ex_spec, EXPLAIN_HOTKEY_ID, self._explain_hotkey_pressed)
                voice_spec = str(self.cfg.get("hotkey_voice", "ctrl+alt+space"))
                if voice_spec != old_voice_spec:
                    self.hotkey.unregister(VOICE_HOTKEY_ID)
                    if not self.hotkey.register(voice_spec, VOICE_HOTKEY_ID, self._voice_hotkey_pressed):
                        self.cfg.set("hotkey_voice", old_voice_spec)
                        self.cfg.save()
                        self.hotkey.register(old_voice_spec, VOICE_HOTKEY_ID, self._voice_hotkey_pressed)
                self._update_tray_menu()
                self._say(tr("say.saved"), 2000)
        finally:
            self._settings_open = False

    def open_chat_history(self) -> None:
        self._dismiss_interaction()
        from chat_history import ChatHistoryDialog
        dlg = ChatHistoryDialog(self.cfg)
        dlg.setWindowIcon(self.icon)
        dlg.resume_requested.connect(self._on_resume_chat)
        dlg.exec()

    def _on_resume_chat(self, history: list) -> None:
        self.brain.clear_history()
        self.brain._history = list(history)
        self.open_input()

    def open_my_data(self) -> None:
        self._dismiss_interaction()
        from my_data_dialog import MyDataDialog
        dlg = MyDataDialog(self.cfg)
        dlg.setWindowIcon(self.icon)
        dlg.exec()

    def _open_onboarding(self, is_update: bool = False) -> None:
        try:
            from onboarding import OnboardingDialog
            dlg = OnboardingDialog(self.cfg, parent=None, is_update=is_update)
            dlg.setWindowIcon(self.icon)
            dlg.exec()
            # Apply updated pet settings
            self.pet.character = str(self.cfg.get("pet.character", "cat_mochi"))
            self.pet.apply_config()
            self._schedule_chatter()
            if self.cfg.get("onboarding_done", False):
                self.pet.drop_in()
                self.pet.celebrate_confetti(4.0)
                u = self.user_name()
                cname = self.char_info().get("name", "Kylie")
                self._say(tr("say.nice_to_meet", u=u, cname=cname), 6000)
        except Exception as e:
            print(f"[main] Fehler beim Öffnen des Onboardings: {e}")

    # -- Phase 6: Freundschaft, Fokus, Lernkarten, Fotobox & Notizen ------------------
    def _award_friendship(self, kind: str) -> tuple[int, bool, int]:
        try:
            from fun import add_friendship_points
            from memory_store import get_memory_store
            store = get_memory_store()
            pts_added, did_lvl_up, new_lvl = add_friendship_points(store, kind)
            QTimer.singleShot(0, self._refresh_friendship_progress)
            return pts_added, did_lvl_up, new_lvl
        except Exception as exc:
            print(f"[friendship] Fehler beim Vergeben von Punkten: {exc}")
            return 0, False, 1

    def _refresh_friendship_progress(self) -> None:
        from fun import get_level_name, get_level_reward, level_for
        from memory_store import get_memory_store
        try:
            points = get_memory_store().get_friendship_points()
            old_points = self._last_friendship_points
            if points != old_points:
                self._last_friendship_points = points
                new_lvl, _ = level_for(points)
                old_lvl, _ = level_for(old_points)
                dialog = getattr(self, '_character_dialog', None)
                if dialog is not None and dialog.isVisible():
                    dialog.refresh_all()
                if points < old_points:
                    self._pending_friendship_level = None
                elif new_lvl > old_lvl:
                    self._pending_friendship_level = new_lvl
            new_lvl = getattr(self, '_pending_friendship_level', None)
            if new_lvl is not None:
                if (self.brain.busy or self.brain.pending_action or self.input.isVisible()
                        or self.update_prompt.isVisible() or getattr(self, '_active_interaction', None)
                        or getattr(self, '_focus_mode', False) or not self.pet.isVisible()
                        or QApplication.activeModalWidget() is not None):
                    return
                self._pending_friendship_level = None
                self.pet.celebrate_confetti(5.0)
                lvl_title = get_level_name(new_lvl)
                reward_title, _ = get_level_reward(new_lvl)
                rew_text = f" Belohnung freigeschaltet: {reward_title}! 🎁" if reward_title else ""
                msg = f"Level {new_lvl}! Wir sind jetzt {lvl_title}, {self.user_name()} 💖{rew_text}"
                self._say(msg, 6000)
                self.brain.record_assistant_message(msg)
        except Exception as exc:
            print(f"[friendship] Fortschritt konnte nicht aktualisiert werden: {exc}")

    def open_character_tree(self) -> None:
        self._dismiss_interaction()
        from character_tree_dialog import CharacterTreeDialog
        from memory_store import get_memory_store
        try:
            store = get_memory_store()
        except Exception:
            store = None
        dlg = CharacterTreeDialog(self.cfg, store, self.pet)
        dlg.bubble_game_requested.connect(self.start_bubble_game)
        dlg.yarn_game_requested.connect(self.start_yarn_game)
        dlg.wallpaper_requested.connect(self.activate_lively_wallpaper)
        dlg.wallpaper_restore_requested.connect(self.restore_desktop_wallpaper)
        dlg.bed_toggled.connect(self.toggle_pet_bed)
        dlg.home_mode_toggled.connect(self.set_home_mode)
        dlg.scripts_requested.connect(self.open_scripts_dialog)
        self._character_dialog = dlg
        worker = getattr(self, '_wallpaper_worker', None)
        if worker is not None and worker.isRunning():
            dlg.set_wallpaper_busy(True, 'Der Hintergrund wird umgestellt…')
        try:
            dlg.exec()
        finally:
            self._character_dialog = None

    # -- v2.5.0: Autonome Skripte, Routinen & Katzen-Zuhause -----------------------------
    def open_scripts_dialog(self) -> None:
        from scripts_dialog import CustomScriptsDialog
        dlg = CustomScriptsDialog()
        dlg.script_executed.connect(lambda name, out: self._say(f"Skript \u201e{name}\u201c ausgeführt! 🐾", 3500))
        dlg.exec()

    def set_home_mode(self, at_home: bool) -> None:
        self._change_wallpaper(at_home)

    def _check_startup_routines(self) -> None:
        try:
            import custom_scripts
            due = custom_scripts.get_due_routines(is_startup=True)
            for s in due:
                self._run_routine_bg(s)
        except Exception as exc:
            print(f"[routines] Startup-Check Fehler: {exc}")

    def _check_custom_routines(self) -> None:
        try:
            import custom_scripts
            due = custom_scripts.get_due_routines()
            for s in due:
                self._run_routine_bg(s)
        except Exception as exc:
            print(f"[routines] Check Fehler: {exc}")

    def _run_routine_bg(self, script_dict: dict) -> None:
        sname = script_dict.get("name", "")
        title = script_dict.get("title") or sname
        import threading
        def _worker():
            import custom_scripts
            res = custom_scripts.run_script(sname)
            if res.get("ok"):
                summary = (res.get("stdout") or "").strip()
                if summary:
                    first_line = summary.splitlines()[0][:90]
                    msg = f"Routine \u201e{title}\u201c ausgeführt! 🐾 {first_line}"
                else:
                    msg = f"Routine \u201e{title}\u201c erfolgreich abgeschlossen! 🐾✨"
                self.routine_message.emit(msg)     # QTimer.singleShot aus threading.Thread kam nie an
            else:
                self.routine_message.emit(f"Routine „{title}“ hat nicht geklappt: {(res.get('error') or '')[:90]}")
        threading.Thread(target=_worker, daemon=True).start()

    def _on_routine_message(self, msg: str) -> None:
        self._say(msg, 6000)

    # -- v2.4.0: Minispiele, Lively Wallpaper & Möbel ----------------------------------
    def start_bubble_game(self) -> None:
        if not hasattr(self, "bubble_mgr") or not self.bubble_mgr:
            from minigames import BubblePopGameManager
            from memory_store import get_memory_store
            self.bubble_mgr = BubblePopGameManager(get_memory_store(), self.cfg)
        self.bubble_mgr.spawn_wave(14)
        self._say("🫧 Seifenblasen-Welle gestartet! Klicke die Blasen an, um sie mit *Plopp!* zu zerplatzen!", 4500)

    def start_yarn_game(self) -> None:
        from minigames import YarnBallWidget
        if not getattr(self, "yarn_ball", None):
            self.yarn_ball = YarnBallWidget()
            self.yarn_ball.kicked.connect(self._on_yarn_kicked)

        hx = self.pet.x() + (120 if self.pet.facing > 0 else -120)
        hy = self.pet.y() - 80
        self.yarn_ball.launch(float(hx), float(hy), 280.0 if self.pet.facing > 0 else -280.0, -220.0)
        self.pet.wake()
        self.pet.chase_mouse(12.0)
        self._say("🧶 Fang das Wollknäuel! Klicke und wirf es mit Schwung über den Desktop!", 4500)

    def _on_yarn_kicked(self) -> None:
        from memory_store import get_memory_store
        from achievements import record_achievement_event
        from fun import add_friendship_points
        try:
            store = get_memory_store()
            add_friendship_points(store, "yarn")
            record_achievement_event(store, "yarn_catches", 1)
        except Exception:
            pass
        self.pet.react_happy()
        cname = self.char_info().get("name", "Kylie")
        self._say(f"Yay! 🐾 {cname} hat das Wollknäuel gefangen und weggestupst!", 3500)

    def activate_lively_wallpaper(self) -> None:
        self._change_wallpaper(True)

    def restore_desktop_wallpaper(self) -> None:
        self._change_wallpaper(False)

    def _change_wallpaper(self, activate: bool) -> None:
        if self._wallpaper_worker is not None and self._wallpaper_worker.isRunning():
            self._say('Der Hintergrund wird bereits umgestellt. Einen Moment bitte.', 4000)
            return
        from wallpaper_worker import WallpaperWorker
        from memory_store import get_memory_store
        self._say('Ich richte das Zimmer ein…' if activate else 'Ich stelle deinen Hintergrund wieder her…', 5000)
        worker = WallpaperWorker(self.cfg, activate, store=get_memory_store(), parent=self)
        self._wallpaper_worker = worker
        dialog = getattr(self, '_character_dialog', None)
        if dialog is not None and dialog.isVisible():
            dialog.set_wallpaper_busy(True, 'Der Hintergrund wird umgestellt…')
        worker.completed.connect(lambda ok, msg: self._wallpaper_changed(activate, ok, msg))
        worker.start()

    def _wallpaper_changed(self, activate: bool, ok: bool, message: str) -> None:
        if ok:
            self.cfg.set('pet.is_at_home', activate)
            self.cfg.set('pet.room_mode', activate)
            self.cfg.save()
            if activate:
                if self.pet_bed and self.cfg.get('furniture.bed_visible', True):
                    self.pet_bed.show()
                self.pet.celebrate(2.5)
            elif self.pet_bed:
                self.pet_bed.hide()
                self.pet.on_bed_hidden()
            self._update_tray_menu()
        dialog = getattr(self, '_character_dialog', None)
        if dialog is not None and dialog.isVisible():
            dialog.set_wallpaper_busy(False, message)
            dialog.refresh_all()
        self._say(message, 6000)

    def toggle_pet_bed(self, visible: Optional[bool] = None) -> None:
        if not hasattr(self, "pet_bed") or not self.pet_bed:
            from furniture import PetBedWidget
            self.pet_bed = PetBedWidget(self.cfg)
            self.pet.pet_bed = self.pet_bed
            self.pet_bed.bed_moved.connect(self.pet.on_bed_moved)
            self.pet_bed.hide_requested.connect(lambda: self.toggle_pet_bed(False))
        new_vis = (not self.pet_bed.isVisible()) if visible is None else visible
        self.cfg.set("furniture.bed_visible", new_vis)
        self.cfg.save()
        if new_vis:
            self.pet_bed.show()
            self.pet.raise_()
            self._say("🛋️ Dein kuscheliges Katzenbett steht bereit! Du kannst es mit der Maus frei verschieben.", 4000)
        else:
            self.pet_bed.hide()
            self.pet.on_bed_hidden()
        self._update_tray_menu()

    def open_friendship_dialog(self) -> None:
        self._dismiss_interaction()
        from fun_dialogs import FriendshipDialog
        from memory_store import get_memory_store
        dlg = FriendshipDialog(get_memory_store(), self.cfg, self.char_info(), self.pet)
        dlg.accessory_changed.connect(lambda acc: self.pet.update())
        dlg.exec()

    def open_focus_stats_dialog(self) -> None:
        self._dismiss_interaction()
        from fun_dialogs import FocusStatsDialog
        from memory_store import get_memory_store
        dlg = FocusStatsDialog(get_memory_store(), self.char_info(), self.pet)
        dlg.exec()

    def open_flashcards_dialog(self) -> None:
        self._dismiss_interaction()
        from fun_dialogs import FlashcardsDialog
        from memory_store import get_memory_store
        dlg = FlashcardsDialog(get_memory_store(), self.pet, cfg=self.cfg)
        dlg.quiz_requested.connect(self.start_flashcard_quiz)
        dlg.exec()

    def start_flashcard_quiz(self, deck: Optional[str] = None) -> None:
        from memory_store import get_memory_store
        store = get_memory_store()
        cards = store.get_cards(deck) if deck else store.get_cards()
        if not cards and deck:
            cards = store.get_cards()
        if not cards:
            self._say(tr("say.no_cards"), 5000)
            return

        sorted_cards = sorted(cards, key=lambda c: c.get("box", 1))
        quiz_cards = sorted_cards[:10]
        random.shuffle(quiz_cards)

        self._quiz_session = {
            "deck": deck or "Allgemein",
            "cards": quiz_cards,
            "index": 0,
            "correct": 0,
            "total": len(quiz_cards),
        }
        self.pet.wake()
        self._say(tr("say.quiz_start", n=len(quiz_cards)), 2500)
        QTimer.singleShot(2600, self._ask_next_quiz_card)

    def _ask_next_quiz_card(self) -> None:
        if not self._quiz_session:
            return
        idx = self._quiz_session["index"]
        cards = self._quiz_session["cards"]
        if idx >= len(cards):
            self._finish_quiz()
            return

        card = cards[idx]
        total = self._quiz_session["total"]
        q_text = f"📚 Frage {idx + 1}/{total}:\n„{card['front']}“\n(Tippe deine Antwort)"
        self._say(q_text, duration_ms=10000, persistent=True)
        QTimer.singleShot(500, lambda: self.open_input(reply_mode=True))

    def _handle_quiz_answer(self, text: str) -> None:
        if not self._quiz_session:
            return
        if text.strip().lower() in ("abbrechen", "stop", "beenden", "quiz beenden"):
            self._quiz_session = None
            self._say(tr("say.quiz_cancelled"), 3000)
            return

        from fun import compare_answer, update_leitner_box
        from memory_store import get_memory_store
        store = get_memory_store()

        session = self._quiz_session
        idx = session["index"]
        card = session["cards"][idx]
        expected = card["back"]

        is_correct, is_close = compare_answer(text, expected)
        new_box = update_leitner_box(card["box"], is_correct)
        try:
            store.update_card_box(card["id"], new_box)
        except Exception:
            pass

        if is_correct:
            session["correct"] += 1
            self.pet.react_happy()
            if is_close:
                feedback = f"Fast perfekt! 🎉\nRichtige Antwort: „{expected}“"
            else:
                feedback = f"Richtig! 🌟\n„{expected}“"
        else:
            self.pet.sad(2.0)
            feedback = f"Leider nicht ganz! 💡\nDie Lösung war: „{expected}“"

        session["index"] += 1
        self._say(feedback, 2500)
        QTimer.singleShot(2600, self._ask_next_quiz_card)

    def _finish_quiz(self) -> None:
        session = self._quiz_session
        self._quiz_session = None
        if not session:
            return
        correct = session["correct"]
        total = session["total"]
        self._award_friendship("quiz")
        if correct >= total * 0.7:
            self.pet.celebrate(4.0)
            msg = f"Quiz abgeschlossen! 🌟 {correct} von {total} richtig! Super gemacht, {self.user_name()}! (+3 Freundschaftspunkte 💖)"
        elif correct >= total * 0.4:
            self.pet.react_happy()
            msg = f"Quiz beendet! 🐾 {correct} von {total} richtig. Guter Versuch! (+3 Freundschaftspunkte 💖)"
        else:
            self.pet.calm()
            msg = f"Quiz beendet! 💡 {correct} von {total} richtig. Nicht aufgeben! (+3 Freundschaftspunkte 💖)"
        self._say(msg, 6000)
        self.brain.record_assistant_message(msg)

        from memory_store import get_memory_store
        try:
            hard = [c for c in get_memory_store().get_cards() if c["box"] == 1]
            if len(hard) >= 3:
                self._difficult_cards_count = len(hard)
        except Exception:
            pass

    def _create_ai_flashcards(self, topic: str, count: int = 10) -> None:
        if not self.cfg.get('ai.enabled', True) or not gemini.has_key():
            self._say(tr("say.cards_need_key"), 4500)
            return

        self._say(tr("say.cards_creating", count=count, topic=topic), persistent=True)
        from fun_dialogs import GeminiCardWorker
        from memory_store import get_memory_store

        worker = GeminiCardWorker(topic)
        def _on_success(cards):
            store = get_memory_store()
            deck_name = topic.strip().capitalize()
            for front, back in cards[:count]:
                store.add_card(deck_name, front, back)
            self.pet.celebrate(3.0)
            self._say(tr("say.cards_done", n=len(cards[:count]), deck_name=deck_name), 6000)
        def _on_fail(err):
            self.pet.sad()
            self._say(tr("say.cards_failed", err=err), 4000)

        worker.success.connect(_on_success)
        worker.failed.connect(_on_fail)
        self._active_workers = [w for w in self._active_workers if not w.isFinished()]   # Referenz halten bis fertig
        self._active_workers.append(worker)
        worker.start()

    def start_photobox(self) -> None:
        cname = self.char_info().get("name", "Kylie")
        self._say(tr("say.photo_warn", cname=cname), 2400)
        pose_choice = random.choice(["dance", "cool", "celebrate"])
        if pose_choice == "dance":
            self.pet.dance(7.0)
        elif pose_choice == "cool":
            self.pet.be_cool(7.0)
        else:
            self.pet.celebrate(7.0)
        acc = random.choice(["sunglasses", "party_hat", "bow", "crown", "bandana", None])
        if acc:
            self.pet.set_accessory(acc, True, until=time.monotonic() + 8.0)
        # Selfie: Kylie posiert kurz doppelt so gross (Fuesse bleiben stehen)
        self._photo_old_scale = self.pet.scale
        self.pet.set_scale(min(2.5, self.pet.scale * 2))

        # Spruch: offline sofort, mit Gemini-Key wird er waehrend des Countdowns ersetzt
        from fun import photo_caption
        self._photo_caption = photo_caption(cname, self.user_name())
        if self.cfg.get('ai.enabled', True) and gemini.has_key():
            import threading
            prompt = tr("photo.caption_prompt", cname=cname, user=self.user_name())

            def _ask() -> None:
                try:
                    txt = gemini.ask(prompt, timeout_s=5).strip().strip('"„“')
                    if 3 <= len(txt) <= 60:
                        self._photo_caption = txt          # nur ein String - kein Qt-Objekt im Thread
                except Exception:
                    pass
            threading.Thread(target=_ask, daemon=True).start()

        QTimer.singleShot(2400, lambda: self._say(tr("say.countdown_3"), 1000))
        QTimer.singleShot(3500, lambda: self._say(tr("say.countdown_2"), 1000))
        QTimer.singleShot(4600, lambda: self._say(tr("say.countdown_1"), 900))
        QTimer.singleShot(5600, self._snap_photobox)

    def _snap_photobox(self) -> None:
        try:
            from fun import flatten_on_white, frame_photobox_image, generate_photobox_filename, photo_crop_rect
            self.bubble.hide_now()
            pet_geo = self.pet.frameGeometry()
            screen = QGuiApplication.screenAt(pet_geo.center()) or self.app.primaryScreen()
            if not screen:
                return
            sg = screen.geometry()
            x, y, w, h = photo_crop_rect(pet_geo.x(), pet_geo.y(), pet_geo.width(), pet_geo.height(),
                                         sg.x(), sg.y(), sg.width(), sg.height())
            img = screen.grabWindow(0, x - sg.x(), y - sg.y(), w, h).toImage()
            self._photo_flash(screen)

            now_dt = datetime.datetime.now()
            framed = frame_photobox_image(img, self._photo_caption, now_dt.strftime("%d.%m.%Y"),
                                          angle=random.uniform(-4.0, 4.0))
            target_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)) / "Desktop Cat"
            target_dir.mkdir(parents=True, exist_ok=True)
            out_path = target_dir / generate_photobox_filename(now_dt)
            framed.save(str(out_path))
            QGuiApplication.clipboard().setImage(flatten_on_white(framed))

            self.pet.react_happy()
            self._say(tr("say.photo_done_clip"), 4000)
            self._last_photo_folder = str(target_dir)
            os.startfile(str(out_path))                    # mit dem Standard-Bildprogramm oeffnen
        except Exception as exc:
            print(f"[photobox] Fehler: {exc}")
            self._say(tr("say.photo_failed", exc=exc), 4000)
        finally:
            QTimer.singleShot(400, lambda: self.pet.set_scale(getattr(self, "_photo_old_scale", 1.0)))

    def _photo_flash(self, screen) -> None:
        """Weisser Blitz + Klick-Klack (nach dem Foto, damit beides nicht drauf ist)."""
        from PyQt6.QtCore import QPropertyAnimation, Qt
        from PyQt6.QtWidgets import QWidget
        flash = QWidget(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                        | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
        flash.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        flash.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        flash.setStyleSheet("background: white;")
        flash.setGeometry(screen.geometry())
        flash.setWindowOpacity(0.85)
        flash.show()
        anim = QPropertyAnimation(flash, b"windowOpacity", flash)
        anim.setDuration(380)
        anim.setStartValue(0.85)
        anim.setEndValue(0.0)
        anim.finished.connect(flash.close)
        anim.start()
        try:
            import threading
            import winsound
            from fun import shutter_wav
            threading.Thread(target=winsound.PlaySound, args=(shutter_wav(), winsound.SND_MEMORY), daemon=True).start()
        except Exception:
            pass

    def _on_tray_message_clicked(self) -> None:
        if getattr(self, "_last_photo_folder", None):
            folder = self._last_photo_folder
            self._last_photo_folder = None
            try:
                import os
                os.startfile(folder)
            except Exception:
                pass

    def create_sticky_note(self, text: str = "", color: str = "yellow") -> None:
        note_id, x, y = self.note_manager.create_note(text=text, color=color)
        self.pet.fly_to(float(x - 50), float(y + 20))
        QTimer.singleShot(1100, lambda: self.pet.push_animation(1.2))
        QTimer.singleShot(2600, self.pet.land)                  # sonst schwebt sie ewig auf der Wolke
        self._say(tr("say.note_stuck"), 3000)

    def _on_note_completed(self, _note_id: int) -> None:
        self.pet.react_happy()
        self._say(tr("say.done_great"), 3500)

    # -- v3.0.0: Voice Interaktion, Push-to-Talk, Lip-Sync & TTS -----------------------
    def _voice_hotkey_pressed(self) -> None:
        if getattr(self, "_focus_mode", False):
            return
        if self._is_recording_voice or self._is_processing_voice:
            return
        # Mikrofon nur, wenn die KI ueberhaupt an ist und ein Zugang existiert (Audio geht an Gemini)
        if not self.cfg.get("ai.enabled", True) or not gemini.has_key():
            self._say(tr("say.voice_needs_ai"), 4000)
            return
        parsed = parse_hotkey(str(self.cfg.get("hotkey_voice", "ctrl+alt+space")))
        self._ptt_vk = parsed[1] if parsed else 0x20

        recorder = voice_recorder.get_recorder()
        if not recorder.start_recording():
            self._say("⚠️ Mikrofon konnte nicht gestartet werden.", 3000)
            return

        self._is_recording_voice = True
        self.pet.set_listening(True)
        self.pet.wake()
        self.pet.freeze(True)
        self._say(tr("say.voice_listening"), 30000)

        # Polling Timer für Keyup der Leertaste (Push-to-Talk)
        self._ptt_poll_timer.start(30)

    def _on_ptt_poll(self) -> None:
        if not self._is_recording_voice:
            self._ptt_poll_timer.stop()
            return

        # Ist die Haupttaste des eingestellten Sprach-Hotkeys noch gedrueckt? (vorher fest die Leertaste)
        key_state = ctypes.windll.user32.GetAsyncKeyState(getattr(self, "_ptt_vk", 0x20))
        is_down = bool(key_state & 0x8000)

        recorder = voice_recorder.get_recorder()
        if not is_down or recorder.duration_seconds() > 30.0:
            self._ptt_poll_timer.stop()
            self._voice_hotkey_released()

    def _voice_hotkey_released(self) -> None:
        if not self._is_recording_voice:
            return
        self._is_recording_voice = False
        self.pet.set_listening(False)
        self.pet.freeze(False)

        recorder = voice_recorder.get_recorder()
        dur = recorder.duration_seconds()
        audio_path = recorder.stop_recording()

        if dur < 0.35 or not audio_path:
            self._say("🐾 Zu kurz! Halte die Tasten gedrückt, während du sprichst.", 3500)
            return

        self._is_processing_voice = True
        self._say(tr("say.voice_thinking"), 30000)
        try:
            worker = VoiceWorker(audio_path, self.cfg.snapshot())
            worker.finished_with_result.connect(self._on_voice_result)
            worker.failed.connect(self._on_voice_failed)
            self._voice_workers = [w for w in getattr(self, "_voice_workers", []) if not w.isFinished()] + [worker]
            worker.start()
        except Exception as exc:              # sonst bliebe die Sprache bis zum Neustart blockiert
            self._is_processing_voice = False
            try:
                os.remove(audio_path)         # Aufnahme der Stimme nicht im Temp-Ordner liegen lassen
            except OSError:
                pass
            self._on_voice_failed(str(exc))

    def _on_voice_result(self, text: str) -> None:
        self._is_processing_voice = False
        if not text:
            self._say("🐾 Ich habe leider nichts gehört. Versuche es noch einmal!", 4000)
            return
        duration_ms = max(4500, min(16000, len(text) * 115))
        self._say(text, duration_ms)

        low = text.lower()
        if "💤" in text or "schlaf" in low or "gute nacht" in low or "ab ins bett" in low:
            self.pet.go_to_sleep()
        elif "💃" in text or "tanz" in low:
            self.pet.dance(6.0)
        elif "🕶️" in text or "cool" in low:
            self.pet.be_cool(6.0)
        elif "wach auf" in low or "guten morgen" in low or "aufstehen" in low:
            self.pet.wake_with_stretch()

        # Synchrone Sprachausgabe + Lip-Sync
        voice_tts.get_tts().speak(text, self.cfg.snapshot())

    def _on_voice_failed(self, err: str) -> None:
        self._is_processing_voice = False
        self._say(f"🐾 Miau, Fehler bei Sprachverarbeitung: {err}", 5000)

    def _toggle_voice_output(self) -> None:
        cur = bool(self.cfg.get("voice.enabled", True))
        self.cfg.set("voice.enabled", not cur)
        self.cfg.save()
        self._update_tray_menu()
        status = "aktiviert 🔊" if not cur else "deaktiviert 🔇"
        self._say(f"Sprachausgabe wurde {status}.", 2500)

    # -- Phase 5: IT-Support, Klick-Guide, Fehler-Doktor & Kopieren/Erklären -----------
    def _explain_hotkey_pressed(self) -> None:
        text = QGuiApplication.clipboard().text().strip()
        if not text:
            self._say(tr("say.select_first"), 4000)
            return
        if len(text) > 4000:
            text = text[:4000]

        menu = style_menu(QMenu())
        a_explain = menu.addAction("💡  Erklären")
        a_translate = menu.addAction("🌍  Übersetzen (DE↔EN)")
        a_summarize = menu.addAction("📝  Zusammenfassen")
        a_improve = menu.addAction("✍️  Verbessern")

        pos = self.pet.mapToGlobal(QPoint(self.pet.width() // 2, 0))
        chosen = menu.exec(pos)
        if not chosen:
            return

        if chosen == a_explain:
            mode = "explain"
        elif chosen == a_translate:
            mode = "translate"
        elif chosen == a_summarize:
            mode = "summarize"
        elif chosen == a_improve:
            mode = "improve"
        else:
            return

        self._run_clipboard_action(mode, text)

    def _run_clipboard_action(self, mode: str, text: str) -> None:
        if not self.cfg.get('ai.enabled', True) or not gemini.has_key():
            self._say(tr("say.explain_need_key"), 4000)
            return

        self.pet.freeze(True)
        self.pet.set_working()
        self._say(tr("say.looking"), persistent=True)

        worker = ClipboardExplainWorker(mode, text)
        worker.finished_with_result.connect(self._on_explain_result)
        worker.failed.connect(self._on_explain_failed)
        worker.finished.connect(self._reap_explain_threads)
        self._explain_workers.add(worker)
        worker.start()

    @pyqtSlot(str, str)
    def _on_explain_result(self, title: str, result: str) -> None:
        self.pet.freeze(False)
        self.bubble.hide_now()
        anchor = self.pet.head_anchor()
        self.explain_card.show_result(title, result, anchor)

    @pyqtSlot(str)
    def _on_explain_failed(self, err: str) -> None:
        self.pet.freeze(False)
        self.bubble.hide_now()
        self._say(tr("say.error", err=err), 4500)

    @pyqtSlot()
    def _reap_explain_threads(self) -> None:
        for t in [t for t in self._explain_workers if t.isFinished()]:
            self._explain_workers.discard(t)
            t.deleteLater()

    # -- Fehler-Doktor -----------------------------------------------------------------
    def start_error_doctor(self) -> None:
        if not self.cfg.get('ai.enabled', True) or not gemini.has_key():
            self._say(tr("say.doctor_need_key"), 4000)
            return

        self.pet.hide()
        self.bubble.hide_now()
        if self.guide_overlay:
            self.guide_overlay.hide()
        QTimer.singleShot(120, self._capture_and_diagnose_error)

    def _capture_and_diagnose_error(self) -> None:
        screen = self._get_active_screen()
        pix = screen.grabWindow(0)
        self.pet.show()
        b64 = pixmap_to_b64(pix)

        self.pet.set_accessory("hacker_glasses", True)
        self.pet.freeze(True)
        self.pet.set_working()
        self._say(tr("say.doctor_scanning"), persistent=True)

        worker = ErrorDoctorWorker(b64)
        worker.finished_with_result.connect(self._on_error_doctor_result)
        worker.failed.connect(self._on_error_doctor_failed)
        worker.finished.connect(self._reap_error_doctor_threads)
        self._error_doctor_workers.add(worker)
        worker.start()

    @pyqtSlot(str)
    def _on_error_doctor_result(self, explanation: str) -> None:
        self.pet.freeze(False)
        self.bubble.hide_now()
        self.pet.react_happy()

        actions = [
            (tr("doctor.btn_show"), lambda: self.start_it_guide("Fehler beheben: " + explanation[:100])),
            (tr("doctor.btn_close"), self._on_error_doctor_closed),
        ]

        self.bubble.show_with_actions(explanation, actions)

    @pyqtSlot(str)
    def _on_error_doctor_failed(self, err: str) -> None:
        self.pet.freeze(False)
        self.pet.set_accessory("hacker_glasses", False)
        self.bubble.hide_now()
        self._say(tr("say.doctor_error", err=err), 4500)

    def _on_error_doctor_closed(self) -> None:
        self.pet.set_accessory("hacker_glasses", False)
        self.bubble.hide_now()

    @pyqtSlot()
    def _reap_error_doctor_threads(self) -> None:
        for t in [t for t in self._error_doctor_workers if t.isFinished()]:
            self._error_doctor_workers.discard(t)
            t.deleteLater()

    # -- IT-Support / Klick-Anleitung --------------------------------------------------
    def start_it_guide(self, question: str) -> None:
        if not self.cfg.get('ai.enabled', True) or not gemini.has_key():
            self._say(tr("say.guide_need_key"), 4000)
            return

        self.pet.set_accessory("hacker_glasses", True)
        self.pet.set_accessory("cloud", True)
        self._say(tr("say.guide_start"), 3000)

        cid = self.pet.character
        self._guide_session = GuideSession(question, self.user_name(), cid)
        if self.guide_overlay is None:
            self.guide_overlay = GuideOverlay()

        QTimer.singleShot(1500, self._guide_capture_and_step)

    def _guide_capture_and_step(self) -> None:
        if not self.cfg.get('ai.enabled', True):
            self._guide_finish(celebrate=False)
            return
        if self._guide_session is None or self._guide_session.done:
            self._guide_finish(celebrate=True)
            return

        target_screen = self._get_active_screen()
        if self.guide_overlay:
            self.guide_overlay.set_screen_geometry(target_screen.geometry())

        self.pet.hide()
        self.bubble.hide_now()
        if self.guide_overlay:
            self.guide_overlay.hide()

        QTimer.singleShot(120, lambda: self._guide_take_screenshot(target_screen))

    def _guide_take_screenshot(self, target_screen: QScreen) -> None:
        pix = target_screen.grabWindow(0)
        self.pet.show()
        b64 = pixmap_to_b64(pix)

        worker = GuideWorker(self._guide_session, b64, target_screen.geometry())
        worker.step_ready.connect(self._guide_on_step_ready)
        worker.failed.connect(self._guide_on_step_failed)
        worker.finished.connect(self._reap_guide_threads)
        self._guide_workers.add(worker)
        worker.start()

    @pyqtSlot(dict, object)
    def _guide_on_step_ready(self, step_dict: dict, rect: Optional[QRect]) -> None:
        if step_dict.get("done") or (self._guide_session and self._guide_session.done):
            self._guide_finish(celebrate=True)
            return

        step_no = self._guide_session.step_no if self._guide_session else 1
        total = self._guide_session.total_steps if self._guide_session else 3
        say_text = f"Schritt {step_no} von ~{total}: {step_dict.get('say', '')}"

        if rect is not None and self.guide_overlay:
            screen_geo = self.guide_overlay.geometry()
            self._guide_fly_near_target(rect, screen_geo)
            self.guide_overlay.set_target(
                rect,
                self.pet.pos(),
                step_dict.get("action", "left"),
                step_dict.get("target", ""),
            )
            self.guide_overlay.show()
        elif self.guide_overlay:
            self.guide_overlay.hide_target()

        actions = [
            (tr("guide.btn_next"), self._guide_capture_and_step),
            (tr("guide.btn_repeat"), lambda: self._guide_repeat(say_text, step_dict, rect)),
            (tr("guide.btn_done"), lambda: self._guide_finish(celebrate=False)),
        ]
        self.bubble.show_with_actions(say_text, actions)

    def _guide_repeat(self, say_text: str, step_dict: dict, rect: Optional[QRect]) -> None:
        if rect is not None and self.guide_overlay:
            screen_geo = self.guide_overlay.geometry()
            self._guide_fly_near_target(rect, screen_geo)
            self.guide_overlay.set_target(
                rect,
                self.pet.pos(),
                step_dict.get("action", "left"),
                step_dict.get("target", ""),
            )
            self.guide_overlay.show()
        actions = [
            (tr("guide.btn_next"), self._guide_capture_and_step),
            (tr("guide.btn_repeat"), lambda: self._guide_repeat(say_text, step_dict, rect)),
            (tr("guide.btn_done"), lambda: self._guide_finish(celebrate=False)),
        ]
        self.bubble.show_with_actions(say_text, actions)


    @pyqtSlot(str)
    def _guide_on_step_failed(self, err: str) -> None:
        self._say(tr("say.guide_step_failed", err=err), 4000)
        self._guide_finish(celebrate=False)

    def _guide_finish(self, celebrate: bool = False) -> None:
        if self.guide_overlay:
            self.guide_overlay.hide()
            self.guide_overlay.hide_target()
        self.pet.set_accessory("cloud", False)
        self.pet.set_accessory("hacker_glasses", False)
        self.pet.land()
        self.bubble.hide_now()
        if celebrate:
            self._say(tr("say.guide_done"), 4000)
            self.pet.celebrate()
        else:
            self._say(tr("say.guide_ended"), 3000)
        self._guide_session = None

    def _get_active_screen(self) -> QScreen:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                center = QPoint((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
                sc = QGuiApplication.screenAt(center)
                if sc:
                    return sc
        except Exception:
            pass
        return QGuiApplication.screenAt(self.pet.pos()) or QGuiApplication.primaryScreen()

    def _guide_fly_near_target(self, target_rect: QRect, screen_geo: QRect) -> None:
        if target_rect.center().x() > screen_geo.x() + screen_geo.width() // 2:
            fly_x = target_rect.left() - 140
        else:
            fly_x = target_rect.right() + 20
        fly_y = target_rect.center().y() - 60
        fly_x = max(screen_geo.left() + 10, min(fly_x, screen_geo.right() - 150))
        fly_y = max(screen_geo.top() + 10, min(fly_y, screen_geo.bottom() - 150))
        self.pet.fly_to(fly_x, fly_y)

    @pyqtSlot()
    def _reap_guide_threads(self) -> None:
        for t in [t for t in self._guide_workers if t.isFinished()]:
            self._guide_workers.discard(t)
            t.deleteLater()

    # -- Intelligente Umgebungs- und Code-Beobachtung (Screen & Coding Companion) ---
    def _smart_ambient_comment(self) -> Optional[str]:
        """Prüft das aktive Fenster und liefert einen charmanten, kontextbezogenen Kommentar."""
        text = self._smart_ambient_raw()
        return text.replace("Boss", self.user_name()) if text else text

    def _smart_ambient_raw(self) -> Optional[str]:
        try:
            import tools
            ctx = tools.get_active_window_context()
            top = ctx.get("top_window", "")
            if not top:
                return None
            top_low = top.lower()

            # 1. Angular
            if "angular" in top_low:
                comments = [
                    "Schön, was du da in Angular programmierst, Boss! 🅰️✨ Brauchst du Tipps für Routing, Signals oder Services?",
                    "Angular-Code sieht super strukturiert aus! 🐾 Vergiss nicht ab und zu 'ng build' zu prüfen.",
                    "Fleißig am Angular-Projekt! 💻 Sag Bescheid, wenn ich dir Komponenten zusammenfassen soll.",
                ]
                return random.choice(comments)

            # 2. React / Next.js / Vue
            if any(k in top_low for k in ("react", "next.js", "nextjs", "vue", "vite")):
                return "Frontend-Magie am Werk! ⚛️✨ Sieht richtig modern und sauber aus, Boss!"

            # 3. Python
            if any(k in top_low for k in ("python", ".py", "pytest")):
                comments = [
                    "Fleißig am Python-Coden, Boss! 🐍🐾 Sag Bescheid, wenn ich ein Skript testen soll.",
                    "Python-Code läuft geschmeidig! 🐍✨ Brauchst du Hilfe bei Bibliotheken?",
                ]
                return random.choice(comments)

            # 4. TypeScript / JavaScript / Web
            if any(k in top_low for k in (".ts", ".js", "typescript", "javascript", "node")):
                return "Sauberer TypeScript-Code! 💻✨ Typen sitzen, alles läuft stabil!"

            # 5. Allgemeiner Code-Editor / IDE
            if any(k in top_low for k in ("code", "antigravity", "visual studio", "pycharm", "webstorm", "intellij", "sublime")):
                app_name = top.split(" - ")[-1] if " - " in top else "deinem Editor"
                comments = [
                    f"Voller Fokus beim Programmieren in {app_name}! 💻🐾 Ich halte dir den Rücken frei.",
                    "Fleißig am Tippen, Boss! ⌨️✨ Denk dran, ab und zu zu speichern!",
                    "Du machst super Fortschritte beim Coden heute! 🌟🐾",
                ]
                return random.choice(comments)

            # 6. Terminal / Konsole
            if any(k in top_low for k in ("powershell", "cmd.exe", "terminal", "bash")):
                return "Kommandozeilen-Profi am Werk! ⚡ Sag Bescheid, wenn ich einen Befehl ausführen soll."

            # 7. Browser Recherche
            if any(k in top_low for k in ("chrome", "vivaldi", "firefox", "edge", "brave", "github", "stack overflow")):
                if "stack overflow" in top_low or "github" in top_low:
                    return "Recherche auf Entwickler-Seiten? 🌐🐾 Wenn du eine Doku brauchst, frag mich einfach!"
                return "Auf Recherche-Tour im Web, Boss? 🌐🔍 Ich pass auf deinen Desktop auf."

            return None
        except Exception:
            return None

    # -- Gelegentliches Geplauder & Intelligente Tipps -------------------------------------------
    def _schedule_chatter(self) -> None:
        self._chatter.stop()
        if self.cfg.get("pet.chatter", True):
            # Alle 90 bis 180 Sekunden für ein aufmerksames, aber unaufdringliches Erlebnis
            self._chatter.start(random.randint(90, 180) * 1000)

    def _on_chatter(self) -> None:
        if self.update_prompt.isVisible() or self.interaction_card.isVisible():
            self._schedule_chatter()
            return
        if getattr(self, "_focus_mode", False) or not self.pet.isVisible() or is_night(self.cfg):
            self._schedule_chatter()
            return
        idle = self.pet.state in (PetState.IDLE, PetState.SLEEP)
        if idle and not self.brain.busy and not self.input.isVisible() and not self.bubble.isVisible():
            if self.pet.state == PetState.SLEEP:
                self.pet.wake()
            import pet_care
            care_stats = pet_care.get_care_stats(self.cfg)
            # hoechstens alle 30 Min. betteln - vorher kam das alle 3-4 Minuten, bis man fuetterte
            can_nag = time.monotonic() - getattr(self, "_last_care_nag", -1e9) > 1800
            if can_nag and care_stats["hunger"] < 35 and random.random() < 0.6:
                self._last_care_nag = time.monotonic()
                self._say(tr("say.care_hungry", name=self.user_name()), 6000)
                self._schedule_chatter()
                return
            if can_nag and care_stats["hygiene"] < 35 and random.random() < 0.6:
                self._last_care_nag = time.monotonic()
                self._say(tr("say.care_dirty"), 6000)
                self._schedule_chatter()
                return
            comment = self._smart_ambient_comment()
            last = getattr(self, "_last_chatter", "")
            if comment and comment != last:
                self._last_chatter = comment
                self._say(comment)
            else:
                self._say(random.choice(self.char_info().get("ambient_lines") or CHATTER_LINES))
        self._schedule_chatter()

    # -- Autonome Screen- und Coding-Beobachtung (Gemini Vision + Kontext) --------
    def _schedule_vision(self, initial_delay_s: Optional[int] = None) -> None:
        self._vision_timer.stop()
        if self.cfg.get("pet.chatter", True):
            # Alle 120 bis 210 Sekunden (2 bis 3,5 Minuten)
            delay = initial_delay_s if initial_delay_s is not None else random.randint(120, 210)
            self._vision_timer.start(delay * 1000)

    def _on_autonomous_vision(self) -> None:
        if not self.cfg.get('ai.enabled', True) or not self.cfg.get('privacy.auto_vision', False) or not gemini.has_key():
            self._schedule_vision()
            return
        if getattr(self, "_focus_mode", False) or not self.pet.isVisible() or is_night(self.cfg) or self.brain.busy or self.input.isVisible() or self.pet.state == PetState.WORKING:
            self._schedule_vision()
            return

        b64_img = ""
        try:
            screen = QGuiApplication.primaryScreen()
            if screen:
                pix = screen.grabWindow(0).scaled(720, 405)
                buf = QBuffer()
                buf.open(QBuffer.OpenModeFlag.WriteOnly)
                pix.save(buf, "PNG")
                b64_img = base64.b64encode(buf.data().data()).decode("utf-8")
        except Exception:
            pass

        import tools
        ctx = tools.get_active_window_context()
        top = ctx.get("top_window", "")
        apps = ctx.get("open_apps", [])

        thread = QThread()
        worker = AmbientVisionWorker(b64_img, top, apps, self.cfg.snapshot())
        worker.moveToThread(thread)
        thread._worker = worker
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ambient_vision_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._reap_vision_threads)     # gebunden -> laeuft im Main-Thread
        self._vision_threads.add(thread)
        thread.start()

        self._schedule_vision()

    def _reap_vision_threads(self) -> None:
        for t in [t for t in self._vision_threads if t.isFinished()]:
            self._vision_threads.discard(t)
            t.deleteLater()

    def _on_ambient_vision_done(self, comment: str) -> None:
        comment = (comment or "").strip()
        if not comment:
            return
        if comment == self._last_ambient_comment:
            return
        self._last_ambient_comment = comment

        if self.pet.state == PetState.SLEEP:
            self.pet.wake()
        self._say(comment, duration_ms=11000)

        # Im Chatverlauf merken, damit Rueckfragen und Antworten verstanden werden!
        self.brain.record_assistant_message(comment)

        # Wenn Mochi eine Frage stellt (endet mit ?), Platzhalter auf Antwort anpassen
        self._mochi_asked_question = "?" in comment


def _single_instance():
    """Verhindert doppelte Instanzen (Mutex). Rueckgabe muss referenziert bleiben."""
    try:
        import win32api
        import win32event
        mutex = win32event.CreateMutex(None, False, "MochiDesktopPetMutex")
        if win32api.GetLastError() == 183:      # ERROR_ALREADY_EXISTS
            return None
        return mutex
    except Exception:
        return True


def main() -> int:
    sys.excepthook = lambda et, ev, tb: print("".join(traceback.format_exception(et, ev, tb)), file=sys.stderr)
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    if any(arg in sys.argv for arg in ("--sync-wallpaper", "--setup-wallpaper")):
        import lively_wallpaper
        target = lively_wallpaper.deploy_room_to_lively_library()
        cfg = Config()
        if cfg.get("pet.is_at_home") or cfg.get("lively.auto_sync"):
            lively_wallpaper.apply_lively_wallpaper(cfg)
        print(f"Desktop background setup complete: {target}")
        return 0

    lock = _single_instance()
    if lock is None:
        print("Desktop Cat laeuft bereits.")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Cat")
    app.setQuitOnLastWindowClosed(False)      # Pet lebt weiter, auch wenn Dialoge schliessen
    cfg = Config()

    buddy = Buddy(app, cfg)
    buddy.start()
    code = app.exec()

    buddy.hotkey.unregister()
    if not buddy.brain.shutdown():
        os._exit(code)                          # Worker haengt (z. B. offener Dateidialog) -> hart beenden
    return code


if __name__ == "__main__":
    sys.exit(main())
