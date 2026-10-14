# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Unit-Tests für Desktop Cat v3.0.0 Features:
1. Windows MCI Voice Recorder (16kHz Mono WAV, Start/Stop/Cancel)
2. Dual Voice TTS Manager (Edge-TTS, SAPI 5 Fallback, Text Preprocessor)
3. Prozeduraler Lip-Sync & Mundbewegung in Sprites und PetWindow
4. Dual Gemini Auth Manager (Option A OAuth 2.0 Loopback & Option C AI Studio Key)
5. Multimodale Gemini Audio-Payload (ask_audio)
6. Hotkey-Parsing für 'ctrl+alt+space'
"""
from __future__ import annotations

import base64
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import auth_manager
import gemini
import pet_sprites
import voice_recorder
import voice_tts
from main import parse_hotkey


class TestVoiceRecorder(unittest.TestCase):
    """Prüft den nativen Windows MCI Voice Recorder."""

    def test_recorder_initial_state(self):
        rec = voice_recorder.VoiceRecorder(alias="TestRecUnit1")
        self.assertFalse(rec.is_recording())
        self.assertEqual(rec.duration_seconds(), 0.0)

    def test_recorder_start_and_cancel(self):
        rec = voice_recorder.VoiceRecorder(alias="TestRecUnit2")
        started = rec.start_recording()
        # Falls kein Mikrofon angeschlossen ist, wirft es zumindest keine Exception
        if started:
            self.assertTrue(rec.is_recording())
            self.assertGreaterEqual(rec.duration_seconds(), 0.0)
            rec.cancel()
            self.assertFalse(rec.is_recording())

    def test_recorder_stop_too_short(self):
        rec = voice_recorder.VoiceRecorder(alias="TestRecUnit3")
        started = rec.start_recording()
        if started:
            # Sofortiges Stoppen ohne Audio sollte None zurückgeben (kein Datenmüll)
            res = rec.stop_recording()
            # Entweder None (da < 100 bytes) oder gelöscht
            self.assertFalse(rec.is_recording())


class TestVoiceTTS(unittest.TestCase):
    """Prüft Text-Preprocessing und TTS-Manager."""

    def test_clean_text_for_speech_removes_code_and_markdown(self):
        raw = (
            "# Wichtige Info\n"
            "Hallo **Boss**! Schau dir [hier](https://example.com) den Code an:\n"
            "```python\n"
            "import os\n"
            "print('Secret')\n"
            "```\n"
            "Und `inline_code` nicht vergessen! *Miau*"
        )
        cleaned = voice_tts.clean_text_for_speech(raw)
        self.assertNotIn("```", cleaned)
        self.assertNotIn("https://example.com", cleaned)
        self.assertNotIn("**Boss**", cleaned)
        self.assertIn("Boss", cleaned)
        self.assertIn("hier", cleaned)
        self.assertIn("[Codeblock]", cleaned)
        self.assertIn("inline_code", cleaned)
        self.assertIn("Miau", cleaned)

    def test_voice_presets_registered(self):
        presets = voice_tts.VOICE_PRESETS
        self.assertIn("de_katja", presets)
        self.assertIn("de_amala", presets)
        self.assertIn("en_ana", presets)
        self.assertEqual(presets["de_katja"]["id"], "de-DE-KatjaNeural")

    def test_tts_manager_volume(self):
        tts = voice_tts.TTSManager()
        tts.set_volume(0.8)
        self.assertFalse(tts.is_speaking())
        tts.stop()


class TestLipSyncMouthMovement(unittest.TestCase):
    """Prüft prozedurale Mundbewegungen bei aktiviertem Lip-Sync."""

    def test_idle_without_speaking_is_default_mouth(self):
        ctx = pet_sprites.PoseContext(key="idle", t=1.0, age=1.0, speaking=False)
        pose = pet_sprites.compute_pose(ctx)
        self.assertEqual(pose.mouth, "w")

    def test_lip_sync_animates_mouth_cycle(self):
        observed_mouths = set()
        for i in range(25):
            t = i * 0.04
            ctx = pet_sprites.PoseContext(key="idle", t=t, age=t, speaking=True)
            pose = pet_sprites.compute_pose(ctx)
            observed_mouths.add(pose.mouth)

        # Sollte zwischen 'w', 'smile' und 'o' wechseln
        self.assertTrue(len(observed_mouths) >= 2)
        self.assertTrue("smile" in observed_mouths or "o" in observed_mouths)


class TestAuthManager(unittest.TestCase):
    """Nur noch API-Key (OAuth entfernt: privates Google-Abo schaltet die Gemini-API nicht frei)."""

    def setUp(self):
        self.auth = auth_manager.AuthManager()

    def test_no_oauth_api_left(self):
        for name in ("build_oauth_url", "start_oauth_flow_async", "get_oauth_data", "is_oauth_configured"):
            self.assertFalse(hasattr(self.auth, name), name)

    def test_get_auth_headers_with_api_key(self):
        with patch.object(self.auth, "get_api_key", return_value="AIzaSyTestKey123"):
            self.assertEqual(self.auth.get_auth_headers(), {"x-goog-api-key": "AIzaSyTestKey123"})
            self.assertEqual(self.auth.get_auth_mode(), "apikey")
        with patch.object(self.auth, "get_api_key", return_value=""):
            self.assertEqual(self.auth.get_auth_headers(), {})
            self.assertFalse(self.auth.has_auth())


class TestGeminiAudioPayload(unittest.TestCase):
    """Prüft die multimodale Vorbereitung von Audio-Daten in gemini.ask_audio."""

    @patch("gemini.ask")
    def test_ask_audio_sends_wav_payload(self, mock_ask):
        mock_ask.return_value = "Hallo, ich habe dich gehört!"
        fake_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(fake_wav)
            tmp_path = f.name

        try:
            res = gemini.ask_audio(tmp_path, prompt="TestPrompt")
            self.assertEqual(res, "Hallo, ich habe dich gehört!")
            mock_ask.assert_called_once()
            _, kwargs = mock_ask.call_args
            self.assertEqual(kwargs.get("audio_mime"), "audio/wav")
            # Base64 muss mit dem erzeugten Fake-WAV übereinstimmen
            expected_b64 = base64.b64encode(fake_wav).decode("ascii")
            self.assertEqual(kwargs.get("audio_b64"), expected_b64)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestHotkeyVoiceParsing(unittest.TestCase):
    """Prüft, ob 'ctrl+alt+space' für Push-to-Talk korrekt geparst wird."""

    def test_parse_ctrl_alt_space(self):
        parsed = parse_hotkey("ctrl+alt+space")
        self.assertIsNotNone(parsed)
        mods, vk = parsed
        # VK_SPACE ist 0x20
        self.assertEqual(vk, 0x20)
        # MOD_CONTROL (0x0002) | MOD_ALT (0x0001) = 0x0003
        self.assertEqual(mods, 0x0003)


# Standalone runner functions for run_tests.py
def test_voice_recorder_flow():
    t = TestVoiceRecorder()
    t.test_recorder_initial_state()
    t.test_recorder_start_and_cancel()
    t.test_recorder_stop_too_short()


def test_voice_tts_flow():
    t = TestVoiceTTS()
    t.test_clean_text_for_speech_removes_code_and_markdown()
    t.test_voice_presets_registered()
    t.test_tts_manager_volume()


def test_lip_sync_mouth_movement_flow():
    t = TestLipSyncMouthMovement()
    t.test_idle_without_speaking_is_default_mouth()
    t.test_lip_sync_animates_mouth_cycle()


def test_dual_auth_manager_flow():
    t = TestAuthManager()
    t.setUp()
    t.test_no_oauth_api_left()
    t.test_get_auth_headers_with_api_key()


def test_gemini_audio_payload_flow():
    t = TestGeminiAudioPayload()
    t.test_ask_audio_sends_wav_payload()


def test_hotkey_voice_parsing_flow():
    t = TestHotkeyVoiceParsing()
    t.test_parse_ctrl_alt_space()


if __name__ == "__main__":
    unittest.main()
