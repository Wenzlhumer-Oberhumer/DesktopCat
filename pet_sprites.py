"""Grafik fuer das Pet: laedt GIF/PNG-Sprites aus assets/ und malt - falls keine vorhanden sind -
eine niedliche Kawaii-Katze per QPainter (komplett prozedural animiert, keine Bilddateien noetig)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
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

STATE_KEYS = ["idle", "walk_right", "walk_left", "dragged", "falling", "working", "success", "sleep", "sad", "dance", "cool"]
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
OUTLINE = QColor("#7A4A3A")
FUR = QColor("#FFB877")
FUR_LIGHT = QColor("#FFCFA0")
FUR_DARK = QColor("#EE8E45")
CREAM = QColor("#FFF1DE")
PINK = QColor("#FFB3C4")
NOSE = QColor("#FF8DA1")
MOUTH = QColor("#D9506A")
EYE_TOP = QColor("#2B2033")
EYE_BOT = QColor("#664A78")
COLLAR = QColor("#FF5C7F")
BELL = QColor("#FFD24D")
GOLD = QColor("#FFD84D")
HEART = QColor("#FF6B94")
WHISKER = QColor(150, 105, 85, 170)


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
    hearts: Optional[float] = None   # 0..1 Alter
    music_notes: Optional[float] = None
    glint: Optional[float] = None
    sweat: bool = False
    tear: Optional[float] = None



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
    p.setBrush(CREAM)
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
        grad = QLinearGradient(ex, ey - ry, ex, ey + ry)
        grad.setColorAt(0, EYE_TOP)
        grad.setColorAt(1, EYE_BOT)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QRectF(ex - rx, ey - ry, rx * 2, ry * 2))
        p.setBrush(QColor("white"))
        big = 3.6 if mode != "wide" else 4.2
        p.drawEllipse(QPointF(ex - 2.7 + lx * 0.8, ey - ry * 0.38), big, big)
        p.drawEllipse(QPointF(ex + 3.2 + lx * 0.4, ey + ry * 0.36), 1.8, 1.8)
        if mode == "sad":
            p.setPen(_pen(OUTLINE, 2.4))
            # innere Enden hoch -> traurige Augenbrauen
            inner = -side
            p.drawLine(QPointF(ex + inner * -9, ey - 12.5), QPointF(ex + inner * 7.5, ey - 17))
    elif mode == "blink":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(EYE_TOP)
        p.drawEllipse(QRectF(cx - 8.4, cy + 2.5, 16.8, 3.0))
    elif mode == "sleep":
        p.setPen(_pen(EYE_TOP, 2.9))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 8, cy - 6, 16, 11), 180 * 16, 180 * 16)
    elif mode == "happy":
        p.setPen(_pen(EYE_TOP, 3.1))
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
    p.setPen(_pen(FUR, 10.5))
    p.drawPath(path)
    end = path.pointAtPercent(1.0)
    p.setPen(_pen(OUTLINE, 2.2))
    p.setBrush(CREAM)
    p.drawEllipse(end, 5.6, 5.6)


def _draw_ear(p: QPainter, sign: int, rot: float):
    """sign=-1 links, +1 rechts; Koordinaten relativ zur Kopfmitte."""
    bx, by = sign * 30, -22
    p.save()
    p.translate(bx, by)
    p.rotate(rot)
    p.translate(-bx, -by)
    outer = QPolygonF([QPointF(sign * 43, -11), QPointF(sign * 38, -51), QPointF(sign * 9, -31)])
    inner = QPolygonF([QPointF(sign * 37, -17), QPointF(sign * 34.5, -42), QPointF(sign * 17, -29)])
    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(FUR)
    p.drawPolygon(outer)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(PINK)
    p.drawPolygon(inner)
    p.restore()


def _draw_head(p: QPainter, pose: Pose):
    p.save()
    p.translate(80 + pose.head_dx, 76 + pose.head_dy + 37)
    p.rotate(pose.head_rot)
    p.translate(0, -37)

    _draw_ear(p, -1, pose.ear_l)
    _draw_ear(p, +1, pose.ear_r)

    grad = QRadialGradient(QPointF(-12, -20), 72)
    grad.setColorAt(0, FUR_LIGHT)
    grad.setColorAt(1, FUR)
    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QRectF(-46, -37, 92, 74))

    # Tabby-Streifen
    p.setPen(_pen(FUR_DARK, 3.2))
    p.drawLine(QPointF(0, -34), QPointF(0, -23))
    p.drawLine(QPointF(-9.5, -33), QPointF(-7.5, -25.5))
    p.drawLine(QPointF(9.5, -33), QPointF(7.5, -25.5))

    # Schnauze
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(CREAM)
    p.drawEllipse(QRectF(-15, 6.5, 30, 19))

    # Wangenroeschen
    if pose.blush > 0:
        p.setBrush(QColor(255, 118, 150, int(_clamp(pose.blush, 0, 1) * 150)))
        for s in (-1, 1):
            p.drawEllipse(QRectF(s * 31 - 8.5, 10.5, 17, 10))

    # Schnurrhaare
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


    # Nase
    p.setPen(_pen(NOSE, 1.6))
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

    # Koerper
    p.setPen(_pen(OUTLINE, 2.6))
    p.setBrush(FUR)
    p.drawEllipse(QRectF(47, 100, 66, 47.5))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(CREAM)
    p.drawEllipse(QRectF(61, 114, 38, 30))

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

    # Halsband + Glocke
    collar = QPainterPath(QPointF(53, 107))
    collar.quadTo(QPointF(80, 129), QPointF(107, 107))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(OUTLINE, 8.2))
    p.drawPath(collar)
    p.setPen(_pen(COLLAR, 5.0))
    p.drawPath(collar)
    bx = 80 + pose.bell
    p.setPen(_pen(OUTLINE, 1.9))
    p.setBrush(BELL)
    p.drawEllipse(QPointF(bx, 121.5), 5.4, 5.4)
    p.setPen(_pen(OUTLINE, 1.2))
    p.drawLine(QPointF(bx - 3.6, 122.2), QPointF(bx + 3.6, 122.2))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 200))
    p.drawEllipse(QPointF(bx - 1.8, 119.2), 1.3, 1.3)

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


def render_icon(size: int = 64) -> QPixmap:
    """Kleines Katzengesicht fuer Tray-Icon (Ausschnitt: Kopf der Katze)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    p.scale(size / 112.0, size / 112.0)
    p.translate(-24, -22)
    draw_cat(p, Pose(shadow=0.0, blush=0.6, eyes="open", tail=0.0))
    p.end()
    return pix
