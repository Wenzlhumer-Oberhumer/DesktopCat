# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Windows MCI Voice Recorder für Desktop Cat (v3.0.0).

Nimmt Audio über das Standard-Mikrofon per Windows MCI (ctypes winmm.dll)
in 16kHz 16-Bit Mono WAV auf (mit automatischem Fallback auf Standard-Format).
Funktioniert 100% nativ auf allen Windows-PCs ohne externe C-Compiler oder Binaries.
"""
from __future__ import annotations

import ctypes
import os
import tempfile
import time
from pathlib import Path
from typing import Optional


class VoiceRecorder:
    """Zeichnet Sprache vom Mikrofon auf und speichert sie als WAV-Datei."""

    def __init__(self, alias: str = "DesktopCatMic"):
        self.alias = alias
        self._is_recording = False
        self._start_time: float = 0.0
        self._winmm = ctypes.windll.winmm
        self._buf = ctypes.create_unicode_buffer(256)

    def _send_mci(self, cmd: str) -> int:
        """Führt einen MCI-Befehl aus und gibt den Rückgabecode zurück (0 = Erfolg)."""
        return int(self._winmm.mciSendStringW(cmd, self._buf, 256, 0))

    def _get_mci_error(self, err_code: int) -> str:
        err_buf = ctypes.create_unicode_buffer(256)
        self._winmm.mciGetErrorStringW(err_code, err_buf, 256)
        return err_buf.value

    def is_recording(self) -> bool:
        return self._is_recording

    def duration_seconds(self) -> float:
        if not self._is_recording:
            return 0.0
        return max(0.0, time.time() - self._start_time)

    def start_recording(self) -> bool:
        """Startet die Aufnahme. Schließt eventuell offene Alt-Aufnahmen vorher."""
        if self._is_recording:
            self.cancel()

        # Sicherstellen, dass das Alias geschlossen ist
        self._send_mci(f"close {self.alias}")

        # Neues Audio-Aufnahmegerät öffnen
        code = self._send_mci(f"open new type waveaudio alias {self.alias}")
        if code != 0:
            return False

        self._send_mci(f"set {self.alias} time format ms")

        # Versuche zuerst 16kHz 16-Bit Mono (Standard für KI-Spracherkennung)
        # In MCI müssen channels, bitspersample, samplespersec, bytespersec und alignment atomar gesetzt werden:
        fmt_cmd = (
            f"set {self.alias} channels 1 bitspersample 16 samplespersec 16000 "
            f"bytespersec 32000 alignment 2"
        )
        self._send_mci(fmt_cmd)

        # Starte Aufnahme
        code = self._send_mci(f"record {self.alias}")
        if code != 0:
            # Falls Hardware 16kHz verweigert hat, zurücksetzen und im Hardware-Standard aufnehmen
            self._send_mci(f"close {self.alias}")
            code = self._send_mci(f"open new type waveaudio alias {self.alias}")
            if code != 0:
                return False
            code = self._send_mci(f"record {self.alias}")
            if code != 0:
                self._send_mci(f"close {self.alias}")
                return False

        self._is_recording = True
        self._start_time = time.time()
        return True

    def stop_recording(self, target_path: Optional[str | Path] = None) -> Optional[str]:
        """Stoppt die Aufnahme und speichert die Datei als WAV.

        Gibt den absoluten Pfad zur WAV-Datei zurück oder None bei Fehlern oder zu kurzer Aufnahme.
        """
        if not self._is_recording:
            return None

        self._is_recording = False
        self._send_mci(f"stop {self.alias}")

        if not target_path:
            fd, tmp = tempfile.mkstemp(prefix="desktopcat_voice_", suffix=".wav")
            os.close(fd)
            target_path = tmp

        target_str = str(Path(target_path).resolve())
        # Anführungszeichen für Dateipfad
        save_cmd = f'save {self.alias} "{target_str}"'
        save_code = self._send_mci(save_cmd)
        self._send_mci(f"close {self.alias}")

        if save_code != 0 or not os.path.exists(target_str):
            return None

        # Prüfen ob Datei Inhalt hat (> 44 Byte WAV Header)
        try:
            sz = os.path.getsize(target_str)
            if sz <= 100:  # Mindestens ein paar Samples Audio
                try:
                    os.remove(target_str)
                except OSError:
                    pass
                return None
        except OSError:
            return None

        return target_str

    def cancel(self) -> None:
        """Bricht eine laufende Aufnahme ohne Speichern ab."""
        if self._is_recording:
            self._is_recording = False
            self._send_mci(f"stop {self.alias}")
            self._send_mci(f"close {self.alias}")


_global_recorder: Optional[VoiceRecorder] = None


def get_recorder() -> VoiceRecorder:
    global _global_recorder
    if _global_recorder is None:
        _global_recorder = VoiceRecorder()
    return _global_recorder
