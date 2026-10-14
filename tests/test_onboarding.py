# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer Phase 10: Kennenlernen mit Kylie (Onboarding, Profil, Ablauf, Offline-Befehle)."""
import tempfile
from pathlib import Path
from unittest.mock import patch

from agent_brain import parse_offline, profile_prompt
from config import Config
from onboarding import OnboardingFlow, OnboardingReactionWorker, clean_free_text
from tools import wipe_my_data


def test_clean_free_text():
    assert clean_free_text("") == ""
    assert clean_free_text("   ") == ""
    assert clean_free_text("Hallo\nWelt\r\nTest", max_len=60) == "Hallo Welt Test"
    assert clean_free_text("A" * 100, max_len=40) == "A" * 40
    assert clean_free_text("   Mehrere   Leerzeichen   ") == "Mehrere Leerzeichen"


def test_profile_prompt_empty():
    # Kein Argument oder leere Config
    assert profile_prompt(None) == ""
    assert profile_prompt({}) == ""
    assert profile_prompt({"profile": {}}) == ""


def test_profile_prompt_privacy_remember_false():
    cfg_data = {
        "privacy": {"remember": False},
        "profile": {"name": "Florian", "interests": "Python", "tone": "frech"},
        "pet": {"user_name": "Flo"},
    }
    assert profile_prompt(cfg_data) == ""


def test_profile_prompt_full_and_length():
    cfg_data = {
        "privacy": {"remember": True},
        "profile": {
            "name": "Florian",
            "pronouns": "er",
            "uses": ["Schule", "Coding", "Gaming"],
            "interests": "Gitarre, Katzen, Python",
            "city": "Linz",
            "tone": "frech & witzig",
        },
        "pet": {"user_name": "Flo"},
    }
    prompt = profile_prompt(cfg_data)
    assert prompt != ""
    assert "ÜBER DEN NUTZER:" in prompt
    assert "Florian" in prompt
    assert "Flo" in prompt
    assert "Pronomen: er" in prompt
    assert "Coding" in prompt
    assert "Gitarre" in prompt
    assert "Linz" in prompt
    assert "Gewünschter Ton: frech & witzig" in prompt
    assert len(prompt) < 450


def test_onboarding_flow_sequence():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)

        # Flow ohne Key (Schritt 11 soll nicht uebersprungen werden)
        flow = OnboardingFlow(cfg, has_key_fn=lambda: False)
        assert flow.current_step() == 1
        assert not flow.is_done()

        # Schritt 1: Willkommen
        assert flow.submit_answer("Klar! 😺")
        assert flow.current_step() == 2

        # Schritt 2: Sprache
        assert flow.submit_answer("English 🇬🇧")
        assert flow.current_step() == 3
        assert cfg.get("language") == "en"

        # Schritt 3: Name (Pflichtfeld)
        assert not flow.submit_answer("")  # leere Eingabe darf nicht weitergehen
        assert not flow.can_skip()
        assert not flow.skip_current_step()
        assert flow.submit_answer("Alex")
        assert flow.current_step() == 4
        assert cfg.get("profile.name") == "Alex"

        # Schritt 4: Spitzname
        assert flow.can_skip()
        assert flow.submit_answer("Chief")
        assert flow.current_step() == 5
        assert cfg.get("pet.user_name") == "Chief"

        # Schritt 5: Pronomen
        assert flow.submit_answer("they / them")
        assert flow.current_step() == 6
        assert cfg.get("profile.pronouns") == "they / them"

        # Schritt 6: PC-Nutzung
        assert flow.submit_answer(["Coding", "Gaming"])
        assert flow.current_step() == 7
        assert "Coding" in cfg.get("profile.uses")

        # Schritt 7: Interessen (Ueberspringen testen)
        assert flow.skip_current_step()
        assert flow.current_step() == 8

        # Schritt 8: Ton
        assert flow.submit_answer("frech")
        assert flow.current_step() == 9
        assert cfg.get("profile.tone") == "frech"

        # Schritt 9: Chatter
        assert flow.submit_answer("oft")
        assert flow.current_step() == 10
        assert cfg.get("pet.chatter") is True

        # Schritt 10: Stadt
        assert flow.submit_answer("Berlin")
        assert flow.current_step() == 11
        assert cfg.get("profile.city") == "Berlin"

        # Schritt 11: Key
        assert flow.submit_answer("AIzaSyTest")
        assert flow.current_step() == 12

        # Schritt 12: Figur
        assert flow.submit_answer("cat_luna")
        assert flow.current_step() == 13
        assert cfg.get("pet.character") == "cat_luna"

        # Schritt 13: Privacy
        assert flow.submit_answer({"save_chats": True, "remember": True, "use_history": True})
        assert flow.current_step() == 14

        # Schritt 14: Autostart
        assert flow.submit_answer("Ja, immer dabei!")
        assert flow.current_step() == 15
        assert cfg.get("autostart") is True

        # Schritt 15: Fertig
        assert flow.submit_answer("Los")
        assert flow.is_done()
        assert cfg.get("onboarding_done") is True


