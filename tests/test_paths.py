import os
import tempfile
from pathlib import Path

from config import Config, _clean_migrated_ai
from paths import DATA_DIR


def test_data_dir_location():
    appdata = os.environ.get("APPDATA")
    if appdata:
        assert str(DATA_DIR).startswith(appdata)
    assert DATA_DIR.name == "Mochi"


def test_clean_migrated_ai_removes_keys():
    old_data = {
        "pet": {"name": "Mochi"},
        "ai": {
            "enabled": True,
            "provider": "openai",
            "openai_api_key": "sk-test12345",
            "openai_model": "gpt-4o",
            "gemini_api_key": "AIzaSyFakeKey",
            "gemini_model": "gemini-1.5-flash",
            "timeout_s": 45,
        },
    }
    cleaned = _clean_migrated_ai(old_data)
    ai = cleaned["ai"]
    assert ai["enabled"] is True
    assert ai["timeout_s"] == 45
    assert "provider" not in ai
    assert "openai_api_key" not in ai
    assert "openai_model" not in ai
    assert "gemini_api_key" not in ai
    assert "gemini_model" not in ai


def test_config_defaults_and_save():
    with tempfile.TemporaryDirectory() as td:
        cfg_file = Path(td) / "config.json"
        cfg = Config(cfg_file)
        assert cfg.get("pet.name") == "Kylie"
        assert cfg.get("update.auto") is True
        cfg.set("pet.name", "TestMochi")
        cfg.save()

        cfg2 = Config(cfg_file)
        assert cfg2.get("pet.name") == "TestMochi"
