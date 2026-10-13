"""Alltags-Logik: Neugier-Fragen, Erinnerungen, Guten-Morgen-Briefing, Geburtstag und Schlafenszeit."""
from __future__ import annotations

import datetime
import random
import re
from typing import Optional

from pet_sprites import get_character_info

GERMAN_MONTHS = {
    "januar": 1, "jänner": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "maerz": 3, "mrz": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

# Offline-Fragen fuer Figuren
QUESTIONS_CAT = [
    "Was machst du heute Schönes nach der Arbeit oder Schule? 😸",
    "Hast du ein Lieblingstier außer Katzen? 🐾",
    "Welche Musik hörst du am liebsten beim Konzentrieren? 🎵",
    "Was ist dein absolutes Wohlfühl-Essen? 🍜",
    "Trinkst du lieber Kaffee oder Tee, wenn du am PC sitzt? ☕",
    "Wohin würdest du gerne mal reisen, wenn du überall hin könntest? ✈️",
    "Welches Spiel oder Hobby begeistert dich gerade am meisten? 🎮",
    "Gibt es ein Buch oder einen Film, den du mir empfehlen würdest? 📚",
    "Bist du eher eine Nachteule oder ein Frühaufsteher? 🌙",
    "Was war das Beste, was dir diese Woche passiert ist? ✨",
    "Hast du ein Lieblingsgetränk für lange Computertage? 🥤",
    "Arbeitest du gerade an einem spannenden Projekt? 💻",
    "Was bringt dich immer sofort zum Lachen? 😺",
    "Gibt es etwas, worauf du dich diesen Monat besonders freust? 🗓️",
    "Magst du lieber Sommerhitze oder gemütliches Regenwetter? 🌧️",
    "Welche Superkraft hättest du gerne für einen Tag? 🦸",
    "Hast du eine Lieblings-Serie, die du gerade schaust? 🍿",
    "Was hilft dir am besten, wenn du mal gestresst bist? 🧘",
    "Gibt es eine Sprache oder Fähigkeit, die du gerne lernen möchtest? 🌍",
    "Darf ich dir später wieder beim Coden oder Tippen zuschauen? 🐾",
]

QUESTIONS_DOG = [
    "Gehst du am Wochenende gerne in der Natur spazieren? 🐶🐾",
    "Was war dein Lieblingsmoment heute? Erzähl mal! 🐕",
    "Hast du ein Lieblingsspielzeug oder Sportart? 🎾",
    "Darf ich dich fragen: Was ist dein liebstes Wochenend-Frühstück? 🥞",
    "Wer ist dein bester Kumpel, wenn du nicht am PC sitzt? 🐾",
    "Magst du lange Ausflüge ans Meer oder in die Berge? 🏔️",
    "Welches Lied macht dir sofort gute Laune? 🎶",
    "Hast du schon mal ein Haustier gehabt? 🐕❤️",
    "Was möchtest du heute noch unbedingt schaffen? 🚀",
    "Darf ich dir eine Runde Gesellschaft leisten? 🐾",
]

QUESTIONS_FANTASY = [
    "Wenn dein PC ein Raumschiff wäre, wohin fliegen wir als Nächstes? 🚀✨",
    "Welche Technologie der Zukunft hättest du gerne jetzt schon? 🤖⚡",
    "Glaubst du an Drachen oder Magie in fremden Galaxien? 🐲🔥",
    "Was ist deine Lieblings-Science-Fiction-Welt? 🌌",
    "Welche Programmiersprache oder Magie findest du am coolsten? 💻⚡",
    "Hast du eine Idee für eine Erfindung, die die Welt braucht? 💡",
    "Welchen Planeten würden wir zuerst erkunden? 🪐",
    "Magst du lieber futuristische Städte oder verzauberte Wälder? 🌲✨",
    "Was ist das epischste Spiel, das du je gespielt hast? 🎮",
    "Soll ich mein Schutzschild für deinen PC aktivieren? 🛡️⚡",
]


# ======================================================================================
#  Reine, testbare Funktionen
# ======================================================================================

def should_ask_curious(now: datetime.datetime, stats: dict, cfg: dict) -> bool:
    """Prueft, ob eine Neugier-Frage gestellt werden soll.

    Bedingungen:
    - daily.curious und privacy.remember muessen True sein.
    - Nicht nachts (zwischen 23:00 und 07:00).
    - Max. 2 Fragen pro Tag.
    - Mindestens 2 Stunden Abstand zur letzten Frage.
    """
    daily_cfg = cfg.get("daily", {}) if isinstance(cfg.get("daily"), dict) else {}
    if not daily_cfg.get("curious", True):
        return False

    priv = cfg.get("privacy", {}) if isinstance(cfg.get("privacy"), dict) else {}
    if not priv.get("remember", True):
        return False

    # Nachtruhe
    if now.hour >= 23 or now.hour < 7:
        return False

    today_str = now.strftime("%Y-%m-%d")
    curious_date = stats.get("curious_date", "")
    try:
        count = int(stats.get("curious_count", "0")) if curious_date == today_str else 0
    except ValueError:
        count = 0

    if count >= 2:
        return False

    try:
        last_ts = float(stats.get("curious_last_ts", "0"))
    except ValueError:
        last_ts = 0.0

    if (now.timestamp() - last_ts) < 7200:  # 2 Stunden
        return False

    return True


def next_birthday(day: int, month: int, today: datetime.date) -> datetime.date:
    """Berechnet das naechste Auftreten eines Geburtstags (heute oder in der Zukunft)."""
    # Schaltjahr-Absicherung fuer 29. Feb
    year = today.year
    try:
        this_year_bday = datetime.date(year, month, day)
    except ValueError:
        this_year_bday = datetime.date(year, month, 28)

    if this_year_bday >= today:
        return this_year_bday

    try:
        return datetime.date(year + 1, month, day)
    except ValueError:
        return datetime.date(year + 1, month, 28)


def parse_birthday_mention(text: str, today: datetime.date) -> Optional[tuple[int, int, datetime.date]]:
    """Erkennt Geburtsdaten im Text wie 'ich habe am 14. März Geburtstag' oder '14.03.'."""
    n = text.lower()
    if "geburtstag" not in n and "geboren" not in n:
        return None

    # Muster 1: "14. März" / "14 März" / "14. mai"
    m1 = re.search(r"\b(\d{1,2})\.?\s+([a-zäöü]+)\b", n)
    if m1:
        d_str, mon_str = m1.group(1), m1.group(2)
        if mon_str in GERMAN_MONTHS:
            day = int(d_str)
            month = GERMAN_MONTHS[mon_str]
            if 1 <= day <= 31:
                return day, month, next_birthday(day, month, today)

    # Muster 2: "14.03." / "14.3."
    m2 = re.search(r"\b(\d{1,2})\.(\d{1,2})\.?", n)
    if m2:
        day = int(m2.group(1))
        month = int(m2.group(2))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return day, month, next_birthday(day, month, today)

    return None


def due_reminders(facts: list[dict], now: datetime.datetime, stats: Optional[dict] = None) -> list[tuple[dict, str, str]]:
    """Ermittelt faellige Erinnerungen und Nachfragen fuer Fakten mit due_date.

    Liefert Liste von (fact_dict, nachricht, stat_key).
    - Am Vortag ab 18:00 Uhr: Vorabend-Erinnerung
    - Am Tag selbst morgens (ab 05:00): Tages-Erinnerung
    - Am Tag danach ab 05:00: Nachfrage („Wie lief ... gestern?“)
    """
    stats = stats or {}
    results: list[tuple[dict, str, str]] = []
    today = now.date()
    today_str = today.strftime("%Y-%m-%d")

    for f in facts:
        due_str = f.get("due_date")
        if not due_str:
            continue
        try:
            due_date = datetime.datetime.strptime(due_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        fid = f.get("id", 0)
        text = f.get("text", "")
        kind = f.get("kind", "fact")

        # 1. Vorabend (Tag vor due_date, ab 18:00)
        if today == due_date - datetime.timedelta(days=1) and now.hour >= 18:
            key = f"remind_{fid}_eve_{today_str}"
            if not stats.get(key):
                if kind == "birthday":
                    msg = f"Morgen hat {text} Geburtstag! 🎂 Hast du schon ein Geschenk?"
                else:
                    msg = f"Morgen ist {text} – du schaffst das! 💪🐾"
                results.append((f, msg, key))

        # 2. Tag selbst (ab 05:00 bis 21:00)
        elif today == due_date and 5 <= now.hour < 21:
            key = f"remind_{fid}_day_{today_str}"
            if not stats.get(key):
                if kind == "birthday":
                    msg = f"Heute ist {text}! Alles Gute zum Geburtstag! 🎂🎉✨"
                else:
                    msg = f"Heute steht {text} an! Ich drücke dir ganz fest die Pfoten! 🐾✨"
                results.append((f, msg, key))

        # 3. Tag danach (Nachfrage ab 05:00)
        elif today == due_date + datetime.timedelta(days=1) and now.hour >= 5:
            key = f"remind_{fid}_after_{today_str}"
            if not stats.get(key):
                if kind != "birthday":
                    msg = f"Wie lief eigentlich {text} gestern? 🍀 Erzähl mal!"
                    results.append((f, msg, key))

    return results


def should_brief(now: datetime.datetime, last_briefing: Optional[str]) -> bool:
    """Gibt True zurueck, wenn heute nach 05:00 Uhr noch kein Briefing gezeigt wurde."""
    if now.hour < 5:
        return False
    today_str = now.strftime("%Y-%m-%d")
    return last_briefing != today_str


def bedtime_due(now: datetime.datetime, bedtime: str, last_shown: Optional[float] = None) -> tuple[bool, bool]:
    """Prueft, ob die Schlafenszeit-Erinnerung faellig ist.

    Rueckgabe: (is_due, is_second_reminder)
    - Erste Erinnerung: ab bedtime.
    - Zweite Erinnerung: nach mind. 30 Minuten, falls der User weiterarbeitet.
    """
    bedtime = (bedtime or "").strip()
    if not bedtime or ":" not in bedtime:
        return False, False

    try:
        b_hour, b_min = [int(p) for p in bedtime.split(":", 1)]
    except ValueError:
        return False, False

    cur_min = now.hour * 60 + now.minute
    target_min = b_hour * 60 + b_min

    # Gueltiger Schlafenszeit-Bereich: von bedtime bis 04:30 Uhr morgens
    is_in_window = False
    if target_min <= cur_min or now.hour < 5:
        is_in_window = True

    if not is_in_window:
        return False, False

    if last_shown is None or (now.timestamp() - last_shown) > 43200:  # > 12h
        return True, False

    diff = now.timestamp() - last_shown
    if 1800 <= diff <= 5400:  # 30-90 min spaeter
        return True, True

    return False, False


def curious_question_for(char_id: str, user_name: str = "Boss", facts: Optional[list[dict]] = None) -> str:
    """Waehlt eine passende neugierige Frage fuer die gegebene Figur."""
    cinfo = get_character_info(char_id)
    species = cinfo.get("species", "").lower()

    if "hund" in species or "shiba" in char_id or "balu" in char_id:
        pool = QUESTIONS_DOG
    elif "drache" in species or "roboter" in species or "byte" in char_id or "drago" in char_id:
        pool = QUESTIONS_FANTASY
    else:
        pool = QUESTIONS_CAT

    q = random.choice(pool)
    return q.replace("Boss", user_name)
