# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Zugang zu Gemini fuer Desktop Cat: kostenloser API-Key aus Google AI Studio.

Der Key liegt in der Windows-Anmeldeinformationsverwaltung (win32cred).
Ein "Google-Konto-Login" (OAuth) ist bewusst NICHT eingebaut: Ein privates Google-Abo
(Google One / AI Pro) schaltet die Gemini-API nicht frei, und OAuth braeuchte pro Nutzer ein
eigenes Google-Cloud-Projekt - ohne Vorteil gegenueber dem Gratis-Key.
"""
from __future__ import annotations

from typing import Optional

_CRED_TARGET_APIKEY = "Mochi/GeminiApiKey"
_CRED_TARGET_OAUTH_LEGACY = "DesktopCat/GoogleOAuth"   # nur noch zum Aufraeumen (v3.0.0)


# -- Windows Credential Hilfsfunktionen -----------------------------------------------

def _read_cred(target: str) -> Optional[str]:
    try:
        import win32cred
        cred = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC)
        return cred["CredentialBlob"].decode("utf-16-le").strip()
    except Exception:
        return None


def _write_cred(target: str, blob: str, username: str = "DesktopCat") -> None:
    import win32cred
    win32cred.CredWrite({
        "Type": win32cred.CRED_TYPE_GENERIC,
        "TargetName": target,
        "UserName": username,
        "CredentialBlob": blob.strip(),
        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
    }, 0)


def _delete_cred(target: str) -> None:
    try:
        import win32cred
        win32cred.CredDelete(target, win32cred.CRED_TYPE_GENERIC, 0)
    except Exception:
        pass


# -- AuthManager ----------------------------------------------------------------------

class AuthManager:
    """Verwaltet den Gemini-API-Key."""

    def __init__(self):
        _delete_cred(_CRED_TARGET_OAUTH_LEGACY)   # alte OAuth-Tokens aus v3.0.0 nicht liegen lassen

    def get_api_key(self) -> str:
        return _read_cred(_CRED_TARGET_APIKEY) or ""

    def save_api_key(self, key: str) -> None:
        _write_cred(_CRED_TARGET_APIKEY, key.strip(), username="Mochi")

    def clear_api_key(self) -> None:
        _delete_cred(_CRED_TARGET_APIKEY)

    def get_auth_mode(self) -> str:
        """'apikey' oder 'none'."""
        return "apikey" if self.get_api_key() else "none"

    def has_auth(self) -> bool:
        return self.get_auth_mode() != "none"

    def get_auth_headers(self) -> dict[str, str]:
        key = self.get_api_key()
        return {"x-goog-api-key": key} if key else {}


_global_auth: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    global _global_auth
    if _global_auth is None:
        _global_auth = AuthManager()
    return _global_auth
