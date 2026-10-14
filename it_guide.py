# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""IT-Support-Modus und Klick-Anleitung: Schritt-Logik, Screenshot-Analyse und Koordinaten-Mapping."""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

from PyQt6.QtCore import QBuffer, QByteArray, QRect, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

import gemini

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = {"left", "right", "double", "type", "scroll", "none"}


def parse_guide_step(text: str) -> Optional[dict]:
    """Parst die Modell-Antwort robust als JSON und validiert die Felder."""
    if not text:
        return None
    cleaned = text.strip()

    # Markdown-Codebloecke entfernen (```json ... ``` oder ``` ... ```)
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()

    # Nach JSON-Objekt suchen { ... }
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if not m:
        return None
    json_str = m.group(0)

    try:
        data = json.loads(json_str)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    say = str(data.get("say", "")).strip()
    action = str(data.get("action", "none")).strip().lower()
    if action not in ALLOWED_ACTIONS:
        action = "none"

    target = str(data.get("target", "")).strip()
    box_raw = data.get("box_2d")
    box_2d: Optional[list[int]] = None
    if isinstance(box_raw, (list, tuple)) and len(box_raw) == 4:
        try:
            box_2d = [int(round(float(v))) for v in box_raw]
        except (ValueError, TypeError):
            box_2d = None

    done = bool(data.get("done", False))
    try:
        total_steps = int(data.get("total_steps", 3))
    except (ValueError, TypeError):
        total_steps = 3

    return {
        "say": say,
        "action": action,
        "target": target,
        "box_2d": box_2d,
        "done": done,
        "total_steps": max(1, total_steps),
    }


def box_to_screen(
    box_2d: Optional[list[int]],
    screen_geometry: QRect,
    image_size: Optional[tuple[int, int]] = None,
    dpi_ratio: float = 1.0,
) -> Optional[QRect]:
    """Wandelt [ymin, xmin, ymax, xmax] (0-1000 normiert) in logische Bildschirm-Pixel um.

    Beachtet Monitor-Offset und clampet auf den Bildschirm.
    Unplausible Boxen (Flaeche <= 0 oder > 50 % des Bildschirms) werden verworfen (None).
    """
    if not box_2d or len(box_2d) != 4:
        return None

    ymin, xmin, ymax, xmax = box_2d
    if xmax <= xmin or ymax <= ymin:
        return None

    # Normierte Flaeche pruefen (0..1)
    norm_w = (xmax - xmin) / 1000.0
    norm_h = (ymax - ymin) / 1000.0
    norm_area = norm_w * norm_h
    if norm_area <= 0 or norm_area > 0.50:
        return None

    sw = screen_geometry.width()
    sh = screen_geometry.height()
    sx = screen_geometry.x()
    sy = screen_geometry.y()

    if sw <= 0 or sh <= 0:
        return None

    x = sx + int(round(xmin / 1000.0 * sw))
    y = sy + int(round(ymin / 1000.0 * sh))
    w = int(round(norm_w * sw))
    h = int(round(norm_h * sh))

    rect = QRect(x, y, w, h)
    clamped = rect.intersected(screen_geometry)
    if clamped.isEmpty() or clamped.width() <= 0 or clamped.height() <= 0:
        return None

    # Gesamtflaeche pruefen
    total_area = sw * sh
    if clamped.width() * clamped.height() > 0.50 * total_area:
        return None

    return clamped


def pixmap_to_b64(pixmap: QPixmap, max_width: int = 1600) -> str:
    """Skaliert ein QPixmap auf max_width und wandelt es in Base64-PNG um."""
    if pixmap.isNull():
        return ""
    if pixmap.width() > max_width:
        scaled = pixmap.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)
    else:
        scaled = pixmap

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    scaled.save(buf, "PNG")
    buf.close()
    return base64.b64encode(ba.data()).decode("ascii")


