# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer Phase 5: IT-Support, Klick-Guide, Koordinaten-Mapping und Overlay."""
import json
import re
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtWidgets import QApplication

from guide_overlay import GuideOverlay
from it_guide import GuideSession, box_to_screen, parse_guide_step
from speech_bubble import ExplainCard, SpeechBubble


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_parse_guide_step_valid_json():
    raw = json.dumps({
        "say": "Klick auf Start.",
        "action": "left",
        "target": "Startmenü",
        "box_2d": [900, 10, 990, 50],
        "done": False,
        "total_steps": 3,
    })
    step = parse_guide_step(raw)
    assert step is not None
    assert step["say"] == "Klick auf Start."
    assert step["action"] == "left"
    assert step["target"] == "Startmenü"
    assert step["box_2d"] == [900, 10, 990, 50]
    assert step["done"] is False
    assert step["total_steps"] == 3


def test_parse_guide_step_markdown_fence():
    raw = """```json
{
  "say": "Klick auf Datei.",
  "action": "left",
  "target": "Datei-Reiter",
  "box_2d": [50, 60, 90, 120],
  "done": false,
  "total_steps": 4
}
```"""
    step = parse_guide_step(raw)
    assert step is not None
    assert step["say"] == "Klick auf Datei."
    assert step["action"] == "left"
    assert step["box_2d"] == [50, 60, 90, 120]
    assert step["done"] is False


def test_parse_guide_step_null_box():
    raw = json.dumps({
        "say": "Öffne zuerst Word.",
        "action": "none",
        "target": "",
        "box_2d": None,
        "done": False,
        "total_steps": 3,
    })
    step = parse_guide_step(raw)
    assert step is not None
    assert step["say"] == "Öffne zuerst Word."
    assert step["action"] == "none"
    assert step["box_2d"] is None
    assert step["done"] is False


def test_parse_guide_step_broken_json():
    raw = "Hier ist der Schritt: { say: nicht abgeschlossen, action: left "
    step = parse_guide_step(raw)
    assert step is None

    empty_step = parse_guide_step("")
    assert empty_step is None


def test_parse_guide_step_done_true():
    raw = json.dumps({
        "say": "Fertig eingerichtet! 🎉",
        "action": "none",
        "target": "",
        "box_2d": None,
        "done": True,
        "total_steps": 2,
    })
    step = parse_guide_step(raw)
    assert step is not None
    assert step["done"] is True


def test_box_to_screen_coordinates_and_multimonitor():
    # 1. Hauptmonitor (0, 0, 1920, 1080), DPI 1.0
    screen1 = QRect(0, 0, 1920, 1080)
    box = [100, 200, 300, 400]  # ymin=100, xmin=200, ymax=300, xmax=400
    rect1 = box_to_screen(box, screen1, dpi_ratio=1.0)
    assert rect1 is not None
    assert rect1.x() == 384   # 200 / 1000 * 1920
    assert rect1.y() == 108   # 100 / 1000 * 1080
    assert rect1.width() == 384
    assert rect1.height() == 216

    # 2. Zweiter Monitor links mit negativem x (-1920, 0, 1920, 1080)
    screen2 = QRect(-1920, 0, 1920, 1080)
    rect2 = box_to_screen(box, screen2, dpi_ratio=1.0)
    assert rect2 is not None
    assert rect2.x() == -1920 + 384  # -1536
    assert rect2.y() == 108
    assert rect2.width() == 384
    assert rect2.height() == 216

    # 3. DPI 1.5 Skalierung (logische Aufloesung 1280x720)
    screen_scaled = QRect(0, 0, 1280, 720)
    rect3 = box_to_screen(box, screen_scaled, dpi_ratio=1.5)
    assert rect3 is not None
    assert rect3.x() == 256   # 200 / 1000 * 1280
    assert rect3.y() == 72    # 100 / 1000 * 720
    assert rect3.width() == 256
    assert rect3.height() == 144


def test_box_to_screen_unplausible_boxes():
    screen = QRect(0, 0, 1920, 1080)
    # None box
    assert box_to_screen(None, screen) is None
    # Falsche Laenge
    assert box_to_screen([100, 200], screen) is None
    # Flaeche <= 0 (xmax <= xmin oder ymax <= ymin)
    assert box_to_screen([100, 200, 100, 400], screen) is None
    assert box_to_screen([100, 400, 300, 200], screen) is None
    # > 50 % des Bildschirms (z. B. 800x800 normiert = 64 % Flaeche)
    assert box_to_screen([0, 0, 800, 800], screen) is None


