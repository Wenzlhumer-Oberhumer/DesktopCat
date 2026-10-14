# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer Alltagslogik: Neugier-Fragen, Erinnerungen, Briefing, Geburtstag und Schlafenszeit."""
from __future__ import annotations

import datetime

from daily import (
    bedtime_due,
    curious_question_for,
    due_reminders,
    next_birthday,
    parse_birthday_mention,
    should_ask_curious,
    should_brief,
)


def test_should_ask_curious():
    cfg = {"daily": {"curious": True}, "privacy": {"remember": True}}

    # Tag, keine Fragen bisher
    now_day = datetime.datetime(2026, 10, 14, 14, 0, 0)
    stats_empty = {}
    assert should_ask_curious(now_day, stats_empty, cfg) is True

    # Nachts (23:30 oder 04:00) -> nicht fragen
    now_night = datetime.datetime(2026, 10, 14, 23, 30, 0)
    assert should_ask_curious(now_night, stats_empty, cfg) is False
    now_early = datetime.datetime(2026, 10, 14, 4, 0, 0)
    assert should_ask_curious(now_early, stats_empty, cfg) is False

    # Max 2 Fragen am selben Tag erreicht
    stats_limit = {"curious_date": "2026-10-14", "curious_count": "2", "curious_last_ts": "0"}
    assert should_ask_curious(now_day, stats_limit, cfg) is False

    # 1 Frage gestellt, aber erst 30 Min her (< 2h)
    stats_recent = {
        "curious_date": "2026-10-14",
        "curious_count": "1",
        "curious_last_ts": str(now_day.timestamp() - 1800),
    }
    assert should_ask_curious(now_day, stats_recent, cfg) is False

    # 1 Frage gestellt, mehr als 2h her -> darf fragen
    stats_ok = {
        "curious_date": "2026-10-14",
        "curious_count": "1",
        "curious_last_ts": str(now_day.timestamp() - 7500),
    }
    assert should_ask_curious(now_day, stats_ok, cfg) is True

    # Schalter deaktiviert
    assert should_ask_curious(now_day, stats_empty, {"daily": {"curious": False}, "privacy": {"remember": True}}) is False
    assert should_ask_curious(now_day, stats_empty, {"daily": {"curious": True}, "privacy": {"remember": False}}) is False


def test_next_birthday():
    today = datetime.date(2026, 3, 10)

    # Geburtstag spaeter im selben Jahr
    nb1 = next_birthday(14, 3, today)
    assert nb1 == datetime.date(2026, 3, 14)

    # Geburtstag heute
    nb2 = next_birthday(10, 3, today)
    assert nb2 == datetime.date(2026, 3, 10)

    # Geburtstag lag frueher im Jahr -> naechstes Jahr
    nb3 = next_birthday(5, 1, today)
    assert nb3 == datetime.date(2027, 1, 5)


def test_parse_birthday_mention():
    today = datetime.date(2026, 5, 1)

    res1 = parse_birthday_mention("Ich habe am 14. März Geburtstag!", today)
    assert res1 is not None
    day, mon, nxt = res1
    assert day == 14
    assert mon == 3
    assert nxt == datetime.date(2027, 3, 14)

    res2 = parse_birthday_mention("Mein Geburtstag ist am 25.12.", today)
    assert res2 is not None
    d2, m2, n2 = res2
    assert d2 == 25
    assert m2 == 12
    assert n2 == datetime.date(2026, 12, 25)

    assert parse_birthday_mention("Wie ist das Wetter in Wien?", today) is None


def test_due_reminders():
    facts = [
        {"id": 1, "text": "Mathematik-Prüfung", "due_date": "2026-06-15", "kind": "fact"},
        {"id": 2, "text": "Mama", "due_date": "2026-06-15", "kind": "birthday"},
    ]

    # 14. Juni, 19:00 Uhr -> Vorabend
    now_eve = datetime.datetime(2026, 6, 14, 19, 0, 0)
    rems_eve = due_reminders(facts, now_eve)
    assert len(rems_eve) == 2
    assert any("Morgen ist" in msg for _, msg, _ in rems_eve)
    assert any("Morgen hat" in msg for _, msg, _ in rems_eve)

    # 14. Juni, 12:00 Uhr -> noch nicht Vorabend
    now_noon = datetime.datetime(2026, 6, 14, 12, 0, 0)
    assert len(due_reminders(facts, now_noon)) == 0

    # 15. Juni, 08:00 Uhr -> Tag selbst
    now_day = datetime.datetime(2026, 6, 15, 8, 0, 0)
    rems_day = due_reminders(facts, now_day)
    assert len(rems_day) == 2
    assert any("Heute steht" in msg for _, msg, _ in rems_day)
    assert any("Alles Gute zum Geburtstag" in msg for _, msg, _ in rems_day)

    # 16. Juni, 09:00 Uhr -> Tag danach (Nachfrage, aber nicht fuer Geburtstag)
    now_after = datetime.datetime(2026, 6, 16, 9, 0, 0)
    rems_after = due_reminders(facts, now_after)
    assert len(rems_after) == 1
    assert "Wie lief eigentlich" in rems_after[0][1]

    # Wenn bereits in stats vermerkt -> keine Wiederholung
    stat_key = rems_after[0][2]
    stats = {stat_key: "1"}
    assert len(due_reminders(facts, now_after, stats)) == 0


def test_should_brief():
    # Vor 05:00 Uhr -> False
    now_early = datetime.datetime(2026, 10, 14, 4, 30, 0)
    assert should_brief(now_early, None) is False

    # Nach 05:00 Uhr, heute noch nicht -> True
    now_morn = datetime.datetime(2026, 10, 14, 7, 30, 0)
    assert should_brief(now_morn, None) is True
    assert should_brief(now_morn, "2026-10-13") is True

    # Heute schon gezeigt -> False
    assert should_brief(now_morn, "2026-10-14") is False


def test_bedtime_due():
    bedtime = "23:00"

    # Noch vor der Zeit (21:00)
    now_early = datetime.datetime(2026, 10, 14, 21, 0, 0)
    assert bedtime_due(now_early, bedtime) == (False, False)

    # Zur Zeit (23:15), noch nie gezeigt
    now_night = datetime.datetime(2026, 10, 14, 23, 15, 0)
    assert bedtime_due(now_night, bedtime, None) == (True, False)

    # Vor 10 Minuten gezeigt (< 30 min) -> nichts
    last_10m = now_night.timestamp() - 600
    assert bedtime_due(now_night, bedtime, last_10m) == (False, False)

    # Vor 40 Minuten gezeigt (30-90 min spaeter) -> zweite Erinnerung
    last_40m = now_night.timestamp() - 2400
    assert bedtime_due(now_night, bedtime, last_40m) == (True, True)

    # Leere Schlafenszeit -> aus
    assert bedtime_due(now_night, "") == (False, False)


def test_curious_question_for():
    q_cat = curious_question_for("cat_mochi", "Florian")
    assert len(q_cat) > 5
    assert "Florian" in q_cat or "?" in q_cat

    q_dog = curious_question_for("dog_shiba", "Florian")
    assert len(q_dog) > 5

    q_fan = curious_question_for("fantasy_byte", "Florian")
    assert len(q_fan) > 5
