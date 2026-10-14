# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Das Pet-Fenster: transparentes Always-on-Top-Overlay mit Zustandsmaschine, Physik und Animation."""
from __future__ import annotations

import math
import random
import time
from collections import deque
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from i18n import tr
import sound_effects
import tools

from accessories import fly_position
from pet_sprites import (
    BASE, FLOOR, PoseContext, SpriteLibrary, _draw_effects, compute_pose, draw_cat,
)
try:
    from pet_sprites import CHARACTERS, draw_character
except ImportError:         # alte pet_sprites ohne Charakter-Registry
    CHARACTERS = {}

    def draw_character(p, pose, char_id):
        draw_cat(p, pose)


def is_night(cfg) -> bool:
    """Nachtmodus (23-7 Uhr) aktiv?"""
    return bool(cfg.get("night_mode", True)) and (time.localtime().tm_hour >= 23 or time.localtime().tm_hour < 7)


class PetState(Enum):
    IDLE = "idle"
    WALK_LEFT = "walk_left"
    WALK_RIGHT = "walk_right"
    DRAGGED = "dragged"
    FALLING = "falling"
    WORKING = "working"
    SUCCESS = "success"
    SLEEP = "sleep"
    SAD = "sad"
    DANCE = "dance"
    COOL = "cool"
    PUSH = "push"
    FLY = "fly"


WALKING = (PetState.WALK_LEFT, PetState.WALK_RIGHT)

# Timer-Intervall pro Zustand (ms). Ruhige Zustaende laufen mit wenig FPS -> kaum CPU-Last.
INTERVALS = {
    PetState.IDLE: 80,
    PetState.SLEEP: 125,
    PetState.WORKING: 33,
    PetState.SAD: 40,
    PetState.SUCCESS: 16,
    PetState.DANCE: 16,
    PetState.COOL: 33,
    PetState.WALK_LEFT: 16,
    PetState.WALK_RIGHT: 16,
    PetState.DRAGGED: 16,
    PetState.FALLING: 16,
    PetState.PUSH: 16,
    PetState.FLY: 16,
}

THROW_MAX = 3200.0          # px/s, damit ein wilder Wurf nicht durch die Wand tunnelt
AIR_DRAG = 0.35             # Anteil Geschwindigkeit, der pro Sekunde in der Luft verloren geht
WALL_BOUNCE = 0.72
CEIL_BOUNCE = 0.6
FLOOR_BOUNCE = 0.38         # genau ein kleiner Hopser am Boden
FLOOR_FRICTION = 0.75


def throw_velocity(samples, release_t: float) -> tuple[float, float]:
    """Wurf-Geschwindigkeit aus den letzten ~100 ms Mausbewegung (px/s).
    Wer vor dem Loslassen kurz stillhaelt (> 150 ms), laesst die Figur nur fallen."""
    if len(samples) < 2 or release_t - samples[-1][0] > 0.15:
        return 0.0, 0.0
    t1, x1, y1 = samples[-1]
    recent = [s for s in samples if t1 - s[0] <= 0.1]
    t0, x0, y0 = recent[0] if len(recent) >= 2 else samples[-2]
    if t1 - t0 < 0.005:
        return 0.0, 0.0
    clamp = lambda v: max(-THROW_MAX, min(THROW_MAX, v))
    return clamp((x1 - x0) / (t1 - t0)), clamp((y1 - y0) / (t1 - t0))


def throw_step(px, py, vx, vy, dt, lo, hi, top, ground, bounced, gravity):
    """Ein Physik-Schritt fuer die geworfene Figur.
    Rueckgabe: (px, py, vx, vy, bounced, event) mit event in None | 'wall' | 'floor_bounce' | 'landed'."""
    event = None
    vy += gravity * dt
    vx *= max(0.0, 1.0 - AIR_DRAG * dt)
    px += vx * dt
    py += vy * dt
    if px < lo or px > hi:
        px = max(lo, min(hi, px))
        vx = -vx * WALL_BOUNCE
        event = "wall"
    if py < top and vy < 0:
        py = top
        vy = -vy * CEIL_BOUNCE
        event = "wall"
    if py >= ground and vy >= 0:
        py = ground
        if not bounced and vy > 260:
            vy = -vy * FLOOR_BOUNCE
            vx *= FLOOR_FRICTION
            return px, py, vx, vy, True, "floor_bounce"
        return px, py, 0.0, 0.0, False, "landed"
    return px, py, vx, vy, bounced, event


MENU_STYLE = """
QMenu { background: #2B2D31; color: #F2F3F5; border: 1px solid #44464D; border-radius: 12px;
        padding: 6px; font: 10pt "Segoe UI"; }
QMenu::item { padding: 8px 24px 8px 14px; border-radius: 8px; }
QMenu::item:selected { background: #FF8FB1; color: #26282C; }
QMenu::separator { height: 1px; background: #44464D; margin: 5px 8px; }
"""


def style_menu(menu: QMenu) -> QMenu:
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    menu.setStyleSheet(MENU_STYLE)
    return menu