def test_guide_session_flow_and_abort():
    # Mock-Antworten fuer 3 Schritte bis done
    mock_responses = [
        json.dumps({"say": "Klick auf Datei", "action": "left", "target": "Datei", "box_2d": [10, 10, 50, 50], "done": False, "total_steps": 3}),
        json.dumps({"say": "Klick auf Optionen", "action": "left", "target": "Optionen", "box_2d": [60, 10, 100, 50], "done": False, "total_steps": 3}),
        json.dumps({"say": "Fertig!", "action": "none", "target": "", "box_2d": None, "done": True, "total_steps": 3}),
    ]
    resp_iter = iter(mock_responses)

    def mock_ask(prompt, timeout_s=45.0, image_b64=None):
        return next(resp_iter)

    session = GuideSession("Wo sind Optionen?", user_name="TestBoss", char_id="cat_mochi")
    screen = QRect(0, 0, 1000, 1000)

    # Schritt 1
    s1, r1 = session.next_step(screen_geometry=screen, ask_fn=mock_ask)
    assert session.step_no == 1
    assert session.done is False
    assert r1 is not None
    assert "Schritt 1: Klick auf Datei" in session.history[0]

    # Schritt 2
    s2, r2 = session.next_step(screen_geometry=screen, ask_fn=mock_ask)
    assert session.step_no == 2
    assert session.done is False
    assert r2 is not None

    # Schritt 3 (done)
    s3, r3 = session.next_step(screen_geometry=screen, ask_fn=mock_ask)
    assert session.step_no == 3
    assert session.done is True
    assert s3["done"] is True

    # Test: Abbruch nach max. 12 Schritten
    infinite_session = GuideSession("Endlos-Frage")
    def mock_infinite_ask(prompt, timeout_s=45.0, image_b64=None):
        return json.dumps({"say": "Weiterer Schritt...", "action": "left", "target": "Btn", "box_2d": [10, 10, 50, 50], "done": False, "total_steps": 20})

    for i in range(12):
        step, _ = infinite_session.next_step(screen_geometry=screen, ask_fn=mock_infinite_ask)
        if i == 11:
            assert infinite_session.done is True
            assert step["done"] is True
    assert infinite_session.step_no == 12

    # 13. Aufruf liefert Abbruch
    s13, _ = infinite_session.next_step(screen_geometry=screen, ask_fn=mock_infinite_ask)
    assert s13["done"] is True


def test_overlay_flags_and_clickthrough():
    _ensure_app()
    overlay = GuideOverlay()
    flags = overlay.windowFlags()
    # Pruefe transparente Eingabe (Klicks gehen durch)
    assert bool(flags & Qt.WindowType.WindowTransparentForInput) is True
    assert bool(flags & Qt.WindowType.FramelessWindowHint) is True
    assert bool(flags & Qt.WindowType.WindowStaysOnTopHint) is True
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) is True


def test_no_simulated_mouse_calls():
    """Verifiziert, dass kein Code-Pfad in *.py SetCursorPos, SendInput, mouse_event oder pyautogui aufruft."""
    repo_root = Path(__file__).resolve().parent.parent
    forbidden_patterns = [
        re.compile(r"\bSetCursorPos\b"),
        re.compile(r"\bSendInput\b"),
        re.compile(r"\bmouse_event\b"),
        re.compile(r"\bpyautogui\b"),
    ]

    found_violations = []
    for py_file in repo_root.glob("*.py"):
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                for pat in forbidden_patterns:
                    if pat.search(line):
                        found_violations.append(f"{py_file.name}:{line_no}: {line.strip()}")

    assert found_violations == [], "Verbotene Maus-Simulationen gefunden:\n" + "\n".join(found_violations)


def test_speech_bubble_show_with_actions():
    _ensure_app()
    bubble = SpeechBubble()
    action_called = []
    actions = [
        ("Weiter ▶", lambda: action_called.append("weiter")),
        ("Fertig ✖", lambda: action_called.append("fertig")),
    ]
    bubble.show_with_actions("Test-Anweisung", actions)
    assert bubble._actions_active is True
    assert len(bubble._buttons) == 2

    # Klick auf Weiter
    bubble._buttons[0].click()
    assert action_called == ["weiter"]
    assert bubble._actions_active is False


def test_explain_card():
    _ensure_app()
    card = ExplainCard()
    card.show_result("💡 Test-Titel", "Das ist der erklärte Text.", QPoint(100, 100))
    assert card.title_label.text() == "💡 Test-Titel"
    assert card.text_label.text() == "Das ist der erklärte Text."
    assert card.isVisible() is True
