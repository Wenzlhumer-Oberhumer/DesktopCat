# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tamagotchi-Care & Charakter-Freischalt-Baum (Gamification).

Verwaltet Beduerfnisse (Hunger, Hygiene, Laune) und die stufenweise
Freischaltung aller Charaktere ueber das Freundschaftslevel.
Die Katze kann NIEMALS sterben (unsterblich!), sondern wird bei
Vernachlaessigung hungrig oder struppig und freut sich umso mehr ueber Zuwendung.
"""
from __future__ import annotations

import datetime
import time
from typing import Any, Optional

from fun import LEVEL_THRESHOLDS, add_friendship_points, level_for

# Stufenweise Freischaltung der 17 Charaktere nach Freundschafts-Level (1-8)
UNLOCK_TIERS: dict[int, list[str]] = {
    1: ["cat_mochi", "animal_arctic_fox", "animal_cocoa_bunny"],                              # Start: Kylie, Flocke & Kakao
    2: ["dog_shiba", "animal_bunny"],              # Level 2 (25 FP): Hachi & Mimi (Häschen)
    3: ["cat_luna", "animal_hamster"],             # Level 3 (75 FP): Luna & Hamsti (Goldhamster)
    4: ["dog_balu", "animal_fox"],                 # Level 4 (150 FP): Balu & Kitsune (Rotfuchs)
    5: ["animal_penguin", "animal_panda"],         # Level 5 (300 FP): Pip & Pao (Roter Panda)
    6: ["fantasy_axolotl", "animal_raccoon"],      # Level 6 (500 FP): Lotti & Roki (Waschbär)
    7: ["fantasy_spooky", "animal_frog"],          # Level 7 (800 FP): Spooky & Kero (Laubfrosch)
    8: ["fantasy_drago", "fantasy_byte"],          # Level 8 (1200 FP): Drago & Byte (Cyber-Bot)
}


def get_character_unlock_req(char_id: str) -> tuple[int, int]:
    """Gibt (benoetigtes_level, benoetigte_punkte) fuer einen Charakter zurueck."""
    for lvl, chars in UNLOCK_TIERS.items():
        if char_id in chars:
            pts = LEVEL_THRESHOLDS[lvl - 1] if lvl - 1 < len(LEVEL_THRESHOLDS) else 0
            return lvl, pts
    return 1, 0


def get_unlocked_characters(store=None) -> set[str]:
    """Gibt alle Charaktere zurueck, die gemaess aktuellem Freundschaftslevel freigeschaltet sind."""
    current_lvl = 1
    if store is not None:
        try:
            pts = int(store.get_stat("friendship_points") or 0)
            current_lvl, _ = level_for(pts)
        except Exception:
            current_lvl = 1

    unlocked: set[str] = set()
    for lvl, chars in UNLOCK_TIERS.items():
        if lvl <= current_lvl:
            unlocked.update(chars)
    # Kylie ist immer freigeschaltet
    unlocked.add("cat_mochi")
    return unlocked


def is_character_unlocked(char_id: str, store=None) -> tuple[bool, int, int]:
    """Prueft, ob ein Charakter freigeschaltet ist.
    Gibt (freigeschaltet?, benoetigtes_level, benoetigte_punkte) zurueck.
    """
    req_lvl, req_pts = get_character_unlock_req(char_id)
    if req_lvl == 1 or char_id == "cat_mochi":
        return True, 1, 0

    current_lvl = 1
    if store is not None:
        try:
            pts = int(store.get_stat("friendship_points") or 0)
            current_lvl, _ = level_for(pts)
        except Exception:
            current_lvl = 1

    return current_lvl >= req_lvl, req_lvl, req_pts


# ======================================================================================
#  Tamagotchi Beduerfnisse (Hunger, Hygiene, Laune)
# ======================================================================================
MIN_STAT = 15   # Unsterblich! Faellt niemals unter 15 %

def get_care_stats(cfg) -> dict[str, int]:
    """Berechnet aktuelle Beduerfnis-Werte (0-100) unter Beruecksichtigung des Zeitverlaufs."""
    care = cfg.get("care", {}) if isinstance(cfg.get("care"), dict) else {}
    now = time.time()
    if not care.get("last_updated") and hasattr(cfg, "set"):
        cfg.set("care.last_updated", now)       # Startpunkt merken, sonst sinkt Hunger bis zur 1. Fuetterung nie
    last_update = float(care.get("last_updated") or now)
    elapsed_hours = max(0.0, (now - last_update) / 3600.0)

    # Zerfall pro Stunde
    hunger_decay = elapsed_hours * 5.0      # nach ~12h hungrig (< 40%)
    hygiene_decay = elapsed_hours * 3.5     # nach ~16h schmutzig
    happiness_decay = elapsed_hours * 4.0

    raw_hunger = float(care.get("hunger", 100)) - hunger_decay
    raw_hygiene = float(care.get("hygiene", 100)) - hygiene_decay
    raw_happiness = float(care.get("happiness", 100)) - happiness_decay

    hunger = int(max(MIN_STAT, min(100, round(raw_hunger))))
    hygiene = int(max(MIN_STAT, min(100, round(raw_hygiene))))
    happiness = int(max(MIN_STAT, min(100, round(raw_happiness))))

    return {
        "hunger": hunger,
        "hygiene": hygiene,
        "happiness": happiness,
    }


def feed_pet(cfg, store=None) -> tuple[dict[str, int], int]:
    """Fuettert die Katze. Fuellt Hunger auf 100 % und vergibt Freundschaftspunkte."""
    stats = get_care_stats(cfg)
    stats["hunger"] = 100
    stats["happiness"] = min(100, stats["happiness"] + 15)

    care = {
        "hunger": stats["hunger"],
        "hygiene": stats["hygiene"],
        "happiness": stats["happiness"],
        "last_updated": time.time(),
        "last_fed": time.time(),
    }
    cfg.set("care", care)
    cfg.save()

    pts = 0
    if store is not None:
        try:
            pts, _, _ = add_friendship_points(store, "treat")
        except Exception:
            pass
    return stats, pts


def wash_pet(cfg, store=None) -> tuple[dict[str, int], int]:
    """Waescht & buerstet die Katze. Fuellt Hygiene auf 100 % und verzaubert mit Schaum."""
    stats = get_care_stats(cfg)
    stats["hygiene"] = 100
    stats["happiness"] = min(100, stats["happiness"] + 15)

    care = {
        "hunger": stats["hunger"],
        "hygiene": stats["hygiene"],
        "happiness": stats["happiness"],
        "last_updated": time.time(),
        "last_washed": time.time(),
    }
    cfg.set("care", care)
    cfg.save()

    pts = 0
    if store is not None:
        try:
            pts, _, _ = add_friendship_points(store, "wash")
        except Exception:
            pass
    return stats, pts


def pet_pet(cfg, store=None) -> dict[str, int]:
    """Streicheln hebt die Laune der Katze sofort an."""
    stats = get_care_stats(cfg)
    stats["happiness"] = min(100, stats["happiness"] + 20)
    care = {
        "hunger": stats["hunger"],
        "hygiene": stats["hygiene"],
        "happiness": stats["happiness"],
        "last_updated": time.time(),
    }
    cfg.set("care", care)
    cfg.save()
    return stats
