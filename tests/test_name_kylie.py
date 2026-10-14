"""Tests fuer Phase 1: Name 'Desktop Cat', Kylie und Namensreaktion."""
import json
import tempfile
from pathlib import Path

from agent_brain import name_reaction
from config import Config
from pet_sprites import CHARACTERS


def test_character_name_is_kylie():
    assert CHARACTERS["cat_mochi"]["name"] == "Kylie"


def test_name_reaction_exact_call():
    res = name_reaction("kylie", "Kylie", "Boss")
    assert res is not None
    assert res.kind == "call"
    assert "Ja? 😺" in res
    assert "Boss" in res
    assert res.reply is not None and "Ja?" in res.reply


def test_name_reaction_upper_and_variations():
    # Groß/Klein und Satzzeichen
    res1 = name_reaction("KYLIE!", "Kylie", "Alex")
    assert res1 is not None
    assert res1.kind == "call"
    assert "Alex" in res1

    # Kosenamen-Variation mit Buchstaben-Wiederholung (z. B. "kyliiie")
    res2 = name_reaction("kyliiie?", "Kylie", "Alex")
    assert res2 is not None
    assert res2.kind == "call"


def test_name_reaction_prefix_with_rest():
    res = name_reaction("Kylie, wie spät ist es", "Kylie")
    assert res is not None
    assert res.kind == "prefix"
    assert res.rest == "wie spät ist es"
    # String-Vergleich funktioniert direkt fuer den Rest
    assert res == "wie spät ist es"


def test_name_reaction_hearts_in_longer_text():
    res = name_reaction("ich mag kylie", "Kylie")
    assert res is not None
    assert res.kind == "hearts"
    assert res.hearts is True


def test_name_reaction_who_are_you():
    for phrase in ("wie heißt du", "Wie heisst du?", "wer bist du"):
        res = name_reaction(phrase, "Kylie")
        assert res is not None
        assert res.kind == "who"
        assert "Kylie" in res
        assert res.reply is not None and "Kylie" in res.reply
        assert "🐾! 🐾" not in res.reply
        assert res.reply == "Ich bin Kylie, deine verschmuste Glückskatze! 🐾"


def test_name_reaction_no_name_returns_none():
    assert name_reaction("wie spät ist es", "Kylie") is None
    assert name_reaction("hallo welt", "Kylie") is None
    assert name_reaction("", "Kylie") is None


def test_name_reaction_works_with_other_characters():
    res_hachi = name_reaction("hachi!", "Hachi", "Boss")
    assert res_hachi is not None
    assert res_hachi.kind == "call"

    res_luna = name_reaction("Luna, mach das Licht aus", "Luna")
    assert res_luna is not None
    assert res_luna.kind == "prefix"
    assert res_luna.rest == "mach das Licht aus"


def test_config_migration_mochi_to_kylie():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        # Alte v2.1-Config mit Mochi als Name
        old_cfg = {
            "pet": {"name": "Mochi", "character": "cat_mochi"},
            "first_run_done": True,
        }
        cfg_file.write_text(json.dumps(old_cfg), encoding="utf-8")

        cfg = Config(cfg_file)
        assert cfg.get("pet.name") == "Kylie"

        # Sicherstellen, dass die Migration auf Platte gespeichert wurde
        with open(cfg_file, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["pet"]["name"] == "Kylie"


def test_config_custom_name_not_overwritten():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        custom_cfg = {
            "pet": {"name": "Sammy", "character": "cat_mochi"},
        }
        cfg_file.write_text(json.dumps(custom_cfg), encoding="utf-8")

        cfg = Config(cfg_file)
        assert cfg.get("pet.name") == "Sammy"
