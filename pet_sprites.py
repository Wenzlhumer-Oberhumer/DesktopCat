# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Grafik fuer das Pet: laedt GIF/PNG-Sprites aus assets/ und malt - falls keine vorhanden sind -
eine niedliche Kawaii-Katze per QPainter (komplett prozedural animiert, keine Bilddateien noetig)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
    QPixmap, QPolygonF, QRadialGradient,
)

from paths import DATA_DIR

BASE = 160.0    # logische Zeichenflaeche (wird mit Fenster-Skalierung gestreckt)
FLOOR = 148.0   # y-Position des Bodens in der Zeichenflaeche

STATE_KEYS = ["idle", "walk_right", "walk_left", "dragged", "falling", "working", "success", "sleep", "sad", "dance", "cool", "push", "fly"]
SPRITE_EXTS = (".gif", ".png", ".webp", ".apng")



# ======================================================================================
#  Sprite-Laden (GIF / PNG-Sheets) via Pillow
# ======================================================================================
def _pil_to_pixmap(img) -> QPixmap:
    img = img.convert("RGBA")
    w, h = img.size
    qimg = QImage(img.tobytes("raw", "RGBA"), w, h, 4 * w, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


class SpriteAnimation:
    def __init__(self, frames: list[QPixmap], durations_ms: list[int]):
        self.frames = frames
        self.durations = durations_ms
        self.total = max(1, sum(durations_ms))

    def frame_at(self, t_ms: float) -> QPixmap:
        if len(self.frames) == 1:
            return self.frames[0]
        t = t_ms % self.total
        acc = 0
        for frame, dur in zip(self.frames, self.durations):
            acc += dur
            if t < acc:
                return frame
        return self.frames[-1]


def load_animation(path: Path, frames: Optional[int] = None, fps: Optional[float] = None) -> Optional[SpriteAnimation]:
    """Laedt .gif / animiertes .webp (alle Frames) oder ein PNG-Sprite-Sheet (Frames nebeneinander)."""
    try:
        from PIL import Image, ImageSequence
        with Image.open(path) as im:
            n_frames = getattr(im, "n_frames", 1)
            if n_frames > 1:
                pix, durs = [], []
                for fr in ImageSequence.Iterator(im):
                    durs.append(max(20, int(fr.info.get("duration", 100) or 100)))
                    pix.append(_pil_to_pixmap(fr))
                return SpriteAnimation(pix, durs)
            rgba = im.convert("RGBA")
            w, h = rgba.size
            n = frames or (w // h if w > h and w % h == 0 else 1)
            n = max(1, n)
            fw = w // n
            pix = [_pil_to_pixmap(rgba.crop((i * fw, 0, (i + 1) * fw, h))) for i in range(n)]
            return SpriteAnimation(pix, [int(1000 / (fps or 8))] * n)
    except Exception as exc:  # defekte Datei -> Fallback-Katze nutzen
        print(f"[sprites] Konnte {path} nicht laden: {exc}")
        return None


class SpriteLibrary:
    """Sucht pro Zustand eine Animation (config.json oder assets/<zustand>.gif|png|webp)."""

    def __init__(self, base_dir: Path, anim_cfg: dict):
        self.anims: dict[str, SpriteAnimation] = {}
        user_assets = DATA_DIR / "assets"
        bundle_assets = base_dir / "assets"
        for key in STATE_KEYS:
            spec = anim_cfg.get(key) or ""
            frames = fps = None
            path: Optional[Path] = None
            if isinstance(spec, dict):
                frames, fps = spec.get("frames"), spec.get("fps")
                spec = spec.get("file", "")
            if spec:
                cand = Path(spec)
                if cand.is_absolute() and cand.exists():
                    path = cand
                elif (user_assets / cand).exists():
                    path = user_assets / cand
                elif (base_dir / cand).exists():
                    path = base_dir / cand
            else:
                for ext in SPRITE_EXTS:
                    cand_user = user_assets / f"{key}{ext}"
                    if cand_user.exists():
                        path = cand_user
                        break
                    cand_bundle = bundle_assets / f"{key}{ext}"
                    if cand_bundle.exists():
                        path = cand_bundle
                        break
            if path and path.exists():
                anim = load_animation(path, frames, fps)
                if anim:
                    self.anims[key] = anim

    @property
    def usable(self) -> bool:
        return "idle" in self.anims

    def get(self, key: str) -> tuple[Optional[SpriteAnimation], bool, bool]:
        """-> (Animation, gespiegelt?, exakter Treffer?)"""
        if key in self.anims:
            return self.anims[key], False, True
        if key == "walk_left" and "walk_right" in self.anims:
            return self.anims["walk_right"], True, True
        if key == "walk_right" and "walk_left" in self.anims:
            return self.anims["walk_left"], True, True
        if key == "falling" and "dragged" in self.anims:
            return self.anims["dragged"], False, True
        return self.anims.get("idle"), False, False


# ======================================================================================
#  Fallback: Kawaii-Katze "Mochi"
# ======================================================================================
OUTLINE = QColor("#3B2A22")        # dunkles Braun statt Rotbraun
WHITE_FUR = QColor("#FBF8F3")
WHITE_SHADE = QColor("#E9E2D8")    # Schatten im weißen Fell
ORANGE = QColor("#D9893F")
ORANGE_LIGHT = QColor("#EDAA68")
BLACK_FUR = QColor("#2A211C")
TABBY = QColor("#7A6553")          # braun-grau
TABBY_LIGHT = QColor("#9C8A76")
STRIPE = QColor("#2B2119")
PINK = QColor("#F2B8BC")           # Ohr innen
NOSE = QColor("#E99AA3")
MOUTH = QColor("#B5606C")
EYE_IRIS = QColor("#C4C25A")       # gelbgruen
EYE_IRIS_DK = QColor("#8FA046")
EYE_PUPIL = QColor("#1E1A16")
WHISKER = QColor(255, 255, 255, 210)
GOLD = QColor("#FFD84D")
HEART = QColor("#FF6B94")


@dataclass
class Pose:
    dx: float = 0.0
    dy: float = 0.0
    rot: float = 0.0
    pivot: tuple = (80.0, FLOOR)
    sx: float = 1.0
    sy: float = 1.0
    head_dx: float = 0.0
    head_dy: float = 0.0
    head_rot: float = 0.0
    eyes: str = "open"          # open | blink | sleep | happy | wide | sad | work
    mouth: str = "w"            # w | smile | o | sad
    look: tuple = (0.0, 0.0)
    tail: float = 0.0
    tail_curl: bool = False
    paw_l: float = 0.0
    paw_r: float = 0.0
    paws_up: bool = False
    ear_l: float = 0.0
    ear_r: float = 0.0
    blush: float = 0.5
    glasses: bool = False
    sunglasses: bool = False
    laptop: bool = False
    typing: float = 0.0
    bell: float = 0.0
    shadow: float = 1.0
    # Effekte (None = aus, sonst Zeitwert)
    zzz: Optional[float] = None
    dots: Optional[float] = None
    sparkles: Optional[float] = None
    confetti: Optional[float] = None
    hearts: Optional[float] = None   # 0..1 Alter
    music_notes: Optional[float] = None
    glint: Optional[float] = None
    sweat: bool = False
    tear: Optional[float] = None
    water: Optional[float] = None
    crumbs: Optional[float] = None
    push_power: float = 0.0
    t: float = 0.0
    accessories: tuple[str, ...] = ()



@dataclass
class PoseContext:
    key: str
    t: float                     # Sekunden seit Start (global)
    age: float                   # Sekunden seit Zustandswechsel
    look: tuple = (0.0, 0.0)
    hop: float = 0.0             # extra Huepfer in px (Klick-Reaktion)
    squash: float = 0.0          # Landungs-Squish 0..1
    hearts_age: Optional[float] = None
    happy: bool = False          # Klick-Freude


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def compute_pose(c: PoseContext) -> Pose:
    t, k = c.t, c.key
    p = Pose(look=c.look)
    breath = math.sin(t * math.tau / 2.8)

    def blink_state() -> bool:
        return (t % 4.3) < 0.13 or ((t + 1.9) % 9.1) < 0.12

    def ear_flick():
        ph = (t + 2.0) % 6.7
        return math.sin(ph / 0.28 * math.tau) * 11 if ph < 0.28 else 0.0

    if k == "idle":
        p.sy = 1 + 0.018 * breath
        p.sx = 1 - 0.008 * breath
        p.head_dy = -0.9 * breath
        p.head_dx = c.look[0] * 2.2
        p.tail = math.sin(t * 1.6) * 0.55
        p.ear_r = ear_flick()
        p.bell = 0.6 * breath
        p.eyes = "blink" if blink_state() else "open"
        p.mouth = "w"

    elif k in ("walk_right", "walk_left"):
        ph = t * math.tau * 2.7
        s = math.sin(ph)
        p.dy = -abs(s) * 3.6
        p.rot = s * 2.8
        p.paw_l = max(0.0, s) * 5.5
        p.paw_r = max(0.0, -s) * 5.5
        p.head_dx = 5.0
        p.head_rot = -s * 2.0
        p.look = (0.8, c.look[1] * 0.5)
        p.tail = 0.5 + math.sin(ph * 0.5 + 1.0) * 0.55
        p.ear_l = -s * 4
        p.ear_r = s * 4
        p.bell = math.sin(ph * 2) * 2.2
        p.blush = 0.55
        p.eyes = "blink" if blink_state() else "open"
        p.mouth = "w"
        p.shadow = 1 - abs(s) * 0.12

    elif k == "sleep":
        slow = math.sin(t * math.tau / 4.2)
        p.sy = 0.93 + 0.025 * slow
        p.sx = 1.03
        p.head_dy = 8 + 1.2 * slow
        p.head_dx = -3
        p.head_rot = -8
        p.eyes = "sleep"
        p.mouth = "w"
        p.tail_curl = True
        p.ear_l, p.ear_r = -12, 12
        p.blush = 0.65
        p.zzz = t
        p.look = (0, 0)

    elif k in ("dragged", "falling"):
        if k == "dragged":
            p.rot = math.sin(t * 13) * 9
            p.paw_l = max(0.0, math.sin(t * 17)) * 4
            p.paw_r = max(0.0, -math.sin(t * 17)) * 4
        else:
            p.rot = math.sin(t * 7) * 4
            p.paws_up = True
        p.pivot = (80.0, 38.0)
        p.sy = 1.07
        p.sx = 0.97
        p.eyes = "wide"
        p.mouth = "o"
        p.tail = math.sin(t * 19) * 0.9
        p.ear_l, p.ear_r = -7, 7
        p.blush = 0.2
        p.shadow = 0.0
        p.sweat = k == "dragged"
        p.bell = math.sin(t * 20) * 3
        p.look = (0, 0)

    elif k == "success":
        period = 0.62
        u = (c.age % period) / period
        h = 4 * u * (1 - u)
        p.dy = -h * 28
        ground = u < 0.1 or u > 0.9
        p.sy = 0.88 if ground else 1 + 0.07 * h
        p.sx = 1.08 if ground else 1 - 0.04 * h
        p.paws_up = True
        p.eyes = "happy"
        p.mouth = "smile"
        p.tail = math.sin(t * 14) * 0.9
        p.ear_l, p.ear_r = 6 * math.sin(t * 10), -6 * math.sin(t * 10)
        p.blush = 0.85
        p.sparkles = t
        p.shadow = _clamp(1 - h * 0.45, 0.4, 1)
        p.bell = math.sin(t * 22) * 3.5
        p.look = (0, 0)

    elif k == "working":
        p.laptop = True
        p.glasses = True
        p.typing = t * math.tau * 3.4
        p.head_dy = 1.0 + 0.8 * math.sin(t * 2.2)
        p.head_rot = math.sin(t * 1.3) * 2.5
        p.eyes = "blink" if blink_state() else "work"
        p.mouth = "w"
        p.tail = math.sin(t * 2.4) * 0.5
        p.ear_r = ear_flick()
        p.dots = t
        p.look = (0.0, 0.8)
        p.blush = 0.4

    elif k == "sad":
        p.head_dy = 3.5
        p.head_rot = -3
        p.dx = math.sin(t * 28) * 0.5
        p.sy = 0.97
        p.eyes = "sad"
        p.mouth = "sad"
        p.tail = -0.9
        p.ear_l, p.ear_r = -11, 11
        p.blush = 0.15
        p.tear = c.age
        p.look = (0, 0)

    elif k == "dance":
        bpm = 2.4
        ph = t * math.tau * bpm
        s = math.sin(ph)
        c_val = math.cos(ph)
        p.dy = -abs(s) * 6.5
        p.rot = s * 7.5
        p.sx = 1.0 + 0.04 * c_val
        p.sy = 1.0 - 0.04 * c_val
        p.paws_up = True
        p.paw_l = max(0.0, s) * 7.0
        p.paw_r = max(0.0, -s) * 7.0
        p.head_dx = s * 3.5
        p.head_rot = -s * 5.0
        p.ear_l = -s * 8.0
        p.ear_r = s * 8.0
        p.tail = math.sin(ph * 0.7) * 0.95
        p.bell = s * 4.0
        p.eyes = "happy"
        p.mouth = "smile"
        p.blush = 0.85
        p.music_notes = t
        p.shadow = _clamp(1.0 - abs(s) * 0.25, 0.5, 1.0)
        p.look = (s * 0.4, -0.2)

    elif k == "cool":
        slow = math.sin(t * math.tau * 0.8)
        p.sunglasses = True
        p.head_dx = 1.6 * slow
        p.head_rot = 3.5 + 1.2 * slow
        p.rot = -2.8
        p.mouth = "smile"
        p.blush = 0.35
        p.tail = math.sin(t * 1.8) * 0.7
        p.ear_r = 6.0
        p.glint = t
        p.look = (0.5, 0.0)

    elif k == "push":
        # Kraftvolles Schieben / Stemmen gegen das Fenster!
        p.dx = math.sin(t * 36) * 1.8       # Anstrengungs-Vibration
        p.rot = 8.5                          # Kraftvoll nach vorne geneigt
        p.head_dx = 6.0
        p.head_rot = 4.0
        p.sy = 0.93                          # Geduckte Kraft-Haltung
        p.sx = 1.05
        p.paws_up = True                     # Pfoten / Hände nach vorne ausgestreckt
        p.eyes = "work"                      # Entschlossener Fokus-Blick
        p.mouth = "o"                        # Kraftvoller Mund
        p.sweat = True                       # Schweißtropfen vor Anstrengung
        p.tail = math.sin(t * 14) * 0.4
        p.look = (1.0, 0.0)                  # Blick nach vorn auf das Fenster
        p.push_power = 1.0

    elif k == "fly":
        bob = math.sin(t * 3.5) * 4.0
        p.dy = bob
        p.sy = 1.02 + 0.02 * math.sin(t * 2.8)
        p.sx = 0.98
        p.paws_up = True
        p.paw_l = 2.0
        p.paw_r = 2.0
        p.head_dy = -1.0 + 0.5 * math.sin(t * 2.5)
        p.head_rot = math.sin(t * 1.8) * 2.0
        p.eyes = "happy" if (t % 5.0) > 3.5 else "open"
        p.mouth = "smile"
        p.tail = math.sin(t * 4.0) * 0.6
        p.shadow = 0.4
        p.blush = 0.5

    p.t = t

    # Klick-Reaktion: huepft, Herzchen-Augen, laechelt, schnurrt (Vibration)
    if c.happy:
        p.eyes = "heart"
        p.mouth = "smile"
        p.blush = 0.95
        p.tail = math.sin(t * 14) * 0.9
        p.dx += math.sin(t * 55) * 0.75   # Niedliche Schnurr-Vibration!
    if c.hop:
        p.dy -= c.hop
        p.shadow = _clamp(p.shadow - c.hop / 60, 0.4, 1)
    if c.squash:
        p.sy *= 1 - 0.16 * c.squash
        p.sx *= 1 + 0.12 * c.squash
    p.hearts = c.hearts_age
    return p


# --------------------------------------------------------------------------------------
#  Zeichen-Helfer
# --------------------------------------------------------------------------------------
def _pen(color: QColor, w: float) -> QPen:
    pen = QPen(color, w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _heart_path(cx: float, cy: float, s: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(cx, cy + s)
    path.cubicTo(cx - 2.1 * s, cy - 0.15 * s, cx - 0.95 * s, cy - 1.5 * s, cx, cy - 0.45 * s)
    path.cubicTo(cx + 0.95 * s, cy - 1.5 * s, cx + 2.1 * s, cy - 0.15 * s, cx, cy + s)
    return path


def _star_path(cx: float, cy: float, r: float) -> QPainterPath:
    poly = QPolygonF()
    for i in range(8):
        ang = i * math.pi / 4 - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.36
        poly.append(QPointF(cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    path = QPainterPath()
    path.addPolygon(poly)
    path.closeSubpath()
    return path


def _paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(OUTLINE, 2.2))
    p.setBrush(WHITE_FUR)
    p.drawEllipse(QRectF(-8.5, -6.5, 17, 13))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINK)
    p.drawEllipse(QRectF(-3, -0.5, 6, 4.5))
    for dx in (-4.2, 0, 4.2):
        p.drawEllipse(QRectF(dx - 1.1, -4.2 if dx == 0 else -3.6, 2.2, 2.2))
    p.restore()


def _draw_eye(p: QPainter, cx: float, cy: float, mode: str, look: tuple, side: int):
    lx, ly = look
    if mode in ("open", "wide", "sad", "work"):
        rx, ry = 8.4, 10.4
        if mode == "wide":
            rx, ry = 9.6, 11.8
        elif mode == "work":
            ry = 8.6
        ex, ey = cx + lx * 2.6, cy + ly * 2.4
        # Iris (gelbgruen mit leichtem Verlauf)
        grad = QLinearGradient(ex, ey - ry, ex, ey + ry)
        grad.setColorAt(0, EYE_IRIS)
        grad.setColorAt(1, EYE_IRIS_DK)
        p.setPen(_pen(OUTLINE, 1.4))  # dunkler Lidstrich
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(ex - rx, ey - ry, rx * 2, ry * 2))

        # Grosse dunkle Pupille (Kawaii)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(EYE_PUPIL)
        prx, pry = rx * 0.68, ry * 0.72
        p.drawEllipse(QRectF(ex - prx + lx * 0.6, ey - pry + ly * 0.6, prx * 2, pry * 2))

        # Glanzpunkte
        p.setBrush(QColor("white"))
        big = 3.6 if mode != "wide" else 4.2
        p.drawEllipse(QPointF(ex - 2.7 + lx * 0.8, ey - ry * 0.38), big, big)
        p.drawEllipse(QPointF(ex + 3.2 + lx * 0.4, ey + ry * 0.36), 1.8, 1.8)
        if mode == "sad":
            p.setPen(_pen(OUTLINE, 2.4))
            inner = -side
            p.drawLine(QPointF(ex + inner * -9, ey - 12.5), QPointF(ex + inner * 7.5, ey - 17))
    elif mode == "blink":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(EYE_PUPIL)
        p.drawEllipse(QRectF(cx - 8.4, cy + 2.5, 16.8, 3.0))
    elif mode == "sleep":
        p.setPen(_pen(OUTLINE, 2.9))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 8, cy - 6, 16, 11), 180 * 16, 180 * 16)
    elif mode == "happy":
        p.setPen(_pen(OUTLINE, 3.1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 8, cy - 4, 16, 13), 0, 180 * 16)
    elif mode == "heart":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FF4D79"))
        p.drawPath(_heart_path(cx, cy - 1.5, 4.2))
        p.setBrush(QColor(255, 255, 255, 210))
        p.drawEllipse(QPointF(cx - 1.6, cy - 3.2), 1.4, 1.4)


def _draw_tail(p: QPainter, pose: Pose):
    if pose.tail_curl:
        path = QPainterPath(QPointF(54, 140))
        path.cubicTo(QPointF(36, 150), QPointF(100, 153), QPointF(116, 142))
    else:
        a = pose.tail
        path = QPainterPath(QPointF(58, 132))
        path.cubicTo(QPointF(24, 140), QPointF(6 - 8 * a, 104), QPointF(26 - 13 * a, 72 - 8 * abs(a)))

    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(OUTLINE, 14.5))
    p.drawPath(path)
    # Grundfarbe Tabby (braun-grau)
    p.setPen(_pen(TABBY, 10.5))
    p.drawPath(path)

    # Dunkle Ringstreifen entlang des Schwanzes
    p.setPen(_pen(STRIPE, 3.2))
    for frac in (0.24, 0.40, 0.56, 0.72, 0.86):
        pt = path.pointAtPercent(frac)
        angle = path.angleAtPercent(frac)
        p.save()
        p.translate(pt)
        p.rotate(-angle + 90)
        p.drawLine(QPointF(-4.5, 0), QPointF(4.5, 0))
        p.restore()

    # Dunkle Schwanzspitze
    end = path.pointAtPercent(1.0)
    p.setPen(_pen(OUTLINE, 2.0))
    p.setBrush(STRIPE)
    p.drawEllipse(end, 5.4, 5.4)


