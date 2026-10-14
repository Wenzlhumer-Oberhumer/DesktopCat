# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Einstellungs-Verwaltung: laedt/speichert config.json und ergaenzt fehlende Werte mit Defaults."""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

from paths import APP_DIR, DATA_DIR

CONFIG_PATH = DATA_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    "language": "de",
    "pet": {
        "name": "Kylie",
        "character": "cat_mochi",
        "room_mode": False,     # Regale/Fensterbrett nur im Lively-Katzenzimmer, sonst unsichtbare Ebenen
        "is_at_home": False,
        "user_name": "Boss",    # Anrede durch den Buddy
        "speed": 90,            # Pixel pro Sekunde
        "scale": 1.0,
        "wander": True,
        "wander_min_s": 5,
        "wander_max_s": 10,
        "chatter": True,        # gelegentliche Zwischenrufe
        "bubble_seconds": 4.0,
        "opacity": 1.0,         # Deckkraft (0.3 - 1.0)
        "always_on_top": True,  # Immer im Vordergrund
        "sound_enabled": True,  # Audio/Soundeffekte bei Aktionen
    },
    "animations": {
        "idle": "", "walk_right": "", "walk_left": "", "dragged": "", "falling": "",
        "working": "", "success": "", "sleep": "", "sad": "",
    },
    "ai": {
        "enabled": True,
        "model": "",
        "timeout_s": 60,
    },
    "autostart": True,
    "first_run_done": False,
    "rename_intro_done": False,
    "hotkey": "ctrl+alt+p",
    "hotkey_explain": "ctrl+alt+e",
    "hotkey_voice": "ctrl+alt+space",
    "voice": {
        "enabled": True,
        "name": "de-DE-KatjaNeural",
        "pitch": "+20%",
        "rate": "+0%",
        "lipsync": True,
        "read_answers": False,
        "online": False,        # Online-Stimme (edge-tts) sendet den Text an Microsoft - nur auf Wunsch
    },
    "wellbeing": {"breaks": True, "break_min": 60, "water": True},
    "battery_warn": True,
    "night_mode": True,
    "treats": 0,
    "update": {
        "auto": True,
        "last_check": 0.0,
    },
    "privacy": {
        "save_chats": True,
        "remember": True,
        "use_history": True,
        "intro_shown": False,
    },
    "daily": {
        "briefing": True,
        "bedtime": "23:00",
        "curious": True,
    },
    "fun": {
        "weather_outfits": True,
        "pc_fever": True,
        "worn": "",
    },
    "care": {
        "hunger": 100,
        "hygiene": 100,
        "happiness": 100,
        "last_updated": 0.0,
        "last_fed": 0.0,
        "last_washed": 0.0,
    },
    "profile": {
        "name": "",
        "pronouns": "",
        "uses": [],
        "interests": "",
        "tone": "",
        "city": "",
    },
    "onboarding_done": False,
    "onboarding_skips": 0,
}


def _clean_migrated_ai(data: dict) -> dict:
    cleaned = copy.deepcopy(data)
    if "ai" in cleaned and isinstance(cleaned["ai"], dict):
        ai = cleaned["ai"]
        ai.pop("gemini_api_key", None)
        ai.pop("gemini_model", None)
        ai.pop("provider", None)
        for k in list(ai.keys()):
            if k.startswith("openai_"):
                ai.pop(k, None)
    return cleaned


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    """Duenner, threadsicherer Wrapper um das Settings-Dict."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else CONFIG_PATH
        self._lock = threading.Lock()
        self.data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    # -- IO ---------------------------------------------------------------
    def load(self) -> None:
        save_needed = False
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                with self._lock:
                    self.data = _merge(DEFAULTS, loaded)
                    # Migration: steht pet.name == "Mochi" -> "Kylie" (einmalig)
                    if self.data.get("pet", {}).get("name") == "Mochi":
                        self.data["pet"]["name"] = "Kylie"
                        save_needed = True
        except FileNotFoundError:
            # Migration (einmalig): alte config.json neben Quellcode pruefen
            old_cand = APP_DIR / "config.json"
            if old_cand != self.path and old_cand.exists():
                try:
                    with open(old_cand, "r", encoding="utf-8") as fh:
                        old_loaded = json.load(fh)
                    if isinstance(old_loaded, dict):
                        cleaned = _clean_migrated_ai(old_loaded)
                        with self._lock:
                            self.data = _merge(DEFAULTS, cleaned)
                            if self.data.get("pet", {}).get("name") == "Mochi":
                                self.data["pet"]["name"] = "Kylie"
                except (OSError, ValueError):
                    pass
            self.save()
            return
        except (OSError, ValueError) as exc:  # kaputte JSON -> mit Defaults weiterarbeiten
            print(f"[config] Konnte config.json nicht lesen ({exc}). Nutze Defaults.")
        if save_needed:
            self.save()

    def save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        with self._lock:
            payload = json.dumps(self.data, indent=2, ensure_ascii=False)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            print(f"[config] Speichern fehlgeschlagen: {exc}")

    # -- Zugriff ----------------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        with self._lock:
            for part in dotted.split("."):
                if not isinstance(node, dict) or part not in node:
                    return default
                node = node[part]
            return node

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        with self._lock:
            node = self.data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

    def snapshot(self) -> dict[str, Any]:
        """Tiefe Kopie, damit Worker-Threads sicher damit arbeiten koennen."""
        with self._lock:
            return copy.deepcopy(self.data)
