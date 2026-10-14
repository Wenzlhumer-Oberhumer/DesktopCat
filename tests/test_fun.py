# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer Phase 6: Freundschaft, Fokus-Statistik, Lernkarten, Fotobox und Notizen."""
from __future__ import annotations

import datetime
import tempfile
from pathlib import Path

from PyQt6.QtGui import QColor, QImage

from fun import (
    add_friendship_points, calculate_streak, compare_answer,
    frame_photobox_image, generate_photobox_filename, level_for,
    parse_flashcards_text, parse_gemini_flashcards_json, update_leitner_box,
)
from memory_store import MemoryStore


def test_level_for():
    # Level 1: 0..24
    lvl, prog = level_for(0)
    assert lvl == 1 and prog == 0.0
    lvl, prog = level_for(12)
    assert lvl == 1 and abs(prog - 12 / 25.0) < 1e-4

    # Level 2: 25..74
    lvl, prog = level_for(25)
    assert lvl == 2 and prog == 0.0
    lvl, prog = level_for(50)
    assert lvl == 2 and abs(prog - 0.5) < 1e-4

    # Level 3: 75..149
    lvl, prog = level_for(75)
    assert lvl == 3 and prog == 0.0

    # Level 8: >= 1200
    lvl, prog = level_for(1200)
    assert lvl == 8 and prog == 1.0
    lvl, prog = level_for(2500)
    assert lvl == 8 and prog == 1.0


def test_daily_limits():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_fun.db"
        store = MemoryStore(db_path)
        today = "2026-10-14"

        # Chat: Max 20 Punkte pro Tag (je 1 Pkt.)
        for _ in range(20):
            added, _, _ = add_friendship_points(store, "chat", date_str=today)
            assert added == 1

        # 21. Chat am selben Tag darf keine Punkte bringen
        added, _, _ = add_friendship_points(store, "chat", date_str=today)
        assert added == 0

        # Neuer Tag: Chat bringt wieder Punkte
        added, _, _ = add_friendship_points(store, "chat", date_str="2026-10-15")
        assert added == 1

        # Leckerli: Max 10 Einheiten pro Tag (je 2 Pkt.)
        for _ in range(10):
            added, _, _ = add_friendship_points(store, "treat", date_str=today)
            assert added == 2

        # 11. Leckerli am selben Tag: keine Punkte
        added, _, _ = add_friendship_points(store, "treat", date_str=today)
        assert added == 0


def test_leitner_logic():
    # Richtig -> Box + 1 (max 5)
    assert update_leitner_box(1, is_correct=True) == 2
    assert update_leitner_box(2, is_correct=True) == 3
    assert update_leitner_box(4, is_correct=True) == 5
    assert update_leitner_box(5, is_correct=True) == 5

    # Falsch -> Zurueck auf Box 1
    assert update_leitner_box(5, is_correct=False) == 1
    assert update_leitner_box(3, is_correct=False) == 1
    assert update_leitner_box(1, is_correct=False) == 1


def test_compare_answer():
    # Exakt gleich
    ok, close = compare_answer("Paris", "Paris")
    assert ok and not close

    # Gross-/Kleinschreibung & Leerzeichen
    ok, close = compare_answer("  berlin ", "Berlin")
    assert ok and not close

    # Umlaute & Sonderzeichen
    ok, close = compare_answer("München!", "Muenchen")
    assert ok

    # Kleine Tippfehler (difflib >= 0.85) -> fast richtig
    ok, close = compare_answer("Photosyntese", "Photosynthese")
    assert ok and close

    # Falsch
    ok, close = compare_answer("Rom", "Paris")
    assert not ok and not close

    # Leere Eingabe
    ok, close = compare_answer("", "Paris")
    assert not ok and not close


def test_parse_flashcards_text():
    raw = """
    # Kommentarzeile
    Hund = Dog
    Katze -> Cat
    Maus : Mouse
    Ungültige Zeile ohne Trenner

    Apfel - Apple
    """
    cards = parse_flashcards_text(raw)
    assert len(cards) == 4
    assert cards[0] == ("Hund", "Dog")
    assert cards[1] == ("Katze", "Cat")
    assert cards[2] == ("Maus", "Mouse")
    assert cards[3] == ("Apfel", "Apple")