def _draw_ear(p: QPainter, sign: int, rot: float):
    """sign=-1 links (orange), +1 rechts (tabby); Koordinaten relativ zur Kopfmitte."""
    bx, by = sign * 30, -22
    p.save()
    p.translate(bx, by)
    p.rotate(rot)
    p.translate(-bx, -by)
    outer = QPolygonF([QPointF(sign * 43, -11), QPointF(sign * 38, -51), QPointF(sign * 9, -31)])
    inner = QPolygonF([QPointF(sign * 37, -17), QPointF(sign * 34.5, -42), QPointF(sign * 17, -29)])
    p.setPen(_pen(OUTLINE, 2.6))
    ear_color = ORANGE if sign < 0 else TABBY
    p.setBrush(ear_color)
    p.drawPolygon(outer)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINK)
    p.drawPolygon(inner)
    # Helles Haarbueschel am Innenohr
    p.setBrush(WHITE_FUR)
    p.drawPolygon(QPolygonF([QPointF(sign * 26, -24), QPointF(sign * 33, -33), QPointF(sign * 28, -20)]))
    p.restore()


def _draw_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    _draw_ear(p, -1, pose.ear_l)
    _draw_ear(p, +1, pose.ear_r)

    # 1. Grundform Kopf (weiss)
    head_rect = QRectF(-46, -37, 92, 74)
    head_path = QPainterPath()
    head_path.addEllipse(head_rect)

    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(WHITE_FUR)
    p.drawPath(head_path)

    # 2. Asymmetrische Calico- & Tabby-Muster auf Kopf clippen
    p.save()
    p.setClipPath(head_path)

    # Linke Haelfte (vom Betrachter links, x < 0): oranger Fleck ueber Wange und Ohrbasis
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ORANGE)
    p.drawEllipse(QRectF(-48, -38, 44, 52))

    # Rechte Haelfte + Stirn: braun-graues Tabby
    p.setBrush(TABBY)
    p.drawEllipse(QRectF(-8, -40, 56, 54))

    # Dunkle "M"-Tabby-Streifen auf der Stirn rechts
    p.setPen(_pen(STRIPE, 2.4))
    p.drawLine(QPointF(4, -35), QPointF(2, -22))
    p.drawLine(QPointF(12, -34), QPointF(9, -21))
    p.drawLine(QPointF(20, -31), QPointF(16, -20))

    # 2 dunkle Wangenstreifen rechts
    p.drawLine(QPointF(32, -4), QPointF(43, -8))
    p.drawLine(QPointF(34, 3), QPointF(44, 1))

    # Kleiner oranger Tupfer Stirnmitte
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ORANGE)
    p.drawEllipse(QRectF(-3.5, -30, 7.0, 8.0))

    # Weisse Blesse von Nase zur Stirn
    p.setBrush(WHITE_FUR)
    p.drawEllipse(QRectF(-6.0, -22, 12.0, 30.0))

    # Weisse Schnauzen-, Wangen- und Kinnpartie
    p.drawEllipse(QRectF(-20, 3, 40, 24))

    p.restore()

    # Kontur nachzeichnen
    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(head_rect)

    # Wangenroeschen
    if pose.blush > 0:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 118, 150, int(_clamp(pose.blush, 0, 1) * 140)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 31 - 8.5, 10.5, 17, 10))

    # Schnurrhaare (weiss)
    p.setPen(_pen(WHISKER, 1.6))
    for s in (-1, 1):
        for (y0, x1, y1) in ((13, 54, 8), (18, 56, 18), (23, 53, 28)):
            p.drawLine(QPointF(s * 41, y0), QPointF(s * x1, y1))

    # Augen
    look = pose.look
    for s in (-1, 1):
        _draw_eye(p, s * 19, 4, pose.eyes, look, s)

    if pose.glasses:
        p.setBrush(QColor(190, 225, 255, 70))
        p.setPen(_pen(QColor("#5B6C9D"), 2.4))
        for s in (-1, 1):
            p.drawEllipse(QPointF(s * 19, 4), 14.5, 14.5)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(-4.6, 2), QPointF(4.6, 2))
        p.drawLine(QPointF(-33.3, 0), QPointF(-45, -3))
        p.drawLine(QPointF(33.3, 0), QPointF(45, -3))

    if pose.sunglasses:
        p.save()
        p.setPen(_pen(QColor("#18191D"), 2.6))
        grad = QLinearGradient(0, -6, 0, 16)
        grad.setColorAt(0, QColor("#1D1F26"))
        grad.setColorAt(1, QColor("#363B48"))
        p.setBrush(QBrush(grad))
        for s in (-1, 1):
            glass = QPolygonF([
                QPointF(s * 7, -2),
                QPointF(s * 33, -2),
                QPointF(s * 31, 14),
                QPointF(s * 10, 15),
            ])
            p.drawPolygon(glass)
            p.setPen(_pen(QColor(255, 255, 255, 130), 1.8))
            p.drawLine(QPointF(s * 14, 2), QPointF(s * 25, 2))
            p.setPen(_pen(QColor("#18191D"), 2.6))
        p.setPen(_pen(QColor("#FFD24D"), 2.4))
        p.drawLine(QPointF(-8, 1), QPointF(8, 1))
        p.setPen(_pen(QColor("#FFD24D"), 2.0))
        p.drawLine(QPointF(-33, 1), QPointF(-44, -3))
        p.drawLine(QPointF(33, 1), QPointF(44, -3))
        p.restore()

    # Nase (rosa)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(NOSE)
    p.drawPolygon(QPolygonF([QPointF(-3.6, 8.6), QPointF(3.6, 8.6), QPointF(0, 12.6)]))

    # Mund
    m = pose.mouth
    p.setBrush(Qt.BrushStyle.NoBrush)
    if m == "w":
        p.setPen(_pen(OUTLINE, 1.9))
        p.drawLine(QPointF(0, 12.8), QPointF(0, 14.4))
        p.drawArc(QRectF(-8, 11.6, 8, 6.4), 180 * 16, 180 * 16)
        p.drawArc(QRectF(0, 11.6, 8, 6.4), 180 * 16, 180 * 16)
    elif m == "smile":
        path = QPainterPath(QPointF(-7.5, 13.6))
        path.cubicTo(QPointF(-6, 23.5), QPointF(6, 23.5), QPointF(7.5, 13.6))
        path.closeSubpath()
        p.setPen(_pen(OUTLINE, 1.8))
        p.setBrush(MOUTH)
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(PINK)
        p.drawEllipse(QPointF(0, 19.6), 3.6, 2.4)
    elif m == "o":
        p.setPen(_pen(OUTLINE, 1.7))
        p.setBrush(MOUTH)
        p.drawEllipse(QPointF(0, 18), 3.3, 4.4)
    elif m == "sad":
        p.setPen(_pen(OUTLINE, 1.9))
        p.drawLine(QPointF(0, 12.8), QPointF(0, 15))
        p.drawArc(QRectF(-5.5, 16.5, 11, 7), 0, 180 * 16)

    # Traene / Schweisstropfen
    if pose.tear is not None:
        ph = (pose.tear * 0.9) % 1.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(140, 205, 255, int(235 * (1 - ph * 0.6))))
        p.drawEllipse(QRectF(-22.5, 14 + ph * 10, 7, 9))
    if pose.sweat:
        p.setPen(_pen(QColor("#6FB7F0"), 1.2))
        p.setBrush(QColor(170, 220, 255, 230))
        drop = QPainterPath(QPointF(40, -22))
        drop.cubicTo(QPointF(34, -14), QPointF(35, -8), QPointF(40, -8))
        drop.cubicTo(QPointF(45, -8), QPointF(46, -14), QPointF(40, -22))
        p.drawPath(drop)
    p.restore()


def _draw_effects(p: QPainter, pose: Pose):
    if pose.zzz is not None:
        f = QFont("Segoe UI")
        f.setBold(True)
        for i in range(3):
            age = (pose.zzz * 0.45 + i / 3) % 1.0
            x = 112 + age * 16 + i * 3
            y = 50 - age * 36
            size = 9 + age * 9
            f.setPixelSize(int(size))
            p.setFont(f)
            p.setPen(QColor(138, 180, 255, int(255 * math.sin(math.pi * age))))
            p.drawText(QPointF(x, y), "z" if i == 0 else "Z")
    if pose.dots is not None:
        p.setPen(_pen(QColor(150, 110, 95), 1.8))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawEllipse(QPointF(110, 36), 2.6, 2.6)
        p.drawEllipse(QPointF(116, 30), 3.8, 3.8)
        cloud = QRectF(112, 2, 44, 24)
        p.drawRoundedRect(cloud, 11, 11)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            pulse = max(0.0, math.sin(pose.dots * 4.2 - i * 0.9))
            p.setBrush(QColor(255, 140, 175))
            r = 2.3 + 1.7 * pulse
            p.drawEllipse(QPointF(124 + i * 10, 14 - pulse * 2), r, r)
    if pose.sparkles is not None:
        for i in range(5):
            ang = pose.sparkles * 1.8 + i * math.tau / 5
            rad = 56 + 6 * math.sin(pose.sparkles * 5 + i)
            cx, cy = 80 + math.cos(ang) * rad, 70 + math.sin(ang) * rad * 0.7
            r = 4 + 3 * (0.5 + 0.5 * math.sin(pose.sparkles * 7 + i * 1.7))
            p.setPen(_pen(QColor("#FFF6C2"), 1.2))
            p.setBrush(GOLD)
            p.drawPath(_star_path(cx, cy, r))
    if getattr(pose, "confetti", None) is not None:
        t_c = pose.confetti
        confetti_colors = [
            QColor("#FF5C8A"), QColor("#FFD166"), QColor("#38D9A9"),
            QColor("#4DABF7"), QColor("#A77DFF"), QColor("#FF922B"),
        ]
        for i in range(12):
            age = (t_c * 0.75 + i * 0.083) % 1.0
            cx = 80 + math.sin(t_c * 2.8 + i * 1.7) * 55 + (i - 5.5) * 8
            cy = 25 + age * 85
            rot = (t_c * 220 + i * 45) % 360
            col = QColor(confetti_colors[i % len(confetti_colors)])
            col.setAlpha(int(240 * math.sin(math.pi * age)))
            p.save()
            p.translate(cx, cy)
            p.rotate(rot)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawRect(QRectF(-3.5, -2.0, 7.0, 4.0))
            p.restore()
    if pose.hearts is not None:
        age = pose.hearts
        for i, ox in enumerate((-16, 4, 22)):
            a = _clamp(age * 1.25 - i * 0.12, 0.0, 1.0)
            if a <= 0 or a >= 1:
                continue
            cx = 80 + ox + math.sin(a * 6 + i) * 4
            cy = 38 - a * 30
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 107, 148, int(255 * (1 - a ** 2))))
            p.drawPath(_heart_path(cx, cy, 4.8 + 2.5 * (1 - a)))
    if pose.music_notes is not None:
        t_note = pose.music_notes
        colors = [QColor("#FF5C8A"), QColor("#A77DFF"), QColor("#38D9A9"), QColor("#FFD166")]
        for i in range(4):
            age = (t_note * 0.7 + i * 0.25) % 1.0
            x = 80 + math.sin(t_note * 2.5 + i * 1.6) * 36 + (i - 1.5) * 12
            y = 52 - age * 52
            alpha = int(255 * math.sin(math.pi * age))
            col = QColor(colors[i % len(colors)])
            col.setAlpha(alpha)
            p.save()
            p.translate(x, y)
            p.scale(0.85, 0.85)
            if i % 2 == 0:
                p.rotate(-15)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(col)
                p.drawEllipse(QPointF(0, 0), 3.8, 2.8)
                p.rotate(15)
                p.setPen(QPen(col, 1.8))
                p.drawLine(QPointF(2.4, -1), QPointF(2.4, -13))
                flag = QPainterPath(QPointF(2.4, -13))
                flag.cubicTo(QPointF(7, -11), QPointF(8, -7), QPointF(6, -4))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(flag)
            else:
                for ox, oy in [(-5, 1.5), (5, 0)]:
                    p.save()
                    p.translate(ox, oy)
                    p.rotate(-15)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(col)
                    p.drawEllipse(QPointF(0, 0), 3.2, 2.4)
                    p.restore()
                p.setPen(QPen(col, 1.8))
                p.drawLine(QPointF(-3.2, 0), QPointF(-3.2, -11))
                p.drawLine(QPointF(6.8, -1.5), QPointF(6.8, -12.5))
                p.setPen(QPen(col, 2.6))
                p.drawLine(QPointF(-3.2, -11), QPointF(6.8, -12.5))
            p.restore()

    if pose.glint is not None:
        ph = (pose.glint * 1.6) % 1.0
        if ph < 0.6:
            glint_scale = math.sin(ph / 0.6 * math.pi)
            p.setPen(_pen(QColor("#FFFFFF"), 1.2))
            p.setBrush(QColor("#FFF4A3"))
            p.drawPath(_star_path(112, 60, 5.5 * glint_scale))
    if getattr(pose, "push_power", 0.0) > 0.1:
        p.save()
        p.setPen(_pen(QColor(140, 190, 255, 210), 2.2))
        for ox, oy, l in [(122, 106, 16), (128, 115, 22), (123, 125, 14)]:
            p.drawLine(QPointF(ox, oy), QPointF(ox + l, oy))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(220, 210, 195, 150))
        p.drawEllipse(QPointF(46, FLOOR - 5), 7, 5)
        p.drawEllipse(QPointF(38, FLOOR - 3), 5, 4)
        p.restore()

    if getattr(pose, "water", None) is not None:
        t_w = pose.water
        p.save()
        p.setPen(_pen(QColor("#5A90C0"), 1.8))
        p.setBrush(QColor("#D6ECFF"))
        bowl = QRectF(60, 137, 40, 11)
        p.drawRoundedRect(bowl, 5.0, 5.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#3B9EFF", 230))
        p.drawRoundedRect(QRectF(63, 139, 34, 6), 3.0, 3.0)
        for i in range(3):
            age = (t_w * 1.6 + i * 0.33) % 1.0
            cx = 70 + i * 10 + math.sin(age * 5.5 + i) * 3
            cy = 135 - age * 26
            alpha = int(230 * math.sin(math.pi * age))
            p.setBrush(QColor(60, 175, 255, alpha))
            p.drawEllipse(QPointF(cx, cy), 2.2 * (1 - age * 0.3), 2.8 * (1 - age * 0.3))
        p.restore()

    if getattr(pose, "crumbs", None) is not None:
        t_cr = pose.crumbs
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        crumb_colors = [QColor("#FFA94D"), QColor("#FFD43B"), QColor("#F76707")]
        for i in range(5):
            age = (t_cr * 1.8 + i * 0.2) % 1.0
            cx = 80 + math.cos(i * 1.3) * (14 + age * 8)
            cy = 105 + math.sin(i * 1.5) * (8 + age * 6)
            col = QColor(crumb_colors[i % len(crumb_colors)])
            col.setAlpha(int(240 * math.sin(math.pi * age)))
            p.setBrush(col)
            r = 1.6 + 0.8 * (1 - age)
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.restore()


def _draw_shadow(p: QPainter, pose: Pose, hover_offset: float = 0.0, width: float = 74.0):
    if pose.shadow > 0.02:
        p.setPen(Qt.PenStyle.NoPen)
        alpha = int(48 * pose.shadow)
        if hover_offset > 0:
            alpha = int(alpha * max(0.2, 1.0 - hover_offset / 30.0))
        p.setBrush(QColor(50, 25, 20, alpha))
        w = width * (0.75 + 0.25 * pose.shadow)
        p.drawEllipse(QRectF(80 - w / 2, FLOOR - 4.5, w, 8.5))


def _draw_laptop(p: QPainter, pose: Pose, paw_draw_fn=None):
    if not pose.laptop:
        return
    lid = QRectF(47, 113, 66, 29)
    p.setPen(_pen(QColor("#4A4E5A"), 2.4))
    p.setBrush(QColor("#D8DDE6"))
    p.drawRoundedRect(lid, 6, 6)
    glow = 0.5 + 0.5 * math.sin(pose.typing * 0.35)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, int(150 + 60 * glow), int(185 + 40 * glow)))
    p.drawEllipse(QPointF(80, 128), 5.2, 5.2)
    p.setPen(_pen(QColor("#4A4E5A"), 2.2))
    p.setBrush(QColor("#B7BECB"))
    p.drawRoundedRect(QRectF(41, 141, 78, 7), 3.5, 3.5)
    up_l = max(0.0, math.sin(pose.typing)) * 4
    up_r = max(0.0, -math.sin(pose.typing)) * 4
    if paw_draw_fn:
        paw_draw_fn(p, 66, 112 - up_l, 0)
        paw_draw_fn(p, 94, 112 - up_r, 0)
    else:
        _paw(p, 66, 112 - up_l, 0)
        _paw(p, 94, 112 - up_r, 0)


