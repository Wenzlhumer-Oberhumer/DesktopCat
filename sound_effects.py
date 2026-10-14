# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Prozedurale Kawaii-Soundeffekte fuer Desktop Cat (v2.4.0).

Erzeugt glasklare, niedliche 16-Bit 44.1kHz WAV-Sounds komplett im RAM
mittels Standard-Bibliothek (wave, struct, math) - 100 % abhaengigkeitsfrei
und latenzfrei abspielbar via winsound.PlaySound(..., SND_ASYNC | SND_MEMORY).
"""
from __future__ import annotations

import io
import math
import struct
import wave
from typing import Optional

try:
    import winsound
except ImportError:
    winsound = None

SAMPLE_RATE = 44100


def _build_wav(samples: list[float]) -> bytes:
    """Verpackt Float-Samples (-1.0 bis 1.0) in einen standardkonformen RIFF/WAVE-Header."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)        # Mono
        wf.setsampwidth(2)        # 16-Bit
        wf.setframerate(SAMPLE_RATE)
        raw = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            val = int(clamped * 32767)
            raw.extend(struct.pack("<h", val))
        wf.writeframes(bytes(raw))
    return buf.getvalue()


def _gen_meow() -> bytes:
    """Niedliches Kawaii-Miauen (aufsteigende und abfallende Harmonische)."""
    dur = 0.36
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # Frequenzkurve: 480 Hz -> 780 Hz -> 580 Hz
        env = math.sin(t / dur * math.pi) ** 0.8
        freq = 480 + 300 * math.sin(t / dur * math.pi)
        phase = 2 * math.pi * freq * t
        # Grundton + weiche Obertoene
        s = 0.65 * math.sin(phase) + 0.25 * math.sin(2 * phase) + 0.10 * math.sin(3 * phase)
        # Schnurr-Vibrato am Ende
        vibrato = 1.0 + 0.15 * math.sin(2 * math.pi * 18 * t)
        samples.append(s * env * vibrato * 0.75)
    return _build_wav(samples)


def _gen_purr() -> bytes:
    """Tiefes, beruhigendes Schnurren."""
    dur = 0.55
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.sin(t / dur * math.pi) ** 0.5
        # Tiefer Brummton (75 Hz) moduliert mit 24 Hz Schnurr-Rhythmus
        rumble = math.sin(2 * math.pi * 75 * t)
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 24 * t)
        sub = 0.3 * math.sin(2 * math.pi * 42 * t)
        s = (rumble * pulse + sub) * env * 0.70
        samples.append(s)
    return _build_wav(samples)


def _gen_pop() -> bytes:
    """Kristallklares Seifenblasen-Plopp."""
    dur = 0.08
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-t * 55.0)
        # Schneller Frequenz-Sweep nach unten: 1100 Hz -> 320 Hz
        freq = 1100.0 - 780.0 * (t / dur)
        s = math.sin(2 * math.pi * freq * t) * env * 0.85
        samples.append(s)
    return _build_wav(samples)


def _gen_chomp() -> bytes:
    """Niedliches Knabbern / Mampfen beim Fuettern."""
    dur = 0.18
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # Zwei kurze Knusper-Schlaege
        env1 = math.exp(-max(0.0, t) * 45.0) if t < 0.09 else 0.0
        env2 = math.exp(-max(0.0, t - 0.09) * 45.0) if t >= 0.09 else 0.0
        env = env1 + env2
        freq = 650.0 + 350.0 * math.sin(2 * math.pi * 80 * t)
        s = (0.7 * math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * 1400 * t)) * env * 0.70
        samples.append(s)
    return _build_wav(samples)


def _gen_water() -> bytes:
    """Sanftes Wassertroepfeln / Schluerfen."""
    dur = 0.22
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.sin(t / dur * math.pi) * math.exp(-t * 12.0)
        freq = 800.0 + 400.0 * math.cos(2 * math.pi * 15 * t)
        s = math.sin(2 * math.pi * freq * t) * env * 0.65
        samples.append(s)
    return _build_wav(samples)


def _gen_squeak() -> bytes:
    """Lustiger Quietsch-Sound fuer den Spielzeugball."""
    dur = 0.16
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.sin(t / dur * math.pi) ** 1.2
        freq = 1600.0 + 800.0 * math.sin(t / dur * math.pi)
        s = (0.8 * math.sin(2 * math.pi * freq * t) + 0.2 * math.sin(4 * math.pi * freq * t)) * env * 0.60
        samples.append(s)
    return _build_wav(samples)


# Sound-Cache (einmalig im RAM generiert)
SOUNDS: dict[str, bytes] = {}

def init_sounds() -> None:
    """Initialisiert alle Sound-Effekte im Speicher."""
    global SOUNDS
    if not SOUNDS:
        SOUNDS["meow"] = _gen_meow()
        SOUNDS["purr"] = _gen_purr()
        SOUNDS["pop"] = _gen_pop()
        SOUNDS["chomp"] = _gen_chomp()
        SOUNDS["water"] = _gen_water()
        SOUNDS["squeak"] = _gen_squeak()


def play_sound(name: str, cfg=None) -> bool:
    """Spielt einen gecachten Soundeffekt asynchron ab, falls Sound aktiviert ist."""
    if cfg is not None and not bool(cfg.get("pet.sound_enabled", True)):
        return False
    if winsound is None:
        return False
    if not SOUNDS:
        init_sounds()
    data = SOUNDS.get(name)
    if not data:
        return False
    try:
        winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC)
        return True
    except Exception:
        return False
