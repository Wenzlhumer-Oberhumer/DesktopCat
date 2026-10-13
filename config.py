"""Einstellungs-Verwaltung: laedt/speichert config.json und ergaenzt fehlende Werte mit Defaults."""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any

from paths import APP_DIR, DATA_DIR

CONFIG_PATH = DATA_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    "pet": {
        "name": "Mochi",
        "speed": 90,            # Pixel pro Sekunde
        "scale": 1.0,
        "wander": True,
        "wander_min_s": 5,
        "wander_max_s": 10,
        "chatter": True,        # gelegentliche Zwischenrufe
        "bubble_seconds": 4.0,
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
    "hotkey": "ctrl+alt+p",
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

    def __init__(self, path: Path = CONFIG_PATH):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    # -- IO ---------------------------------------------------------------
    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                with self._lock:
                    self.data = _merge(DEFAULTS, loaded)
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
                except (OSError, ValueError):
                    pass
            self.save()
        except (OSError, ValueError) as exc:  # kaputte JSON -> mit Defaults weiterarbeiten
            print(f"[config] Konnte config.json nicht lesen ({exc}). Nutze Defaults.")

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
