# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Trophäen- und Achievement-System (v2.4.0).

Verwaltet 12 freischaltbare Meilensteine mit Fortschrittsanzeige,
Freundschaftspunkte-Belohnungen und Persistenz in MemoryStore.
"""
from __future__ import annotations

from typing import Any, Optional

ACHIEVEMENTS: list[dict[str, Any]] = [
    {
        "id": "bubble_king",
        "title": "Seifenblasen-König",
        "desc": "Platze 20 Seifenblasen im Minispiel",
        "icon": "🫧",
        "stat": "bubbles_popped",
        "target": 20,
        "fp_reward": 50,
    },
    {
        "id": "ball_catcher",
        "title": "Ball-Jongleur",
        "desc": "Wirf das Wollknäuel und lass es 10x fangen",
        "icon": "🧶",
        "stat": "yarn_catches",
        "target": 10,
        "fp_reward": 50,
    },
    {
        "id": "gourmet",
        "title": "Gourmet-Meister",
        "desc": "Verwöhne dein Tier mit 25 Leckerlis",
        "icon": "🐟",
        "stat": "treats_given",
        "target": 25,
        "fp_reward": 75,
    },
    {
        "id": "clean_cat",
        "title": "Glanz & Gloria",
        "desc": "Gönne deinem Haustier 15 Schaumbäder",
        "icon": "🧼",
        "stat": "washes_given",
        "target": 15,
        "fp_reward": 50,
    },
    {
        "id": "focus_titan",
        "title": "Fokus-Titan",
        "desc": "Schließe 10 Pomodoro-Sessions erfolgreich ab",
        "icon": "⏱️",
        "stat": "focus_sessions_done",
        "target": 10,
        "fp_reward": 100,
    },
    {
        "id": "big_family",
        "title": "Große Familie",
        "desc": "Schalte alle 15 Charaktere im Baum frei",
        "icon": "🌟",
        "stat": "chars_unlocked_count",
        "target": 15,
        "fp_reward": 200,
    },
    {
        "id": "best_friends",
        "title": "Seelenverwandte",
        "desc": "Erreiche Freundschaftslevel 8",
        "icon": "💖",
        "stat": "friendship_level",
        "target": 8,
        "fp_reward": 250,
    },
    {
        "id": "photomodel",
        "title": "Fotomodell",
        "desc": "Schieße 3 Erinnerungsfotos in der Fotobox",
        "icon": "📸",
        "stat": "photos_taken",
        "target": 3,
        "fp_reward": 30,
    },
    {
        "id": "ghost_hunter",
        "title": "Geisterjäger",
        "desc": "Schließe das Halloween-Event ab",
        "icon": "🎃",
        "stat": "event_halloween_done",
        "target": 1,
        "fp_reward": 100,
    },
    {
        "id": "winter_elf",
        "title": "Weihnachtself",
        "desc": "Schließe das Winterzauber-Event ab",
        "icon": "🎄",
        "stat": "event_winter_done",
        "target": 1,
        "fp_reward": 100,
    },
    {
        "id": "night_owl",
        "title": "Nachteule",
        "desc": "Kuschle mit deinem Tier nach 23:00 Uhr",
        "icon": "🌙",
        "stat": "night_pets_done",
        "target": 1,
        "fp_reward": 25,
    },
    {
        "id": "room_designer",
        "title": "Zimmer-Designer",
        "desc": "Aktiviere das dynamische Katzenzimmer-Wallpaper",
        "icon": "🖼️",
        "stat": "wallpaper_activated",
        "target": 1,
        "fp_reward": 50,
    },
]


def get_all_achievements() -> list[dict[str, Any]]:
    return ACHIEVEMENTS


def get_achievement_status(store, ach: dict[str, Any]) -> tuple[int, int, bool]:
    """Gibt (aktueller_fortschritt, ziel, freigeschaltet?) zurueck."""
    if store is None:
        return 0, ach["target"], False
    try:
        is_unlocked = store.get_stat(f"ach_unlocked_{ach['id']}") == "1"
        cur = int(store.get_stat(ach["stat"]) or 0)
        return min(ach["target"], cur), ach["target"], is_unlocked
    except Exception:
        return 0, ach["target"], False


def record_achievement_event(store, stat_key: str, count: int = 1) -> list[dict[str, Any]]:
    """Erhoeht einen Zaehler und prueft, ob Achievements freigeschaltet wurden.
    Gibt die Liste neu freigeschalteter Achievements zurueck.
    """
    if store is None:
        return []
    try:
        cur = store.increment_stat(stat_key, count)
    except Exception:
        return []

    newly_unlocked = []
    for ach in ACHIEVEMENTS:
        if ach["stat"] == stat_key:
            ach_key = f"ach_unlocked_{ach['id']}"
            if store.get_stat(ach_key) != "1":
                if cur >= ach["target"]:
                    if store.claim_achievement(ach['id'], ach['stat'], ach['target'], ach['fp_reward']):
                        newly_unlocked.append(ach)
    return newly_unlocked


def unlock_achievement_direct(store, ach_id: str) -> Optional[dict[str, Any]]:
    """Schaltet ein Achievement direkt frei (z.B. bei Event-Abschluss)."""
    if store is None:
        return None
    for ach in ACHIEVEMENTS:
        if ach["id"] == ach_id:
            if store.claim_achievement(ach['id'], ach['stat'], ach['target'], ach['fp_reward']):
                return ach
            return None
    return None
