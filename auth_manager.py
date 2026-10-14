# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Authentifizierungs-Manager für Gemini in Desktop Cat (v3.0.0).

Unterstützt zwei nahtlose Anmeldewege:
- Option A: Google OAuth 2.0 Browser-Login (Standard-Webbrowser + Loopback-Server localhost:8085)
- Option C: 1-Klick Google AI Studio Express API-Key
Alle Tokens und Keys werden sicher in der Windows-Anmeldeinformationsverwaltung (win32cred) gespeichert.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

import requests

_CRED_TARGET_APIKEY = "Mochi/GeminiApiKey"
_CRED_TARGET_OAUTH = "DesktopCat/GoogleOAuth"

OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_REDIRECT_PORT = 8085
OAUTH_REDIRECT_URI = f"http://127.0.0.1:{OAUTH_REDIRECT_PORT}/oauth2callback"
OAUTH_SCOPE = "https://www.googleapis.com/auth/generative-language"


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


# -- OAuth 2.0 Loopback HTTP Server ----------------------------------------------------

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Fängt den OAuth2 Authorization Code vom Browser ab."""

    server: _OAuthServer

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/oauth2callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if code:
            self.server.auth_code = code
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<title>Desktop Cat - Anmeldung erfolgreich</title>"
                "<style>body{font-family:Segoe UI,sans-serif;text-align:center;padding:50px;background:#18191E;color:#F0F0F5;}"
                ".card{background:#252730;display:inline-block;padding:30px 50px;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.4);}"
                "h2{color:#FF85A2;margin-bottom:10px;}p{color:#A0A5B5;}</style></head>"
                "<body><div class='card'><h2>🐾 Super! Erfolgreich angemeldet.</h2>"
                "<p>Desktop Cat ist nun verbunden.<br>Du kannst dieses Browserfenster schließen.</p>"
                "</div></body></html>"
            )
            self.wfile.write(html.encode("utf-8"))
        else:
            self.server.auth_error = error or "Unbekannter Fehler bei der Autorisierung"
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<title>Desktop Cat - Fehler</title>"
                "<style>body{font-family:Segoe UI,sans-serif;text-align:center;padding:50px;background:#18191E;color:#F0F0F5;}</style></head>"
                "<body><h2>❌ Anmeldung abgebrochen oder fehlgeschlagen.</h2>"
                f"<p>{self.server.auth_error}</p></body></html>"
            )
            self.wfile.write(html.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:
        # Keine störenden Konsolenausgaben
        pass


class _OAuthServer(HTTPServer):
    def __init__(self, server_address):
        super().__init__(server_address, _OAuthCallbackHandler)
        self.auth_code: Optional[str] = None
        self.auth_error: Optional[str] = None


# -- AuthManager Hauptklasse -----------------------------------------------------------

class AuthManager:
    """Verwaltet Google OAuth 2.0 Tokens und AI Studio API Keys."""

    def __init__(self):
        self._server_thread: Optional[threading.Thread] = None

    # -- Option C: API-Key Zugriff -----------------------------------------------------

    def get_api_key(self) -> str:
        return _read_cred(_CRED_TARGET_APIKEY) or ""

    def save_api_key(self, key: str) -> None:
        _write_cred(_CRED_TARGET_APIKEY, key.strip(), username="Mochi")

    def clear_api_key(self) -> None:
        _delete_cred(_CRED_TARGET_APIKEY)

    # -- Option A: OAuth 2.0 Zugriff ---------------------------------------------------

    def get_oauth_data(self) -> Optional[dict]:
        blob = _read_cred(_CRED_TARGET_OAUTH)
        if not blob:
            return None
        try:
            return json.loads(blob)
        except Exception:
            return None

    def save_oauth_data(self, data: dict) -> None:
        blob = json.dumps(data)
        _write_cred(_CRED_TARGET_OAUTH, blob, username="DesktopCatOAuth")

    def clear_oauth_data(self) -> None:
        _delete_cred(_CRED_TARGET_OAUTH)

    def is_oauth_configured(self) -> bool:
        data = self.get_oauth_data()
        return bool(data and (data.get("access_token") or data.get("refresh_token")))

    def get_valid_oauth_token(self) -> Optional[str]:
        """Gibt ein gültiges Access-Token zurück; erneuert es automatisch per Refresh-Token."""
        data = self.get_oauth_data()
        if not data:
            return None

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_at = float(data.get("expires_at", 0))

        # Falls Token noch mindestens 60 Sekunden gültig ist
        if access_token and time.time() < (expires_at - 60):
            return access_token

        # Andernfalls per refresh_token erneuern
        if refresh_token:
            client_id = data.get("client_id", "")
            client_secret = data.get("client_secret", "")
            try:
                resp = requests.post(
                    OAUTH_TOKEN_URL,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=(5, 12),
                )
                if resp.ok:
                    token_info = resp.json()
                    new_access = token_info.get("access_token")
                    expires_in = int(token_info.get("expires_in", 3600))
                    data["access_token"] = new_access
                    data["expires_at"] = time.time() + expires_in
                    self.save_oauth_data(data)
                    return new_access
            except Exception:
                pass

        return access_token if access_token else None

    # -- Kombinierte Header für Gemini -------------------------------------------------

    def get_auth_mode(self) -> str:
        """Gibt 'oauth', 'apikey' oder 'none' zurück."""
        if self.is_oauth_configured():
            return "oauth"
        if bool(self.get_api_key()):
            return "apikey"
        return "none"

    def has_auth(self) -> bool:
        return self.get_auth_mode() != "none"

    def get_auth_headers(self) -> dict[str, str]:
        """Gibt die passenden HTTP-Header für die Generative Language API zurück."""
        # 1. Bevorzuge OAuth falls aktiv
        if self.is_oauth_configured():
            tok = self.get_valid_oauth_token()
            if tok:
                return {"Authorization": f"Bearer {tok}"}

        # 2. Ansonsten API-Key
        key = self.get_api_key()
        if key:
            return {"x-goog-api-key": key}

        return {}

    # -- OAuth 2.0 Flow starten --------------------------------------------------------

    def build_oauth_url(self, client_id: str) -> str:
        params = {
            "client_id": client_id.strip(),
            "redirect_uri": OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def start_oauth_flow_async(
        self,
        client_id: str,
        client_secret: str,
        on_success: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Startet den lokalen Callback-Server und öffnet den Browser für die Anmeldung."""
        def _flow():
            server: Optional[_OAuthServer] = None
            try:
                server = _OAuthServer(("127.0.0.1", OAUTH_REDIRECT_PORT))
                server.timeout = 180.0  # 3 Minuten Zeit zum Anmelden

                # Browser öffnen
                auth_url = self.build_oauth_url(client_id)
                webbrowser.open(auth_url)

                # Auf Redirect warten
                start = time.time()
                while not server.auth_code and not server.auth_error and (time.time() - start < 180):
                    server.handle_request()

                if server.auth_error:
                    if on_error:
                        on_error(server.auth_error)
                    return

                code = server.auth_code
                if not code:
                    if on_error:
                        on_error("Zeitüberschreitung bei der Anmeldung im Browser.")
                    return

                # Code gegen Access & Refresh Token tauschen
                token_resp = requests.post(
                    OAUTH_TOKEN_URL,
                    data={
                        "client_id": client_id.strip(),
                        "client_secret": client_secret.strip(),
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": OAUTH_REDIRECT_URI,
                    },
                    timeout=(6, 15),
                )

                if not token_resp.ok:
                    err_msg = f"Token-Austausch fehlgeschlagen ({token_resp.status_code})"
                    try:
                        err_msg = token_resp.json().get("error_description", err_msg)
                    except Exception:
                        pass
                    if on_error:
                        on_error(err_msg)
                    return

                tokens = token_resp.json()
                save_payload = {
                    "client_id": client_id.strip(),
                    "client_secret": client_secret.strip(),
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                    "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
                    "token_type": tokens.get("token_type", "Bearer"),
                }
                self.save_oauth_data(save_payload)

                if on_success:
                    on_success()

            except Exception as e:
                if on_error:
                    on_error(f"OAuth Server Fehler: {e}")
            finally:
                if server:
                    try:
                        server.server_close()
                    except Exception:
                        pass

        self._server_thread = threading.Thread(target=_flow, daemon=True)
        self._server_thread.start()


_global_auth: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    global _global_auth
    if _global_auth is None:
        _global_auth = AuthManager()
    return _global_auth
