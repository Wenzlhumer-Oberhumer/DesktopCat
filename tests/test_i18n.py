"""Tests für Internationalisierung (i18n) – Phase 7."""
import glob
import os
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent_brain import name_reaction, parse_offline
import i18n
from i18n import tr
import pet_sprites


def test_strings_completeness():
    """Jeder Key in STRINGS hat sowohl 'de' als auch 'en' mit nicht-leeren Texten."""
    assert len(i18n.STRINGS) > 50
    missing_de = []
    missing_en = []
    for key, entry in i18n.STRINGS.items():
        assert isinstance(entry, dict), f"Key {key} ist kein Dict!"
        if "de" not in entry or not entry["de"]:
            missing_de.append(key)
        if "en" not in entry or not entry["en"]:
            missing_en.append(key)

    assert missing_de == [], f"Fehlende 'de' Übersetzungen für: {missing_de}"
    assert missing_en == [], f"Fehlende 'en' Übersetzungen für: {missing_en}"


def test_codebase_keys_exist():
    """Kein Key, der im Code mit tr(\"...\") benutzt wird, fehlt in STRINGS."""
    root = str(_ROOT)
    pattern = re.compile(r'tr\(["\']([^"\'\)\s]+)["\']')
    used_keys = set()

    for py_path in glob.glob(os.path.join(root, "*.py")):
        with open(py_path, "r", encoding="utf-8") as f:
            content = f.read()
        for match in pattern.finditer(content):
            used_keys.add(match.group(1))

    assert len(used_keys) > 20, f"Zu wenige Keys gefunden: {len(used_keys)}"
    missing_in_strings = [k for k in sorted(used_keys) if k not in i18n.STRINGS]
    assert missing_in_strings == [], f"Im Code genutzte Keys fehlen in i18n.STRINGS: {missing_in_strings}"


def test_character_info_en():
    """get_character_info liefert in 'en' englische Texte für alle 9 Figuren."""
    orig_lang = i18n.lang()
    try:
        i18n.set_language("en")
        char_ids = list(pet_sprites.CHARACTERS.keys())
        assert len(char_ids) == 9

        for cid in char_ids:
            info = pet_sprites.get_character_info(cid)
            assert "species" in info
            assert "desc" in info
            assert "pet_sounds" in info
            assert "ambient_lines" in info
            assert "task_start" in info
            assert "task_done" in info
            assert "ai_persona" in info

            assert len(info["pet_sounds"]) > 0
            assert len(info["ambient_lines"]) > 0
            assert len(info["task_start"]) > 0
            assert len(info["task_done"]) > 0

            de_info = pet_sprites.CHARACTERS[cid]
            if "en" in de_info:
                en_block = de_info["en"]
                if "species" in en_block:
                    assert info["species"] == en_block["species"]
                if "desc" in en_block:
                    assert info["desc"] == en_block["desc"]
    finally:
        i18n.set_language(orig_lang)


def test_offline_parser_en():
    """Offline-Parser: Englischsprachige Befehle funktionieren im Englisch-Modus."""
    orig_lang = i18n.lang()
    try:
        i18n.set_language("en")

        # 1. Uhrzeit / Datum
        res = parse_offline("what time is it")
        assert res is not None
        assert res.tool == "show_time_and_date"

        res_date = parse_offline("what's today's date")
        assert res_date is not None
        assert res_date.tool == "show_time_and_date"

        # 2. Timer
        res_timer = parse_offline("set a timer for 5 minutes")
        assert res_timer is not None
        assert res_timer.tool == "set_timer"
        assert res_timer.args.get("minutes") == 5

        # 3. Wetter
        res_weather = parse_offline("what's the weather in vienna")
        assert res_weather is not None
        assert res_weather.tool == "get_weather"
        assert res_weather.args.get("location") == "vienna"

        # 4. Notizen
        res_notes = parse_offline("my notes")
        assert res_notes is not None
        assert res_notes.tool == "manage_notes"
        assert res_notes.args.get("action") == "read"

        # 5. PC Aufraeumen
        res_clean = parse_offline("clean my pc")
        assert res_clean is not None
        assert res_clean.tool == "clean_pc"

        # 6. Netzwerk
        res_net = parse_offline("what is my ip")
        assert res_net is not None
        assert res_net.tool == "network_info"

        # 7. Daten vergessen
        res_forget = parse_offline("forget everything")
        assert res_forget is not None
        assert res_forget.tool == "wipe_my_data"

        # 8. Name / Wer bist du
        res_who = name_reaction("who are you", "Kylie", "Boss")
        assert res_who is not None
        assert "Kylie" in str(res_who)
    finally:
        i18n.set_language(orig_lang)


def test_tr_formatting_and_fallback():
    """tr formatiert Platzhalter korrekt und faellt sauber zurueck."""
    s = tr("friendship.title", name="Sammy")
    assert "Sammy" in s

    assert tr("unknown.nonexistent.key") == "unknown.nonexistent.key"


if __name__ == "__main__":
    test_strings_completeness()
    test_codebase_keys_exist()
    test_character_info_en()
    test_offline_parser_en()
    test_tr_formatting_and_fallback()
    print("All i18n tests passed successfully!")
