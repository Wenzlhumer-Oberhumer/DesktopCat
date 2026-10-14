# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Saisonale Mini-Events & Feiertags-Quests (v2.4.0).

Verwaltet automatisch saisonale Events (Halloween, Weihnachten/Winter, Frühling/Ostern, Sommer)
mit Quests, exklusiven Belohnungs-Accessoires und Partikel-Themen.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from achievements import unlock_achievement_direct

SEASONAL_EVENTS: dict[str, dict[str, Any]] = {
    "halloween": {
        "id": "halloween",
        "title": "🎃 Halloween Spuk-Woche",
        "subtitle": "Geisterstunde auf dem Desktop! Verwöhne deine Tiere mit Süßem.",
        "icon": "🎃",
        "months": [10],
        "days": (15, 31),
        "quests": [
            {
                "id": "hl_treats",
                "title": "Süßes sonst gibt's Saures! 🍬",
                "desc": "Gib deinem Tier 5 Leckerlis während des Events",
                "stat": "quest_hl_treats",
                "target": 5,
                "reward_title": "Hexenhut 🧙",
                "reward_acc": "party_hat",
                "ach_id": "ghost_hunter",
            }
        ]
    },
    "winter": {
        "id": "winter",
        "title": "🎄 Winter- & Weihnachtszauber",
        "subtitle": "Kuschelige Kaminfeuer-Stimmung und Schneeflocken auf dem Desktop.",
        "icon": "🎄",
        "months": [12, 1],
        "days": (1, 31),
        "quests": [
            {
                "id": "wt_bubbles",
                "title": "Eisige Seifenblasen ❄️",
                "desc": "Platze 10 Seifenblasen im Minispiel",
                "stat": "quest_wt_bubbles",
                "target": 10,
                "reward_title": "Kuschelschal 🧣",
                "reward_acc": "scarf",
                "ach_id": "winter_elf",
            }
        ]
    },
    "spring": {
        "id": "spring",
        "title": "🌸 Frühlings-Erwachen & Blütenzauber",
        "subtitle": "Rosa Kirschblüten und bunte Frühlings-Stimmung.",
        "icon": "🌸",
        "months": [3, 4],
        "days": (15, 30),
        "quests": [
            {
                "id": "sp_groom",
                "title": "Großer Frühlingsputz 🧼",
                "desc": "Wasche & bürste dein Tier 3x blitzsauber",
                "stat": "quest_sp_washes",
                "target": 3,
                "reward_title": "Blumen-Schleife 🎀",
                "reward_acc": "ribbon",
                "ach_id": None,
            }
        ]
    },
    "summer": {
        "id": "summer",
        "title": "☀️ Sommer-Sonne & Badespaß",
        "subtitle": "Heiße Sommertage – vergiss nicht, regelmäßig Wasser zu trinken!",
        "icon": "☀️",
        "months": [6, 7, 8],
        "days": (1, 31),
        "quests": [
            {
                "id": "sm_water",
                "title": "Kühles Nass 🥣",
                "desc": "Trinke 5x Wasser zusammen mit deinem Tier",
                "stat": "quest_sm_water",
                "target": 5,
                "reward_title": "Cooler Fächer 🪭",
                "reward_acc": "fan",
                "ach_id": None,
            }
        ]
    }
}


def get_current_event(now: Optional[datetime.datetime] = None) -> dict[str, Any]:
    """Ermittelt das aktuell aktive saisonale Event basierend auf dem Datum."""
    dt = now or datetime.datetime.now()
    month = dt.month
    day = dt.day

    # 1. Spezifische Datumsbereiche
    if month == 10 and day >= 15:
        return SEASONAL_EVENTS["halloween"]
    if month == 12 or (month == 1 and day <= 10):
        return SEASONAL_EVENTS["winter"]
    if month in (3, 4):
        return SEASONAL_EVENTS["spring"]
    if month in (6, 7, 8):
        return SEASONAL_EVENTS["summer"]

    # Außerhalb der Haupt-Feiertage: Winterzauber oder Frühlingszauber
    if month in (11, 1, 2):
        return SEASONAL_EVENTS["winter"]
    return SEASONAL_EVENTS["spring"]


def get_quest_status(store, quest: dict[str, Any]) -> tuple[int, int, bool]:
    """Gibt (aktueller_wert, ziel, abgeschlossen?) fuer eine Quest zurueck."""
    if store is None:
        return 0, quest["target"], False
    try:
        done = store.get_stat(f"quest_done_{quest['id']}") == "1"
        cur = int(store.get_stat(quest["stat"]) or 0)
        return min(quest["target"], cur), quest["target"], done
    except Exception:
        return 0, quest["target"], False


def record_quest_event(store, stat_key: str, count: int = 1) -> list[dict[str, Any]]:
    """Aktualisiert Quest-Zaehler und schliesst Quests ab, falls Ziel erreicht."""
    if store is None:
        return []
    try:
        cur = int(store.get_stat(stat_key) or 0) + count
        store.set_stat(stat_key, str(cur))
    except Exception:
        return []

    completed = []
    event = get_current_event()
    for quest in event.get("quests", []):
        if quest["stat"] == stat_key:
            done_key = f"quest_done_{quest['id']}"
            if store.get_stat(done_key) != "1":
                if cur >= quest["target"]:
                    store.set_stat(done_key, "1")
                    completed.append(quest)
                    # Falls verknüpftes Achievement existiert, direkt entsperren
                    if quest.get("ach_id"):
                        unlock_achievement_direct(store, quest["ach_id"])
    return completed
