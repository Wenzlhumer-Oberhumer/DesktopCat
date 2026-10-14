# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Dual Voice TTS & Audio Player Engine für Desktop Cat (v3.0.0).

Kombiniert:
1. Microsoft Neural Edge-TTS (online, kristallklar, niedlicher Kawaii-Pitch +20%)
2. Windows SAPI 5 (100% offline Fallback)
3. Synchrone Signale für Lip-Sync (Mundbewegung) via PyQt6 QtMultimedia
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

# Beliebte Stimmen fuer Deutsch und Englisch
VOICE_PRESETS = {
    "de_katja": {"id": "de-DE-KatjaNeural", "name": "Katja (Niedlich & Freundlich)", "lang": "de"},
    "de_amala": {"id": "de-DE-AmalaNeural", "name": "Amala (Lebendig & Sanft)", "lang": "de"},
    "de_conrad": {"id": "de-DE-ConradNeural", "name": "Conrad (Männlich & Ruhig)", "lang": "de"},
    "de_killian": {"id": "de-DE-KillianNeural", "name": "Killian (Jungkater)", "lang": "de"},
    "en_ana": {"id": "en-US-AnaNeural", "name": "Ana (Cute & Playful)", "lang": "en"},
    "en_ava": {"id": "en-US-AvaNeural", "name": "Ava (Warm & Clear)", "lang": "en"},
}


def clean_text_for_speech(text: str) -> str:
    """Bereitet Chat- und KI-Antworten fuer das Vorlesen vor.

    Entfernt Code-Bloecke, Markdown-Links, Formatierungssterne und unpassende Sonderzeichen.
    """
    if not text:
        return ""

    t = text
    # 1. Code-Bloecke (```...```) entfernen
    t = re.sub(r"```[\s\S]*?```", " [Codeblock] ", t)
    # 2. Inline-Code (`...`) säubern
    t = re.sub(r"`([^`]+)`", r"\1", t)
    # 3. Markdown Links [Titel](url) -> Titel
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # 4. Fett/Kursiv (**text**, *text*)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    # Kursiv mit Unterstrich nur an Wortgrenzen (nicht mitten in foo_bar)
    t = re.sub(r"\b__([^_]+)__\b", r"\1", t)
    t = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", t)
    # 5. Überschriften (#, ##, ...)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
    # 6. Aufzählungszeichen am Zeilenanfang
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.MULTILINE)
    # 7. Unnötige Leerzeichen & Zeilenumbrüche glätten
    t = re.sub(r"\s+", " ", t).strip()
    return t


class _EdgeTtsWorker(QThread):
    """Generiert im Hintergrund eine MP3 per edge-tts."""

    finished_file = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, text: str, voice: str, pitch: str, rate: str):
        super().__init__()
        self.text = text
        self.voice = voice
        self.pitch = pitch
        self.rate = rate

    def run(self) -> None:
        try:
            import edge_tts

            fd, out_path = tempfile.mkstemp(prefix="desktopcat_tts_", suffix=".mp3")
            os.close(fd)

            async def _synthesize():
                comm = edge_tts.Communicate(
                    text=self.text,
                    voice=self.voice,
                    pitch=self.pitch,
                    rate=self.rate,
                )
                await comm.save(out_path)

            asyncio.run(_synthesize())

            if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
                self.finished_file.emit(out_path)
            else:
                self.failed.emit("Edge-TTS Datei zu klein oder leer")
        except Exception as e:
            self.failed.emit(str(e))


