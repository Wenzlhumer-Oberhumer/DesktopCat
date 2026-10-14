# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Logik fuer Zubehoer (Accessoires), Saison-, Wetter- und System-Reaktionen sowie Flugphysik."""
from __future__ import annotations

import ctypes
import datetime
from typing import Any, Optional, Union

ACCESSORY_NAMES: tuple[str, ...] = (
    "hacker_glasses",
    "cloud",
    "party_hat",
    "nightcap",
    "pumpkin_hat",
    "santa_hat",
    "new_year",
    "umbrella",
    "sunglasses",
    "scarf",
    "beanie",
    "crown",
    "bow",
    "bandana",
    "fan",
)

HEAD_SLOT_PRIORITY: tuple[str, ...] = (
    "hacker_glasses",
    "nightcap",
    "party_hat",
    "sunglasses",
    "beanie",
    "pumpkin_hat",
    "santa_hat",
    "new_year",
    "crown",
)


def seasonal_accessory(d: Union[datetime.date, datetime.datetime]) -> Optional[str]:
    """Gibt das passende saisonale Accessoire fuer ein Datum zurueck."""
    month, day = d.month, d.day
    # Halloween (15.-31.10.)
    if month == 10 and 15 <= day <= 31:
        return "pumpkin_hat"
    # Silvester / Neujahr (31.12. - 01.01.)
    if (month == 12 and day == 31) or (month == 1 and day == 1):
        return "new_year"
    # Weihnachten (01.-26.12.)
    if month == 12 and 1 <= day <= 26:
        return "santa_hat"
    return None


def weather_accessory(temp_c: Optional[float], condition_text: str = "") -> Optional[str]:
    """Gibt ein passendes Wetter-Accessoire zurueck (Regen -> umbrella, Schnee -> beanie, Hitze -> sunglasses, Kaelte -> scarf)."""
    text = (condition_text or "").lower()
    if any(w in text for w in ("regen", "rain", "schauer", "shower", "gewitter", "thunderstorm", "drizzle", "niesel")):
        return "umbrella"
    if any(w in text for w in ("schnee", "snow", "graupel", "sleet")):
        return "beanie"
    if temp_c is not None and temp_c > 25.0:
        return "sunglasses"
    if temp_c is not None and temp_c < 3.0:
        return "scarf"
    return None


def weather_accessories(temp_c: Optional[float], condition_text: str = "") -> list[str]:
    """Gibt alle passenden Wetter-Accessoires zurueck (z. B. scarf + beanie bei Schnee)."""
    accs: list[str] = []
    text = (condition_text or "").lower()
    if any(w in text for w in ("regen", "rain", "schauer", "shower", "gewitter", "thunderstorm", "drizzle", "niesel")):
        accs.append("umbrella")
    if any(w in text for w in ("schnee", "snow", "graupel", "sleet")):
        accs.extend(["scarf", "beanie"])
    elif temp_c is not None and temp_c < 3.0:
        accs.append("scarf")
    if temp_c is not None and temp_c > 25.0:
        accs.append("sunglasses")
    return accs


# ======================================================================================
#  Windows System-Monitoring (CPU & RAM ohne Fremdpakete)
# ======================================================================================
class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def get_system_times() -> Optional[tuple[int, int, int]]:
    """Liest rohe Zeitwerte (Idle, Kernel, User) ueber GetSystemTimes."""
    try:
        idle_time = FILETIME()
        kernel_time = FILETIME()
        user_time = FILETIME()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle_time), ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return _filetime_to_int(idle_time), _filetime_to_int(kernel_time), _filetime_to_int(user_time)
    except Exception:
        pass
    return None


def calculate_cpu_percent(t1: tuple[int, int, int], t2: tuple[int, int, int]) -> float:
    """Berechnet CPU-Auslastung in Prozent aus zwei GetSystemTimes-Messungen."""
    idle1, kernel1, user1 = t1
    idle2, kernel2, user2 = t2
    idle_delta = idle2 - idle1
    kernel_delta = kernel2 - kernel1
    user_delta = user2 - user1
    total_delta = kernel_delta + user_delta
    if total_delta <= 0:
        return 0.0
    cpu = (1.0 - (idle_delta / total_delta)) * 100.0
    return max(0.0, min(100.0, round(cpu, 1)))


def get_ram_load_percent() -> float:
    """Ermittelt den aktuellen physischen RAM-Verbrauch in Prozent (0-100)."""
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return float(stat.dwMemoryLoad)
    except Exception:
        pass
    return 0.0


# ======================================================================================
#  Flug-Positionierung
# ======================================================================================
def fly_position(
    target: Union[tuple[float, float], Any],
    pet_size: Union[tuple[float, float], Any],
    screen_rect: Union[tuple[float, float, float, float], Any],
) -> tuple[float, float]:
    """Berechnet globale Koordinaten (px, py), damit die fliegende Figur NEBEN dem Ziel schwebt."""
    # Extraktion target (tx, ty)
    if hasattr(target, "x") and hasattr(target, "y"):
        tx, ty = float(target.x()), float(target.y())
    else:
        tx, ty = float(target[0]), float(target[1])

    # Extraktion pet_size (pw, ph)
    if hasattr(pet_size, "width") and hasattr(pet_size, "height"):
        pw, ph = float(pet_size.width()), float(pet_size.height())
    else:
        pw, ph = float(pet_size[0]), float(pet_size[1])

    # Extraktion screen_rect (sx, sy, sw, sh)
    if hasattr(screen_rect, "left") and hasattr(screen_rect, "top"):
        sx = float(screen_rect.left())
        sy = float(screen_rect.top())
        sw = float(screen_rect.width())
        sh = float(screen_rect.height())
    else:
        sx, sy, sw, sh = float(screen_rect[0]), float(screen_rect[1]), float(screen_rect[2]), float(screen_rect[3])

    # Standardmaessig rechts neben das Ziel platzieren
    offset_x = 24.0
    candidate_x = tx + offset_x
    if candidate_x + pw > sx + sw:
        # Falls rechts ueber den Bildschirmrand hinausragt: links platzieren
        candidate_x = tx - pw - offset_x

    # Klemmen innerhalb des Bildschirms
    safe_x = max(sx, min(sx + sw - pw, candidate_x))

    # Y leicht zentriert oder knapp oberhalb des Ziels
    candidate_y = ty - ph * 0.4
    safe_y = max(sy, min(sy + sh - ph, candidate_y))

    return round(safe_x, 1), round(safe_y, 1)
