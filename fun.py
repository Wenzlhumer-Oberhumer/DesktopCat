# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Freundschaft, Fokus-Statistik, Lernkarten-Leitner-System und Fotobox (Phase 6)."""
from __future__ import annotations

import datetime
import difflib
import json
import re
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QImage, QPainter, QPen,
)

import i18n

LEVEL_THRESHOLDS = [0, 25, 75, 150, 300, 500, 800, 1200]
LEVEL_NAMES = {
    1: "Bekannte",
    2: "Kumpel",
    3: "Freunde",
    4: "Gute Freunde",
    5: "Beste Freunde",
    6: "Seelenverwandte",
    7: "Unzertrennlich",
    8: "Ewige Legenden",
}
LEVEL_NAMES_EN = {
    1: "Acquaintances",
    2: "Buddies",
    3: "Friends",
    4: "Good Friends",
    5: "Best Friends",
    6: "Soulmates",
    7: "Inseparable",
    8: "Eternal Legends",
}

LEVEL_REWARDS = {
    1: ("Standard", None),
    2: ("Schleife", "bow"),
    3: ("Halstuch", "bandana"),
    4: ("Schal", "scarf"),
    5: ("Partyhut", "party_hat"),
    6: ("Sonnenbrille-Pose", "sunglasses"),
    7: ("Krone", "crown"),
    8: ("Goldener Glanz", "gold_sparkle"),
}
LEVEL_REWARDS_EN = {
    1: ("Default", None),
    2: ("Bow", "bow"),
    3: ("Bandana", "bandana"),
    4: ("Scarf", "scarf"),
    5: ("Party Hat", "party_hat"),
    6: ("Sunglasses Pose", "sunglasses"),
    7: ("Crown", "crown"),
    8: ("Golden Sparkle", "gold_sparkle"),
}


def get_level_name(lvl: int) -> str:
    if i18n.lang() == "en":
        return LEVEL_NAMES_EN.get(lvl, "Friends")
    return LEVEL_NAMES.get(lvl, "Freunde")


def get_level_reward(lvl: int) -> tuple[str, Optional[str]]:
    if i18n.lang() == "en":
        return LEVEL_REWARDS_EN.get(lvl, ("", None))
    return LEVEL_REWARDS.get(lvl, ("", None))

DAILY_LIMITS = {
    "chat": 20,
    "treat": 10,
    "pomodoro": 9999,
    "quiz": 9999,
    "curious": 9999,
}

POINTS_PER_EVENT = {
    "chat": 1,
    "treat": 2,
    "pomodoro": 5,
    "quiz": 3,
    "curious": 3,
}


def level_for(points: int) -> tuple[int, float]:
    """Berechnet das Freundschafts-Level (1-8) und den Fortschritt zum naechsten Level (0.0 - 1.0)."""
    pts = max(0, int(points))
    max_idx = len(LEVEL_THRESHOLDS) - 1

    for i in range(max_idx, -1, -1):
        if pts >= LEVEL_THRESHOLDS[i]:
            level = i + 1
            if level >= len(LEVEL_THRESHOLDS):
                return 8, 1.0
            next_t = LEVEL_THRESHOLDS[i + 1]
            cur_t = LEVEL_THRESHOLDS[i]
            span = max(1, next_t - cur_t)
            prog = (pts - cur_t) / float(span)
            return level, max(0.0, min(1.0, prog))

    return 1, 0.0


def add_friendship_points(
    store,
    kind: str,
    date_str: Optional[str] = None,
) -> tuple[int, bool, int]:
    """Prueft das Tageslimit und vergibt Freundschaftspunkte.

    Gibt (added_points, did_level_up, new_level) zurueck.
    """
    if date_str is None:
        date_str = datetime.date.today().isoformat()

    limit = DAILY_LIMITS.get(kind, 9999)
    current_count = store.get_daily_friendship_count(kind, date_str)
    if current_count >= limit:
        cur_pts = store.get_friendship_points()
        cur_lvl, _ = level_for(cur_pts)
        return 0, False, cur_lvl

    pts_to_add = POINTS_PER_EVENT.get(kind, 1)
    store.increment_daily_friendship(kind, date_str)

    old_pts = store.get_friendship_points()
    new_pts = old_pts + pts_to_add
    store.set_friendship_points(new_pts)

    old_lvl, _ = level_for(old_pts)
    new_lvl, _ = level_for(new_pts)
    did_level_up = bool(new_lvl > old_lvl)

    return pts_to_add, did_level_up, new_lvl


# ======================================================================================
#  Fokus & Pomodoro-Statistik
# ======================================================================================
def calculate_streak(dates_with_focus: set[str], today: Optional[datetime.date] = None) -> int:
    """Berechnet die ununterbrochene Serie an Tagen mit Fokus-Einheiten."""
    if today is None:
        today = datetime.date.today()

    streak = 0
    cur_d = today
    # Wenn heute noch nichts erledigt wurde, ab gestern pruefen
    if cur_d.isoformat() not in dates_with_focus:
        cur_d = cur_d - datetime.timedelta(days=1)

    while cur_d.isoformat() in dates_with_focus:
        streak += 1
        cur_d = cur_d - datetime.timedelta(days=1)

    return streak


