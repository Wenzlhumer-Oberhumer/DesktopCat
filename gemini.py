# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Gemini API mit eigenem Gratis-Key aus Google AI Studio.

Der Key liegt in der Windows-Anmeldeinformationsverwaltung (nicht im Klartext in config.json).
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

import requests

import auth_manager
from i18n import tr

KEY_URL = "https://aistudio.google.com/app/apikey"

# Schnelle Lite-Modelle zuerst (Free Tier); *-latest-Aliase ueberleben Modellwechsel.
# Das volle Flash-Modell nur als Reserve, falls die Lite-Modelle ueberlastet sind.
MODELS = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]
_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_CRED_TARGET = "Mochi/GeminiApiKey"


class LLMError(Exception):
    """Fehler beim Gemini-Aufruf mit benutzerfreundlicher Meldung."""


# -- Key- & Auth-Speicher -------------------------------------------------------------
def get_key() -> str:
    return auth_manager.get_auth_manager().get_api_key()


def has_key() -> bool:
    return auth_manager.get_auth_manager().has_auth()


def save_key(key: str) -> None:
    auth_manager.get_auth_manager().save_api_key(key)


def clear_key() -> None:
    auth_manager.get_auth_manager().clear_api_key()
    auth_manager.get_auth_manager().clear_oauth_data()


def validate_key(key: str) -> None:
    """Prueft den Key ueber die Modellliste: schnell und ohne Kontingent-Verbrauch. Wirft LLMError."""
    try:
        resp = requests.get(_API.split("/models/")[0] + "/models", params={"pageSize": 1},
                            headers={"x-goog-api-key": key.strip()}, timeout=(6, 10))
    except requests.RequestException:
        raise LLMError(tr("gemini.no_internet"))
    if not resp.ok:
        raise LLMError(_error_text(resp))


# -- Anfrage --------------------------------------------------------------------------
def _error_text(resp: requests.Response) -> str:
    try:
        err = resp.json().get("error", {})
    except ValueError:
        err = {}
    status, msg = str(err.get("status", "")), str(err.get("message", ""))
    if _key_invalid(resp):
        return tr("gemini.invalid_key")
    if resp.status_code == 429 or status == "RESOURCE_EXHAUSTED":
        return tr("gemini.quota_exceeded")
    if resp.status_code in (500, 503):
        return tr("gemini.overloaded")
    return tr("gemini.error", code=resp.status_code, msg=msg[:160] or resp.reason)


def _key_invalid(resp: requests.Response) -> bool:
    # Nur echte Key-Fehler; ein 403 kann auch "Modell im Free Tier nicht erlaubt" heissen
    return resp.status_code == 401 or "API_KEY_INVALID" in resp.text or "API key not valid" in resp.text


def ask(prompt: str, timeout_s: float = 60.0, model: Optional[str] = None,
        image_b64: Optional[str] = None, key: Optional[str] = None,
        audio_b64: Optional[str] = None, audio_mime: str = "audio/wav") -> str:
    """Schickt einen Prompt (optional mit Bild oder Audio) an Gemini und gibt den Antworttext zurueck."""
    if key:
        headers = {"x-goog-api-key": key.strip()}
    else:
        auth_mgr = auth_manager.get_auth_manager()
        if auth_mgr.is_oauth_configured():
            headers = auth_mgr.get_auth_headers()
        else:
            k = get_key().strip()
            headers = {"x-goog-api-key": k} if k else {}

    if not headers:
        raise LLMError(tr("gemini.enter_key_first"))

    parts: list[dict] = [{"text": prompt}]
    if image_b64:
        parts.append({"inlineData": {"mimeType": "image/png", "data": image_b64}})
    if audio_b64:
        parts.append({"inlineData": {"mimeType": audio_mime, "data": audio_b64}})

    # minimales "Nachdenken": halbiert die Antwortzeit, reicht fuer Mochis kurze Antworten
    payload = {"contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"thinkingConfig": {"thinkingLevel": "minimal"}}}

    models = [m for m in [model, *MODELS] if m]
    last = tr("gemini.unreachable")
    for m in dict.fromkeys(models):
        try:
            resp = requests.post(_API.format(model=m), json=payload, timeout=(6, timeout_s),
                                 headers=headers)
        except requests.Timeout:
            last = tr("gemini.timeout")
            continue
        except requests.RequestException:
            raise LLMError(tr("gemini.no_internet"))
        # Modell weg (404), gesperrt (403), Kontingent pro Modell (429) oder ueberlastet (5xx) -> naechstes
        if not _key_invalid(resp) and resp.status_code in (403, 404, 429, 500, 503):
            last = _error_text(resp)
            continue
        if not resp.ok:
            raise LLMError(_error_text(resp))
        data = resp.json()
        cands = data.get("candidates") or []
        if not cands:
            reason = (data.get("promptFeedback") or {}).get("blockReason")
            blocked_msg = tr("gemini.blocked") + (f" ({reason})" if reason else "")
            raise LLMError(blocked_msg)
        out = cands[0].get("content", {}).get("parts") or []
        return "".join(p.get("text", "") for p in out if not p.get("thought")).strip()
    raise LLMError(last)


def ask_audio(audio_source: str | bytes | Path, prompt: Optional[str] = None,
              timeout_s: float = 60.0, model: Optional[str] = None) -> str:
    """Sendet eine Audio-Datei (WAV) direkt an Gemini zur multimodalen Spracherkennung."""
    if isinstance(audio_source, (str, Path)):
        p = Path(audio_source)
        if not p.exists():
            raise LLMError(f"Audiodatei nicht gefunden: {p}")
        with open(p, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(audio_source, bytes):
        raw_bytes = audio_source
    else:
        raise ValueError("audio_source muss ein Pfad oder bytes sein")

    audio_b64 = base64.b64encode(raw_bytes).decode("ascii")

    effective_prompt = prompt or (
        "Du hörst eine Sprachaufnahme des Nutzers. "
        "Verstehe genau, was der Nutzer sagt oder fragt, und antworte kurz, "
        "charmant und liebenswert auf Deutsch (maximal 1-3 Sätze)."
    )

    return ask(
        prompt=effective_prompt,
        timeout_s=timeout_s,
        model=model,
        audio_b64=audio_b64,
        audio_mime="audio/wav",
    )