class GuideSession:
    """Verwaltet den Fortschritt einer Klick-Anleitungs-Sitzung (max. 12 Schritte)."""

    def __init__(self, question: str, user_name: str = "Boss", char_id: str = "cat_mochi"):
        self.question = question
        self.user_name = user_name
        self.char_id = char_id
        self.step_no = 0
        self.history: list[str] = []
        self.total_steps = 3
        self.done = False

    def format_prompt(self) -> str:
        hist_str = "; ".join(self.history) if self.history else "Keine bisherigen Schritte."
        return (
            f"Du bist ein geduldiger IT-Helfer. Frage des Nutzers: \"{self.question}\".\n"
            f"Bisherige Schritte: {hist_str}.\n"
            "Schau dir den Screenshot an und gib GENAU EINEN nächsten Schritt als JSON zurück, ohne Markdown:\n"
            "{\"say\": \"<kurze Anweisung auf Deutsch, 1 Satz>\", \"action\": \"left|right|double|type|scroll|none\",\n"
            " \"target\": \"<Name des Elements>\", \"box_2d\": [ymin, xmin, ymax, xmax], \"done\": false,\n"
            " \"total_steps\": <Schätzung>}\n"
            "box_2d in 0-1000 normierten Koordinaten des Bildes. Wenn das Ziel nicht sichtbar ist (z. B. Programm nicht offen), action \"none\", box_2d null und say erklärt, was der Nutzer zuerst öffnen soll. Wenn fertig: \"done\": true.\n"
            "Erfinde keine Positionen. Wenn du unsicher bist, box_2d null."
        )

    def next_step(
        self,
        image_b64: str = "",
        screen_geometry: Optional[QRect] = None,
        ask_fn=None,
    ) -> tuple[dict, Optional[QRect]]:
        """Fuehrt den naechsten Schritt aus (ruft gemini.ask auf, parst Antwort und mappt Box)."""
        if self.step_no >= 12:
            self.done = True
            finish_step = {
                "say": "Das waren viele Schritte – ich hoffe, du hast alles gefunden! 🐾",
                "action": "none",
                "target": "",
                "box_2d": None,
                "done": True,
                "total_steps": self.step_no,
            }
            return finish_step, None

        if ask_fn is None:
            ask_fn = gemini.ask

        prompt = self.format_prompt()
        raw = ask_fn(prompt, timeout_s=45.0, image_b64=image_b64 if image_b64 else None)
        parsed = parse_guide_step(raw)
        if parsed is None:
            parsed = {
                "say": "Ich konnte die Bildschirmanweisung nicht ganz verstehen – bitte versuch es nochmal 🐾",
                "action": "none",
                "target": "",
                "box_2d": None,
                "done": False,
                "total_steps": max(self.total_steps, self.step_no + 1),
            }

        self.step_no += 1
        if self.step_no >= 12:
            parsed["done"] = True
        self.done = bool(parsed.get("done", False))
        self.total_steps = int(parsed.get("total_steps", self.total_steps))

        say_txt = parsed.get("say", "")
        self.history.append(f"Schritt {self.step_no}: {say_txt}")

        rect = None
        if screen_geometry is not None and parsed.get("box_2d") is not None:
            rect = box_to_screen(parsed["box_2d"], screen_geometry)

        return parsed, rect


class GuideWorker(QThread):
    """Worker-Thread fuer einen Analyseschritt des IT-Guides."""

    step_ready = pyqtSignal(dict, object)
    failed = pyqtSignal(str)

    def __init__(self, session: GuideSession, image_b64: str, screen_geometry: QRect, ask_fn=None):
        super().__init__()
        self.session = session
        self.image_b64 = image_b64
        self.screen_geometry = screen_geometry
        self.ask_fn = ask_fn

    def run(self) -> None:
        try:
            step, rect = self.session.next_step(
                image_b64=self.image_b64,
                screen_geometry=self.screen_geometry,
                ask_fn=self.ask_fn,
            )
            self.step_ready.emit(step, rect)
        except Exception as exc:
            logger.exception("GuideWorker Fehler")
            self.failed.emit(str(exc))
