"""Gemini API mit eigenem Gratis-Key aus Google AI Studio.

Der Key liegt in der Windows-Anmeldeinformationsverwaltung (nicht im Klartext in config.json).
"""
from __future__ import annotations

from typing import Optional

import requests

KEY_URL = "https://aistudio.google.com/app/apikey"
MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]   # *-latest-Aliase ueberleben Modellwechsel
_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_CRED_TARGET = "Mochi/GeminiApiKey"


class LLMError(Exception):
    """Fehler beim Gemini-Aufruf mit benutzerfreundlicher Meldung."""


# -- Key-Speicher ---------------------------------------------------------------------
def get_key() -> str:
    try:
        import win32cred
        cred = win32cred.CredRead(_CRED_TARGET, win32cred.CRED_TYPE_GENERIC)
        return cred["CredentialBlob"].decode("utf-16-le").strip()
    except Exception:  # noqa: BLE001 - kein Eintrag / kein pywin32
        return ""


def has_key() -> bool:
    return bool(get_key())


def save_key(key: str) -> None:
    import win32cred
    win32cred.CredWrite({
        "Type": win32cred.CRED_TYPE_GENERIC,
        "TargetName": _CRED_TARGET,
        "UserName": "Mochi",
        "CredentialBlob": key.strip(),
        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
    }, 0)


def clear_key() -> None:
    try:
        import win32cred
        win32cred.CredDelete(_CRED_TARGET, win32cred.CRED_TYPE_GENERIC, 0)
    except Exception:  # noqa: BLE001 - war schon weg
        pass


def validate_key(key: str) -> None:
    """Prueft den Key ueber die Modellliste: schnell und ohne Kontingent-Verbrauch. Wirft LLMError."""
    try:
        resp = requests.get(_API.split("/models/")[0] + "/models", params={"pageSize": 1},
                            headers={"x-goog-api-key": key.strip()}, timeout=(6, 10))
    except requests.RequestException:
        raise LLMError("Keine Internetverbindung zu Gemini 📡")
    if not resp.ok:
        raise LLMError(_error_text(resp))


# -- Anfrage --------------------------------------------------------------------------
def _error_text(resp: requests.Response) -> str:
    try:
        err = resp.json().get("error", {})
    except ValueError:
        err = {}
    status, msg = str(err.get("status", "")), str(err.get("message", ""))
    if resp.status_code in (401, 403) or "API_KEY_INVALID" in resp.text or "API key not valid" in msg:
        return "Mein API-Key ist ungültig – bitte in den Einstellungen neu eintragen 🔑"
    if resp.status_code == 429 or status == "RESOURCE_EXHAUSTED":
        return "Mein Gratis-Kontingent ist gerade aufgebraucht – versuch es gleich nochmal 😿"
    return f"Gemini-Fehler {resp.status_code}: {msg[:160] or resp.reason}"


def ask(prompt: str, timeout_s: float = 60.0, model: Optional[str] = None,
        image_b64: Optional[str] = None, key: Optional[str] = None) -> str:
    """Schickt einen Prompt (optional mit PNG-Screenshot) an Gemini und gibt den Antworttext zurueck."""
    key = (key or get_key()).strip()
    if not key:
        raise LLMError("Bitte zuerst in den Einstellungen deinen Gemini-Key eintragen 🔑")

    parts: list[dict] = [{"text": prompt}]
    if image_b64:
        parts.append({"inlineData": {"mimeType": "image/png", "data": image_b64}})
    payload = {"contents": [{"role": "user", "parts": parts}]}

    models = [m for m in [model, *MODELS] if m]
    last = "Gemini ist gerade nicht erreichbar 😿"
    for m in dict.fromkeys(models):
        try:
            resp = requests.post(_API.format(model=m), json=payload, timeout=(6, timeout_s),
                                 headers={"x-goog-api-key": key})
        except requests.Timeout:
            raise LLMError("Die KI antwortet nicht (Zeitüberschreitung) ⌛")
        except requests.RequestException:
            raise LLMError("Keine Internetverbindung zu Gemini 📡")
        if resp.status_code == 404:          # Modell gibt es nicht (mehr) -> naechstes probieren
            last = _error_text(resp)
            continue
        if not resp.ok:
            raise LLMError(_error_text(resp))
        data = resp.json()
        cands = data.get("candidates") or []
        if not cands:
            reason = (data.get("promptFeedback") or {}).get("blockReason")
            raise LLMError("Die KI wollte darauf nicht antworten" + (f" ({reason})" if reason else ""))
        out = cands[0].get("content", {}).get("parts") or []
        return "".join(p.get("text", "") for p in out if not p.get("thought")).strip()
    raise LLMError(last)
