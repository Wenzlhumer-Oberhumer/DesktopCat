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
    days_names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
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


def frame_photobox_image(screenshot: QImage, date_time_str: str, char_name: str = "Kylie") -> QImage:
    """Erstellt ein huebsches Polaroid-Foto mit weissem Rahmen, Datum und Stempel."""
    sw, sh = screenshot.width(), screenshot.height()

    border_side = max(18, int(sw * 0.025))
    border_top = border_side
    border_bottom = int(border_side * 2.8)

    fw = sw + 2 * border_side
    fh = sh + border_top + border_bottom

    framed = QImage(fw, fh, QImage.Format.Format_ARGB32_Premultiplied)
    framed.fill(QColor(250, 248, 245))

    p = QPainter(framed)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # 1. Bild zeichnen
    photo_rect = QRectF(border_side, border_top, sw, sh)
    p.drawImage(photo_rect, screenshot)

    # Sanfter Schatten/Rahmen um das Foto
    p.setPen(QPen(QColor(0, 0, 0, 40), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(photo_rect)

    # 2. Unterer Bereich mit Stempel
    stamp_y = sh + border_top + int(border_bottom * 0.4)
    font = QFont("Segoe UI", max(11, int(border_bottom * 0.22)))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor(60, 62, 68))

    stamp_text = f"Desktop Cat 🐾  •  {char_name} & Du  •  {date_time_str}"
    fm = QFontMetrics(font)
    tw = fm.horizontalAdvance(stamp_text)
    tx = (fw - tw) / 2.0
    p.drawText(QPointF(tx, stamp_y), stamp_text)

    # Kleine Deko-Herzen links und rechts
    heart_font = QFont("Segoe UI", max(12, int(border_bottom * 0.26)))
    p.setFont(heart_font)
    p.setPen(QColor("#FF8FB1"))
    p.drawText(QPointF(border_side + 10, stamp_y), "💖")
    p.drawText(QPointF(fw - border_side - 30, stamp_y), "✨")

    p.end()
    return framed