def test_parse_gemini_flashcards_json():
    # Markdown Block
    raw_md = """```json
    [
        {"front": "Wasser", "back": "H2O"},
        {"front": "Sauerstoff", "back": "O2"}
    ]
    ```"""
    cards = parse_gemini_flashcards_json(raw_md)
    assert len(cards) == 2
    assert cards[0] == ("Wasser", "H2O")
    assert cards[1] == ("Sauerstoff", "O2")

    # Roher JSON String mit alternativen Keys
    raw_alt = '[{"frage": "Hauptstadt von Frankreich?", "antwort": "Paris"}]'
    cards_alt = parse_gemini_flashcards_json(raw_alt)
    assert len(cards_alt) == 1
    assert cards_alt[0] == ("Hauptstadt von Frankreich?", "Paris")

    # Defektes JSON
    assert parse_gemini_flashcards_json("kein json") == []


def test_focus_streak():
    today = datetime.date(2026, 10, 14)

    # 3 Tage in Folge inklusive heute
    dates = {"2026-10-14", "2026-10-13", "2026-10-12"}
    assert calculate_streak(dates, today) == 3

    # Heute noch nichts, aber gestern und vorgestern -> Streak 2
    dates_yesterday = {"2026-10-13", "2026-10-12"}
    assert calculate_streak(dates_yesterday, today) == 2

    # Luecke vor 2 Tagen
    dates_gap = {"2026-10-14", "2026-10-12"}
    assert calculate_streak(dates_gap, today) == 1

    # Gar keine Eintraege
    assert calculate_streak(set(), today) == 0


def test_photobox_filename_and_frame():
    dt = datetime.datetime(2026, 10, 14, 15, 30, 45)
    fn = generate_photobox_filename(dt)
    assert fn == "Foto_2026-10-14_15-30-45.png"

    # Polaroid Rahmen zeichnen
    test_img = QImage(200, 150, QImage.Format.Format_ARGB32_Premultiplied)
    test_img.fill(QColor("skyblue"))

    framed = frame_photobox_image(test_img, "14.10.2026 15:30", "Kylie")
    assert not framed.isNull()
    assert framed.width() > test_img.width()
    assert framed.height() > test_img.height()


def test_notes_crud_and_wipe():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_notes.db"
        store = MemoryStore(db_path)

        # 1. Notiz anlegen
        nid = store.add_note("Milch kaufen", color="mint", x=150, y=200)
        assert nid > 0

        notes = store.get_notes(include_done=False)
        assert len(notes) == 1
        assert notes[0]["text"] == "Milch kaufen"
        assert notes[0]["color"] == "mint"
        assert notes[0]["x"] == 150
        assert notes[0]["y"] == 200

        # 2. Notiz aktualisieren (Verschieben & Text)
        store.update_note(nid, text="Hafermilch kaufen", x=180, y=220)
        updated = store.get_notes()[0]
        assert updated["text"] == "Hafermilch kaufen"
        assert updated["x"] == 180
        assert updated["y"] == 220

        # 3. Als erledigt markieren
        store.update_note(nid, done=1)
        assert len(store.get_notes(include_done=False)) == 0
        assert len(store.get_notes(include_done=True)) == 1

        # 4. Lernkarten und Fokus ebenfalls speichern
        assert store.add_card("Englisch", "Cat", "Katze") > 0
        store.record_focus("2026-10-14", 25)
        store.set_friendship_points(150)
        assert len(store.get_cards()) == 1
        assert len(store.get_focus_data()) == 1
        assert store.get_friendship_points() == 150

        # 5. wipe_everything() loescht alles restlos
        store.wipe_everything()
        assert len(store.get_notes(include_done=True)) == 0
        assert len(store.get_cards()) == 0
        assert len(store.get_focus_data()) == 0
        assert store.get_friendship_points() == 0