def test_onboarding_flow_skip_key_if_has_key():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)

        # Mit vorhandenem Key
        flow = OnboardingFlow(cfg, has_key_fn=lambda: True)
        flow.step = 10
        flow.submit_answer("Wien")
        # Soll direkt zu Schritt 12 (Figur) springen
        assert flow.current_step() == 12


def test_onboarding_flow_update_prefill():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)
        cfg.set("profile.name", "Florian")
        cfg.set("pet.user_name", "Flo")
        cfg.set("pet.character", "dog_shiba")
        cfg.save()

        flow = OnboardingFlow(cfg, is_update=True)
        assert flow.answers.get("name") == "Florian"
        assert flow.answers.get("user_name") == "Flo"
        assert flow.answers.get("character") == "dog_shiba"


def test_onboarding_flow_skip_later():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)
        flow = OnboardingFlow(cfg)
        assert cfg.get("onboarding_skips", 0) == 0

        flow.skip_later()
        assert cfg.get("onboarding_skips") == 1
        flow.skip_later()
        assert cfg.get("onboarding_skips") == 2


def test_offline_nenn_mich_chef():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)
        cfg.save()
        with patch("config.CONFIG_PATH", cfg_file):
            plan = parse_offline("nenn mich ab jetzt Chef")
            assert plan.ok is True
            assert "Chef" in (plan.reply or "")
            cfg.load()
            assert cfg.get("pet.user_name") == "Chef"

            plan2 = parse_offline("wie heiße ich?")
            assert plan2.ok is True
            assert "Chef" in (plan2.reply or "") or "Du bist" in (plan2.reply or "")


def test_wipe_my_data_resets_profile_and_onboarding():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)
        cfg.set("profile.name", "Florian")
        cfg.set("profile.tone", "frech")
        cfg.set("onboarding_done", True)
        cfg.save()

        db_file = Path(td) / "test.db"
        from memory_store import MemoryStore
        store = MemoryStore(db_file)

        with patch("config.CONFIG_PATH", cfg_file), \
             patch("memory_store.get_memory_store", return_value=store):
            res = wipe_my_data()
            assert res.ok is True

            cfg.load()
            assert cfg.get("profile.name") == ""
            assert cfg.get("profile.tone") == ""
            assert cfg.get("onboarding_done") is False


def test_gemini_reaction_worker_fallback():
    from onboarding import FALLBACK_REACTIONS_DE, FALLBACK_REACTIONS_EN
    worker = OnboardingReactionWorker("cat_mochi", "Name: Flo", "Hobby?", "Gitarre", "de")
    replies = []
    worker.reaction_ready.connect(replies.append)

    with patch("gemini.ask", side_effect=Exception("Timeout / Offline")):
        worker.run()

    assert len(replies) == 1
    assert replies[0] in FALLBACK_REACTIONS_DE or replies[0] in FALLBACK_REACTIONS_EN
