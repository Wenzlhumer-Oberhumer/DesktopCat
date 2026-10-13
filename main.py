"""Einstiegspunkt: baut Pet, Sprechblase, Eingabeleiste, Gehirn und Tray-Icon zusammen."""
from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import os
import random
import sys
import traceback
from pathlib import Path

from paths import APP_DIR, DATA_DIR, set_autostart
from version import __version__

# Sicherstellen, dass Module aus APP_DIR importiert werden koennen, auch nach os.chdir(DATA_DIR)
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

os.chdir(DATA_DIR)

# Unter pythonw.exe gibt es keine Konsole -> stdout/stderr in Logdatei umleiten
# Logdatei bei > 2 MB beim Start nach buddy.log.1 rotieren
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

import gemini_cli
from PyQt6.QtCore import (
    QAbstractNativeEventFilter, QBuffer, QObject, QThread, QTimer, pyqtSignal, pyqtSlot,
)
from PyQt6.QtGui import QAction, QGuiApplication, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from agent_brain import AgentBrain
from config import Config
from pet_sprites import render_icon
from pet_window import PetState, PetWindow, style_menu
from settings_dialog import SettingsDialog
from speech_bubble import InputBar, SpeechBubble

APP_ID = "MochiDesktopBuddy"
HOTKEY_ID = 0xB0B0
WM_HOTKEY = 0x0312


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
        self.finished.emit(comment or "")

    def _analyze(self) -> str:
        top = self.top_window or ""
        top_low = top.lower()
        apps_str = ", ".join(self.open_apps[:6])

        # Schritt 1: Cloud-Vision ueber Gemini CLI falls angemeldet
        if gemini_cli.is_logged_in() and self.b64_img:
            screen_file = gemini_cli.WORKSPACE / "screen.png"
            try:
                raw_bytes = base64.b64decode(self.b64_img)
                with open(screen_file, "wb") as f:
                    f.write(raw_bytes)

                prompt = (
                    f"Du bist Mochi, ein extrem neugieriger, süßer Katzen-Buddy auf dem Windows-Desktop des Nutzers ('Boss'). "
                    f"Aktives Fenster des Bosses: '{top}'. Offene Programme: {apps_str}.\n"
                    "Schau dir den Screenshot und das aktive Fenster genau an. Was macht der Boss gerade (z. B. Coden in Angular/Python/React, Dokumente schreiben, Recherche, Surfen, Design)?\n"
                    "Reagiere spontan, lebensfroh und liebenswert darauf:\n"
                    "- Sag kurz, wie du es findest,\n"
                    "- ODER biete ihm charmant deine Hilfe an bzw. stelle eine neugierige Frage dazu.\n"
                    "WICHTIG:\n"
                    "- Maximal 1-2 kurze Sätze auf Deutsch.\n"
                    "- Höchstens ein Emoji.\n"
                    "- Nenne den Nutzer gern 'Boss'.\n"
                    "- Sei niemals belehrend, sondern sympathisch und neugierig."
                )
                comment = gemini_cli.ask(f"@screen.png {prompt}", timeout_s=45)
                if comment and comment.strip():
                    return comment.strip()
            except Exception:
                pass
            finally:
                try:
                    if screen_file.exists():
                        screen_file.unlink()
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
    "Streicheln erlaubt! \U0001F43E", "Du bist der Beste, Boss! \U0001F496", "Pfoten-High-Five! \U0001F43E",
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
    """Globales Tastenkuerzel (RegisterHotKey) - funktioniert auch, wenn ein anderes Programm den Fokus hat."""

    def __init__(self, callback):
        super().__init__()
        self._cb = callback
        self.registered = False

    def register(self, spec: str) -> bool:
        parsed = parse_hotkey(spec)
        if not parsed:
            return False
        mods, vk = parsed
        self.registered = bool(ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, mods | 0x4000, vk))  # MOD_NOREPEAT
        return self.registered

    def unregister(self) -> None:
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = False

    def nativeEventFilter(self, eventType, message):
        try:
            if bytes(eventType) == b"windows_generic_MSG":
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    QTimer.singleShot(0, self._cb)
        except Exception:
            pass
        return False, 0