def record_focus_session(store, minutes: int, date_str: Optional[str] = None) -> None:
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    store.record_focus(date_str, max(1, int(minutes)))


def get_focus_stats(store, today: Optional[datetime.date] = None) -> dict:
    if today is None:
        today = datetime.date.today()

    all_data = store.get_focus_data()
    dates_with_focus = {row["date"] for row in all_data if row["count"] > 0}
    streak = calculate_streak(dates_with_focus, today)

    data_by_date = {row["date"]: row for row in all_data}
    today_str = today.isoformat()
    today_row = data_by_date.get(today_str, {"minutes": 0, "count": 0})

    # Letzte 7 Tage (inklusive heute)
    days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if i18n.lang() == "en" else ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    weekly = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        d_str = d.isoformat()
        row = data_by_date.get(d_str, {"minutes": 0, "count": 0})
        day_label = days_names[d.weekday()]
        weekly.append((d_str, day_label, row["minutes"], row["count"]))

    return {
        "today_minutes": today_row["minutes"],
        "today_count": today_row["count"],
        "weekly": weekly,
        "streak": streak,
    }


# ======================================================================================
#  Lernkarten & Leitner-System
# ======================================================================================
def parse_flashcards_text(text: str) -> list[tuple[str, str]]:
    """Parst zeilenbasierten Text im Format 'Vorderseite = Rueckseite'."""
    cards: list[tuple[str, str]] = []
    if not text:
        return cards

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        sep = None
        for candidate in ("=", "->", " - ", ":"):
            if candidate in line:
                sep = candidate
                break

        if sep:
            parts = line.split(sep, 1)
            front, back = parts[0].strip(), parts[1].strip()
            if front and back:
                cards.append((front, back))

    return cards


def parse_gemini_flashcards_json(raw: str) -> list[tuple[str, str]]:
    """Parst KI-generierte Lernkarten aus JSON."""
    if not raw:
        return []

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if m:
            cleaned = m.group(1).strip()

    start_idx = cleaned.find("[")
    end_idx = cleaned.rfind("]")
    if start_idx == -1 or end_idx <= start_idx:
        return []

    try:
        data = json.loads(cleaned[start_idx : end_idx + 1])
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    cards: list[tuple[str, str]] = []
    for item in data:
        if isinstance(item, dict):
            front = str(item.get("front") or item.get("frage") or item.get("question") or "").strip()
            back = str(item.get("back") or item.get("antwort") or item.get("answer") or "").strip()
            if front and back:
                cards.append((front, back))

    return cards


def normalize_answer(ans: str) -> str:
    """Normalisiert eine Antwort fuer robusten Vergleich."""
    s = (ans or "").strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compare_answer(given: str, expected: str) -> tuple[bool, bool]:
    """Vergleicht User-Antwort mit Musterloesung.

    Gibt (is_correct, is_close) zurueck.
    """
    g_norm = normalize_answer(given)
    e_norm = normalize_answer(expected)

    if not g_norm or not e_norm:
        return False, False

    if g_norm == e_norm:
        return True, False

    ratio = difflib.SequenceMatcher(None, g_norm, e_norm).ratio()
    if ratio >= 0.85:
        return True, True

    return False, False


def update_leitner_box(current_box: int, is_correct: bool) -> int:
    """Leitner-Regel: Richtig -> Box + 1 (max 5), Falsch -> Box 1."""
    if is_correct:
        return min(5, max(1, current_box) + 1)
    return 1


# ======================================================================================
#  Fotobox
# ======================================================================================
def generate_photobox_filename(now: Optional[datetime.datetime] = None) -> str:
    if now is None:
        now = datetime.datetime.now()
    return f"Foto_{now.strftime('%Y-%m-%d_%H-%M-%S')}.png"


def photo_crop_rect(pet_x: int, pet_y: int, pet_w: int, pet_h: int,
                    scr_x: int, scr_y: int, scr_w: int, scr_h: int) -> tuple[int, int, int, int]:
    """Quadratischer Selfie-Ausschnitt rund um die Figur (ca. 1,7x ihre Groesse), immer ganz im Bildschirm."""
    side = int(min(max(pet_w, pet_h) * 1.7, scr_w, scr_h))
    x = pet_x + pet_w // 2 - side // 2
    y = pet_y + pet_h + int(side * 0.06) - side          # Figur unten mittig, etwas Boden darunter
    x = max(scr_x, min(x, scr_x + scr_w - side))
    y = max(scr_y, min(y, scr_y + scr_h - side))
    return x, y, side, side


