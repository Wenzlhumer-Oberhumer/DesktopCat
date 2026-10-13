"""Tests fuer MemoryStore, Chat-Speicherung, Fakten und Datenschutz."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from agent_brain import confirm_question, parse_cli_response, parse_offline
from memory_store import MemoryStore
from tools import DANGEROUS_TOOLS


def test_add_message_and_30min_split():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        t0 = 100000.0
        with patch("time.time", return_value=t0):
            store.add_message("user", "Hallo Kylie, wie geht es dir?", "cat_mochi")
            store.add_message("assistant", "Mir geht es super!", "cat_mochi")

        convs = store.conversations()
        assert len(convs) == 1
        assert convs[0]["title"] == "Hallo Kylie, wie geht es dir?"[:40]
        assert convs[0]["msg_count"] == 2

        # 10 Minuten spaeter -> selbes Gespraech
        with patch("time.time", return_value=t0 + 600):
            store.add_message("user", "Noch eine Frage...", "cat_mochi")

        convs = store.conversations()
        assert len(convs) == 1
        assert convs[0]["msg_count"] == 3

        # 35 Minuten nach der letzten Nachricht -> neues Gespraech
        with patch("time.time", return_value=t0 + 600 + 2100):
            store.add_message("user", "Ein neues Thema heute", "cat_mochi")

        convs = store.conversations()
        assert len(convs) == 2
        # Neuestes zuerst
        assert convs[0]["title"] == "Ein neues Thema heute"
        assert convs[0]["msg_count"] == 1
        assert convs[1]["msg_count"] == 3


def test_conversation_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        store.add_message("user", "Koche Rezept für Pfannkuchen", "cat_mochi")
        store.add_message("assistant", "Pfannkuchen sind lecker!", "cat_mochi")

        # Suche nach Titel/Inhalt
        assert len(store.conversations("Pfannkuchen")) == 1
        assert len(store.conversations("rezept")) == 1
        assert len(store.conversations("Spaghetti")) == 0


def test_relevant_snippets():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        t0 = 100000.0
        # Altes Gespraech
        with patch("time.time", return_value=t0):
            store.add_message("user", "Ich programmiere gerade fleißig in Python und mag Algorithmen", "cat_mochi")
            store.add_message("assistant", "Python ist wunderbar!", "cat_mochi")

        # Neues Gespraech (mehr als 30 Min spaeter)
        with patch("time.time", return_value=t0 + 5000):
            store.add_message("user", "Hilfe bei etwas anderem", "cat_mochi")

            # Suche nach 'Python' und 'Algorithmen'
            snippets = store.relevant_snippets("Kannst du mir bei Python und Algorithmen helfen?", limit=3)
            assert len(snippets) > 0
            assert any("Python" in s for s in snippets)

            # Aktuelles Gespraech darf NICHT in Snippets auftauchen
            snippets_current = store.relevant_snippets("Hilfe bei etwas anderem", limit=3)
            assert len(snippets_current) == 0


def test_facts_crud_and_forget_matching():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        fid1 = store.add_fact("Trinkt gerne Espresso ohne Zucker")
        fid2 = store.add_fact("Geburtstag am 15. August", due_date="2026-08-15", kind="date")

        facts = store.facts()
        assert len(facts) == 2
        assert facts[0]["id"] == fid2  # Neueste zuerst
        assert facts[1]["id"] == fid1

        # forget_matching
        deleted = store.forget_matching("espresso")
        assert deleted == 1
        assert len(store.facts()) == 1

        # delete_fact
        store.delete_fact(fid2)
        assert len(store.facts()) == 0


def test_wipe_everything():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        store.add_message("user", "Hallo", "cat_mochi")
        store.add_fact("Fakt 1")
        store.set_stat("level", "3")

        assert len(store.conversations()) == 1
        assert len(store.facts()) == 1
        assert store.get_stat("level") == "3"

        store.wipe_everything()

        assert len(store.conversations()) == 0
        assert len(store.facts()) == 0
        assert store.get_stat("level") is None


def test_export_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        store.add_message("user", "Testnachricht für Export", "cat_mochi")
        store.add_fact("Liebt Katzenminze")

        export_file = Path(tmpdir) / "export.txt"
        store.export_text(export_file)

        assert export_file.exists()
        content = export_file.read_text(encoding="utf-8")
        assert "Testnachricht für Export" in content
        assert "Liebt Katzenminze" in content
        assert "Desktop Cat - Exportierte Daten" in content


def test_parse_cli_response_with_and_without_remember():
    # Ohne remember
    raw_plain = '{"say": "Hallo Boss!", "tool": null}'
    say, tool = parse_cli_response(raw_plain)
    assert say == "Hallo Boss!"
    assert tool is None

    resp = parse_cli_response(raw_plain)
    assert resp.remember == []
    assert resp.remember_dates == []

    # Mit remember und remember_dates
    raw_remember = '''{
        "say": "Das merke ich mir!",
        "tool": null,
        "remember": ["Trinkt gerne Cappuccino", "Mag Sci-Fi Filme"],
        "remember_dates": [{"text": "Zahnarzttermin", "date": "2026-11-04"}]
    }'''
    resp2 = parse_cli_response(raw_remember)
    assert resp2.say == "Das merke ich mir!"
    assert resp2.tool is None
    assert resp2.remember == ["Trinkt gerne Cappuccino", "Mag Sci-Fi Filme"]
    assert len(resp2.remember_dates) == 1
    assert resp2.remember_dates[0]["text"] == "Zahnarzttermin"
    assert resp2.remember_dates[0]["date"] == "2026-11-04"

    # Robustheit bei kaputtem remember
    raw_broken = '{"say": "Hi", "remember": 123, "remember_dates": "ungültig"}'
    resp3 = parse_cli_response(raw_broken)
    assert resp3.say == "Hi"
    assert resp3.remember == []
    assert resp3.remember_dates == []


def test_vergiss_alles_generates_confirmation():
    # "vergiss alles" erzeugt Sicherheitsabfrage statt direkt zu loeschen
    plan_wipe = parse_offline("vergiss alles")
    assert plan_wipe.tool == "wipe_my_data"
    assert "wipe_my_data" in DANGEROUS_TOOLS

    q_wipe = confirm_question("wipe_my_data", {}, "Boss", "cat_mochi")
    assert "wirklich alle gemerkten Fakten" in q_wipe

    # "vergiss, dass ich gerne Tee trinke"
    plan_forget = parse_offline("vergiss, dass ich gerne Tee trinke")
    assert plan_forget.tool == "forget_facts"
    assert "forget_facts" in DANGEROUS_TOOLS
    assert "ich gerne Tee trinke" in plan_forget.args.get("query", "")

    q_forget = confirm_question("forget_facts", plan_forget.args, "Boss", "cat_mochi")
    assert "Tee" in q_forget

    # "was weißt du über mich"
    plan_list = parse_offline("was weißt du über mich")
    assert plan_list.tool == "list_facts"


def test_stats_get_and_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path)

        assert store.get_stat("focus_minutes", default="0") == "0"
        store.set_stat("focus_minutes", "25")
        assert store.get_stat("focus_minutes") == "25"
        store.set_stat("focus_minutes", "50")
        assert store.get_stat("focus_minutes") == "50"