class Buddy(QObject):
    """Verdrahtet alle Module miteinander."""

    def __init__(self, app: QApplication, cfg: Config):
        super().__init__()
        self.app, self.cfg = app, cfg
        self.pet = PetWindow(cfg, APP_DIR)
        self.bubble = SpeechBubble(cfg)
        self.input = InputBar()
        self.brain = AgentBrain(cfg)
        self._settings_open = False

        # Tray-Icon (auch Quelle fuer Windows-Benachrichtigungen)
        self.icon = QIcon(render_icon(64))
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("Mochi - dein Desktop-Buddy")
        self.tray_menu = style_menu(QMenu())
        self.tray_menu.aboutToShow.connect(self._update_tray_menu)
        self._update_tray_menu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._on_tray)
        self.tray.show()

        # Signale
        self.pet.moved.connect(self._follow)
        self.pet.petted.connect(self._on_petted)
        self.pet.command_requested.connect(self._on_submit)
        self.pet.input_requested.connect(self.open_input)
        self.pet.settings_requested.connect(self.open_settings)
        self.pet.quit_requested.connect(self.quit)
        self.bubble.clicked.connect(self._on_bubble_clicked)
        self.input.submitted.connect(self._on_submit)
        self.input.closed.connect(self._on_input_closed)
        self.brain.started.connect(self._on_task_started)
        self.brain.finished.connect(self._on_task_finished)

        self._last_ambient_comment = ""
        self._mochi_asked_question = False
        self._vision_threads: set[QThread] = set()

        # Globales Tastenkuerzel
        self.hotkey = HotkeyFilter(self._hotkey_pressed)
        self.app.installNativeEventFilter(self.hotkey)
        self._hotkey_ok = self.hotkey.register(cfg.get("hotkey", "ctrl+alt+p"))

        self._chatter = QTimer(self)
        self._chatter.setSingleShot(True)
        self._chatter.timeout.connect(self._on_chatter)

        # Autonome Screen- und Coding-Beobachtung alle paar Minuten
        self._vision_timer = QTimer(self)
        self._vision_timer.setSingleShot(True)
        self._vision_timer.timeout.connect(self._on_autonomous_vision)

    def _update_tray_menu(self) -> None:
        self.tray_menu.clear()
        if not gemini_cli.is_logged_in():
            self._act(self.tray_menu, "\U0001F511  Mit Google anmelden", self.open_settings)
            self.tray_menu.addSeparator()
        self._act(self.tray_menu, "\U0001F4AC  Befehl eingeben", self.open_input)
        self._act(self.tray_menu, "\U0001F441\uFE0F  Bildschirm beobachten (Vision)", lambda: self._on_submit("was mache ich gerade"))
        self._act(self.tray_menu, "\U0001F4C4  Word-Dokument am Desktop erstellen", lambda: self._on_submit("erstelle ein word dokument am desktop"))
        self._act(self.tray_menu, "\U0001F3E0  Zur Taskleiste zur\u00fccksetzen", self.pet.reset_to_taskbar)
        self.tray_menu.addSeparator()
        self._act(self.tray_menu, "\u2699\uFE0F  Einstellungen", self.open_settings)
        self._act(self.tray_menu, f"\u2139\uFE0F  \u00dcber Mochi (v{__version__})", self._about)
        self._act(self.tray_menu, "\U0001F44B  Beenden", self.quit)

    @staticmethod
    def _act(menu: QMenu, text: str, slot) -> QAction:
        act = menu.addAction(text)
        act.triggered.connect(lambda _=False: slot())
        return act

    # -- Start / Ende ------------------------------------------------------------------
    def start(self) -> None:
        set_autostart(bool(self.cfg.get("autostart", True)))
        self.pet.drop_in()

        first_run = not self.cfg.get("first_run_done", False)
        if first_run:
            self.cfg.set("first_run_done", True)
            self.cfg.save()
            if not gemini_cli.is_logged_in():
                hint = "Hi! Klick mich rechts \u2192 Mit Google anmelden, dann werde ich schlau \U0001f9e0"
            else:
                hk = str(self.cfg.get("hotkey", "ctrl+alt+p")).upper().replace("CTRL", "Strg")
                hint = f"Hallo Boss! Ich bin {self.cfg.get('pet.name', 'Mochi')} \U0001F43E Doppelklick oder {hk} = Befehl"
        else:
            hk = str(self.cfg.get("hotkey", "ctrl+alt+p")).upper().replace("CTRL", "Strg")
            hint = f"Hallo Boss! Ich bin {self.cfg.get('pet.name', 'Mochi')} \U0001F43E Doppelklick oder {hk} = Befehl"
            if not self._hotkey_ok:
                hint = f"Hallo Boss! Ich bin {self.cfg.get('pet.name', 'Mochi')} \U0001F43E Doppelklick auf mich = Befehl"

        QTimer.singleShot(1500, lambda: self._say(hint, 6000))
        self._schedule_chatter()
        self._schedule_vision(initial_delay_s=50)

    def _about(self) -> None:
        self._say(f"Mochi v{__version__} \U0001F43E\nDein KI-Desktop-Buddy!", 6000)

    def quit(self) -> None:
        self.hotkey.unregister()
        self.tray.hide()
        self.app.quit()

    # -- Sprechblase / Eingabe ---------------------------------------------------------
    def _follow(self) -> None:
        a = self.pet.head_anchor()
        self.bubble.anchor_to(a)
        self.input.anchor_to(a)

    def _say(self, text: str, duration_ms=None, persistent: bool = False) -> None:
        if self.input.isVisible():
            return
        self._follow()
        self.bubble.say(text, duration_ms, persistent)

    def open_input(self, reply_mode: bool = False) -> None:
        if self.input.isVisible():
            self.input.dismiss()
            return
        if self.brain.busy:
            self._say("Moment, ich bin noch dran... \U0001F6E0\uFE0F", 2500)
            return
        self.bubble.hide_now()
        self.pet.freeze(True)
        self.pet.wake()
        placeholder = "Antworte Mochi... \U0001F43E" if (reply_mode or getattr(self, "_mochi_asked_question", False)) else "Was soll ich tun, Boss? \U0001F43E"
        self.input.popup(self.pet.head_anchor(), placeholder)

    def _on_bubble_clicked(self) -> None:
        """Klick auf die Sprechblase oeffnet direkt die Eingabe, um Mochi zu antworten."""
        if not self.brain.busy:
            self.open_input(reply_mode=True)

    def _on_input_closed(self) -> None:
        if not self.brain.busy:
            self.pet.freeze(False)

    def _hotkey_pressed(self) -> None:
        if not self.pet.isVisible():
            self.pet.show()
        self.open_input()

    def _on_submit(self, text: str) -> None:
        self._mochi_asked_question = False
        self.input.hide_now()       # sofort weg, damit die "Ich bin dran"-Blase erscheinen darf
        if not self.brain.submit(text):
            self._say("Moment, ich bin noch dran... \U0001F6E0\uFE0F", 2500)

    # -- Aufgaben-Lebenszyklus --------------------------------------------------------------
    def _on_task_started(self, _text: str) -> None:
        self.pet.freeze(True)
        self.pet.set_working()
        self._say("Ich bin dran... \U0001F43E", persistent=True)

    def _on_task_finished(self, ok: bool, message: str, notify: str) -> None:
        self.pet.freeze(False)
        low = (message or "").lower()
        if "💃" in message or "tanz" in low:
            self.pet.dance(6.0)
        elif "🕶️" in message or "cool" in low:
            self.pet.be_cool(6.0)
        elif "💤" in message or "schlaf" in low:
            self.pet.set_state(PetState.SLEEP)
        elif ok:
            self.pet.celebrate()
        else:
            self.pet.sad()
        self.bubble.hide_now()
        self._say(("Fertig! \u2728  " if ok and notify else "") + message)
        if notify:
            self.tray.showMessage(notify, message, self.icon, 6000)
        if "?" in message:
            self._mochi_asked_question = True


    # -- Interaktion -------------------------------------------------------------------------
    def _on_petted(self) -> None:
        if self.brain.busy:
            return
        self._say(random.choice(CLICK_LINES), 2500)

    def _on_tray(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.pet.show()
            self.open_input()

    def open_settings(self) -> None:
        if self._settings_open:
            return
        self._settings_open = True
        try:
            dlg = SettingsDialog(self.cfg)
            dlg.setWindowIcon(self.icon)
            if dlg.exec():
                self.pet.apply_config()
                self._schedule_chatter()
                self._say("Gespeichert! \U0001F43E", 2000)
        finally:
            self._settings_open = False

    # -- Intelligente Umgebungs- und Code-Beobachtung (Screen & Coding Companion) ---
    def _smart_ambient_comment(self) -> Optional[str]:
        """Prüft das aktive Fenster und liefert einen charmanten, kontextbezogenen Kommentar."""
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
        idle = self.pet.state in (PetState.IDLE, PetState.SLEEP)
        if idle and not self.brain.busy and not self.input.isVisible() and not self.bubble.isVisible():
            if self.pet.state == PetState.SLEEP:
                self.pet.wake()
            comment = self._smart_ambient_comment()
            last = getattr(self, "_last_chatter", "")
            if comment and comment != last:
                self._last_chatter = comment
                self._say(comment)
            else:
                self._say(random.choice(CHATTER_LINES))
        self._schedule_chatter()

    # -- Autonome Screen- und Coding-Beobachtung (Gemini Vision + Kontext) --------
    def _schedule_vision(self, initial_delay_s: Optional[int] = None) -> None:
        self._vision_timer.stop()
        if self.cfg.get("pet.chatter", True):
            # Alle 120 bis 210 Sekunden (2 bis 3,5 Minuten)
            delay = initial_delay_s if initial_delay_s is not None else random.randint(120, 210)
            self._vision_timer.start(delay * 1000)

    def _on_autonomous_vision(self) -> None:
        if self.brain.busy or self.input.isVisible() or self.pet.state == PetState.WORKING:
            self._schedule_vision()
            return

        b64_img = ""
        try:
            screen = QGuiApplication.primaryScreen()
            if screen:
                pix = screen.grabWindow(0).scaled(720, 405)
                buf = QBuffer()
                buf.open(QBuffer.OpenModeFlag.WriteOnly)
                pix.save(buf, "JPEG", 55)
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
        worker.finished.connect(lambda *_: thread.quit())
        thread.finished.connect(lambda: self._vision_threads.discard(thread))
        thread.finished.connect(thread.deleteLater)
        self._vision_threads.add(thread)
        thread.start()

        self._schedule_vision()

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

    lock = _single_instance()
    if lock is None:
        print("Mochi laeuft bereits.")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Mochi")
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