class PetWindow(QWidget):
    input_requested = pyqtSignal()
    chats_requested = pyqtSignal()
    data_requested = pyqtSignal()
    command_requested = pyqtSignal(str)
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    petted = pyqtSignal()        # einfacher Klick
    moved = pyqtSignal()         # Position hat sich geaendert (Sprechblase folgt)
    character_changed = pyqtSignal(str)
    treat_given = pyqtSignal()
    arrived = pyqtSignal()
    error_doctor_requested = pyqtSignal()
    friendship_requested = pyqtSignal()
    focus_stats_requested = pyqtSignal()
    flashcards_requested = pyqtSignal()
    photobox_requested = pyqtSignal()
    new_note_requested = pyqtSignal()
    onboarding_requested = pyqtSignal()
    hide_requested = pyqtSignal()
    focus_mode_requested = pyqtSignal()
    wash_requested = pyqtSignal()
    character_tree_requested = pyqtSignal()
    bubble_game_requested = pyqtSignal()
    yarn_game_requested = pyqtSignal()
    wallpaper_requested = pyqtSignal()
    pet_bed_requested = pyqtSignal()
    scripts_requested = pyqtSignal()
    home_mode_toggled = pyqtSignal(bool)
    restore_wallpaper_requested = pyqtSignal()


    GRAVITY = 2300.0

    def __init__(self, cfg, base_dir: Path):
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool                         # kein Eintrag in Taskleiste / Alt-Tab
        )
        if bool(cfg.get("pet.always_on_top", True)):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWindowTitle("Desktop Cat")
        self.setWindowOpacity(max(0.3, min(1.0, float(cfg.get("pet.opacity", 1.0)))))

        self.cfg = cfg
        self.character = str(cfg.get("pet.character", "cat_mochi"))
        self._chase_until = 0.0
        self.sprites = SpriteLibrary(base_dir, cfg.get("animations", {}) or {})

        self.state = PetState.IDLE
        self._state_since = time.monotonic()
        self._state_until: Optional[float] = None
        self._t0 = time.monotonic()
        self._last = self._t0
        self.facing = 1                      # 1 = rechts, -1 = links
        self.frozen = False                  # z. B. waehrend die Eingabeleiste offen ist
        self._px = 0.0
        self._py = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._walk_target = 0.0
        self._look = (0.0, 0.0)
        self._land_squash = 0.0
        self._hop_t: Optional[float] = None
        self._hearts_t: Optional[float] = None
        self._confetti_t: Optional[float] = None
        self._confetti_until = 0.0
        self._yawn_until = 0.0
        self._happy_until = 0.0
        self._water_until = 0.0
        self._water_t: Optional[float] = None
        self._crumbs_until = 0.0
        self._crumbs_t: Optional[float] = None
        self._bubbles_until = 0.0
        self._bubbles_t: Optional[float] = None
        self._bounced = False
        self._pose = None
        self._last_sig = None
        self.pet_bed = None
        self._going_to_bed = False
        self.room_mode = bool(cfg.get("pet.room_mode", False))
        self._is_speaking = False
        self._is_listening = False

        # Zubehoer & Fliegen (Phase 4)
        self._accessories: set[str] = set()
        self._accessory_until: dict[str, float] = {}
        self._fly_target: Optional[QPointF] = None
        self._arrived_emitted: bool = False

        self._pressed = False
        self._dragging = False
        self._suppress_click = False
        self._press_global = QPoint()
        self._grab_off = QPoint()
        self._samples: deque = deque(maxlen=30)     # (t, x, y) der letzten Mausbewegungen

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_single_click)

        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.timeout.connect(self._tick)

        self._wander_timer = QTimer(self)
        self._wander_timer.setSingleShot(True)
        self._wander_timer.timeout.connect(self._on_wander)

        self.apply_config()

    # ==================================================================================
    #  Konfiguration / Geometrie
    # ==================================================================================
    def apply_config(self) -> None:
        self.speed = float(self.cfg.get("pet.speed", 90))
        scale = max(0.5, min(2.5, float(self.cfg.get("pet.scale", 1.0))))
        if not hasattr(self, "scale") or abs(scale - self.scale) > 1e-6:
            old_bottom = self._py + self.height()
            self.scale = scale
            self.setFixedSize(int(BASE * scale), int(BASE * scale))
            if hasattr(self, "_placed"):
                self._py = old_bottom - self.height()
                self._apply_pos()
        char = str(self.cfg.get("pet.character", "cat_mochi"))
        if char != self.character and char in CHARACTERS:
            self.character = char
            self.character_changed.emit(char)
            self.update()
        self.wander_enabled = bool(self.cfg.get("pet.wander", True))
        opacity = max(0.3, min(1.0, float(self.cfg.get("pet.opacity", 1.0))))
        self.setWindowOpacity(opacity)
        always_on_top = bool(self.cfg.get("pet.always_on_top", True))
        current_flags = self.windowFlags()
        is_on_top = bool(current_flags & Qt.WindowType.WindowStaysOnTopHint)
        if always_on_top != is_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, always_on_top)
            if self.isVisible():
                self.show()
        if getattr(self, "pet_bed", None) and hasattr(self.pet_bed, "set_always_on_top"):
            self.pet_bed.set_always_on_top(always_on_top)
        if self.isVisible():
            self._schedule_wander()

    def set_character(self, char_id: str) -> None:
        if char_id in CHARACTERS and char_id != self.character:
            from memory_store import get_memory_store
            import pet_care
            try:
                store = get_memory_store()
            except Exception:
                store = None
            unlocked, _, _ = pet_care.is_character_unlocked(char_id, store)
            if not unlocked:
                self.character_tree_requested.emit()
                return

            self.character = char_id
            self.cfg.set("pet.character", char_id)
            self.cfg.save()
            self.character_changed.emit(char_id)
            self.react_happy()
            self.update()

    def char_info(self) -> dict:
        return CHARACTERS.get(self.character) or {}

    def push_animation(self, seconds: float = 1.5) -> None:
        self.wake()
        self.facing = 1
        self.set_state(PetState.PUSH, seconds)

    def chase_mouse(self, seconds: float = 15.0) -> None:
        """Spielmodus: folgt dem Mauszeiger (x) mit der normalen Lauflogik."""
        self.wake()
        self._chase_until = time.monotonic() + seconds

    def give_treat(self) -> None:
        self.cfg.set("treats", int(self.cfg.get("treats", 0)) + 1)
        self.cfg.save()
        self.eat_treat(3.5)
        self.treat_given.emit()

    def drink_water(self, seconds: float = 5.0) -> None:
        """Laesst die Katze sichtbar Wasser aus ihrem Wassernaepfchen trinken."""
        self.wake()
        sound_effects.play_sound("water", self.cfg)
        now = time.monotonic()
        self._water_t = now
        self._water_until = now + seconds
        self._restart_timer()
        self._anim_timer.start(16)
        self.update()

    def eat_treat(self, seconds: float = 3.5) -> None:
        """Knabber- und Mampf-Animation beim Fuettern."""
        self.wake()
        sound_effects.play_sound("chomp", self.cfg)
        now = time.monotonic()
        self._crumbs_t = now
        self._crumbs_until = now + seconds
        self._hearts_t = now
        self._happy_until = now + seconds
        self._restart_timer()
        self._anim_timer.start(16)
        self.update()

    def wash_pet(self, seconds: float = 4.5) -> None:
        """Laesst die Katze genussvoll ein Schaumbad nehmen mit schwebenden Seifenblasen."""
        self.wake()
        sound_effects.play_sound("pop", self.cfg)
        now = time.monotonic()
        self._bubbles_t = now
        self._bubbles_until = now + seconds
        self._hearts_t = now
        self._happy_until = now + seconds
        self._restart_timer()
        self._anim_timer.start(16)
        self.update()

    # -- Zubehoer & Fliegen (Phase 4) --------------------------------------------------
    def set_accessory(self, name: str, on: bool, until: Optional[float] = None) -> None:
        """Aktiviert oder deaktiviert ein Accessoire (optional mit Ablaufzeit)."""
        if on:
            self._accessories.add(name)
            if until is not None:
                self._accessory_until[name] = until
            else:
                self._accessory_until.pop(name, None)
        else:
            self._accessories.discard(name)
            self._accessory_until.pop(name, None)
        self.update()

    def fly_to(self, x: float, y: float) -> None:
        """Fliegt auf der Wolke sanft zu den Desktop-Koordinaten (x, y) und stoppt daneben."""
        self.wake()
        screen_rect = self._avail()
        fx, fy = fly_position((x, y), (self.width(), self.height()), screen_rect)
        self._fly_target = QPointF(fx, fy)
        self._arrived_emitted = False
        self.set_accessory("cloud", True)
        if fx > self._px + 10:
            self.facing = 1
        elif fx < self._px - 10:
            self.facing = -1
        self.set_state(PetState.FLY)

    def land(self) -> None:
        """Kehrt auf den Boden zurueck; die Wolke loest sich auf."""
        self.set_accessory("cloud", False)
        self._fly_target = None
        self._arrived_emitted = False
        self._vx = 0.0
        self._vy = 0.0
        if self._py < self._ground_y() - 2.0:
            self.set_state(PetState.FALLING)
        else:
            self.set_state(PetState.IDLE)

    def _fly(self, dt: float) -> None:
        if self._fly_target is None:
            return
        tx, ty = self._fly_target.x(), self._fly_target.y()
        dx = tx - self._px
        dy = ty - self._py
        dist = math.hypot(dx, dy)

        if dist < 4.0:
            self._px = tx
            self._py = ty
            self._apply_pos()
            if not self._arrived_emitted:
                self._arrived_emitted = True
                self.arrived.emit()
            return

        speed = max(100.0, min(600.0, dist * 3.6))
        step = speed * dt
        if step >= dist:
            self._px = tx
            self._py = ty
            self._apply_pos()
            if not self._arrived_emitted:
                self._arrived_emitted = True
                self.arrived.emit()
        else:
            self._px += (dx / dist) * step
            self._py += (dy / dist) * step
            self._apply_pos()
            if dx > 10:
                self.facing = 1
            elif dx < -10:
                self.facing = -1

    def _screen_for_x(self, cx: float):
        screens = QGuiApplication.screens()
        for s in screens:
            g = s.geometry()
            if g.left() <= cx <= g.right():
                return s
        return QGuiApplication.primaryScreen()

    def _avail(self) -> "QRect":
        return self._screen_for_x(self._px + self.width() / 2).availableGeometry()

    def _ground_y(self) -> float:
        """y des Fensters, wenn das Pet direkt auf der Oberkante der Taskleiste steht."""
        return self._avail().bottom() + 1 - FLOOR * self.scale

    def _perch_levels(self, x: Optional[float] = None) -> list[float]:
        """Gibt die verfuegbaren Hoehenebenen zurueck (Boden, Bett, und im Raum-Modus Wandregal / Fensterbrett)."""
        avail = self._avail()
        ground = self._ground_y()
        levels = [ground]
        if getattr(self, "pet_bed", None) and self.pet_bed.isVisible():
            bed_x, bed_y = self.pet_bed.get_dock_position()
            # Bettchen ist nur eine gueltige Ebene, wenn sich die Katze horizontal darauf befindet
            if x is None or abs(x - bed_x) < 70.0:
                levels.append(bed_y)
        if bool(self.cfg.get("pet.room_mode", False)):
            h = float(avail.height())
            shelf = float(avail.top() + h * 0.22)
            window_sill = float(avail.top() + h * 0.48)
            levels.extend([window_sill, shelf])
        return sorted(set(levels))

    def _closest_perch_y(self, y: float, x: Optional[float] = None) -> float:
        """Findet die naechstgelegene Hoehenebene unterhalb oder nahe von y."""
        check_x = self._px if x is None else x
        levels = self._perch_levels(check_x)
        ground = self._ground_y()
        candidates = [lvl for lvl in levels if lvl >= y - 12]
        return min(candidates, key=lambda l: abs(l - y)) if candidates else ground

    def on_bed_moved(self, bx: int, by: int) -> None:
        """Wird aufgerufen, wenn das Katzenbettchen per Maus verschoben wird."""
        if getattr(self, "pet_bed", None) and self.pet_bed.isVisible():
            dock_x, dock_y = self.pet_bed.get_dock_position()
            if self.state == PetState.SLEEP:
                self._px = dock_x
                self._py = dock_y
                self._apply_pos()
            elif self._going_to_bed:
                self._walk_target = dock_x
                direction = 1 if dock_x > self._px else -1
                self.facing = direction
                self.set_state(PetState.WALK_RIGHT if direction > 0 else PetState.WALK_LEFT)

    def on_bed_hidden(self) -> None:
        """Wird aufgerufen, wenn das Katzenbettchen ausgeblendet wird."""
        ground = self._ground_y()
        if self.state == PetState.SLEEP:
            if self._py < ground - 15:
                self.wake()
                self._vy = 40.0
                self.set_state(PetState.FALLING)
        elif self._going_to_bed:
            self.wake()
            self.set_state(PetState.IDLE)

    def _leap_to_perch(self, target_y: float) -> None:
        """Laesst die Katze mit einem agilen Katzensprung auf eine hoehere oder tiefere Ebene springen."""
        self.wake()
        dx = random.choice([-140.0, 140.0])
        lo, hi = self._x_bounds()
        target_x = max(lo + 60, min(hi - 60, self._px + dx))
        self.facing = 1 if target_x > self._px else -1
        self._vx = (target_x - self._px) * 1.5
        dy = target_y - self._py
        self._vy = min(-500.0, dy * 2.2 - 250.0) if dy < 0 else -180.0
        self.set_state(PetState.FALLING)

    def _x_bounds(self) -> tuple[float, float]:
        g = self._avail()
        return float(g.left()), float(g.right() + 1 - self.width())

    def _virtual_rect(self):
        return QGuiApplication.primaryScreen().virtualGeometry()

    def _apply_pos(self) -> None:
        self.move(round(self._px), round(self._py))

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.moved.emit()

    def head_anchor(self) -> QPoint:
        """Punkt knapp ueber dem Kopf (globale Koordinaten) - dorthin zeigt der Pfeil der Sprechblase."""
        return QPoint(int(self.x() + self.width() / 2), int(self.y() + 24 * self.scale))

    # ==================================================================================
    #  Lebenszyklus
    # ==================================================================================
    def drop_in(self) -> None:
        """Setzt das Pet sichtbar direkt auf die Taskleiste."""
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self._px = float(geo.right() - self.width() * 2.2 - 60)
        self._py = float(self._ground_y())
        self._vx = self._vy = 0.0
        self._placed = True
        self._apply_pos()
        self.set_state(PetState.IDLE)
        self.show()
        self.raise_()
        self.react_happy()

    def reset_to_taskbar(self) -> None:
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self._px = float(geo.center().x() - self.width() / 2)
        self._py = float(self._ground_y())
        self._vx = self._vy = 0.0
        self._dragging = False
        self.frozen = False
        self._apply_pos()
        self.set_state(PetState.IDLE)
        self.show()
        self.raise_()
        self.react_happy()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._last = time.monotonic()
        self._restart_timer()
        self._schedule_wander()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._anim_timer.stop()
        self._wander_timer.stop()

    # ==================================================================================
    #  Zustandsmaschine
    # ==================================================================================
    def set_state(self, state: PetState, duration: Optional[float] = None) -> None:
        if state != self.state:
            self.state = state
            self._state_since = time.monotonic()
        self._state_until = (time.monotonic() + duration) if duration else None
        if state in (PetState.WALK_LEFT, PetState.WALK_RIGHT):
            self.facing = -1 if state == PetState.WALK_LEFT else 1
        self.setCursor(Qt.CursorShape.ClosedHandCursor if state == PetState.DRAGGED else Qt.CursorShape.PointingHandCursor)
        self._restart_timer()
        self.update()

    def _restart_timer(self) -> None:
        if self.isVisible():
            self._anim_timer.start(INTERVALS.get(self.state, 33))

    def wake(self) -> None:
        self._going_to_bed = False
        if self.state == PetState.SLEEP:
            self.set_state(PetState.IDLE)

    def go_to_sleep(self) -> None:
        """Laesst die Katze zum Katzenbettchen spazieren und sich dort schlafen legen (ohne Teleport!)."""
        if self.state == PetState.SLEEP:
            return
        if self.state == PetState.DRAGGED or self._dragging or self.frozen:
            return

        if getattr(self, "pet_bed", None) and self.pet_bed.isVisible():
            bed_x, bed_y = self.pet_bed.get_dock_position()
            dist_x = abs(self._px - bed_x)
            dist_y = abs(self._py - bed_y)
            # Falls die Katze noch nicht im Bettchen ist: gemuetlich hinlaufen!
            if dist_x > 18 or dist_y > 18:
                self.wake()
                self._going_to_bed = True
                self._walk_target = bed_x
                direction = 1 if bed_x > self._px else -1
                self.facing = direction
                self.set_state(PetState.WALK_RIGHT if direction > 0 else PetState.WALK_LEFT)
                return
            else:
                self._px = bed_x
                self._py = bed_y
                self._apply_pos()

        # Falls kein Bett da ist oder sie schon dort steht: direkt schlafen
        self._going_to_bed = False
        self.set_state(PetState.SLEEP)
        self._schedule_wander(random.uniform(14, 28))

    # -- oeffentliche API fuer den Controller ---------------------------------------------
    def set_working(self) -> None:
        self._click_timer.stop()
        self.set_state(PetState.WORKING)

    def celebrate(self, seconds: float = 2.6) -> None:
        self.set_state(PetState.SUCCESS, seconds)

    def celebrate_confetti(self, seconds: float = 4.0) -> None:
        self.wake()
        now = time.monotonic()
        self._confetti_t = now
        self._confetti_until = now + seconds
        self._hop_t = now
        self._anim_timer.start(16)
        self.set_state(PetState.SUCCESS, seconds)

    def wake_with_stretch(self, seconds: float = 2.0) -> None:
        self.wake()
        now = time.monotonic()
        self._yawn_until = now + seconds
        self._hop_t = now
        self._happy_until = now + seconds
        self._anim_timer.start(16)
        self.set_state(PetState.IDLE)

    def dance(self, seconds: float = 6.0) -> None:
        self.wake()
        self.set_state(PetState.DANCE, seconds)

    def be_cool(self, seconds: float = 6.0) -> None:
        self.wake()
        self.set_state(PetState.COOL, seconds)

    def sad(self, seconds: float = 3.0) -> None:
        self.set_state(PetState.SAD, seconds)


    def calm(self) -> None:
        self.set_state(PetState.IDLE)

    def freeze(self, on: bool) -> None:
        self.frozen = on
        if on:
            if self.state in WALKING or self.state == PetState.SLEEP:
                self.set_state(PetState.IDLE)
        else:
            self._schedule_wander()

    def react_happy(self) -> None:
        """Klick-Reaktion: Huepfer + Herzchen."""
        self.wake()
        sound_effects.play_sound("purr", self.cfg)
        now = time.monotonic()
        self._hop_t = now
        self._hearts_t = now
        self._happy_until = now + 1.5
        self._restart_timer()
        if self.state == PetState.IDLE:
            self._anim_timer.start(16)      # fuer den Huepfer kurz mit voller Frame-Rate

    # ==================================================================================
    #  Autonomes Wandern
    # ==================================================================================
    def _schedule_wander(self, delay_s: Optional[float] = None) -> None:
        if not self.isVisible():
            return
        lo = float(self.cfg.get("pet.wander_min_s", 5))
        hi = max(lo, float(self.cfg.get("pet.wander_max_s", 10)))
        self._wander_timer.start(int((delay_s if delay_s is not None else random.uniform(lo, hi)) * 1000))

    def _on_wander(self) -> None:
        busy = self.state not in (PetState.IDLE, PetState.SLEEP) or self.frozen or self._dragging
        if busy or not self.wander_enabled or time.monotonic() < self._chase_until:
            self._schedule_wander()
            return
        r = random.random()

        # 1. Schlafen: Bevorzugt im Katzenbett (zu Fuss hingehen statt Teleport)
        if (is_night(self.cfg) and r < 0.6) or (r < 0.28):
            self.go_to_sleep()
            return

        # 2. Raum-Modus: 2D-Klettern & Springen auf andere Ebenen (ohne Wolke)
        if bool(self.cfg.get("pet.room_mode", False)) and r < 0.48:
            levels = self._perch_levels()
            other_levels = [lvl for lvl in levels if abs(lvl - self._py) > 40]
            if other_levels:
                chosen_y = random.choice(other_levels)
                self._leap_to_perch(chosen_y)
                self._schedule_wander(random.uniform(6, 12))
                return

        # 3. Stehen bleiben oder horizontal laufen
        if r < 0.70:
            self.wake()
            self._schedule_wander()
        else:
            self._start_walk()
            self._schedule_wander()

    def _start_walk(self) -> None:
        lo, hi = self._x_bounds()
        direction = random.choice((-1, 1))
        if self._px - lo < 80:
            direction = 1
        elif hi - self._px < 80:
            direction = -1
        target = self._px + direction * random.uniform(70, 280)
        self._walk_target = max(lo, min(hi, target))
        if abs(self._walk_target - self._px) < 20:
            self.set_state(PetState.IDLE)
            return
        self.set_state(PetState.WALK_RIGHT if self._walk_target > self._px else PetState.WALK_LEFT)

    # ==================================================================================
    #  Tick: Physik + Animation
    # ==================================================================================
    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(now - self._last, 0.08)
        self._last = now

        if self._state_until is not None and now >= self._state_until:
            self._state_until = None
            if self.state in (PetState.SUCCESS, PetState.SAD, PetState.PUSH):
                self.set_state(PetState.IDLE)

        if now < self._chase_until and not self.frozen and not self._dragging                 and self.state in (PetState.IDLE, PetState.WALK_LEFT, PetState.WALK_RIGHT):
            lo, hi = self._x_bounds()
            self._walk_target = max(lo, min(hi, QCursor.pos().x() - self.width() / 2))
            if abs(self._walk_target - self._px) > 12:
                self.set_state(PetState.WALK_RIGHT if self._walk_target > self._px else PetState.WALK_LEFT)

        s = self.state
        if s in WALKING:
            self._walk(dt)
        elif s == PetState.FALLING:
            self._fall(dt)
        elif s == PetState.FLY:                 # IT-Guide, Fehler-Doktor, Haftnotiz: Flug auf der Wolke
            self._fly(dt)
        elif s != PetState.DRAGGED and not self._dragging:
            closest = self._closest_perch_y(self._py, self._px)
            if self._py < closest - 15:
                self._vx = self._vy = 0.0       # z. B. Ebene hat sich bewegt -> nachfallen
                self.set_state(PetState.FALLING)

        # Effekt-Timer abklingen lassen
        if self._land_squash > 0:
            self._land_squash = max(0.0, self._land_squash - dt * 5.5)
        if self._hop_t is not None and now - self._hop_t > 0.5:
            self._hop_t = None
        if self._hearts_t is not None and now - self._hearts_t > 1.5:
            self._hearts_t = None

        # Blickrichtung zur Maus oder Ziel
        if s == PetState.FLY and self._fly_target is not None:
            dx = self._fly_target.x() - self._px
            dy = self._fly_target.y() - self._py
            self._look = (max(-1.0, min(1.0, dx / 200.0)), max(-1.0, min(1.0, dy / 200.0)))
        elif s in (PetState.IDLE, PetState.WALK_LEFT, PetState.WALK_RIGHT):
            c = QCursor.pos()
            hx = self._px + self.width() / 2
            hy = self._py + 76 * self.scale
            self._look = (max(-1.0, min(1.0, (c.x() - hx) / 260.0)), max(-1.0, min(1.0, (c.y() - hy) / 260.0)))
        else:
            self._look = (0.0, 0.0)

        # Ruhige Zustaende: nach dem Huepfer wieder auf niedrige FPS zurueck
        if s == PetState.IDLE and self._hop_t is None and self._hearts_t is None and self._land_squash == 0:
            if self._anim_timer.interval() != INTERVALS[PetState.IDLE]:
                self._anim_timer.setInterval(INTERVALS[PetState.IDLE])
                self._anim_timer.setTimerType(Qt.TimerType.CoarseTimer)

        if self.sprites.usable:
            self.update()
            return
        pose = self._build_pose(now)
        sig = self._signature(pose)
        self._pose = pose
        if sig != self._last_sig:             # nur neu zeichnen, wenn man wirklich etwas sieht
            self._last_sig = sig
            self.update()

    @staticmethod
    def _signature(p) -> tuple:
        """Grob quantisierte Pose: gleiche Signatur = fuers Auge identisches Bild."""
        def q(v, step):
            return round(v / step)
        if p.zzz is not None or p.dots is not None or p.sparkles is not None or p.hearts is not None \
                or p.tear is not None:
            return (object(),)               # laufende Effekte -> immer zeichnen
        return (
            q(p.dx, .35), q(p.dy, .35), q(p.rot, .4), q(p.sx, .006), q(p.sy, .006), q(p.head_dx, .35),
            q(p.head_dy, .35), q(p.head_rot, .4), p.eyes, p.mouth, q(p.look[0], .2), q(p.look[1], .2),
            q(p.tail, .1), q(p.paw_l, .4), q(p.paw_r, .4), q(p.ear_l, 1.0), q(p.ear_r, 1.0), q(p.bell, .4),
            q(p.typing, .3), q(p.blush, .05), q(p.shadow, .05), p.laptop, p.tail_curl,
        )

    def _walk(self, dt: float) -> None:
        if self._going_to_bed:
            vrect = self._virtual_rect()
            lo, hi = float(vrect.left()), float(vrect.right() + 1 - self.width())
        else:
            lo, hi = self._x_bounds()

        step = self.speed * dt
        diff = self._walk_target - self._px

        # Falls die Katze zum Bettchen läuft: stufenloser 2D-Flug/Schritt direkt ins Bettchen
        if self._going_to_bed and getattr(self, "pet_bed", None) and self.pet_bed.isVisible():
            bed_x, bed_y = self.pet_bed.get_dock_position()
            dist_x = abs(self._walk_target - self._px)
            dy = bed_y - self._py

            # Horizontaler Schritt
            if dist_x <= step:
                self._px = self._walk_target
            else:
                self._px += math.copysign(step, diff)
                self._px = max(lo, min(hi, self._px))

            # Vertikaler sanfter Schritt (stufenlos angepasst an die Restdistanz)
            dist_to_bed = abs(self._px - self._walk_target)
            if abs(dy) > 1.0:
                time_rem = max(0.05, dist_to_bed / max(10.0, self.speed))
                speed_y = max(60.0, abs(dy) / time_rem)
                step_y = speed_y * dt
                self._py += math.copysign(min(abs(dy), step_y), dy)
            else:
                self._py = bed_y

            # Erst wenn X UND Y gleichzeitig und stufenlos angekommen sind: Einschlafen!
            if abs(self._px - self._walk_target) <= 1.0 and abs(self._py - bed_y) <= 3.0:
                self._px = self._walk_target
                self._py = bed_y
                self._going_to_bed = False
                self._apply_pos()
                self.set_state(PetState.SLEEP)
                self._schedule_wander(random.uniform(14, 28))
                return

            self._apply_pos()
            return

        # Normales Wandern
        if abs(diff) <= step:
            self._px = self._walk_target
            self._apply_pos()
            self.set_state(PetState.IDLE)
            return

        self._px += math.copysign(step, diff)
        self._px = max(lo, min(hi, self._px))

        closest = self._closest_perch_y(self._py, self._px)
        if closest > self._py + 15:
            # Über den Rand des Betts / Regals gelaufen -> fällt natürlich nach unten
            self._vy = 40.0
            self.set_state(PetState.FALLING)
            return
        else:
            self._py = closest

        self._apply_pos()

    def _fall(self, dt: float) -> None:
        lo, hi = self._x_bounds()
        land_vx = self._vx
        target_ground = self._closest_perch_y(self._py, self._px)
        self._px, self._py, self._vx, self._vy, self._bounced, event = throw_step(
            self._px, self._py, self._vx, self._vy, dt, lo, hi, float(self._avail().top()), target_ground,
            self._bounced, self.GRAVITY)
        if event in ("wall", "floor_bounce"):
            self._land_squash = 1.0 if event == "floor_bounce" else 0.6
        elif event == "landed":
            self._land_squash = 1.0
            self.set_state(PetState.IDLE)
            if self.wander_enabled and abs(land_vx) > 80:   # Schwung mitnehmen und weiterspazieren
                direction = 1 if land_vx > 0 else -1
                QTimer.singleShot(450, lambda: self._walk_after_landing(direction))
        self._apply_pos()

    def _walk_after_landing(self, direction: int) -> None:
        if self.state != PetState.IDLE or self._dragging or self.frozen:
            return
        lo, hi = self._x_bounds()
        if (direction > 0 and hi - self._px < 80) or (direction < 0 and self._px - lo < 80):
            direction = -direction
        self._walk_target = max(lo, min(hi, self._px + direction * random.uniform(160, 360)))
        if abs(self._walk_target - self._px) >= 20:
            self.set_state(PetState.WALK_RIGHT if direction > 0 else PetState.WALK_LEFT)

    # ==================================================================================
    #  Zeichnen & Voice / Lip-Sync
    # ==================================================================================
    def set_speaking(self, speaking: bool) -> None:
        """Aktiviert oder deaktiviert die Mundbewegung (Lip-Sync) während Sprachausgabe."""
        if self._is_speaking != bool(speaking):
            self._is_speaking = bool(speaking)
            self.update()

    def is_speaking(self) -> bool:
        return self._is_speaking

    def set_listening(self, listening: bool) -> None:
        """Zeigt ein Mikrofon-Badge an, während der Nutzer per Push-to-Talk spricht."""
        if self._is_listening != bool(listening):
            self._is_listening = bool(listening)
            self.update()

    def is_listening(self) -> bool:
        return self._is_listening

    def _build_pose(self, now: float):
        # Abgelaufene temporaere Accessoires aufraeumen
        expired = [name for name, u in self._accessory_until.items() if now >= u]
        for name in expired:
            self._accessories.discard(name)
            self._accessory_until.pop(name, None)

        hop = 0.0
        if self._hop_t is not None:
            u = (now - self._hop_t) / 0.5
            hop = 4 * u * (1 - u) * 22 if 0 <= u <= 1 else 0.0
        hearts_age = None
        if self._hearts_t is not None:
            hearts_age = (now - self._hearts_t) / 1.5
        look = self._look
        if self.facing < 0:
            look = (-look[0], look[1])
        ctx = PoseContext(key=self.state.value, t=now - self._t0, age=now - self._state_since, look=look, hop=hop,
                          squash=self._land_squash, hearts_age=hearts_age, happy=now < self._happy_until,
                          speaking=self._is_speaking)
        pose = compute_pose(ctx)
        if self.state == PetState.FALLING:          # im Flug in Wurfrichtung kippen
            pose.rot += max(-25.0, min(25.0, self._vx / 60.0)) * self.facing
        active_accs = set(self._accessories)
        worn = str(self.cfg.get("fun.worn", "")).strip()
        if worn:
            if worn == "gold_sparkle":
                pose.sparkles = now - self._t0
            else:
                active_accs.add(worn)
        pose.accessories = tuple(sorted(active_accs))
        if "fan" in active_accs:
            pose.sweat = True
        if self.state == PetState.FLY:
            pose.dy += math.sin((now - self._state_since) * 3.5) * 4.0
        if now < self._confetti_until and self._confetti_t is not None:
            pose.confetti = now - self._confetti_t
            pose.sparkles = now - self._confetti_t
        if now < self._yawn_until:
            pose.mouth = "o"
            pose.eyes = "happy"
        if now < self._water_until and self._water_t is not None:
            pose.water = now - self._water_t
            pose.mouth = "smile"
            pose.eyes = "happy"
            pose.head_dy += 2.5
        if now < self._crumbs_until and self._crumbs_t is not None:
            pose.crumbs = now - self._crumbs_t
            pose.mouth = "smile"
            pose.eyes = "happy"
        if now < self._bubbles_until and self._bubbles_t is not None:
            pose.bubbles = now - self._bubbles_t
            pose.mouth = "smile"
            pose.eyes = "happy"
        return pose

    def paintEvent(self, _event) -> None:
        now = time.monotonic()
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
                         | QPainter.RenderHint.TextAntialiasing)
        p.scale(self.scale, self.scale)
        flip = self.facing < 0

        if self.sprites.usable:
            hop = 0.0
            if self._hop_t is not None:
                u = (now - self._hop_t) / 0.5
                hop = 4 * u * (1 - u) * 22 if 0 <= u <= 1 else 0.0
            self._paint_sprite(p, self.state.value, now - self._t0, now - self._state_since, hop, flip)
        else:
            pose = replace(self._pose) if self._pose is not None else self._build_pose(now)
            p.save()
            if flip:
                p.translate(BASE, 0)
                p.scale(-1, 1)
            # Effekte (Text, Herzen ...) duerfen nicht gespiegelt werden -> separat zeichnen
            effects = (pose.zzz, pose.dots, pose.sparkles, pose.hearts, getattr(pose, "confetti", None))
            if flip:
                pose.zzz = pose.dots = pose.sparkles = pose.hearts = None
                pose.confetti = None
            draw_character(p, pose, self.character)
            p.restore()
            if flip:
                pose.zzz, pose.dots, pose.sparkles, pose.hearts, pose.confetti = effects
                _draw_effects(p, pose)

        # v3.0.0 Visueller Mikrofon-Indikator beim Push-to-Talk Zuhören
        if self._is_listening:
            p.save()
            pulse = (math.sin((now - self._t0) * 8.0) + 1.0) * 0.5
            p.setPen(Qt.PenStyle.NoPen)
            # Pulsierender pink-roter Kreis
            p.setBrush(QColor(255, 60, 110, int(180 + 75 * pulse)))
            p.drawEllipse(QPointF(80, 24), 13 + 2.5 * pulse, 13 + 2.5 * pulse)
            # Weißes Mikrofon-Emoji
            f = QFont("Segoe UI Emoji")
            f.setPixelSize(13)
            p.setFont(f)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(68, 12, 24, 24), Qt.AlignmentFlag.AlignCenter, "🎙️")
            p.restore()

        p.end()

    def _paint_sprite(self, p: QPainter, key: str, t: float, age: float, hop: float, flip: bool) -> None:
        anim, mirrored, exact = self.sprites.get(key)
        if anim is None:
            return
        pix = anim.frame_at(((time.monotonic() - self._t0) * 1000))
        dx = dy = rot = 0.0
        sy = 1.0
        if not exact:      # kein eigenes Sprite fuer diesen Zustand -> Idle-Bild mit Bewegung aufpeppen
            if key in ("walk_left", "walk_right"):
                dy = -abs(math.sin(t * 8)) * 4
                rot = math.sin(t * 8) * 3
            elif key in ("dragged", "falling"):
                rot = math.sin(t * 13) * 9
            elif key == "success":
                u = (age % 0.62) / 0.62
                dy = -4 * u * (1 - u) * 28
            elif key == "working":
                sy = 1 + 0.02 * math.sin(t * 9)
            elif key == "sad":
                dy = 3
            elif key == "sleep":
                sy = 0.94
        dy -= hop
        sy *= 1 - 0.14 * self._land_squash
        # Zielrechteck: einpassen, unten buendig am Boden
        avail_w, avail_h = BASE - 16, FLOOR - 4
        sc = min(avail_w / pix.width(), avail_h / pix.height())
        w, h = pix.width() * sc, pix.height() * sc
        mirror = flip != mirrored
        p.save()
        p.translate(BASE / 2 + dx, FLOOR + dy)
        p.rotate(rot)
        p.scale(-1 if mirror else 1, sy)
        p.drawPixmap(QRectF(-w / 2, -h, w, h), pix, QRectF(pix.rect()))
        p.restore()

    # ==================================================================================
    #  Maus: Klick, Doppelklick, Drag & Drop, Kontextmenue
    # ==================================================================================
    def mousePressEvent(self, e) -> None:
        self._going_to_bed = False
        if e.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._dragging = False
            self._press_global = e.globalPosition().toPoint()
            self._grab_off = self._press_global - self.pos()
            self._samples.clear()
            e.accept()

    def mouseMoveEvent(self, e) -> None:
        if not self._pressed:
            return
        gp = e.globalPosition().toPoint()
        if not self._dragging:
            if (gp - self._press_global).manhattanLength() < 6:
                return
            self._dragging = True
            self._click_timer.stop()
            self.wake()
            self._vx = self._vy = 0.0
            if self.state == PetState.FLY:
                self.set_accessory("cloud", False)
                self._fly_target = None
            self.set_state(PetState.DRAGGED)
        target = gp - self._grab_off
        vr = self._virtual_rect()
        self._px = float(max(vr.left(), min(target.x(), vr.right() + 1 - self.width())))
        self._py = float(max(vr.top(), min(target.y(), vr.bottom() + 1 - self.height())))
        self._apply_pos()
        self._samples.append((time.monotonic(), gp.x(), gp.y()))

    def mouseReleaseEvent(self, e) -> None:
        if e.button() != Qt.MouseButton.LeftButton or not self._pressed:
            return
        self._pressed = False
        if self._dragging:
            self._dragging = False
            self._vx, self._vy = throw_velocity(self._samples, time.monotonic())
            if abs(self._vx) > 100:
                self.facing = 1 if self._vx > 0 else -1
            self._bounced = False
            self.set_state(PetState.FALLING)
            self._schedule_wander()
        elif self._suppress_click:
            self._suppress_click = False
        else:
            self._click_timer.start(QApplication.doubleClickInterval())

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self._suppress_click = True
            self._pressed = False
            self.wake()
            self.input_requested.emit()

    def _on_single_click(self) -> None:
        sound_effects.play_sound("meow", self.cfg)
        self.react_happy()
        self.petted.emit()

    def wheelEvent(self, e) -> None:
        # Ctrl + Mausrad oder Shift + Mausrad skaliert die Katze stufenlos
        mods = e.modifiers()
        if bool(mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
            delta = 0.05 if e.angleDelta().y() > 0 else -0.05
            new_scale = round(max(0.6, min(2.5, self.scale + delta)), 2)
            if abs(new_scale - self.scale) > 1e-4:
                self.set_scale(new_scale)
                self.cfg.set("pet.scale", new_scale)
                self.cfg.save()
            e.accept()
            return
        super().wheelEvent(e)

    def set_scale(self, new_scale: float) -> None:
        """Groesse aendern, Fuesse bleiben am selben Platz (auch fuer das Fotobox-Selfie)."""
        old_bottom = self._py + self.height()
        old_cx = self._px + self.width() / 2
        self.scale = new_scale
        self.setFixedSize(int(BASE * new_scale), int(BASE * new_scale))
        self._py = old_bottom - self.height()
        lo, hi = self._x_bounds()
        self._px = max(lo, min(hi, old_cx - self.width() / 2))
        self._apply_pos()
        self.moved.emit()
        self.update()

    def contextMenuEvent(self, e) -> None:
        self._click_timer.stop()
        menu = self.build_menu()
        menu.exec(e.globalPos())

    def build_menu(self) -> QMenu:
        menu = style_menu(QMenu(self))
        cmd = self.command_requested.emit
        cname = self.char_info().get("name", "Kylie")

        import gemini
        if not gemini.has_key():
            menu.addAction(tr("menu.enter_key")).triggered.connect(self.settings_requested.emit)
            menu.addSeparator()

        menu.addAction(tr("menu.input")).triggered.connect(self.input_requested.emit)
        menu.addAction(tr("menu.feed_pet", name=cname)).triggered.connect(self.give_treat)
        menu.addAction(tr("menu.wash_pet", name=cname)).triggered.connect(self.wash_requested.emit)
        menu.addAction(tr("menu.hide_pet", name=cname)).triggered.connect(self.hide_requested.emit)
        menu.addAction(tr("menu.focus_mode")).triggered.connect(self.focus_mode_requested.emit)
        menu.addSeparator()

        # Freundschaft & Lernen Untermenü
        learn_menu = menu.addMenu(tr("menu.sub_learn"))
        style_menu(learn_menu)
        learn_menu.addAction(tr("menu.character_tree")).triggered.connect(self.character_tree_requested.emit)
        learn_menu.addAction(tr("menu.friendship")).triggered.connect(self.friendship_requested.emit)
        learn_menu.addAction(tr("menu.focus_stats")).triggered.connect(self.focus_stats_requested.emit)
        learn_menu.addAction(tr("menu.flashcards")).triggered.connect(self.flashcards_requested.emit)
        learn_menu.addAction(tr("menu.photo", name=cname)).triggered.connect(self.photobox_requested.emit)

        # Notizen & Hilfe Untermenü
        tools_sub = menu.addMenu(tr("menu.sub_tools"))
        style_menu(tools_sub)
        tools_sub.addAction(tr("menu.new_note")).triggered.connect(self.new_note_requested.emit)
        tools_sub.addAction(tr("menu.error_doctor")).triggered.connect(self.error_doctor_requested.emit)
        tools_sub.addAction(tr("menu.chats")).triggered.connect(self.chats_requested.emit)
        tools_sub.addAction(tr("menu.data")).triggered.connect(self.data_requested.emit)
        tools_sub.addAction(tr("menu.scripts")).triggered.connect(self.scripts_requested.emit)
        tools_sub.addAction(tr("menu.onboarding")).triggered.connect(self.onboarding_requested.emit)
        menu.addSeparator()

        # Charakter-Auswahl (Live-Wechsel mit Freischalt-Prüfung)
        if CHARACTERS:
            char_menu = menu.addMenu(tr("menu.choose_char"))
            style_menu(char_menu)
            from memory_store import get_memory_store
            import pet_care
            try:
                store = get_memory_store()
            except Exception:
                store = None
            for cid in CHARACTERS:
                from pet_sprites import get_character_info
                ci = get_character_info(cid)
                unlocked, req_lvl, _ = pet_care.is_character_unlocked(cid, store)
                if unlocked:
                    check = "✔  " if cid == self.character else "    "
                    char_menu.addAction(f"{check}{ci['emoji']}  {ci['name']} ({ci['species']})").triggered.connect(
                        lambda _=False, c=cid: self.set_character(c))
                else:
                    char_menu.addAction(f"🔒  {ci['emoji']}  {ci['name']} (Lvl {req_lvl})").triggered.connect(
                        self.character_tree_requested.emit)
            menu.addSeparator()

        # Coole Tricks & Animationen
        tricks = menu.addMenu(tr("menu.tricks"))
        style_menu(tricks)
        name = self.char_info().get("name", "Buddy")
        tricks.addAction(tr("menu.dance", name=name)).triggered.connect(lambda: self.dance(6.0))
        tricks.addAction(tr("menu.cool")).triggered.connect(lambda: self.be_cool(6.0))
        tricks.addAction(tr("menu.push")).triggered.connect(lambda: self.push_animation(1.5))
        tricks.addAction(tr("menu.chase")).triggered.connect(lambda: self.chase_mouse(15.0))
        tricks.addAction(tr("menu.treat")).triggered.connect(self.give_treat)
        tricks.addAction(tr("menu.wash_pet", name=name)).triggered.connect(self.wash_requested.emit)
        tricks.addAction(tr("menu.bubble_game")).triggered.connect(self.bubble_game_requested.emit)
        tricks.addAction(tr("menu.yarn_game")).triggered.connect(self.yarn_game_requested.emit)
        tricks.addAction(tr("menu.lively_wallpaper")).triggered.connect(self.wallpaper_requested.emit)
        tricks.addAction("🖼️  Hintergrund wiederherstellen").triggered.connect(self.restore_wallpaper_requested.emit)
        tricks.addAction(tr("menu.pet_bed")).triggered.connect(self.pet_bed_requested.emit)
        is_home = bool(self.cfg.get("pet.is_at_home", False))
        home_action_text = tr("home.outside") if is_home else tr("home.at_home")
        tricks.addAction(home_action_text).triggered.connect(lambda: self.home_mode_toggled.emit(not is_home))
        tricks.addAction(tr("menu.sleep")).triggered.connect(self.go_to_sleep)
        tricks.addAction(tr("menu.wake")).triggered.connect(self.wake)

        # Schnelle Tools
        tools_menu = menu.addMenu(tr("menu.quick_tools"))
        style_menu(tools_menu)
        slide_menu = tools_menu.addMenu(tr("menu.push_windows"))
        style_menu(slide_menu)
        try:
            wins = tools.get_open_windows()
        except Exception:       # Tool-Funktion fehlt oder Windows-API-Fehler
            wins = []
        for ow in wins[:10]:
            title = ow["title"]
            short = title[:28] + ("..." if len(title) > 28 else "")
            slide_menu.addAction(f"❌  {short}").triggered.connect(
                lambda _=False, t=title: cmd(f"schließe {t}"))
        if not wins:
            slide_menu.addAction(tr("menu.no_windows")).setEnabled(False)
        tools_menu.addSeparator()
        for key, c in (
            ("menu.pomodoro_25", "pomodoro starten"),
            ("menu.pause_5", "timer 5 minuten"),
            ("menu.live_weather", "wie ist das wetter"),
            ("menu.clean_pc", "leere den papierkorb"),
            ("menu.network_ip", "wie ist meine ip"),
        ):
            tools_menu.addAction(tr(key)).triggered.connect(lambda _=False, c=c: cmd(c))
        tools_menu.addSeparator()
        for key, c in (
            ("menu.watch_screen", "was mache ich gerade"),
            ("menu.create_word", "erstelle ein word dokument am desktop"),
            ("menu.create_ppt", "erstelle eine powerpoint am desktop"),
            ("menu.screenshot", "screenshot"),
            ("menu.tidy_desktop", "desktop aufraeumen"),
            ("menu.datetime", "wie spaet ist es"),
            ("menu.systeminfo", "systeminfo"),
            ("menu.vol_up", "lauter"),
            ("menu.vol_down", "leiser"),
            ("menu.mute", "stumm"),
            ("menu.play_pause", "pause"),
        ):
            tools_menu.addAction(tr(key)).triggered.connect(lambda _=False, c=c: cmd(c))

        # Ordner
        folders_menu = menu.addMenu(tr("menu.folders"))
        style_menu(folders_menu)
        folders_menu.addAction(tr("menu.folder_downloads")).triggered.connect(lambda: self.command_requested.emit("oeffne downloads"))
        folders_menu.addAction(tr("menu.folder_docs")).triggered.connect(lambda: self.command_requested.emit("oeffne dokumente"))
        folders_menu.addAction(tr("menu.folder_desktop")).triggered.connect(lambda: self.command_requested.emit("oeffne desktop"))
        folders_menu.addAction(tr("menu.folder_trash")).triggered.connect(lambda: self.command_requested.emit("oeffne papierkorb"))

        menu.addSeparator()
        menu.addAction(tr("menu.reset_taskbar")).triggered.connect(self.reset_to_taskbar)
        menu.addAction(tr("menu.settings")).triggered.connect(self.settings_requested.emit)
        menu.addSeparator()
        menu.addAction(tr("menu.quit")).triggered.connect(self.quit_requested.emit)
        return menu