class TTSManager(QObject):
    """Zentrale Sprachausgabe mit Edge-TTS, SAPI 5 Fallback und Lip-Sync Signalen."""

    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()
    speaking_error = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)

        self._player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._is_speaking = False
        self._current_file: Optional[str] = None
        self._workers: list = []          # laufende Edge-Worker festhalten (sonst "Destroyed while running")
        self._request = 0                 # nur die neueste Anfrage darf noch sprechen
        self._sapi_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def is_speaking(self) -> bool:
        return self._is_speaking

    def set_volume(self, volume: float) -> None:
        """Lautstärke 0.0 bis 1.0."""
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    @pyqtSlot(QMediaPlayer.PlaybackState)
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            if not self._is_speaking:
                self._is_speaking = True
                self.speaking_started.emit()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            if self._is_speaking:
                self._is_speaking = False
                self.speaking_finished.emit()
            self._cleanup_file()

    def _cleanup_file(self) -> None:
        if self._current_file and os.path.exists(self._current_file):
            try:
                os.remove(self._current_file)
            except OSError:
                pass
            self._current_file = None

    def stop(self) -> None:
        """Stoppt die aktuelle Sprachausgabe sofort."""
        self._stop_event.set()
        if self._player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._player.stop()
        if self._is_speaking:
            self._is_speaking = False
            self.speaking_finished.emit()
        self._cleanup_file()

    def speak(self, text: str, cfg: Optional[dict] = None) -> None:
        """Liest den übergebenen Text vor. Prüft voice.enabled, nutzt Edge-TTS oder SAPI 5."""
        cfg = cfg or {}
        voice_cfg = cfg.get("voice", {}) if isinstance(cfg.get("voice"), dict) else {}

        # Prüfe ob Sprachausgabe aktiviert ist
        if not bool(voice_cfg.get("enabled", True)):
            return

        clean = clean_text_for_speech(text)
        if not clean:
            return

        self.stop()
        self._stop_event.clear()
        self._request += 1

        # Standard: eingebaute Windows-Stimme (offline, kein Text verlaesst den PC).
        # Die Online-Stimme (edge-tts, inoffizieller Microsoft-Dienst) nur, wenn ausdruecklich eingeschaltet.
        if not bool(voice_cfg.get("online", False)):
            self._fallback_sapi(clean)
            return

        # Konfiguration
        lang = str(cfg.get("language", "de")).lower()
        default_voice = "de-DE-KatjaNeural" if lang.startswith("de") else "en-US-AnaNeural"
        voice_id = str(voice_cfg.get("name", default_voice))
        pitch = str(voice_cfg.get("pitch", "+20%"))
        rate = str(voice_cfg.get("rate", "+0%"))

        # Versuche zuerst Edge-TTS
        worker = _EdgeTtsWorker(clean, voice_id, pitch, rate)
        worker.request_id = self._request
        worker.text = clean
        worker.finished_file.connect(self._on_edge_success)
        worker.failed.connect(self._on_edge_failed)
        self._workers = [w for w in self._workers if not w.isFinished()] + [worker]
        worker.start()

    @pyqtSlot(str)
    def _on_edge_failed(self, err: str) -> None:
        w = self.sender()
        if w is not None and getattr(w, "request_id", -1) == self._request:
            self._fallback_sapi(getattr(w, "text", ""), err)

    @pyqtSlot(str)
    def _on_edge_success(self, file_path: str) -> None:
        w = self.sender()
        if self._stop_event.is_set() or (w is not None and getattr(w, "request_id", -1) != self._request):
            try:
                os.remove(file_path)
            except OSError:
                pass
            return
        self._current_file = file_path
        self._player.setSource(QUrl.fromLocalFile(file_path))
        self._player.play()

    def _fallback_sapi(self, text: str, reason: str = "") -> None:
        """Offline-Fallback via Windows SAPI 5 SpVoice."""
        if self._stop_event.is_set():
            return

        def _run_sapi():
            try:
                import pythoncom
                import win32com.client
                pythoncom.CoInitialize()
                try:
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    self._is_speaking = True
                    self.speaking_started.emit()
                    # Synchron sprechen
                    speaker.Speak(text)
                finally:
                    pythoncom.CoUninitialize()
            except Exception as e:
                self.speaking_error.emit(f"SAPI 5 Error: {e}")
            finally:
                self._is_speaking = False
                self.speaking_finished.emit()

        self._sapi_thread = threading.Thread(target=_run_sapi, daemon=True)
        self._sapi_thread.start()


_global_tts: Optional[TTSManager] = None


def get_tts() -> TTSManager:
    global _global_tts
    if _global_tts is None:
        _global_tts = TTSManager()
    return _global_tts