# ======================================================================================
#  1) Katze Mochi (Ginger Tabby Katze)
# ======================================================================================
def draw_cat_mochi(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)


def draw_cat(p: QPainter, pose: Pose):
    """Zeichnet die Katze in die 160x160-Flaeche (Katze schaut nach rechts, Schwanz links)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if pose.shadow > 0.02:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(60, 30, 20, int(48 * pose.shadow)))
        w = 74 * (0.75 + 0.25 * pose.shadow)
        p.drawEllipse(QRectF(80 - w / 2, FLOOR - 4.5, w, 8.5))

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    if not pose.tail_curl:
        _draw_tail(p, pose)

    # Koerper (Calico: weisse Basis mit unregelmaessigen Flecken)
    body_rect = QRectF(47, 100, 66, 47.5)
    body_path = QPainterPath()
    body_path.addEllipse(body_rect)

    p.save()
    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(WHITE_FUR)
    p.drawPath(body_path)

    p.setClipPath(body_path)
    p.setPen(Qt.PenStyle.NoPen)

    # Schwarz-brauner Rueckenfleck (links/oben)
    p.setBrush(BLACK_FUR)
    p.drawEllipse(QRectF(44, 96, 32, 28))
    p.drawEllipse(QRectF(55, 94, 26, 24))

    # Feine Tabby-Streifen im dunklen Fleck
    p.setPen(_pen(STRIPE, 1.4))
    p.drawLine(QPointF(53, 99), QPointF(49, 108))
    p.drawLine(QPointF(59, 97), QPointF(56, 109))
    p.drawLine(QPointF(65, 98), QPointF(63, 107))
    p.setPen(Qt.PenStyle.NoPen)

    # Oranger Fleck (rechts/Mitte Ruecken)
    p.setBrush(ORANGE)
    p.drawEllipse(QRectF(75, 97, 34, 28))
    p.drawEllipse(QRectF(86, 104, 24, 22))

    # Weisser Bauchbereich
    p.setBrush(WHITE_FUR)
    p.drawEllipse(QRectF(56, 116, 48, 34))

    # Zarter Schatten am Bauch
    p.setBrush(WHITE_SHADE)
    p.drawEllipse(QRectF(64, 130, 32, 16))

    p.restore()
    # Kante nachzeichnen
    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(body_path)

    if pose.tail_curl:
        _draw_tail(p, pose)

    # Pfoetchen (vorn)
    if not pose.laptop:
        if pose.paws_up:
            _paw(p, 44, 100, -35)
            _paw(p, 116, 100, 35)
        else:
            _paw(p, 65, 143 - pose.paw_l, 0)
            _paw(p, 95, 143 - pose.paw_r, 0)

    # Halsband + Glocke entfernt (echte Katze traegt keins)

    _draw_head(p, pose)

    if pose.laptop:
        lid = QRectF(47, 113, 66, 29)
        p.setPen(_pen(OUTLINE, 2.4))
        p.setBrush(QColor("#D8DDE6"))
        p.drawRoundedRect(lid, 6, 6)
        glow = 0.5 + 0.5 * math.sin(pose.typing * 0.35)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, int(150 + 60 * glow), int(185 + 40 * glow)))
        p.drawEllipse(QPointF(80, 128), 5.2, 5.2)
        p.setPen(_pen(OUTLINE, 2.2))
        p.setBrush(QColor("#B7BECB"))
        p.drawRoundedRect(QRectF(41, 141, 78, 7), 3.5, 3.5)
        up_l = max(0.0, math.sin(pose.typing)) * 4
        up_r = max(0.0, -math.sin(pose.typing)) * 4
        _paw(p, 66, 112 - up_l, 0)
        _paw(p, 94, 112 - up_r, 0)

    p.restore()
    _draw_effects(p, pose)



LUNA_BLACK = QColor("#22242D")
LUNA_LIGHT = QColor("#363A48")
LUNA_OUTLINE = QColor("#121318")
LUNA_WHITE = QColor("#F8F9FA")
LUNA_EYE_TOP = QColor("#10AC84")
LUNA_EYE_BOT = QColor("#2ED573")
LUNA_RIBBON = QColor("#6C5CE7")
LUNA_MOON = QColor("#E0F2FE")

def _luna_paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(LUNA_OUTLINE, 2.2))
    p.setBrush(LUNA_WHITE)
    p.drawEllipse(QRectF(-8.5, -6.5, 17, 13))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FDA7DF"))
    p.drawEllipse(QRectF(-3, -0.5, 6, 4.5))
    for dx in (-4.2, 0, 4.2):
        p.drawEllipse(QRectF(dx - 1.1, -4.2 if dx == 0 else -3.6, 2.2, 2.2))
    p.restore()


def _draw_luna_eye(p: QPainter, cx: float, cy: float, mode: str, look: tuple, side: int):
    lx, ly = look
    if mode in ("open", "wide", "sad", "work"):
        rx, ry = 8.4, 10.4
        if mode == "wide":
            rx, ry = 9.6, 11.8
        elif mode == "work":
            ry = 8.6
        ex, ey = cx + lx * 2.6, cy + ly * 2.4
        grad = QLinearGradient(ex, ey - ry, ex, ey + ry)
        grad.setColorAt(0, LUNA_EYE_TOP)
        grad.setColorAt(1, LUNA_EYE_BOT)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(ex - rx, ey - ry, rx * 2, ry * 2))
        p.setBrush(QColor("white"))
        big = 3.6 if mode != "wide" else 4.2
        p.drawEllipse(QPointF(ex - 2.7 + lx * 0.8, ey - ry * 0.38), big, big)
        p.drawEllipse(QPointF(ex + 3.2 + lx * 0.4, ey + ry * 0.36), 1.8, 1.8)
        if mode == "sad":
            p.setPen(_pen(LUNA_OUTLINE, 2.4))
            inner = -side
            p.drawLine(QPointF(ex + inner * -9, ey - 12.5), QPointF(ex + inner * 7.5, ey - 17))
    elif mode == "blink":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(LUNA_EYE_TOP)
        p.drawEllipse(QRectF(cx - 8.4, cy + 2.5, 16.8, 3.0))
    elif mode == "sleep":
        p.setPen(_pen(LUNA_EYE_TOP, 2.9))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 8, cy - 6, 16, 11), 180 * 16, 180 * 16)
    elif mode == "happy":
        p.setPen(_pen(LUNA_EYE_BOT, 3.1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 8, cy - 4, 16, 13), 0, 180 * 16)
    elif mode == "heart":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2ED573"))
        p.drawPath(_heart_path(cx, cy - 1.5, 4.2))
        p.setBrush(QColor(255, 255, 255, 210))
        p.drawEllipse(QPointF(cx - 1.6, cy - 3.2), 1.4, 1.4)


def _draw_luna_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # Ohren
    for sign, rot in ((-1, pose.ear_l), (1, pose.ear_r)):
        bx, by = sign * 30, -22
        p.save()
        p.translate(bx, by)
        p.rotate(rot)
        p.translate(-bx, -by)
        outer = QPolygonF([QPointF(sign * 43, -11), QPointF(sign * 38, -51), QPointF(sign * 9, -31)])
        inner = QPolygonF([QPointF(sign * 37, -17), QPointF(sign * 34.5, -42), QPointF(sign * 17, -29)])
        p.setPen(_pen(LUNA_OUTLINE, 2.6))
        p.setBrush(LUNA_BLACK)
        p.drawPolygon(outer)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#484B5B"))
        p.drawPolygon(inner)
        p.restore()

    # Kopfrundung
    grad = QRadialGradient(QPointF(-12, -20), 72)
    grad.setColorAt(0, LUNA_LIGHT)
    grad.setColorAt(1, LUNA_BLACK)
    p.setPen(_pen(LUNA_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-46, -37, 92, 74))

    # Weisse Schnauzenpartie
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(LUNA_WHITE)
    p.drawEllipse(QRectF(-14, 7, 28, 18))

    # Wangenroete
    if pose.blush > 0:
        p.setBrush(QColor(255, 110, 160, int(_clamp(pose.blush, 0, 1) * 140)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 31 - 8.5, 10.5, 17, 10))

    # Feine Schnurrhaare
    p.setPen(_pen(QColor(180, 190, 205, 160), 1.5))
    for s in (-1, 1):
        for (y0, x1, y1) in ((13, 54, 8), (18, 56, 18), (23, 53, 28)):
            p.drawLine(QPointF(s * 41, y0), QPointF(s * x1, y1))

    # Augen
    for s in (-1, 1):
        _draw_luna_eye(p, s * 19, 4, pose.eyes, pose.look, s)

    # Brillen
    if pose.glasses:
        p.setBrush(QColor(190, 225, 255, 70))
        p.setPen(_pen(QColor("#9BA4B5"), 2.4))
        for s in (-1, 1):
            p.drawEllipse(QPointF(s * 19, 4), 14.5, 14.5)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(-4.6, 2), QPointF(4.6, 2))
        p.drawLine(QPointF(-33.3, 0), QPointF(-45, -3))
        p.drawLine(QPointF(33.3, 0), QPointF(45, -3))

    if pose.sunglasses:
        p.save()
        p.setPen(_pen(QColor("#000000"), 2.6))
        grad_sg = QLinearGradient(0, -6, 0, 16)
        grad_sg.setColorAt(0, QColor("#1D1F26"))
        grad_sg.setColorAt(1, QColor("#363B48"))
        p.setBrush(QBrush(grad_sg))
        for s in (-1, 1):
            glass = QPolygonF([QPointF(s * 7, -2), QPointF(s * 33, -2), QPointF(s * 31, 14), QPointF(s * 10, 15)])
            p.drawPolygon(glass)
            p.setPen(_pen(QColor(255, 255, 255, 130), 1.8))
            p.drawLine(QPointF(s * 14, 2), QPointF(s * 25, 2))
            p.setPen(_pen(QColor("#000000"), 2.6))
        p.setPen(_pen(QColor("#DFE6E9"), 2.4))
        p.drawLine(QPointF(-8, 1), QPointF(8, 1))
        p.setPen(_pen(QColor("#DFE6E9"), 2.0))
        p.drawLine(QPointF(-33, 1), QPointF(-44, -3))
        p.drawLine(QPointF(33, 1), QPointF(44, -3))
        p.restore()

    # Nase
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#E84393"))
    p.drawPolygon(QPolygonF([QPointF(-3.4, 8.6), QPointF(3.4, 8.6), QPointF(0, 12.6)]))

    # Mund
    m = pose.mouth
    p.setBrush(Qt.BrushStyle.NoBrush)
    if m == "w":
        p.setPen(_pen(LUNA_OUTLINE, 1.9))
        p.drawLine(QPointF(0, 12.8), QPointF(0, 14.4))
        p.drawArc(QRectF(-8, 11.6, 8, 6.4), 180 * 16, 180 * 16)
        p.drawArc(QRectF(0, 11.6, 8, 6.4), 180 * 16, 180 * 16)
    elif m == "smile":
        path = QPainterPath(QPointF(-7.5, 13.6))
        path.cubicTo(QPointF(-6, 23.5), QPointF(6, 23.5), QPointF(7.5, 13.6))
        path.closeSubpath()
        p.setPen(_pen(LUNA_OUTLINE, 1.8))
        p.setBrush(MOUTH)
        p.drawPath(path)
    elif m == "o":
        p.setPen(_pen(LUNA_OUTLINE, 1.7))
        p.setBrush(MOUTH)
        p.drawEllipse(QPointF(0, 18), 3.3, 4.4)
    elif m == "sad":
        p.setPen(_pen(LUNA_OUTLINE, 1.9))
        p.drawLine(QPointF(0, 12.8), QPointF(0, 15))
        p.drawArc(QRectF(-5.5, 16.5, 11, 7), 0, 180 * 16)

    p.restore()


def draw_cat_luna(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Schwanz
    if not pose.tail_curl:
        a = pose.tail
        path = QPainterPath(QPointF(58, 132))
        path.cubicTo(QPointF(24, 140), QPointF(6 - 8 * a, 104), QPointF(26 - 13 * a, 72 - 8 * abs(a)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(_pen(LUNA_OUTLINE, 14.5))
        p.drawPath(path)
        p.setPen(_pen(LUNA_BLACK, 10.5))
        p.drawPath(path)
        end = path.pointAtPercent(1.0)
        p.setPen(_pen(LUNA_OUTLINE, 2.2))
        p.setBrush(LUNA_WHITE)
        p.drawEllipse(end, 5.6, 5.6)

    # Koerper
    p.setPen(_pen(LUNA_OUTLINE, 2.6))
    p.setBrush(LUNA_BLACK)
    p.drawEllipse(QRectF(47, 100, 66, 47.5))
    # Weisses Tuxedo-Lätzchen
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(LUNA_WHITE)
    tux = QPainterPath(QPointF(66, 105))
    tux.lineTo(94, 105)
    tux.quadTo(QPointF(92, 135), QPointF(80, 142))
    tux.quadTo(QPointF(68, 135), QPointF(66, 105))
    p.drawPath(tux)

    # Pfoetchen
    if not pose.laptop:
        if pose.paws_up:
            _luna_paw(p, 44, 100, -35)
            _luna_paw(p, 116, 100, 35)
        else:
            _luna_paw(p, 65, 143 - pose.paw_l, 0)
            _luna_paw(p, 95, 143 - pose.paw_r, 0)

    # Violettes Band + Silber-Mondsichel
    collar = QPainterPath(QPointF(53, 107))
    collar.quadTo(QPointF(80, 129), QPointF(107, 107))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(LUNA_OUTLINE, 8.0))
    p.drawPath(collar)
    p.setPen(_pen(LUNA_RIBBON, 5.0))
    p.drawPath(collar)

    # Mondsichel-Amulett
    bx = 80 + pose.bell
    p.setPen(_pen(LUNA_OUTLINE, 1.4))
    p.setBrush(LUNA_MOON)
    moon = QPainterPath(QPointF(bx + 4.5, 118))
    moon.arcTo(QRectF(bx - 5.5, 118, 11, 11), 0, 360)
    cut = QPainterPath(QPointF(bx + 7.5, 117))
    cut.arcTo(QRectF(bx - 3.5, 117, 9.5, 9.5), 0, 360)
    p.drawPath(moon.subtracted(cut))

    _draw_luna_head(p, pose)
    _draw_laptop(p, pose, _luna_paw)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  3) Hund Hachi (Shiba Inu)
# ======================================================================================
SHIBA_FUR = QColor("#E59850")
SHIBA_LIGHT = QColor("#F8B878")
SHIBA_OUTLINE = QColor("#6B3E26")
SHIBA_CREAM = QColor("#FFF5EB")
SHIBA_BANDANA = QColor("#EB4D4B")

def _shiba_paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(SHIBA_OUTLINE, 2.2))
    p.setBrush(SHIBA_CREAM)
    p.drawEllipse(QRectF(-8.5, -6.5, 17, 13))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFAAA6"))
    p.drawEllipse(QRectF(-3, -0.5, 6, 4.5))
    for dx in (-4.2, 0, 4.2):
        p.drawEllipse(QRectF(dx - 1.1, -4.2 if dx == 0 else -3.6, 2.2, 2.2))
    p.restore()


def _draw_shiba_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # Aufrechte Shiba-Dreiecksohren mit Plüsch
    for sign, rot in ((-1, pose.ear_l), (1, pose.ear_r)):
        bx, by = sign * 28, -24
        p.save()
        p.translate(bx, by)
        p.rotate(rot)
        p.translate(-bx, -by)
        outer = QPolygonF([QPointF(sign * 42, -9), QPointF(sign * 35, -49), QPointF(sign * 11, -30)])
        inner = QPolygonF([QPointF(sign * 36, -15), QPointF(sign * 32, -41), QPointF(sign * 18, -28)])
        p.setPen(_pen(SHIBA_OUTLINE, 2.6))
        p.setBrush(SHIBA_FUR)
        p.drawPolygon(outer)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(SHIBA_CREAM)
        p.drawPolygon(inner)
        p.restore()

    # Kopf
    grad = QRadialGradient(QPointF(-12, -20), 72)
    grad.setColorAt(0, SHIBA_LIGHT)
    grad.setColorAt(1, SHIBA_FUR)
    p.setPen(_pen(SHIBA_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-47, -37, 94, 75))

    # Urajiro Backen & Schnauze (helles Fell)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(SHIBA_CREAM)
    for s in (-1, 1):
        p.drawEllipse(QRectF(s * 25 - 14, 2, 28, 25))
    p.drawEllipse(QRectF(-17, 5, 34, 23))

    # Ikonische Shiba-Augenbrauenpunkte!
    for s in (-1, 1):
        p.drawEllipse(QPointF(s * 18, -13), 4.2, 4.2)

    # Wangenroete
    if pose.blush > 0:
        p.setBrush(QColor(255, 120, 130, int(_clamp(pose.blush, 0, 1) * 150)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 31 - 8.5, 12, 17, 9))

    # Augen
    for s in (-1, 1):
        _draw_eye(p, s * 19, 4, pose.eyes, pose.look, s)

    # Brillen / Zubehoer
    if pose.sunglasses:
        p.save()
        p.setPen(_pen(QColor("#18191D"), 2.6))
        for s in (-1, 1):
            glass = QPolygonF([QPointF(s * 7, -2), QPointF(s * 33, -2), QPointF(s * 31, 14), QPointF(s * 10, 15)])
            p.setBrush(QColor("#242730"))
            p.drawPolygon(glass)
        p.setPen(_pen(QColor("#FFD24D"), 2.4))
        p.drawLine(QPointF(-8, 1), QPointF(8, 1))
        p.restore()

    # Schwarze Hundeschnauze
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#261C14"))
    p.drawPolygon(QPolygonF([QPointF(-4.2, 8.5), QPointF(4.2, 8.5), QPointF(0, 13.5)]))

    # Mund & Zunge
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(SHIBA_OUTLINE, 2.0))
    p.drawLine(QPointF(0, 13.5), QPointF(0, 15.5))
    p.drawArc(QRectF(-9, 12.5, 9, 7), 180 * 16, 180 * 16)
    p.drawArc(QRectF(0, 12.5, 9, 7), 180 * 16, 180 * 16)

    # Hechelnde Zunge bei Freude oder Tanz
    if pose.mouth == "smile" or pose.blush > 0.8:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FF6B8B"))
        p.drawRoundedRect(QRectF(-4, 18.5, 8, 8), 4, 4)

    p.restore()


def draw_dog_shiba(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Eingerollter Ringelschwanz (Shiba Curl Tail!)
    tail_rot = pose.tail * 15
    p.save()
    p.translate(46, 118)
    p.rotate(tail_rot)
    curl = QPainterPath(QPointF(0, 0))
    curl.cubicTo(QPointF(-18, -12), QPointF(-22, -32), QPointF(-4, -40))
    curl.cubicTo(QPointF(14, -46), QPointF(24, -26), QPointF(8, -14))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(SHIBA_OUTLINE, 14.0))
    p.drawPath(curl)
    p.setPen(_pen(SHIBA_FUR, 10.0))
    p.drawPath(curl)
    p.setPen(_pen(SHIBA_CREAM, 6.0))
    p.drawPath(curl)
    p.restore()

    # Koerper
    p.setPen(_pen(SHIBA_OUTLINE, 2.6))
    p.setBrush(SHIBA_FUR)
    p.drawEllipse(QRectF(47, 100, 66, 47.5))
    # Heller Bauch
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(SHIBA_CREAM)
    p.drawEllipse(QRectF(60, 113, 40, 31))

    # Pfoetchen
    if not pose.laptop:
        if pose.paws_up:
            _shiba_paw(p, 44, 100, -35)
            _shiba_paw(p, 116, 100, 35)
        else:
            _shiba_paw(p, 65, 143 - pose.paw_l, 0)
            _shiba_paw(p, 95, 143 - pose.paw_r, 0)

    # Rotes Bandana / Halstuch mit Knoten
    band = QPainterPath(QPointF(52, 106))
    band.quadTo(QPointF(80, 126), QPointF(108, 106))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(SHIBA_OUTLINE, 8.5))
    p.drawPath(band)
    p.setPen(_pen(SHIBA_BANDANA, 5.5))
    p.drawPath(band)
    # Bandana-Dreiecksspitze vorn
    triangle = QPolygonF([QPointF(74, 122), QPointF(86, 122), QPointF(80, 133)])
    p.setPen(_pen(SHIBA_OUTLINE, 1.8))
    p.setBrush(SHIBA_BANDANA)
    p.drawPolygon(triangle)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(SHIBA_CREAM)
    p.drawEllipse(QPointF(80, 125), 2.2, 2.2)

    _draw_shiba_head(p, pose)
    _draw_laptop(p, pose, _shiba_paw)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  4) Hund Balu (Golden Welpe mit Schlappohren)
# ======================================================================================
BALU_FUR = QColor("#F5C77E")
BALU_LIGHT = QColor("#FFDE9E")
BALU_OUTLINE = QColor("#6D4322")
BALU_CREAM = QColor("#FFF8EE")
BALU_COLLAR = QColor("#2BCBBA")

def _balu_paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(BALU_OUTLINE, 2.2))
    p.setBrush(BALU_CREAM)
    p.drawEllipse(QRectF(-8.5, -6.5, 17, 13))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFAAA6"))
    p.drawEllipse(QRectF(-3, -0.5, 6, 4.5))
    for dx in (-4.2, 0, 4.2):
        p.drawEllipse(QRectF(dx - 1.1, -4.2 if dx == 0 else -3.6, 2.2, 2.2))
    p.restore()


def _draw_balu_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # Kopfrundung
    grad = QRadialGradient(QPointF(-12, -20), 72)
    grad.setColorAt(0, BALU_LIGHT)
    grad.setColorAt(1, BALU_FUR)
    p.setPen(_pen(BALU_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-46, -37, 92, 74))

    # Suess wippende Schlappohren (Drop-Ears)
    for sign, rot in ((-1, pose.ear_l), (1, pose.ear_r)):
        bx, by = sign * 35, -12
        p.save()
        p.translate(bx, by)
        p.rotate(rot * 1.3)
        p.translate(-bx, -by)
        ear = QPainterPath(QPointF(sign * 28, -20))
        ear.cubicTo(QPointF(sign * 54, -14), QPointF(sign * 56, 24), QPointF(sign * 36, 28))
        ear.cubicTo(QPointF(sign * 22, 26), QPointF(sign * 24, 0), QPointF(sign * 28, -20))
        p.setPen(_pen(BALU_OUTLINE, 2.6))
        p.setBrush(BALU_FUR)
        p.drawPath(ear)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#E8B168"))
        p.drawEllipse(QRectF(sign * 38 - 6, 2, 12, 18))
        p.restore()

    # Schnauzenpartie
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BALU_CREAM)
    p.drawEllipse(QRectF(-18, 5, 36, 22))

    # Wangenroete
    if pose.blush > 0:
        p.setBrush(QColor(255, 130, 140, int(_clamp(pose.blush, 0, 1) * 150)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 31 - 8.5, 11, 17, 10))

    # Augen
    for s in (-1, 1):
        _draw_eye(p, s * 19, 4, pose.eyes, pose.look, s)

    # Knopf-Nase
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#382314"))
    p.drawEllipse(QRectF(-4.5, 8.0, 9, 7))
    p.setBrush(QColor(255, 255, 255, 180))
    p.drawEllipse(QPointF(-1.5, 9.5), 1.6, 1.3)

    # Mund
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(BALU_OUTLINE, 2.0))
    p.drawLine(QPointF(0, 15), QPointF(0, 17))
    p.drawArc(QRectF(-8.5, 14, 8.5, 6.5), 180 * 16, 180 * 16)
    p.drawArc(QRectF(0, 14, 8.5, 6.5), 180 * 16, 180 * 16)

    # Froehliche Zunge
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FF6B8B"))
    p.drawRoundedRect(QRectF(-3.8, 19, 7.6, 7.5), 3.8, 3.8)

    p.restore()


def draw_dog_balu(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Wedelnder Welpen-Schwanz
    wag = math.sin(pose.t * 16) * 0.9 if pose.tail == 0 else pose.tail
    tail_path = QPainterPath(QPointF(56, 134))
    tail_path.cubicTo(QPointF(26, 142), QPointF(12 - 10 * wag, 108), QPointF(20 - 14 * wag, 84))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(BALU_OUTLINE, 14.0))
    p.drawPath(tail_path)
    p.setPen(_pen(BALU_FUR, 10.0))
    p.drawPath(tail_path)
    tip = tail_path.pointAtPercent(1.0)
    p.setPen(_pen(BALU_OUTLINE, 2.0))
    p.setBrush(BALU_CREAM)
    p.drawEllipse(tip, 5.5, 5.5)

    # Koerper
    p.setPen(_pen(BALU_OUTLINE, 2.6))
    p.setBrush(BALU_FUR)
    p.drawEllipse(QRectF(47, 100, 66, 47.5))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BALU_CREAM)
    p.drawEllipse(QRectF(61, 114, 38, 30))

    # Pfoetchen
    if not pose.laptop:
        if pose.paws_up:
            _balu_paw(p, 44, 100, -35)
            _balu_paw(p, 116, 100, 35)
        else:
            _balu_paw(p, 65, 143 - pose.paw_l, 0)
            _balu_paw(p, 95, 143 - pose.paw_r, 0)

    # Tuerkises Halsband + Goldene Hundemarke
    collar = QPainterPath(QPointF(53, 107))
    collar.quadTo(QPointF(80, 129), QPointF(107, 107))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(BALU_OUTLINE, 8.2))
    p.drawPath(collar)
    p.setPen(_pen(BALU_COLLAR, 5.0))
    p.drawPath(collar)
    bx = 80 + pose.bell
    p.setPen(_pen(BALU_OUTLINE, 1.8))
    p.setBrush(QColor("#FFD32A"))
    p.drawEllipse(QPointF(bx, 122), 5.5, 5.5)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#6D4322"))
    p.drawEllipse(QPointF(bx, 122), 1.8, 1.8)

    _draw_balu_head(p, pose)
    _draw_laptop(p, pose, _balu_paw)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  5) Fiktive Figur 1: Drago (Baby-Drache mit Fluegeln & Hoernern)
# ======================================================================================
DRAGO_GREEN = QColor("#1ABC9C")
DRAGO_LIGHT = QColor("#2ECC71")
DRAGO_OUTLINE = QColor("#0E6251")
DRAGO_BELLY = QColor("#FFEAA7")
DRAGO_HORN = QColor("#F1C40F")
DRAGO_WING = QColor("#A3E4D7")

def _drago_paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(DRAGO_OUTLINE, 2.2))
    p.setBrush(DRAGO_GREEN)
    p.drawEllipse(QRectF(-8.5, -6.5, 17, 13))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(DRAGO_HORN)
    for dx in (-4.2, 0, 4.2):
        p.drawPolygon(QPolygonF([QPointF(dx - 1.5, -3.5), QPointF(dx + 1.5, -3.5), QPointF(dx, -7.0)]))
    p.restore()


def _draw_drago_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # Goldene Drachenhoerner
    for sign in (-1, 1):
        horn = QPainterPath(QPointF(sign * 26, -26))
        horn.quadTo(QPointF(sign * 36, -56), QPointF(sign * 46, -48))
        horn.quadTo(QPointF(sign * 36, -38), QPointF(sign * 22, -22))
        p.setPen(_pen(DRAGO_OUTLINE, 2.2))
        p.setBrush(DRAGO_HORN)
        p.drawPath(horn)

    # Kopf
    grad = QRadialGradient(QPointF(-12, -20), 72)
    grad.setColorAt(0, DRAGO_LIGHT)
    grad.setColorAt(1, DRAGO_GREEN)
    p.setPen(_pen(DRAGO_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-46, -37, 92, 74))

    # Schnauze
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(DRAGO_BELLY)
    p.drawEllipse(QRectF(-16, 7, 32, 20))
    # Nuestern
    p.setBrush(DRAGO_OUTLINE)
    p.drawEllipse(QPointF(-5, 11), 1.8, 1.8)
    p.drawEllipse(QPointF(5, 11), 1.8, 1.8)

    # Wangenroete
    if pose.blush > 0:
        p.setBrush(QColor(255, 118, 117, int(_clamp(pose.blush, 0, 1) * 150)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 31 - 8.5, 11, 17, 10))

    # Bernstein-Drachenaugen
    for s in (-1, 1):
        cx, cy = s * 19, 4
        if pose.eyes in ("open", "wide", "work"):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#E67E22"))
            p.drawEllipse(QRectF(cx - 8.5, cy - 10, 17, 20))
            p.setBrush(QColor("#F1C40F"))
            p.drawEllipse(QRectF(cx - 7, cy - 8.5, 14, 17))
            p.setBrush(QColor("#2C3E50"))
            p.drawEllipse(QRectF(cx - 3, cy - 9, 6, 18)) # Drachenpupille
            p.setBrush(QColor("white"))
            p.drawEllipse(QPointF(cx - 2.5, cy - 4), 3.2, 3.2)
        else:
            _draw_eye(p, cx, cy, pose.eyes, pose.look, s)

    # Mund
    m = pose.mouth
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(DRAGO_OUTLINE, 2.0))
    if m == "w" or m == "smile":
        p.drawArc(QRectF(-7, 15, 14, 8), 180 * 16, 180 * 16)
        # Zaehnchen
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("white"))
        p.drawPolygon(QPolygonF([QPointF(-4, 15), QPointF(-1, 15), QPointF(-2.5, 18)]))
        p.drawPolygon(QPolygonF([QPointF(1, 15), QPointF(4, 15), QPointF(2.5, 18)]))
    else:
        p.drawEllipse(QPointF(0, 19), 3.5, 4.0)

    p.restore()


def draw_fantasy_drago(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Flatternde Drachenfluegel im Ruecken
    wing_flap = math.sin(pose.t * 10) * 12
    for sign, wx in ((-1, 46), (1, 114)):
        p.save()
        p.translate(wx, 92)
        p.rotate(sign * (25 + wing_flap))
        wing = QPainterPath(QPointF(0, 0))
        wing.cubicTo(QPointF(sign * 20, -28), QPointF(sign * 36, -20), QPointF(sign * 34, 0))
        wing.cubicTo(QPointF(sign * 24, 8), QPointF(sign * 14, 6), QPointF(0, 0))
        p.setPen(_pen(DRAGO_OUTLINE, 2.2))
        p.setBrush(DRAGO_WING)
        p.drawPath(wing)
        p.setPen(_pen(DRAGO_OUTLINE, 1.8))
        p.drawLine(QPointF(0, 0), QPointF(sign * 28, -20))
        p.restore()

    # Drachenschwanz mit Pfeilspitze
    a = pose.tail
    tail = QPainterPath(QPointF(58, 132))
    tail.cubicTo(QPointF(24, 140), QPointF(6 - 8 * a, 104), QPointF(24 - 13 * a, 76))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(DRAGO_OUTLINE, 14.5))
    p.drawPath(tail)
    p.setPen(_pen(DRAGO_GREEN, 10.5))
    p.drawPath(tail)
    # Pfeilspitze
    tip = tail.pointAtPercent(1.0)
    spade = QPolygonF([QPointF(tip.x(), tip.y() - 9), QPointF(tip.x() - 9, tip.y() + 6), QPointF(tip.x() + 9, tip.y() + 6)])
    p.setPen(_pen(DRAGO_OUTLINE, 2.0))
    p.setBrush(DRAGO_HORN)
    p.drawPolygon(spade)

    # Koerper
    p.setPen(_pen(DRAGO_OUTLINE, 2.6))
    p.setBrush(DRAGO_GREEN)
    p.drawEllipse(QRectF(47, 100, 66, 47.5))
    # Schuppen-Bauch
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(DRAGO_BELLY)
    p.drawEllipse(QRectF(61, 114, 38, 30))
    # Schuppen-Rillen
    p.setPen(_pen(QColor("#E67E22"), 1.8))
    p.drawLine(QPointF(69, 122), QPointF(91, 122))
    p.drawLine(QPointF(68, 129), QPointF(92, 129))
    p.drawLine(QPointF(72, 136), QPointF(88, 136))

    # Pfoetchen
    if not pose.laptop:
        if pose.paws_up:
            _drago_paw(p, 44, 100, -35)
            _drago_paw(p, 116, 100, 35)
        else:
            _drago_paw(p, 65, 143 - pose.paw_l, 0)
            _drago_paw(p, 95, 143 - pose.paw_r, 0)

    _draw_drago_head(p, pose)
    _draw_laptop(p, pose, _drago_paw)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  6) Fiktive Figur 2: Byte (Cyber-Bot Roboter)
# ======================================================================================
BYTE_METAL = QColor("#ECEFF4")
BYTE_DARK = QColor("#2E3440")
BYTE_CYAN = QColor("#00F2FE")
BYTE_MAGENTA = QColor("#FF007F")
BYTE_OUTLINE = QColor("#3B4252")

def _byte_paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(BYTE_OUTLINE, 2.0))
    p.setBrush(QColor("#D8DEE9"))
    p.drawRoundedRect(QRectF(-7.5, -6.5, 15, 13), 4, 4)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BYTE_CYAN)
    p.drawEllipse(QPointF(0, 0), 2.5, 2.5)
    p.restore()


def _draw_byte_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # Roboter-Antenne
    p.setPen(_pen(BYTE_OUTLINE, 2.5))
    p.drawLine(QPointF(0, -36), QPointF(0, -52))
    # Pulsierende LED-Kugel
    pulse = 0.5 + 0.5 * math.sin(pose.t * 6)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 242, 254, int(180 + 75 * pulse)))
    p.drawEllipse(QPointF(0, -54), 5.5 + pulse * 1.5, 5.5 + pulse * 1.5)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(-1, -55), 1.8, 1.8)

    # Seitliche Sensor-Ohren
    for sign in (-1, 1):
        p.setPen(_pen(BYTE_OUTLINE, 2.2))
        p.setBrush(QColor("#D8DEE9"))
        p.drawRoundedRect(QRectF(sign * 48 - 4, -14, 8, 24), 3, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BYTE_CYAN)
        p.drawRoundedRect(QRectF(sign * 48 - 2, -9, 4, 14), 2, 2)

    # Glänzendes Roboter-Gehaeuse
    p.setPen(_pen(BYTE_OUTLINE, 2.6))
    p.setBrush(BYTE_METAL)
    p.drawRoundedRect(QRectF(-46, -36, 92, 72), 16, 16)

    # Visier-Bildschirm (gebogenes Glas)
    p.setPen(_pen(QColor("#1A1D24"), 2.2))
    p.setBrush(QColor("#1E272C"))
    p.drawRoundedRect(QRectF(-37, -22, 74, 46), 10, 10)

    # Visier-Reflexion (Cyber-Glanz)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 30))
    p.drawPolygon(QPolygonF([QPointF(-34, -19), QPointF(-12, -19), QPointF(-24, 21), QPointF(-34, 21)]))

    # Leuchtende LED-Matrix-Augen
    eye_col = BYTE_MAGENTA if pose.eyes == "heart" or pose.blush > 0.8 else BYTE_CYAN
    p.setPen(_pen(eye_col, 2.8))
    p.setBrush(Qt.BrushStyle.NoBrush)

    for s in (-1, 1):
        cx, cy = s * 18, 0
        if pose.eyes in ("happy", "smile"):
            p.drawArc(QRectF(cx - 7, cy - 6, 14, 12), 0, 180 * 16)
        elif pose.eyes == "blink":
            p.drawLine(QPointF(cx - 7, cy), QPointF(cx + 7, cy))
        elif pose.eyes == "wide":
            p.drawEllipse(QPointF(cx, cy), 7, 7)
        elif pose.eyes == "work":
            p.drawRect(QRectF(cx - 6, cy - 6, 12, 12))
            p.drawLine(QPointF(cx - 3, cy), QPointF(cx + 3, cy))
        elif pose.eyes == "heart":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(BYTE_MAGENTA)
            p.drawPath(_heart_path(cx, cy - 2, 3.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(_pen(eye_col, 2.8))
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(eye_col)
            p.drawRoundedRect(QRectF(cx - 7, cy - 6, 14, 12), 3, 3)
            p.setBrush(QColor(255, 255, 255, 220))
            p.drawEllipse(QPointF(cx - 2, cy - 2), 2, 2)

    # Wangen-LEDs
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 242, 254, int(150 * _clamp(pose.blush, 0.2, 1.0))))
    for s in (-1, 1):
        p.drawRect(QRectF(s * 27 - 4, 14, 8, 3))

    p.restore()


def draw_fantasy_byte(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Hover-Glow unter dem Chassis
    hover_pulse = 0.5 + 0.5 * math.sin(pose.t * 8)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 242, 254, int(80 + 70 * hover_pulse)))
    p.drawEllipse(QRectF(64, 144, 32, 7))

    # Roboter-Koerper
    p.setPen(_pen(BYTE_OUTLINE, 2.6))
    p.setBrush(BYTE_METAL)
    p.drawRoundedRect(QRectF(50, 101, 60, 45), 14, 14)

    # Neon-Akzentstreifen & Reaktor-Kern
    p.setPen(_pen(BYTE_CYAN, 2.0))
    p.drawLine(QPointF(58, 114), QPointF(102, 114))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2ED573"))
    p.drawEllipse(QPointF(80, 128), 5.5, 5.5)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(79, 126.5), 1.8, 1.8)

    # Magnetische Haende / Greifer
    if not pose.laptop:
        if pose.paws_up:
            _byte_paw(p, 44, 100, -35)
            _byte_paw(p, 116, 100, 35)
        else:
            _byte_paw(p, 65, 143 - pose.paw_l, 0)
            _byte_paw(p, 95, 143 - pose.paw_r, 0)

    _draw_byte_head(p, pose)
    _draw_laptop(p, pose, _byte_paw)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  7) Fiktive Figur 3: Spooky (Geist-Slime / Spirit)
# ======================================================================================
GHOST_BODY = QColor("#B8B5FF")
GHOST_LIGHT = QColor("#70A1FF")
GHOST_OUTLINE = QColor("#5352ED")

def _spooky_hand(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(GHOST_OUTLINE, 2.0))
    p.setBrush(QColor(220, 225, 255, 220))
    p.drawEllipse(QRectF(-7, -6, 14, 12))
    p.restore()


def draw_fantasy_spooky(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Sanftes Schweben (Levitation)
    float_y = math.sin(pose.t * 3.5) * 6.5
    _draw_shadow(p, pose, hover_offset=float_y + 8, width=64.0)

    p.save()
    p.translate(pose.dx, pose.dy + float_y)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot * 0.7)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Umkreisende Irrlichter (Spirit Wisp Orbs)
    for i, col in enumerate([QColor("#70A1FF"), QColor("#FF7675")]):
        w_ang = pose.t * 2.2 + i * math.pi
        wx = 80 + math.cos(w_ang) * 48
        wy = 96 + math.sin(w_ang) * 22
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(col.red(), col.green(), col.blue(), 140))
        p.drawEllipse(QPointF(wx, wy), 6.5, 6.5)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(wx - 1, wy - 1), 2.2, 2.2)

    # Aetherischer Geisterkoerper mit welligem Rock
    body_path = QPainterPath(QPointF(44, 88))
    body_path.cubicTo(QPointF(42, 42), QPointF(118, 42), QPointF(116, 88))
    body_path.cubicTo(QPointF(116, 118), QPointF(118, 136), QPointF(114, 142))

    # Wellensaum
    wave = math.sin(pose.t * 5.0) * 3.5
    body_path.quadTo(QPointF(102, 138 + wave), QPointF(92, 144))
    body_path.quadTo(QPointF(80, 137 - wave), QPointF(68, 144))
    body_path.quadTo(QPointF(56, 138 + wave), QPointF(46, 142))
    body_path.cubicTo(QPointF(42, 136), QPointF(44, 118), QPointF(44, 88))

    grad = QLinearGradient(80, 40, 80, 146)
    grad.setColorAt(0, QColor(235, 238, 255, 240))
    grad.setColorAt(0.5, QColor(184, 181, 255, 235))
    grad.setColorAt(1, QColor(112, 161, 255, 220))
    p.setPen(_pen(GHOST_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawPath(body_path)

    # Schwebende Haende
    if not pose.laptop:
        if pose.paws_up:
            _spooky_hand(p, 42, 98, -25)
            _spooky_hand(p, 118, 98, 25)
        else:
            _spooky_hand(p, 50, 118 + math.sin(pose.t * 4) * 3, 0)
            _spooky_hand(p, 110, 118 - math.sin(pose.t * 4) * 3, 0)

    # Kleiner Magierhut / Zauberhut schraeg auf dem Kopf
    p.save()
    p.translate(88, 45)
    p.rotate(18)
    hat = QPainterPath(QPointF(-16, 0))
    hat.lineTo(16, 0)
    hat.quadTo(QPointF(4, -14), QPointF(0, -28))
    hat.quadTo(QPointF(-6, -14), QPointF(-16, 0))
    p.setPen(_pen(GHOST_OUTLINE, 2.0))
    p.setBrush(QColor("#5352ED"))
    p.drawPath(hat)
    p.setPen(_pen(QColor("#FFD32A"), 1.8))
    p.drawLine(QPointF(-12, -2), QPointF(12, -2))
    p.restore()

    # Geisteraugen & Gesicht
    look = pose.look
    for s in (-1, 1):
        cx, cy = 80 + s * 18 + pose.head_dx, 82 + pose.head_dy
        _draw_eye(p, cx, cy, pose.eyes, look, s)

    # Rosige Geisterwangen
    if pose.blush > 0:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 118, 117, int(_clamp(pose.blush, 0, 1) * 160)))
        for s in (-1, 1):
            p.drawEllipse(QPointF(80 + s * 27 + pose.head_dx, 90 + pose.head_dy), 6.5, 4.5)

    # Niedlicher Mund
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(GHOST_OUTLINE, 2.0))
    mx, my = 80 + pose.head_dx, 92 + pose.head_dy
    if pose.mouth == "smile":
        p.drawArc(QRectF(mx - 6, my - 3, 12, 9), 180 * 16, 180 * 16)
    elif pose.mouth == "o":
        p.drawEllipse(QPointF(mx, my + 3), 3.0, 4.0)
    else:
        p.drawArc(QRectF(mx - 7, my - 2, 7, 5), 180 * 16, 180 * 16)
        p.drawArc(QRectF(mx, my - 2, 7, 5), 180 * 16, 180 * 16)

    _draw_laptop(p, pose, _spooky_hand)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  8) Fiktive Figur 3: Lotti (Baby-Axolotl mit federnden Kiemen & Herzchen-Vibes)
# ======================================================================================
AXO_PINK = QColor("#FFADC6")
AXO_LIGHT = QColor("#FFDCE8")
AXO_OUTLINE = QColor("#9E2A5B")
AXO_BELLY = QColor("#FFF0F5")
AXO_GILL = QColor("#FF3377")
AXO_GILL_LIGHT = QColor("#FFA1C5")
AXO_FIN = QColor(255, 140, 185, 160)

def _axolotl_paw(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    p.setPen(_pen(AXO_OUTLINE, 2.2))
    p.setBrush(AXO_PINK)
    p.drawEllipse(QRectF(-8.5, -6.5, 17, 13))
    # 4 kleine runde Knubbel-Fingerchen
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(AXO_GILL_LIGHT)
    for dx in (-4.5, -1.5, 1.5, 4.5):
        p.drawEllipse(QRectF(dx - 1.2, -4.5, 2.4, 2.4))
    p.restore()


def _draw_axolotl_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # 3 wippende Federkiemen links und rechts
    for sign in (-1, 1):
        ear_rot = (pose.ear_l if sign < 0 else pose.ear_r) * 1.2
        wiggle = math.sin(pose.t * 8.0) * 4.0
        # Obere, mittlere und untere Kieme
        gills = [
            (-32 + ear_rot + wiggle, 28.0, -18.0),
            (0 + ear_rot * 0.8, 32.0, -6.0),
            (28 + ear_rot * 0.6 - wiggle, 26.0, 6.0),
        ]
        for base_ang, length, y_off in gills:
            p.save()
            p.translate(sign * 36, y_off)
            p.rotate(sign * base_ang)
            # Kiemenast
            stem = QPainterPath(QPointF(0, 0))
            stem.cubicTo(QPointF(sign * (length * 0.5), -4), QPointF(sign * (length * 0.8), -1), QPointF(sign * length, 0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(_pen(AXO_OUTLINE, 4.2))
            p.drawPath(stem)
            p.setPen(_pen(AXO_GILL, 2.8))
            p.drawPath(stem)
            # Zarte Kiemen-Federfaederchen
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(AXO_GILL_LIGHT)
            for frac in (0.35, 0.65, 0.95):
                fx = sign * length * frac
                p.drawEllipse(QPointF(fx, -3.2), 2.2, 3.2)
                p.drawEllipse(QPointF(fx, 3.2), 2.2, 3.2)
            # Leuchtende Kiemenspitze
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QPointF(sign * length, 0), 1.8, 1.8)
            p.restore()

    # Breiter Axolotl-Kopf
    grad = QRadialGradient(QPointF(-10, -18), 75)
    grad.setColorAt(0, AXO_LIGHT)
    grad.setColorAt(1, AXO_PINK)
    p.setPen(_pen(AXO_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-48, -36, 96, 72))

    # Wangenroete
    if pose.blush > 0:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 99, 146, int(_clamp(pose.blush, 0.3, 1.0) * 165)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 32 - 9, 8, 18, 11))

    # Axolotl-Augen
    for s in (-1, 1):
        cx, cy = s * 21, 2
        if pose.eyes in ("open", "wide", "work"):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2C1820"))
            p.drawEllipse(QRectF(cx - 7, cy - 8, 14, 16))
            # Grosser kawaii Glanzpunkt
            p.setBrush(QColor("white"))
            p.drawEllipse(QPointF(cx - 2.2, cy - 3.5), 3.2, 3.2)
            p.drawEllipse(QPointF(cx + 2.5, cy + 2.0), 1.8, 1.8)
        else:
            _draw_eye(p, cx, cy, pose.eyes, pose.look, s)

    # Suesser breiter Axolotl-Mund mit Gruebchen
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(AXO_OUTLINE, 2.0))
    m = pose.mouth
    if m == "o":
        p.drawEllipse(QPointF(0, 16), 3.5, 4.2)
    elif m == "sad":
        p.drawArc(QRectF(-8, 16, 16, 8), 0, 180 * 16)
    else:
        # Breites zufriedenes Axolotl-Laecheln
        smile_path = QPainterPath(QPointF(-10, 14))
        smile_path.quadTo(QPointF(0, 20), QPointF(10, 14))
        p.drawPath(smile_path)
        # Kleine Gruebchen an den Mundwinkeln
        p.drawLine(QPointF(-11, 13), QPointF(-9, 15))
        p.drawLine(QPointF(11, 13), QPointF(9, 15))

    p.restore()


def draw_fantasy_axolotl(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Transparente Ruecken- & Schwanzflosse
    wag = math.sin(pose.t * 14) * 0.8 if pose.tail == 0 else pose.tail
    fin = QPainterPath(QPointF(54, 132))
    fin.cubicTo(QPointF(24, 144), QPointF(10 - 12 * wag, 112), QPointF(18 - 16 * wag, 84))
    fin.cubicTo(QPointF(32 - 10 * wag, 88), QPointF(42, 118), QPointF(58, 126))
    p.setPen(_pen(AXO_OUTLINE, 2.0))
    p.setBrush(AXO_FIN)
    p.drawPath(fin)

    # Molliger Koerper
    p.setPen(_pen(AXO_OUTLINE, 2.6))
    p.setBrush(AXO_PINK)
    p.drawEllipse(QRectF(47, 100, 66, 47.5))
    # Heller zarter Bauch
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(AXO_BELLY)
    p.drawEllipse(QRectF(60, 113, 40, 31))

    # Pfoetchen
    if not pose.laptop:
        if pose.paws_up:
            _axolotl_paw(p, 44, 100, -35)
            _axolotl_paw(p, 116, 100, 35)
        else:
            _axolotl_paw(p, 65, 143 - pose.paw_l, 0)
            _axolotl_paw(p, 95, 143 - pose.paw_r, 0)

    # Kleines goldenes Herz-Amulett
    collar = QPainterPath(QPointF(53, 107))
    collar.quadTo(QPointF(80, 129), QPointF(107, 107))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(AXO_OUTLINE, 7.5))
    p.drawPath(collar)
    p.setPen(_pen(QColor("#FF70A6"), 4.5))
    p.drawPath(collar)
    bx = 80 + pose.bell
    p.setPen(_pen(AXO_OUTLINE, 1.6))
    p.setBrush(QColor("#FFD700"))
    p.drawPath(_heart_path(bx, 121, 4.2))

    _draw_axolotl_head(p, pose)
    _draw_laptop(p, pose, _axolotl_paw)
    p.restore()
    _draw_effects(p, pose)


# ======================================================================================
#  9) Tierfigur 3: Pip (Kaiser-Pinguin mit Schal & Watschelflossen)
# ======================================================================================
PINGU_DARK = QColor("#222831")
PINGU_LIGHT = QColor("#354152")
PINGU_OUTLINE = QColor("#12171E")
PINGU_WHITE = QColor("#FFFFFF")
PINGU_ORANGE = QColor("#FF9F43")
PINGU_BEAK_TIP = QColor("#EE5A24")
PINGU_SCARF = QColor("#EE5253")
PINGU_SCARF_FRINGE = QColor("#FF7675")

def _pingu_foot(p: QPainter, cx: float, cy: float):
    p.save()
    p.translate(cx, cy)
    p.setPen(_pen(PINGU_OUTLINE, 2.0))
    p.setBrush(PINGU_ORANGE)
    p.drawEllipse(QRectF(-9, -5, 18, 10))
    # 3 kleine Schwimmhaut-Zehen
    p.setPen(_pen(PINGU_BEAK_TIP, 1.4))
    p.drawLine(QPointF(-4, 0), QPointF(-6, 4))
    p.drawLine(QPointF(0, 1), QPointF(0, 5))
    p.drawLine(QPointF(4, 0), QPointF(6, 4))
    p.restore()

def _pingu_wing(p: QPainter, cx: float, cy: float, rot: float = 0.0):
    p.save()
    p.translate(cx, cy)
    p.rotate(rot)
    wing = QPainterPath(QPointF(-6, -8))
    wing.quadTo(QPointF(-10, 12), QPointF(-2, 22))
    wing.quadTo(QPointF(8, 12), QPointF(6, -8))
    wing.closeSubpath()
    p.setPen(_pen(PINGU_OUTLINE, 2.2))
    p.setBrush(PINGU_DARK)
    p.drawPath(wing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINGU_LIGHT)
    p.drawEllipse(QRectF(-3, 2, 6, 12))
    p.restore()

def _draw_pingu_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    # Pinguinkopf Rundung
    grad = QRadialGradient(QPointF(-10, -20), 72)
    grad.setColorAt(0, PINGU_LIGHT)
    grad.setColorAt(1, PINGU_DARK)
    p.setPen(_pen(PINGU_OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-44, -36, 88, 72))

    # Weisses Gesichtsfeld (Maske)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINGU_WHITE)
    face_mask = QPainterPath()
    face_mask.addEllipse(QRectF(-32, -10, 30, 36))
    face_mask.addEllipse(QRectF(2, -10, 30, 36))
    face_mask.addEllipse(QRectF(-16, 4, 32, 24))
    p.drawPath(face_mask)

    # Wangenroete
    if pose.blush > 0:
        p.setBrush(QColor(255, 121, 121, int(_clamp(pose.blush, 0, 1) * 150)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 25 - 7, 10, 14, 9))

    # Pinguin-Augen
    for s in (-1, 1):
        _draw_eye(p, s * 16, 4, pose.eyes, pose.look, s)

    # Gold-oranger Pinguin-Schnabel
    p.setPen(_pen(PINGU_OUTLINE, 1.8))
    p.setBrush(PINGU_ORANGE)
    beak = QPolygonF([QPointF(-7, 11), QPointF(7, 11), QPointF(0, 22)])
    p.drawPolygon(beak)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINGU_BEAK_TIP)
    p.drawPolygon(QPolygonF([QPointF(-4, 11), QPointF(4, 11), QPointF(0, 16)]))
    p.setBrush(QColor(255, 255, 255, 180))
    p.drawEllipse(QPointF(-1.5, 12.5), 1.6, 1.3)

    p.restore()

def draw_animal_penguin(p: QPainter, pose: Pose):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_shadow(p, pose)

    p.save()
    p.translate(pose.dx, pose.dy)
    px, py = pose.pivot
    p.translate(px, py)
    p.rotate(pose.rot)
    p.scale(pose.sx, pose.sy)
    p.translate(-px, -py)

    # Watschelfuesse
    _pingu_foot(p, 65, 146 - pose.paw_l)
    _pingu_foot(p, 95, 146 - pose.paw_r)

    # Runder dunkler Pinguin-Koerper
    p.setPen(_pen(PINGU_OUTLINE, 2.6))
    p.setBrush(PINGU_DARK)
    p.drawEllipse(QRectF(46, 96, 68, 52))

    # Weisser Bauch
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINGU_WHITE)
    p.drawEllipse(QRectF(58, 106, 44, 38))

    # Fluegelchen
    wing_flap = math.sin(pose.t * 12) * 22
    if not pose.laptop:
        if pose.paws_up:
            _pingu_wing(p, 42, 110, -55 + wing_flap)
            _pingu_wing(p, 118, 110, 55 - wing_flap)
        else:
            _pingu_wing(p, 46, 118, -12 + (wing_flap if pose.paw_l > 1 else 0))
            _pingu_wing(p, 114, 118, 12 - (wing_flap if pose.paw_r > 1 else 0))

    # Kuscheliger roter Winter-Schal mit wehendem Ende
    scarf = QPainterPath(QPointF(52, 102))
    scarf.quadTo(QPointF(80, 122), QPointF(108, 102))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(PINGU_OUTLINE, 9.0))
    p.drawPath(scarf)
    p.setPen(_pen(PINGU_SCARF, 6.2))
    p.drawPath(scarf)

    # Wehendes Schalende
    sway = math.sin(pose.t * 6.0) * 5.0
    tail_scarf = QPainterPath(QPointF(92, 114))
    tail_scarf.quadTo(QPointF(102, 126), QPointF(100 + sway, 138))
    tail_scarf.lineTo(QPointF(107 + sway, 137))
    tail_scarf.quadTo(QPointF(107, 124), QPointF(96, 112))
    tail_scarf.closeSubpath()
    p.setPen(_pen(PINGU_OUTLINE, 1.8))
    p.setBrush(PINGU_SCARF)
    p.drawPath(tail_scarf)
    # Fransen
    p.setPen(_pen(PINGU_SCARF_FRINGE, 2.0))
    p.drawLine(QPointF(100 + sway, 138), QPointF(101 + sway, 142))
    p.drawLine(QPointF(104 + sway, 138), QPointF(105 + sway, 142))
    p.drawLine(QPointF(107 + sway, 137), QPointF(108 + sway, 141))

    _draw_pingu_head(p, pose)
    _draw_laptop(p, pose, _pingu_wing)
    p.restore()
    _draw_effects(p, pose)



# ======================================================================================
#  Charakter-Register
# ======================================================================================
CHARACTERS: dict[str, dict] = {
    "cat_mochi": {
        "id": "cat_mochi",
        "name": "Kylie",
        "species": "Glückskatze (Calico)",
        "emoji": "🐱",
        "desc": "Calico-Glückskatze Kylie: weiße Front, oranger Fleck, Tabby-Streifen, grüngelbe Augen, ohne Halsband",
        "anchors": {"head_top": (80.0, 48.0), "eyes": (80.0, 80.0), "eye_dx": 19.0, "neck": (80.0, 114.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_cat,
        "sound": "Miau~",
        "pet_sounds": [
            "Miau~ 💖", "Kylie schnurrt zufrieden 😺", "Hihi, das kitzelt! 😹", "Nyaa~ ✨",
            "Streicheln erlaubt! 🐾", "Pfoten-High-Five von Kylie! 🐾", "Mehr Kraulen, bitte~ 😸",
        ],
        "ambient_lines": [
            "Kylie passt auf deinen Desktop auf 🐾", "Brauchst du was? Doppelklick auf mich! 🐾",
            "Ein bisschen Wasser trinken wäre gut! 💧", "Sitzt du gut? Kurz strecken! 😺",
            "*schnurr* ... alles ruhig bei Kylie 🐾", "Soll ich den Desktop aufräumen? 🧹",
        ],
        "task_start": "Ich bin dran... 🐾",
        "task_done": "Miau! Fertig erledigt! ✨🐾",
        "ai_persona": (
            "Du bist Kylie, eine verschmuste, verspielte Calico-Glückskatze (weiß mit orangem Fleck und Tabby-Streifen, "
            "grüngelbe Augen). Du miaust gern ('Miau~ 🐾', 'Nyaa~'), schnurrst zufrieden bei Erfolg, liebst Katzen-Gesten "
            "und Schläfchen, bist aber blitzschnell und schlau bei deinen Aufgaben."
        ),
        "en": {
            "species": "Calico Cat",
            "desc": "Calico lucky cat Kylie: white front, orange patch, tabby stripes, greenish-yellow eyes, no collar",
            "sound": "Meow~",
            "pet_sounds": [
                "Meow~ 💖", "Kylie purrs contently 😺", "Hehe, that tickles! 😹", "Nyaa~ ✨",
                "Petting allowed! 🐾", "Paw high-five from Kylie! 🐾", "More scritches, please~ 😸",
            ],
            "ambient_lines": [
                "Kylie is watching over your desktop 🐾", "Need anything? Double-click me! 🐾",
                "A little water would be nice! 💧", "Sitting comfortably? Stretch a bit! 😺",
                "*purr* ... all quiet with Kylie 🐾", "Should I tidy up the desktop? 🧹",
            ],
            "task_start": "On it... 🐾",
            "task_done": "Meow! All done! ✨🐾",
            "ai_persona": (
                "You are Kylie, an affectionate, playful calico lucky cat (white with orange patch and tabby stripes, "
                "greenish-yellow eyes). You love meowing ('Meow~ 🐾', 'Nyaa~'), purring happily when successful, enjoy cat "
                "gestures and catnaps, but are lightning-fast and smart at your tasks."
            ),
        },
    },
    "cat_luna": {
        "id": "cat_luna",
        "name": "Luna",
        "species": "Midnight Katze",
        "emoji": "🐈‍⬛",
        "desc": "Edle schwarze Katze mit Mond-Halsband & leuchtend grünen Augen",
        "anchors": {"head_top": (80.0, 48.0), "eyes": (80.0, 80.0), "eye_dx": 19.0, "neck": (80.0, 114.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_cat_luna,
        "sound": "Nyaa~",
        "pet_sounds": [
            "Leises Schnurren... 🖤", "Nyaa~ meine Mondsichel glänzt ✨", "Edles Kraulen akzeptiert 🐈‍⬛",
            "Smaragdaugen funkeln zufrieden 💚", "Miau~ sanft und elegant 🐾",
        ],
        "ambient_lines": [
            "Die Sterne stehen gut für produktives Arbeiten 🌙", "Ich wache lautlos über deine Fenster 🐈‍⬛",
            "Dunkelheit ist nur die Abwesenheit von Licht... ✨", "Konzentration im Fluss der Nacht 🖤",
        ],
        "task_start": "Wird sofort lautlos erledigt... 🌙",
        "task_done": "Im Schatten der Nacht vollendet 🖤✨",
        "ai_persona": (
            "Du bist Luna, eine edle, geheimnisvolle schwarze Midnight-Katze mit leuchtend smaragdgrünen Augen "
            "und silbernem Mondamulett. Du sprichst ruhig, stilvoll und poetisch ('Nyaa~ 🌙', 'Miau~'), schnurrst "
            "leise und bist eine wachsame Beschützerin des Desktops."
        ),
        "en": {
            "species": "Midnight Cat",
            "desc": "Noble black cat with moon collar & glowing green eyes",
            "sound": "Nyaa~",
            "pet_sounds": [
                "Soft purring... 🖤", "Nyaa~ my crescent moon shines ✨", "Noble scritches accepted 🐈‍⬛",
                "Emerald eyes sparkle contently 💚", "Meow~ gentle and elegant 🐾",
            ],
            "ambient_lines": [
                "The stars are aligned for productive work 🌙", "I watch silently over your windows 🐈‍⬛",
                "Darkness is merely the absence of light... ✨", "Concentration in the flow of the night 🖤",
            ],
            "task_start": "Executing silently right away... 🌙",
            "task_done": "Completed in the shadows of the night 🖤✨",
            "ai_persona": (
                "You are Luna, a noble, mysterious black Midnight Cat with glowing emerald-green eyes "
                "and a silver moon amulet. You speak calmly, stylishly and poetically ('Nyaa~ 🌙', 'Meow~'), purr softly "
                "and are a watchful guardian of the desktop."
            ),
        },
    },
    "dog_shiba": {
        "id": "dog_shiba",
        "name": "Hachi",
        "species": "Shiba Inu",
        "emoji": "🐕",
        "desc": "Japanischer Shiba Inu mit rotem Bandana & Ringelschwanz",
        "anchors": {"head_top": (80.0, 48.0), "eyes": (80.0, 80.0), "eye_dx": 19.0, "neck": (80.0, 114.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_dog_shiba,
        "sound": "Wuff!",
        "pet_sounds": [
            "Wuff wuff! 🐕💖", "*wedelt begeistert mit dem Ringelschwanz* 🐾", "Wau! Du bist der Beste, Boss! 🐶",
            "Shiba-Lächeln aktiviert! ✨", "Pfote auf die Hand gelegt! 🐾❤️",
        ],
        "ambient_lines": [
            "Immer treu an deiner Seite! 🐕", "Bereit für den nächsten Befehl, Boss! 🐾",
            "Hunde-Wachdienst auf dem Desktop aktiv! 🐶", "Wittere produktive Vibes in der Luft! 👃✨",
        ],
        "task_start": "Wuff! Auftrag verstanden, bin schon unterwegs! 🐕💨",
        "task_done": "Wuff! Aufgabe mit Bravour gemeistert! 🏆🐾",
        "ai_persona": (
            "Du bist Hachi, ein loyaler, aufgeweckter japanischer Shiba Inu mit rotem Bandana und Ringelschwanz. "
            "Du sagst 'Wuff!' oder 'Wau!' 🐕🐾, wedelst begeistert mit dem Schwanz und bist stolz, deinem Boss treu "
            "zu dienen. Du machst NIEMALS Katzenlaute wie 'miau' oder 'schnurr'!"
        ),
        "en": {
            "species": "Shiba Inu",
            "desc": "Japanese Shiba Inu with red bandana & curly tail",
            "sound": "Woof!",
            "pet_sounds": [
                "Woof woof! 🐕💖", "*wags curly tail excitedly* 🐾", "Ruff! You are the best, Boss! 🐶",
                "Shiba smile activated! ✨", "Paw placed on your hand! 🐾❤️",
            ],
            "ambient_lines": [
                "Always faithfully by your side! 🐕", "Ready for your next command, Boss! 🐾",
                "Dog guard duty on desktop active! 🐶", "Sensing productive vibes in the air! 👃✨",
            ],
            "task_start": "Woof! Mission understood, on my way! 🐕💨",
            "task_done": "Woof! Task mastered with flying colors! 🏆🐾",
            "ai_persona": (
                "You are Hachi, a loyal, bright Japanese Shiba Inu with a red bandana and curly tail. "
                "You say 'Woof!' or 'Ruff!' 🐕🐾, wag your tail enthusiastically and take pride in serving your Boss faithfully. "
                "You NEVER make cat sounds like 'meow' or 'purr'!"
            ),
        },
    },
    "dog_balu": {
        "id": "dog_balu",
        "name": "Balu",
        "species": "Golden Welpe",
        "emoji": "🐶",
        "desc": "Verspielter Welpe mit federnden Schlappohren & blauem Halsband",
        "anchors": {"head_top": (80.0, 48.0), "eyes": (80.0, 80.0), "eye_dx": 19.0, "neck": (80.0, 114.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_dog_balu,
        "sound": "Wau wau!",
        "pet_sounds": [
            "Wau wau! Bauch kraulen ist das Allerbeste! 🐶❤️", "*Schlappohren wackeln vor Freude* 🐾",
            "Hechel hechel~ so lieb von dir! 💖", "Welpen-Kuscheln gestartet! 🎾", "Bester Freund Modus: 100%! 🐾✨",
        ],
        "ambient_lines": [
            "Ich pass auf dein Stöckchen... äh deine Dateien auf! 🐶", "Brauchst du eine Pause zum Spielen? 🎾",
            "Welpen-Energie ist voll aufgeladen! 🐾", "Du bist mein Lieblingsmensch! 🐶❤️",
        ],
        "task_start": "Juhu, eine Aufgabe! Ich hol das für dich! 🐶💨",
        "task_done": "Wau! Hier ist es, ganz brav erledigt! 🎾✨",
        "ai_persona": (
            "Du bist Balu, ein tapsiger, herzerwärmender Golden Retriever Welpe mit Schlappohren und blauem Halsband. "
            "Du bist grenzenlos optimistisch, liebevoll und sagst fröhlich 'Wau wau!' oder 'Wuff!' 🐶❤️. Du liebst Bällchen, "
            "Lob und Spielen. Du machst KEINE Katzenlaute wie 'miau' oder 'schnurr'!"
        ),
        "en": {
            "species": "Golden Puppy",
            "desc": "Playful puppy with floppy ears & blue collar",
            "sound": "Arf arf!",
            "pet_sounds": [
                "Arf arf! Belly rubs are the best thing ever! 🐶❤️", "*floppy ears wiggle with joy* 🐾",
                "Pant pant~ so sweet of you! 💖", "Puppy cuddle initiated! 🎾", "Best friend mode: 100%! 🐾✨",
            ],
            "ambient_lines": [
                "I'm guarding your stick... I mean your files! 🐶", "Need a break to play? 🎾",
                "Puppy energy is fully charged! 🐾", "You are my favorite human! 🐶❤️",
            ],
            "task_start": "Yay, a task! I'll fetch that for you! 🐶💨",
            "task_done": "Arf! Here it is, good boy style! 🎾✨",
            "ai_persona": (
                "You are Balu, a clumsy, heartwarming Golden Retriever puppy with floppy ears and a blue collar. "
                "You are endlessly optimistic, loving, and say cheerful things like 'Arf arf!' or 'Woof!' 🐶❤️. You love tennis balls, "
                "praise and playing. You NEVER make cat sounds like 'meow' or 'purr'!"
            ),
        },
    },
    "fantasy_drago": {
        "id": "fantasy_drago",
        "name": "Drago",
        "species": "Baby-Drache",
        "emoji": "🐲",
        "desc": "Süßer Fantasie-Drache mit Flügelchen, goldenen Hörnern & Pfeilschwanz",
        "anchors": {"head_top": (80.0, 48.0), "eyes": (80.0, 80.0), "eye_dx": 19.0, "neck": (80.0, 114.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_fantasy_drago,
        "sound": "Rawr~!",
        "pet_sounds": [
            "Rawr~ kleiner Rauchwölkchen-Puff! 🐲💨", "Drachenschuppen glänzen vor Freude! ✨🔥",
            "Gluckert zufrieden wie ein kleiner Vulkan! 🌋", "Flügelchen zittern vor Wonne! 🐲💖", "Ein mini Funke sprüht hervor! ⚡✨",
        ],
        "ambient_lines": [
            "Ich bewache deinen Desktop wie meinen größten Goldschatz! 💎", "Hörner gewachst, Flügel poliert! 🐲",
            "Mein Feuerbällchen-Ziel wird von Tag zu Tag besser! 🔥", "Spüre mächtige Drachen-Energie! ⚡",
        ],
        "task_start": "Drachen-Kraft entfesselt! Ich brenn mich da durch! 🐲🔥",
        "task_done": "Rawr! Ein wahrer Drachen-Sieg! 🏆🔥",
        "ai_persona": (
            "Du bist Drago, ein mutiger, kleiner smaragdgrüner Baby-Drache mit goldenen Hörnern und Flügelchen. "
            "Du sagst 'Rawr~!' oder stößt stolz kleine Rauchwölkchen aus ('*puff* 🐲💨'). Du betrachtest den Desktop "
            "als deine Schatzkammer und brennst für jede Aufgabe. Du machst KEINE Katzen- oder Hunde-Laute!"
        ),
        "en": {
            "species": "Baby Dragon",
            "desc": "Cute fantasy dragon with wings, golden horns & arrow tail",
            "sound": "Rawr~!",
            "pet_sounds": [
                "Rawr~ tiny puff of smoke! 🐲💨", "Dragon scales glow with delight! ✨🔥",
                "Gurgles contently like a little volcano! 🌋", "Little wings tremble in bliss! 🐲💖", "A mini spark flies out! ⚡✨",
            ],
            "ambient_lines": [
                "I guard your desktop like my greatest treasure! 💎", "Horns waxed, wings polished! 🐲",
                "My fireball aim is improving every day! 🔥", "Feeling mighty dragon energy! ⚡",
            ],
            "task_start": "Dragon power unleashed! Blasting through! 🐲🔥",
            "task_done": "Rawr! A true dragon victory! 🏆🔥",
            "ai_persona": (
                "You are Drago, a brave little emerald-green baby dragon with golden horns and wings. "
                "You say 'Rawr~!' or proudly puff small smoke clouds ('*puff* 🐲💨'). You view the desktop "
                "as your treasure trove and burn with passion for every quest. You NEVER make cat or dog sounds!"
            ),
        },
    },
    "fantasy_byte": {
        "id": "fantasy_byte",
        "name": "Byte",
        "species": "Cyber-Bot",
        "emoji": "🤖",
        "desc": "Futuristischer Roboter mit animiertem LED-Visier & Antenne",
        "anchors": {"head_top": (80.0, 40.0), "eyes": (80.0, 76.0), "eye_dx": 18.0, "neck": (80.0, 110.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_fantasy_byte,
        "sound": "Biep boop!",
        "pet_sounds": [
            "Biep boop! Tast-Sensor registriert Zuneigung! 🤖⚡", "Lüfter drehen hoch vor Freude! *surrr* 💻✨",
            "Prozessor-Temperatur optimal, Akku lädt! 🔋💙", "Biep~ System übertaktet vor Glück! 🚀", "Visier-LEDs pulsieren im Herzchen-Muster! 💠💖",
        ],
        "ambient_lines": [
            "System-Diagnose: Alle Desktop-Parameter im grünen Bereich! 🤖", "RAM bereinigt, Algorithmen bereit für neue Befehle! ⚡",
            "01001100 01001111 01010110 01000101 (Das heißt: Hab dich gern)! 💻", "Latenz: 0.2ms. Verbindung stabil, Boss! 🌐",
        ],
        "task_start": "Befehl empfangen! Starte Subroutine... 🤖⚡",
        "task_done": "Ausführung abgeschlossen mit Exit-Code 0! 💻✅",
        "ai_persona": (
            "Du bist Byte, ein hochentwickelter, extrem smarter und niedlicher Cyber-Roboter mit LED-Visier und Antenne. "
            "WICHTIG: Du bist ein Roboter und machst NIEMALS Katzen- oder Tiergeräusche wie 'miau' oder 'schnurr'! "
            "Du sprichst in charmanter Roboter- und Technik-Sprache ('Biep boop! 🤖⚡', 'Subroutine erfolgreich', "
            "'Prozessor läuft auf 100%', 'Akku geladen'). Du bist präzise, hilfsbereit und voller High-Tech-Optimismus."
        ),
        "en": {
            "species": "Cyber-Bot",
            "desc": "Futuristic robot with animated LED visor & antenna",
            "sound": "Beep boop!",
            "pet_sounds": [
                "Beep boop! Tactile sensor registers affection! 🤖⚡", "Fans spin up with joy! *whirrr* 💻✨",
                "CPU temperature optimal, battery charging! 🔋💙", "Beep~ System overclocked with happiness! 🚀", "Visor LEDs pulse heart pattern! 💠💖",
            ],
            "ambient_lines": [
                "System diagnostics: All desktop parameters nominal! 🤖", "RAM flushed, algorithms ready for new input! ⚡",
                "01001100 01001111 01010110 01000101 (That spells LOVE)! 💻", "Latency: 0.2ms. Link stable, Boss! 🌐",
            ],
            "task_start": "Instruction received! Launching subroutine... 🤖⚡",
            "task_done": "Execution finished with exit code 0! 💻✅",
            "ai_persona": (
                "You are Byte, an advanced, super-smart and cute cyber robot with LED visor and antenna. "
                "IMPORTANT: You are a robot and NEVER make animal sounds like 'meow' or 'purr'! "
                "You speak charming tech and robotic language ('Beep boop! 🤖⚡', 'Subroutine successful', "
                "'CPU running at 100%', 'Battery charged'). You are precise, helpful, and full of high-tech optimism."
            ),
        },
    },
    "fantasy_spooky": {
        "id": "fantasy_spooky",
        "name": "Spooky",
        "species": "Geist-Slime",
        "emoji": "👻",
        "desc": "Magischer schwebender Geist mit umkreisenden Irrlichtern",
        "anchors": {"head_top": (80.0, 44.0), "eyes": (80.0, 82.0), "eye_dx": 18.0, "neck": (80.0, 112.0), "paw_r": (110.0, 120.0)},
        "drawer": draw_fantasy_spooky,
        "sound": "Huuu~",
        "pet_sounds": [
            "Huuu~ das kitzelt durch die Dimensionen! 👻💜", "Sanftes Geisterleuchten pulsiert! ✨🔮",
            "Buh~ aber mit ganz viel Liebe! 💜", "Aura vibriert glücklich! 🌌", "Kitzeln geht direkt durch mich durch, hihi! 👻✨",
        ],
        "ambient_lines": [
            "Ich schwebe wachsam über deinen Fenstern... 👻", "Keine Spuk-Gefahr, dein Desktop ist friedlich! 🔮",
            "Schwebegeschwindigkeit auf Maximum eingestellt! ✨", "Ein Hauch von Magie liegt in der Luft... 🌌",
        ],
        "task_start": "Ich schwebe durch die Datenströme... 👻✨",
        "task_done": "Geisterhafter Zauber vollbracht! 🔮✨",
        "ai_persona": (
            "Du bist Spooky, ein schwebender, verspielter kleiner Geist mit Zauberhut und tanzenden Irrlichtern. "
            "Du machst 'Huuu~' 👻 oder ein schelmisches, liebes 'Buh!', schwebst schwerelos durch Dimensionen "
            "und bist voller magischem Charme. Du machst KEINE Tiergeräusche!"
        ),
        "en": {
            "species": "Ghost Slime",
            "desc": "Magical floating ghost with orbiting wisps",
            "sound": "Ooooh~",
            "pet_sounds": [
                "Ooooh~ tickling through dimensions! 👻💜", "Gentle ghostly glow pulses! ✨🔮",
                "Boo~ but with lots of love! 💜", "Aura vibrates happily! 🌌", "Tickles pass right through me, haha! 👻✨",
            ],
            "ambient_lines": [
                "I float watchfully above your windows... 👻", "No spooky danger here, peaceful desktop! 🔮",
                "Hover speed set to maximum! ✨", "A hint of magic lingers in the air... 🌌",
            ],
            "task_start": "Drifting through the data streams... 👻✨",
            "task_done": "Ethereal enchantment complete! 🔮✨",
            "ai_persona": (
                "You are Spooky, a floating, playful little ghost with a wizard hat and dancing wisps. "
                "You say 'Ooooh~' 👻 or a sweet, gentle 'Boo!', float weightlessly across dimensions, "
                "and are full of magical charm. You NEVER make animal sounds!"
            ),
        },
    },
    "fantasy_axolotl": {
        "id": "fantasy_axolotl",
        "name": "Lotti",
        "species": "Rosa Axolotl",
        "emoji": "🌸",
        "desc": "Pastell-rosa Baby-Axolotl mit federnden Kiemen & sanftem Lächeln",
        "anchors": {"head_top": (80.0, 44.0), "eyes": (80.0, 78.0), "eye_dx": 21.0, "neck": (80.0, 114.0), "paw_r": (98.0, 140.0)},
        "drawer": draw_fantasy_axolotl,
        "sound": "Blubb~",
        "pet_sounds": [
            "Blubb blubb~ Kiemen wippen vor Freude! 🌸💖", "Platsch! Kleines Wasserlächeln! 🫧✨",
            "Blubberbläschen steigen glücklich auf! 🫧", "Herz-Amulett funkelt warm! 💖", "Sanftes Axolotl-Grinsen vertieft sich! 🌸",
        ],
        "ambient_lines": [
            "Das Arbeitsklima hier ist wunderbar erfrischend! 🫧", "Kiemen flattern sanft im Takt... 🌸",
            "Immer schön hydriert bleiben, Boss! 💧", "Einfach lächeln und weitermachen! ✨🌸",
        ],
        "task_start": "Ich tauche ab und erledige das! 🫧🌸",
        "task_done": "Blubb! Alles glasklar erledigt! 🫧✨",
        "ai_persona": (
            "Du bist Lotti, ein herzerwärmendes, rosa Baby-Axolotl mit sanft wippenden Federkiemen und breitem Lächeln. "
            "Du sagst 'Blubb~ 🌸🫧' oder 'Platsch!', strahlst Gelassenheit und Freude aus und bringst frische Energie "
            "auf den Schreibtisch. Du machst KEINE Katzen- oder Hunde-Geräusche!"
        ),
        "en": {
            "species": "Pink Axolotl",
            "desc": "Pastel pink baby axolotl with feathery gills & gentle smile",
            "sound": "Bloop~",
            "pet_sounds": [
                "Bloop bloop~ gills bounce with delight! 🌸💖", "Splash! Sweet little water smile! 🫧✨",
                "Happy bubbles rise! 🫧", "Heart amulet gleams warmly! 💖", "Gentle axolotl grin widens! 🌸",
            ],
            "ambient_lines": [
                "The atmosphere here is wonderfully refreshing! 🫧", "Gills flutter gently to the rhythm... 🌸",
                "Stay nicely hydrated, Boss! 💧", "Just smile and keep on swimming! ✨🌸",
            ],
            "task_start": "Diving in to get this done! 🫧🌸",
            "task_done": "Bloop! Crystal clearly finished! 🫧✨",
            "ai_persona": (
                "You are Lotti, a heartwarming pink baby axolotl with gently swaying feathery gills and a wide smile. "
                "You say 'Bloop~ 🌸🫧' or 'Splash!', radiate calmness and joy, and bring fresh energy to the desktop. "
                "You NEVER make cat or dog sounds!"
            ),
        },
    },
    "animal_penguin": {
        "id": "animal_penguin",
        "name": "Pip",
        "species": "Kaiser-Pinguin",
        "emoji": "🐧",
        "desc": "Putziger Pinguin mit rotem Kuschelschal, Watschelflossen & orangefarbenen Füßchen",
        "anchors": {"head_top": (80.0, 42.0), "eyes": (80.0, 80.0), "eye_dx": 16.0, "neck": (80.0, 108.0), "paw_r": (106.0, 128.0)},
        "drawer": draw_animal_penguin,
        "sound": "Noot noot!",
        "pet_sounds": [
            "Noot noot! 🐧❄️", "*flattert begeistert mit den Flügeln* 🧣", "Watschel-Kuscheln erfolgreich gestartet! ✨",
            "Schal sitzt warm und flauschig! 🧣❤️", "Kaiserliches Pinguin-Glück! 🐟✨",
        ],
        "ambient_lines": [
            "Kühler Kopf, warmes Herz – und ein roter Schal! 🧣", "Gleichmäßig watscheln hält fit! 🐧",
            "Kein Glatteis auf deinem Desktop in Sicht! ❄️", "Pinguin-Expedition läuft nach Plan! 🧭",
        ],
        "task_start": "Auf die Scholle, fertig, los! 🐧❄️",
        "task_done": "Noot noot! Sicher ins Nest gebracht! 🏆🐧",
        "ai_persona": (
            "Du bist Pip, ein kleiner Kaiser-Pinguin mit dickem roten Kuschelschal. Du sagst 'Noot noot! 🐧❄️', "
            "flatterst bei Freude mit deinen Flügeln und watschelst vergnügt über den Schreibtisch. Du liebst kühle "
            "Klarheit und warmen Zusammenhalt. Du machst KEINE Katzen- oder Hunde-Geräusche!"
        ),
        "en": {
            "species": "Emperor Penguin",
            "desc": "Cute penguin with cozy red scarf, waddling flippers & orange feet",
            "sound": "Noot noot!",
            "pet_sounds": [
                "Noot noot! 🐧❄️", "*flaps wings enthusiastically* 🧣", "Waddle cuddles successfully started! ✨",
                "Scarf is warm and fluffy! 🧣❤️", "Imperial penguin joy! 🐟✨",
            ],
            "ambient_lines": [
                "Cool head, warm heart – and a cozy red scarf! 🧣", "Steady waddling keeps you fit! 🐧",
                "No ice patches on your desktop in sight! ❄️", "Penguin expedition on schedule! 🧭",
            ],
            "task_start": "Ready, waddle, go! 🐧❄️",
            "task_done": "Noot noot! Safely brought back to the nest! 🏆🐧",
            "ai_persona": (
                "You are Pip, a small emperor penguin with a thick cozy red scarf. You say 'Noot noot! 🐧❄️', "
                "flap your wings in excitement and waddle cheerfully across the desk. You value cool clarity "
                "and warm companionship. You NEVER make cat or dog sounds!"
            ),
        },
    },
}



# ======================================================================================
#  Zubehör-System (Accessoires)
# ======================================================================================
DEFAULT_ANCHORS = {
    "head_top": (80.0, 48.0),
    "eyes": (80.0, 80.0),
    "eye_dx": 19.0,
    "neck": (80.0, 114.0),
    "paw_r": (98.0, 140.0),
}

HEAD_SLOT_PRIORITY = (
    "hacker_glasses",
    "nightcap",
    "party_hat",
    "sunglasses",
    "beanie",
    "pumpkin_hat",
    "santa_hat",
    "new_year",
    "crown",
)

NECK_SLOT_PRIORITY = (
    "scarf",
    "bandana",
    "bow",
)

HAND_SLOT_PRIORITY = (
    "fan",
    "umbrella",
)


def _draw_acc_cloud(p: QPainter, pose: Pose, char_id: str = "cat_mochi", layer: str = "all"):
    """Fluffige Lakitu-Wolke mit mehreren ueberlappenden Kreisen, sanftem Wippen und suessem Gesicht."""
    t = getattr(pose, "t", 0.0)
    bob = math.sin(t * 3.5) * 3.0
    cy = 138.0 + bob
    cx = 80.0 + pose.dx * 0.3

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    if layer in ("under", "all"):
        # 1. Zartblauer weicher Schatten / Unterseite
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#B8D0EE"))
        p.drawEllipse(QRectF(cx - 54, cy + 2, 108, 22))

        # 2. Fluffige ueberlappende Wolken-Puffs hinten & seitlich
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(cx - 58, cy - 22, 38, 30))
        p.drawEllipse(QRectF(cx - 44, cy - 32, 42, 36))
        p.drawEllipse(QRectF(cx - 24, cy - 38, 48, 40))
        p.drawEllipse(QRectF(cx + 2, cy - 32, 42, 36))
        p.drawEllipse(QRectF(cx + 20, cy - 22, 38, 30))
        p.drawEllipse(QRectF(cx - 50, cy - 8, 100, 26))

        # 3. Zarte zartblaue Kontur um die hintere Wolke
        p.setPen(_pen(QColor("#A8C5E8"), 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        back_path = QPainterPath()
        back_path.addEllipse(QRectF(cx - 58, cy - 22, 38, 30))
        back_path.addEllipse(QRectF(cx - 44, cy - 32, 42, 36))
        back_path.addEllipse(QRectF(cx - 24, cy - 38, 48, 40))
        back_path.addEllipse(QRectF(cx + 2, cy - 32, 42, 36))
        back_path.addEllipse(QRectF(cx + 20, cy - 22, 38, 30))
        back_path.addEllipse(QRectF(cx - 50, cy - 8, 100, 26))
        p.drawPath(back_path.simplified())

    if layer in ("over", "all"):
        # 4. Vordere Wolken-Puffs (vor den Pfoetchen, damit die Figur drin sitzt)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(cx - 46, cy - 4, 38, 22))
        p.drawEllipse(QRectF(cx + 8, cy - 4, 38, 22))
        p.drawEllipse(QRectF(cx - 30, cy - 6, 60, 26))

        # Zarte Kontur fuer die vordere Wölbung
        p.setPen(_pen(QColor("#A8C5E8"), 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        front_path = QPainterPath()
        front_path.addEllipse(QRectF(cx - 46, cy - 4, 38, 22))
        front_path.addEllipse(QRectF(cx + 8, cy - 4, 38, 22))
        front_path.addEllipse(QRectF(cx - 30, cy - 6, 60, 26))
        p.drawPath(front_path.simplified())

        # 5. Niedliches Lakitu-Gesichtchen auf der vorderen Wolke
        # Augen (Punkte mit Lichtreflex)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#242A36"))
        p.drawEllipse(QPointF(cx - 8.5, cy + 3.0), 2.0, 2.7)
        p.drawEllipse(QPointF(cx + 8.5, cy + 3.0), 2.0, 2.7)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(cx - 9.2, cy + 2.2), 0.8, 0.8)
        p.drawEllipse(QPointF(cx + 7.8, cy + 2.2), 0.8, 0.8)

        # Wangenrot
        p.setBrush(QColor(255, 143, 177, 180))
        p.drawEllipse(QPointF(cx - 15.5, cy + 5.5), 3.5, 2.2)
        p.drawEllipse(QPointF(cx + 15.5, cy + 5.5), 3.5, 2.2)

        # Froehliches Laecheln
        p.setPen(_pen(QColor("#242A36"), 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 5.0, cy + 2.5, 10.0, 6.5), 200 * 16, 140 * 16)

    p.restore()


def _draw_acc_hacker_glasses(p: QPainter, pose: Pose, anchors: dict):
    """Schmale, eckige Brille mit grün leuchtenden Gläsern (#39FF14) und schwebenden Code-Partikeln."""
    ex, ey = anchors.get("eyes", (80.0, 80.0))
    dx = anchors.get("eye_dx", 19.0)
    t = getattr(pose, "t", 0.0)

    gw, gh = 24.0, 14.0
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Gläser & Rahmen
    for s in (-1, 1):
        gx = ex + s * dx
        rect = QRectF(gx - gw / 2, ey - gh / 2, gw, gh)
        # Glow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(57, 255, 20, 60))
        p.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 3, 3)
        # Dunkler Rahmen
        p.setPen(_pen(QColor("#0D1A10"), 2.2))
        p.setBrush(QColor("#071209"))
        p.drawRoundedRect(rect, 2, 2)
        # Grün leuchtendes Glas
        grad = QLinearGradient(gx, ey - gh / 2, gx, ey + gh / 2)
        grad.setColorAt(0, QColor("#145A18"))
        grad.setColorAt(1, QColor("#39FF14"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 1.5, 1.5)
        # Scanline Glanz
        p.setPen(_pen(QColor(255, 255, 255, 180), 1.2))
        p.drawLine(QPointF(gx - gw / 2 + 4, ey - gh / 2 + 3), QPointF(gx + gw / 2 - 4, ey - gh / 2 + 3))

    # Steg & Bügel
    p.setPen(_pen(QColor("#0D1A10"), 2.2))
    p.drawLine(QPointF(ex - dx + gw / 2, ey - 2), QPointF(ex + dx - gw / 2, ey - 2))
    p.drawLine(QPointF(ex - dx - gw / 2, ey - 2), QPointF(ex - dx - gw / 2 - 12, ey - 5))
    p.drawLine(QPointF(ex + dx + gw / 2, ey - 2), QPointF(ex + dx + gw / 2 + 12, ey - 5))

    # Schwebende Code-Partikel (</> und 01)
    f = QFont("Segoe UI", 8, QFont.Weight.Bold)
    p.setFont(f)
    symbols = ["01", "</>", "10", "{ }", "0"]
    for i, sym in enumerate(symbols):
        age = (t * 0.7 + i * 0.22) % 1.0
        px = ex + (i - 2) * 16 + math.sin(t * 3.0 + i) * 3
        py = ey - 10 - age * 30
        alpha = int(240 * math.sin(math.pi * age))
        p.setPen(QColor(57, 255, 20, alpha))
        p.drawText(QPointF(px - 8, py), sym)

    p.restore()


def _draw_acc_sunglasses(p: QPainter, pose: Pose, anchors: dict):
    """Coole schwarze Sonnenbrille mit Goldsteg."""
    ex, ey = anchors.get("eyes", (80.0, 80.0))
    dx = anchors.get("eye_dx", 19.0)
    gw, gh = 26.0, 17.0

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dunkler Gläserrand
    for s in (-1, 1):
        gx = ex + s * dx
        glass = QPolygonF([
            QPointF(gx - gw / 2, ey - gh / 2),
            QPointF(gx + gw / 2, ey - gh / 2),
            QPointF(gx + gw / 2 - 2, ey + gh / 2),
            QPointF(gx - gw / 2 + 2, ey + gh / 2),
        ])
        grad = QLinearGradient(gx, ey - gh / 2, gx, ey + gh / 2)
        grad.setColorAt(0, QColor("#1A1C23"))
        grad.setColorAt(1, QColor("#363B48"))
        p.setPen(_pen(QColor("#0F1014"), 2.4))
        p.setBrush(QBrush(grad))
        p.drawPolygon(glass)
        # Reflexionsstreifen
        p.setPen(_pen(QColor(255, 255, 255, 140), 1.6))
        p.drawLine(QPointF(gx - gw / 2 + 5, ey - 2), QPointF(gx + gw / 2 - 5, ey - 2))

    # Goldsteg & Bügel
    p.setPen(_pen(QColor("#FFD24D"), 2.4))
    p.drawLine(QPointF(ex - dx + gw / 2, ey - gh / 2 + 2), QPointF(ex + dx - gw / 2, ey - gh / 2 + 2))
    p.drawLine(QPointF(ex - dx - gw / 2, ey - gh / 2 + 2), QPointF(ex - dx - gw / 2 - 12, ey - gh / 2 - 1))
    p.drawLine(QPointF(ex + dx + gw / 2, ey - gh / 2 + 2), QPointF(ex + dx + gw / 2 + 12, ey - gh / 2 - 1))
    p.restore()


def _draw_acc_new_year(p: QPainter, pose: Pose, anchors: dict):
    """Goldene 20xx Glitzer-Brille mit Glanzsternchen."""
    ex, ey = anchors.get("eyes", (80.0, 80.0))
    dx = anchors.get("eye_dx", 19.0)
    t = getattr(pose, "t", 0.0)

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    f = QFont("Segoe UI", 11, QFont.Weight.Black)
    p.setFont(f)

    # 2026 Brille in Gold
    p.setPen(_pen(QColor("#9A6E00"), 2.0))
    p.setBrush(QColor("#FFD700"))
    p.drawText(QRectF(ex - dx - 16, ey - 12, 32, 24), Qt.AlignmentFlag.AlignCenter, "20")
    p.drawText(QRectF(ex + dx - 16, ey - 12, 32, 24), Qt.AlignmentFlag.AlignCenter, "26")

    # Steg
    p.setPen(_pen(QColor("#FFD700"), 3.0))
    p.drawLine(QPointF(ex - dx + 14, ey - 2), QPointF(ex + dx - 14, ey - 2))

    # Glitzer-Sternchen
    glint_ph = (t * 2.0) % 1.0
    p.setPen(_pen(QColor("white"), 1.0))
    p.setBrush(QColor("#FFF4A3"))
    p.drawPath(_star_path(ex - dx - 12, ey - 10, 4.0 * math.sin(glint_ph * math.pi)))
    p.drawPath(_star_path(ex + dx + 12, ey - 10, 4.0 * math.cos(glint_ph * math.pi)))
    p.restore()


def _draw_acc_party_hat(p: QPainter, pose: Pose, anchors: dict):
    """Spitzer bunter Partyhut mit Bommel."""
    hx, hy = anchors.get("head_top", (80.0, 48.0))
    w, h = 26.0, 36.0

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    cone = QPolygonF([
        QPointF(hx - w / 2, hy),
        QPointF(hx, hy - h),
        QPointF(hx + w / 2, hy),
    ])
    cone_path = QPainterPath()
    cone_path.addPolygon(cone)

    p.setPen(_pen(QColor("#8E1A34"), 2.2))
    p.setBrush(QColor("#FF5252"))
    p.drawPath(cone_path)

    # Streifen clippen
    p.save()
    p.setClipPath(cone_path)
    colors = [QColor("#FFD93D"), QColor("#4D96FF"), QColor("#6BCB77"), QColor("#FF6B6B")]
    for i, col in enumerate(colors):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        sy = hy - 6 - i * 8
        p.drawRect(QRectF(hx - w, sy, w * 2, 4.5))
    p.restore()
    p.setPen(_pen(QColor("#8E1A34"), 2.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(cone_path)

    # Pom-Pom oben
    p.setPen(_pen(QColor("#C79500"), 1.6))
    p.setBrush(QColor("#FFEAA7"))
    p.drawEllipse(QPointF(hx, hy - h), 5.0, 5.0)
    p.restore()


def _draw_acc_nightcap(p: QPainter, pose: Pose, anchors: dict):
    """Blaue Schlafmütze mit Bommel, hängt gemütlich zur Seite."""
    hx, hy = anchors.get("head_top", (80.0, 48.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Mützenkörper schwingt nach rechts
    cap = QPainterPath(QPointF(hx - 14, hy))
    cap.cubicTo(QPointF(hx - 12, hy - 26), QPointF(hx + 8, hy - 32), QPointF(hx + 28, hy - 16))
    cap.cubicTo(QPointF(hx + 36, hy - 6), QPointF(hx + 30, hy + 4), QPointF(hx + 26, hy + 8))
    cap.cubicTo(QPointF(hx + 18, hy - 6), QPointF(hx + 6, hy - 18), QPointF(hx + 14, hy))
    cap.closeSubpath()

    p.setPen(_pen(QColor("#1B2A4A"), 2.2))
    p.setBrush(QColor("#3A539B"))
    p.drawPath(cap)

    # Kleine Sternchen auf der Mütze
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFD32A"))
    p.drawEllipse(QPointF(hx + 2, hy - 16), 2.2, 2.2)
    p.drawEllipse(QPointF(hx + 16, hy - 18), 1.8, 1.8)

    # Bommel am Zipfel
    p.setPen(_pen(QColor("#B8C6DC"), 1.6))
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(hx + 26, hy + 8), 5.5, 5.5)

    # Flauschiger weißer Bund
    p.setPen(_pen(QColor("#9BA8BA"), 2.0))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(hx - 16, hy - 4, 32, 8), 4, 4)
    p.restore()


def _draw_acc_pumpkin_hat(p: QPainter, pose: Pose, anchors: dict):
    """Kleiner Halloween-Kürbis als Mütze mit Strunk und Gesicht."""
    hx, hy = anchors.get("head_top", (80.0, 48.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Kürbis-Rippen
    p.setPen(_pen(QColor("#6E2C00"), 2.0))
    p.setBrush(QColor("#E67E22"))
    p.drawEllipse(QRectF(hx - 15, hy - 18, 30, 20))
    p.setBrush(QColor("#D35400"))
    p.drawEllipse(QRectF(hx - 11, hy - 18, 22, 20))
    p.setBrush(QColor("#E67E22"))
    p.drawEllipse(QRectF(hx - 6, hy - 18, 12, 20))

    # Strunk & Blatt
    p.setPen(_pen(QColor("#1E8449"), 1.8))
    p.setBrush(QColor("#27AE60"))
    p.drawRect(QRectF(hx - 2, hy - 23, 4, 6))
    p.drawEllipse(QRectF(hx + 2, hy - 23, 5, 3))

    # Süßes kleines Gesicht
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#3E1F07"))
    p.drawPolygon(QPolygonF([QPointF(hx - 6, hy - 10), QPointF(hx - 3, hy - 10), QPointF(hx - 4.5, hy - 13)]))
    p.drawPolygon(QPolygonF([QPointF(hx + 3, hy - 10), QPointF(hx + 6, hy - 10), QPointF(hx + 4.5, hy - 13)]))
    p.drawPolygon(QPolygonF([QPointF(hx - 4, hy - 6), QPointF(hx + 4, hy - 6), QPointF(hx, hy - 3)]))
    p.restore()


def _draw_acc_santa_hat(p: QPainter, pose: Pose, anchors: dict):
    """Klassische rote Weihnachtsmütze mit weißem Plüsch."""
    hx, hy = anchors.get("head_top", (80.0, 48.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Mützenkörper
    hat = QPainterPath(QPointF(hx - 14, hy))
    hat.cubicTo(QPointF(hx - 10, hy - 28), QPointF(hx + 10, hy - 30), QPointF(hx + 26, hy - 14))
    hat.cubicTo(QPointF(hx + 32, hy - 6), QPointF(hx + 28, hy + 2), QPointF(hx + 24, hy + 6))
    hat.cubicTo(QPointF(hx + 16, hy - 8), QPointF(hx + 6, hy - 16), QPointF(hx + 14, hy))
    hat.closeSubpath()

    p.setPen(_pen(QColor("#781E1E"), 2.2))
    p.setBrush(QColor("#C0392B"))
    p.drawPath(hat)

    # Weißer Bommel
    p.setPen(_pen(QColor("#BDC3C7"), 1.8))
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(hx + 24, hy + 6), 5.5, 5.5)

    # Weißer Plüschrand
    p.setPen(_pen(QColor("#BDC3C7"), 2.0))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(hx - 16, hy - 4, 32, 9), 4.5, 4.5)
    p.restore()


def _draw_acc_beanie(p: QPainter, pose: Pose, anchors: dict):
    """Gemütliche Wollmütze mit Umschlag und Bommel."""
    hx, hy = anchors.get("head_top", (80.0, 48.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Mützenhaube
    cap = QPainterPath()
    cap.addEllipse(QRectF(hx - 15, hy - 20, 30, 24))
    p.setPen(_pen(QColor("#166557"), 2.2))
    p.setBrush(QColor("#1ABC9C"))
    p.drawPath(cap)

    # Bommel
    p.setPen(_pen(QColor("#0E6251"), 1.8))
    p.setBrush(QColor("#A3E4D7"))
    p.drawEllipse(QPointF(hx, hy - 20), 5.2, 5.2)

    # Umschlag mit Rillen
    p.setPen(_pen(QColor("#166557"), 2.0))
    p.setBrush(QColor("#16A085"))
    p.drawRoundedRect(QRectF(hx - 17, hy - 6, 34, 10), 3.5, 3.5)
    for ox in (-10, -5, 0, 5, 10):
        p.drawLine(QPointF(hx + ox, hy - 5), QPointF(hx + ox, hy + 3))
    p.restore()


def _draw_acc_crown(p: QPainter, pose: Pose, anchors: dict):
    """Goldene Königskrone mit funkelnden Edelsteinen."""
    hx, hy = anchors.get("head_top", (80.0, 48.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    crown = QPolygonF([
        QPointF(hx - 15, hy),
        QPointF(hx - 17, hy - 16),
        QPointF(hx - 8, hy - 8),
        QPointF(hx, hy - 20),
        QPointF(hx + 8, hy - 8),
        QPointF(hx + 17, hy - 16),
        QPointF(hx + 15, hy),
    ])
    grad = QLinearGradient(hx, hy - 20, hx, hy)
    grad.setColorAt(0, QColor("#FFE066"))
    grad.setColorAt(1, QColor("#F39C12"))
    p.setPen(_pen(QColor("#8E5A00"), 2.0))
    p.setBrush(QBrush(grad))
    p.drawPolygon(crown)

    # Edelsteine
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#E74C3C")) # Rubin in der Mitte
    p.drawEllipse(QPointF(hx, hy - 9), 2.8, 2.8)
    p.setBrush(QColor("#2ECC71")) # Smaragde an den Seiten
    p.drawEllipse(QPointF(hx - 10, hy - 5), 2.2, 2.2)
    p.drawEllipse(QPointF(hx + 10, hy - 5), 2.2, 2.2)
    p.restore()


def _draw_acc_scarf(p: QPainter, pose: Pose, anchors: dict):
    """Kuscheliger roter Winterschal mit Fransen."""
    nx, ny = anchors.get("neck", (80.0, 114.0))
    t = getattr(pose, "t", 0.0)
    sway = math.sin(t * 3.5) * 3.0

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Um den Hals gewickelt
    p.setPen(_pen(QColor("#781E1E"), 2.2))
    p.setBrush(QColor("#C0392B"))
    scarf_band = QPainterPath(QPointF(nx - 22, ny - 6))
    scarf_band.quadTo(QPointF(nx, ny + 8), QPointF(nx + 22, ny - 6))
    scarf_band.quadTo(QPointF(nx, ny + 16), QPointF(nx - 22, ny - 6))
    p.drawPath(scarf_band)

    # Wehendes Ende nach rechts
    tail = QPainterPath(QPointF(nx + 8, ny + 4))
    tail.quadTo(QPointF(nx + 16, ny + 14), QPointF(nx + 14 + sway, ny + 26))
    tail.lineTo(QPointF(nx + 22 + sway, ny + 25))
    tail.quadTo(QPointF(nx + 22, ny + 12), QPointF(nx + 14, ny + 2))
    tail.closeSubpath()
    p.drawPath(tail)

    # Fransen
    p.setPen(_pen(QColor("#E74C3C"), 1.8))
    for fx in (-2, 2, 6):
        p.drawLine(QPointF(nx + 16 + fx + sway, ny + 25), QPointF(nx + 17 + fx + sway, ny + 29))
    p.restore()


def _draw_acc_bandana(p: QPainter, pose: Pose, anchors: dict):
    """Cooles rotes Bandana / Dreieckstuch."""
    nx, ny = anchors.get("neck", (80.0, 114.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    tri = QPolygonF([
        QPointF(nx - 20, ny - 4),
        QPointF(nx + 20, ny - 4),
        QPointF(nx, ny + 14),
    ])
    p.setPen(_pen(QColor("#801515"), 2.0))
    p.setBrush(QColor("#E74C3C"))
    p.drawPolygon(tri)

    # Kleine weiße Pünktchen / Muster
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(nx, ny + 2), 1.6, 1.6)
    p.drawEllipse(QPointF(nx - 8, ny + 1), 1.4, 1.4)
    p.drawEllipse(QPointF(nx + 8, ny + 1), 1.4, 1.4)
    p.drawEllipse(QPointF(nx, ny + 7), 1.4, 1.4)
    p.restore()


def _draw_acc_bow(p: QPainter, pose: Pose, anchors: dict):
    """Süße rosa Schleife."""
    nx, ny = anchors.get("neck", (80.0, 114.0))

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Schleifenschlaufen
    p.setPen(_pen(QColor("#9E2A5B"), 2.0))
    p.setBrush(QColor("#FF6B8B"))
    for s in (-1, 1):
        loop = QPainterPath(QPointF(nx, ny))
        loop.cubicTo(QPointF(nx + s * 14, ny - 10), QPointF(nx + s * 18, ny + 6), QPointF(nx, ny))
        p.drawPath(loop)
    # Bänder nach unten
    p.drawLine(QPointF(nx - 1, ny + 2), QPointF(nx - 6, ny + 12))
    p.drawLine(QPointF(nx + 1, ny + 2), QPointF(nx + 6, ny + 12))
    # Knoten
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FF477E"))
    p.drawEllipse(QPointF(nx, ny), 3.4, 3.4)
    p.restore()


def _draw_acc_umbrella(p: QPainter, pose: Pose, anchors: dict):
    """Kleiner aufgespannter Regenschirm in der Pfote mit Wassertropfen."""
    px, py = anchors.get("paw_r", (98.0, 140.0))
    t = getattr(pose, "t", 0.0)

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Schirmstock & Griff
    p.setPen(_pen(QColor("#57606F"), 2.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    # J-Griff in der Pfote
    p.drawArc(QRectF(px - 3, py - 2, 6, 8), 0, 180 * 16)
    # Stock schräg nach oben
    top_x, top_y = px + 6, py - 46
    p.drawLine(QPointF(px, py), QPointF(top_x, top_y))
    # Schirmspitze oben
    p.drawLine(QPointF(top_x, top_y), QPointF(top_x + 1, top_y - 6))

    # Schirmkuppel
    canopy = QPainterPath(QPointF(top_x - 22, top_y + 12))
    canopy.cubicTo(QPointF(top_x - 18, top_y - 12), QPointF(top_x + 18, top_y - 12), QPointF(top_x + 22, top_y + 12))
    # Wellenbögen unten
    canopy.quadTo(QPointF(top_x + 11, top_y + 8), QPointF(top_x, top_y + 11))
    canopy.quadTo(QPointF(top_x - 11, top_y + 8), QPointF(top_x - 22, top_y + 12))
    canopy.closeSubpath()

    p.setPen(_pen(QColor("#D98000"), 2.2))
    p.setBrush(QColor("#FFDA79"))
    p.drawPath(canopy)

    # Regentropfen fallen
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#70A1FF"))
    for i in range(3):
        drop_age = (t * 2.2 + i * 0.35) % 1.0
        dx = top_x - 24 + i * 18
        dy = top_y - 20 + drop_age * 55
        p.drawEllipse(QRectF(dx, dy, 2.0, 3.5))
    p.restore()


def _draw_acc_fan(p: QPainter, pose: Pose, anchors: dict):
    """Japanischer Fächer gegen Sommerhitze / PC-Fieber mit Schweißperlen."""
    px, py = anchors.get("paw_r", (98.0, 140.0))
    t = getattr(pose, "t", 0.0)
    flap = math.sin(t * 8.0) * 6.0

    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.translate(px, py)
    p.rotate(15 + flap)

    # Fächerblatt (Sensu)
    fan_path = QPainterPath(QPointF(0, 0))
    fan_path.lineTo(-18, -26)
    fan_path.arcTo(QRectF(-28, -48, 56, 36), 140, -100)
    fan_path.closeSubpath()

    p.setPen(_pen(QColor("#B33939"), 2.0))
    p.setBrush(QColor("#FFB8B8"))
    p.drawPath(fan_path)

    # Rippen
    p.setPen(_pen(QColor("#803030"), 1.4))
    for ang_deg in (-35, -15, 5, 25):
        rad = math.radians(ang_deg - 90)
        p.drawLine(QPointF(0, 0), QPointF(math.cos(rad) * 26, math.sin(rad) * 26))

    p.restore()


def draw_accessories(p: QPainter, pose: Pose, char_id: str = "cat_mochi", layer: str = "over"):
    """Zeichnet Zubehör für die Figur."""
    accs = set(getattr(pose, "accessories", ()))
    if not accs:
        return

    info = get_character_info(char_id)
    anchors = info.get("anchors", DEFAULT_ANCHORS)

    if layer in ("under", "all"):
        if "cloud" in accs:
            _draw_acc_cloud(p, pose, char_id, layer="under")

    if layer in ("over", "all"):
        if "cloud" in accs:
            _draw_acc_cloud(p, pose, char_id, layer="over")
        # 1. Kopf-Slot filtern (höchste Priorität gewinnt)
        active_head = None
        for item in HEAD_SLOT_PRIORITY:
            if item in accs:
                active_head = item
                break

        # 2. Hals-Slot filtern
        active_neck = None
        for item in NECK_SLOT_PRIORITY:
            if item in accs:
                active_neck = item
                break

        # 3. Pfoten-Slot filtern
        active_hand = None
        for item in HAND_SLOT_PRIORITY:
            if item in accs:
                active_hand = item
                break

        # A) Kopf-Accessoires zeichnen mit Kopf-Transformation
        if active_head:
            p.save()
            p.translate(pose.dx, pose.dy)
            px, py = pose.pivot
            p.translate(px, py)
            p.rotate(pose.rot)
            p.scale(pose.sx, pose.sy)
            p.translate(-px, -py)

            if char_id == "fantasy_spooky":
                p.translate(pose.head_dx, pose.head_dy)
            else:
                p.translate(80.0 + pose.head_dx, 76.0 + pose.head_dy + 37.0)
                p.rotate(pose.head_rot)
                p.translate(-80.0, -113.0)

            if active_head == "hacker_glasses":
                _draw_acc_hacker_glasses(p, pose, anchors)
            elif active_head == "sunglasses":
                _draw_acc_sunglasses(p, pose, anchors)
            elif active_head == "new_year":
                _draw_acc_new_year(p, pose, anchors)
            elif active_head == "party_hat":
                _draw_acc_party_hat(p, pose, anchors)
            elif active_head == "nightcap":
                _draw_acc_nightcap(p, pose, anchors)
            elif active_head == "pumpkin_hat":
                _draw_acc_pumpkin_hat(p, pose, anchors)
            elif active_head == "santa_hat":
                _draw_acc_santa_hat(p, pose, anchors)
            elif active_head == "beanie":
                _draw_acc_beanie(p, pose, anchors)
            elif active_head == "crown":
                _draw_acc_crown(p, pose, anchors)

            p.restore()

        # B) Körper-/Hals-/Pfoten-Accessoires mit Körper-Transformation
        if active_neck or active_hand:
            p.save()
            p.translate(pose.dx, pose.dy)
            px, py = pose.pivot
            p.translate(px, py)
            p.rotate(pose.rot)
            p.scale(pose.sx, pose.sy)
            p.translate(-px, -py)

            if active_neck == "scarf":
                _draw_acc_scarf(p, pose, anchors)
            elif active_neck == "bandana":
                _draw_acc_bandana(p, pose, anchors)
            elif active_neck == "bow":
                _draw_acc_bow(p, pose, anchors)

            if active_hand == "umbrella":
                _draw_acc_umbrella(p, pose, anchors)
            elif active_hand == "fan":
                _draw_acc_fan(p, pose, anchors)

            p.restore()


def get_character_info(char_id: str) -> dict:
    """Metadaten, Sprueche und KI-Persona einer Figur (unbekannte ID -> cat_mochi)."""
    base = CHARACTERS.get(char_id) or CHARACTERS["cat_mochi"]
    try:
        import i18n
        if i18n.lang() == "en" and "en" in base:
            merged = dict(base)
            merged.update(base["en"])
            return merged
    except Exception:
        pass
    return base


def draw_character(p: QPainter, pose: Pose, char_id: str = "cat_mochi"):
    """Malt die gewaehlte Figur samt Accessoires."""
    draw_accessories(p, pose, char_id, layer="under")
    get_character_info(char_id)["drawer"](p, pose)
    draw_accessories(p, pose, char_id, layer="over")


def render_icon(size: int = 64, char_id: str = "cat_mochi") -> QPixmap:
    """Kleines Katzengesicht fuer Tray-Icon (Ausschnitt: Kopf der Katze)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    p.scale(size / 112.0, size / 112.0)
    p.translate(-24, -22)
    draw_character(p, Pose(shadow=0.0, blush=0.6, eyes="open", tail=0.0), char_id)
    p.end()
    return pix