_CAPTIONS_DE = [
    "{pet} & {user} – beste Freunde 🐾", "Selfie-Time mit {pet}! 📸", "{user}s liebste Desktop-Katze 💖",
    "Heute schon gekuschelt? {pet} schon! 😺", "Team {pet} & {user} ✨", "Bitte lächeln… Miau! 😸",
    "{pet} war hier 🐾", "Arbeitspause mit {pet} ☕",
]
_CAPTIONS_EN = [
    "{pet} & {user} – best friends 🐾", "Selfie time with {pet}! 📸", "{user}'s favourite desktop buddy 💖",
    "Team {pet} & {user} ✨", "Say cheese… meow! 😸", "{pet} was here 🐾",
]


def photo_caption(pet: str, user: str, rng=None) -> str:
    """Offline-Spruch fuer den Polaroid-Rand (Gemini-Spruch ersetzt ihn, falls verfuegbar)."""
    import random as _random
    pool = _CAPTIONS_EN if i18n.lang() == "en" else _CAPTIONS_DE
    return (rng or _random).choice(pool).format(pet=pet, user=user)


def shutter_wav() -> bytes:
    """Kurzes Kamera-"Klick-Klack" als WAV im Speicher (Windows hat keinen Ausloese-Sound)."""
    import io
    import random as _random
    import struct
    import wave
    rate, rng = 22050, _random.Random(7)
    samples = []
    for start_ms, length_ms, vol in ((0, 45, 0.55), (85, 60, 0.4)):
        while len(samples) < rate * start_ms // 1000:
            samples.append(0)
        n = rate * length_ms // 1000
        for i in range(n):
            samples.append(int(32767 * vol * (1 - i / n) ** 3 * (rng.random() * 2 - 1)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def frame_photobox_image(photo: QImage, caption: str, date_str: str, angle: float = -3.0,
                         size: int = 900) -> QImage:
    """Echtes Polaroid: quadratisches Foto, breiter Rand unten mit Handschrift, leicht schief, weicher Schatten.
    Rueckgabe hat einen transparenten Hintergrund."""
    from PyQt6.QtGui import QTransform
    border = int(size * 0.06)
    bottom = int(size * 0.26)
    pw, ph = size + 2 * border, size + border + bottom

    card = QImage(pw, ph, QImage.Format.Format_ARGB32_Premultiplied)
    card.fill(QColor(252, 250, 245))
    p = QPainter(card)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    side = min(photo.width(), photo.height())
    src = photo.copy((photo.width() - side) // 2, (photo.height() - side) // 2, side, side)
    p.drawImage(QRectF(border, border, size, size), src)
    p.setPen(QPen(QColor(0, 0, 0, 30), 1.0))
    p.drawRect(QRectF(border, border, size, size))
    # leichter Glanz wie bei echtem Fotopapier
    p.fillRect(QRectF(border, border, size, size * 0.35), QColor(255, 255, 255, 14))

    p.setPen(QColor(55, 55, 65))
    cap_font = QFont("Segoe Print", 10)
    cap_font.setPixelSize(int(bottom * 0.24))
    while QFontMetrics(cap_font).horizontalAdvance(caption) > pw - 2 * border and cap_font.pixelSize() > 12:
        cap_font.setPixelSize(cap_font.pixelSize() - 2)
    p.setFont(cap_font)
    p.drawText(QRectF(border, size + border + bottom * 0.12, size, bottom * 0.45),
               Qt.AlignmentFlag.AlignCenter, caption)
    date_font = QFont("Segoe Print", 10)
    date_font.setPixelSize(int(bottom * 0.15))
    p.setFont(date_font)
    p.setPen(QColor(120, 120, 130))
    p.drawText(QRectF(border, size + border + bottom * 0.58, size, bottom * 0.3),
               Qt.AlignmentFlag.AlignCenter, f"{date_str}  ·  Desktop Cat 🐾")
    p.end()

    rotated = card.transformed(QTransform().rotate(angle), Qt.TransformationMode.SmoothTransformation)
    pad = int(size * 0.05)
    out = QImage(rotated.width() + 2 * pad, rotated.height() + 2 * pad, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # weicher Schatten: mehrere versetzte, halbtransparente Kopien der Kartenform
    shadow = QImage(rotated.size(), QImage.Format.Format_ARGB32_Premultiplied)
    shadow.fill(Qt.GlobalColor.transparent)
    sp = QPainter(shadow)
    sp.drawImage(0, 0, rotated)
    sp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    sp.fillRect(shadow.rect(), QColor(0, 0, 0, 255))
    sp.end()
    for i, alpha in enumerate((0.05, 0.05, 0.05, 0.05, 0.04, 0.03)):
        p.setOpacity(alpha)
        off = pad * 0.25 + i * 3
        p.drawImage(QPointF(pad + off * 0.4, pad + off), shadow)
    p.setOpacity(1.0)
    p.drawImage(QPointF(pad, pad), rotated)
    p.end()
    return out


def flatten_on_white(img: QImage) -> QImage:
    """Fuer die Zwischenablage: viele Apps zeigen Transparenz schwarz an."""
    out = QImage(img.size(), QImage.Format.Format_RGB32)
    out.fill(QColor(255, 255, 255))
    p = QPainter(out)
    p.drawImage(0, 0, img)
    p.end()
    return out

