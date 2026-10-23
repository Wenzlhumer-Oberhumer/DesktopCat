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


def _gen_meow_purr() -> bytes:
    """Kombiniertes Kawaii-Miez-Schnurren (~0.62s): Sanftes Anmaunzen gefolgt von warmem Schnurren."""
    dur = 0.62
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # Meow-Anteil (0.0 .. 0.24s)
        s_meow = 0.0
        if t < 0.24:
            env_m = math.sin(t / 0.24 * math.pi) ** 0.8
            freq_m = 520.0 + 260.0 * math.sin(t / 0.24 * math.pi)
            phase_m = 2.0 * math.pi * freq_m * t
            s_m = 0.65 * math.sin(phase_m) + 0.25 * math.sin(2 * phase_m) + 0.10 * math.sin(3 * phase_m)
            vib_m = 1.0 + 0.12 * math.sin(2 * math.pi * 18 * t)
            s_meow = s_m * env_m * vib_m * 0.72

        # Purr-Anteil (0.20 .. 0.62s)
        s_purr = 0.0
        if t >= 0.20:
            t_p = t - 0.20
            dur_p = 0.42
            env_p = math.sin(t_p / dur_p * math.pi) ** 0.5
            rumble = math.sin(2.0 * math.pi * 75.0 * t_p)
            pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * 24.0 * t_p)
            sub = 0.3 * math.sin(2.0 * math.pi * 42.0 * t_p)
            s_purr = (rumble * pulse + sub) * env_p * 0.70

        # Crossfade zwischen 0.20s und 0.24s
        if t < 0.20:
            s = s_meow
        elif t > 0.24:
            s = s_purr
        else:
            alpha = (t - 0.20) / 0.04
            s = (1.0 - alpha) * s_meow + alpha * s_purr
        samples.append(s)
    return _build_wav(samples)


def _gen_chirp() -> bytes:
    """Niedlicher, aufsteigender Katzen-Aktivierungs-Triller (~0.20s: 'brrp!' von 520 Hz bis 920 Hz mit 22-Hz-Triller)."""
    dur = 0.20
    n = int(SAMPLE_RATE * dur)
    samples = []
    phase = 0.0
    dt = 1.0 / SAMPLE_RATE
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.sin(t / dur * math.pi) ** 0.6
        freq = 520.0 + (920.0 - 520.0) * (t / dur) + 45.0 * math.sin(2.0 * math.pi * 22.0 * t)
        phase += 2.0 * math.pi * freq * dt
        trill_amp = 0.78 + 0.22 * math.sin(2.0 * math.pi * 22.0 * t)
        s = (0.70 * math.sin(phase) + 0.22 * math.sin(2.0 * phase) + 0.08 * math.sin(3.0 * phase))
        samples.append(s * env * trill_amp * 0.75)
    return _build_wav(samples)


def _gen_yawn() -> bytes:
    """Sanfter, schlaefriger absteigender Katzen-Gaehner / Seufzer (~0.45s: 620 Hz -> 340 Hz)."""
    dur = 0.45
    n = int(SAMPLE_RATE * dur)
    samples = []
    phase = 0.0
    dt = 1.0 / SAMPLE_RATE
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.sin(t / dur * math.pi) ** 0.85
        freq = 620.0 - (620.0 - 340.0) * (t / dur)
        phase += 2.0 * math.pi * freq * dt
        harmonics = 0.65 * math.sin(phase) + 0.25 * math.sin(2.0 * phase) + 0.10 * math.sin(3.0 * phase)
        breathy = 0.05 * math.sin(2.0 * math.pi * 1200.0 * t)
        s = (harmonics + breathy) * env * 0.65
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
        SOUNDS["meow_purr"] = _gen_meow_purr()
        SOUNDS["chirp"] = _gen_chirp()
        SOUNDS["yawn"] = _gen_yawn()


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
