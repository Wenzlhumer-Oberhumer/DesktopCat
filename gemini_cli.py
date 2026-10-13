"""Gemini CLI Schnittstelle: CLI finden, Login-Status, Login starten, Prompt ausfuehren."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from paths import APP_DIR, DATA_DIR

GEMINI_HOME = Path.home() / ".gemini"
CREDS = GEMINI_HOME / "oauth_creds.json"
ACCOUNTS = GEMINI_HOME / "google_accounts.json"
WORKSPACE = DATA_DIR / "cli_workspace"


class LLMError(Exception):
    """Fehler beim Aufruf der Gemini CLI mit benutzerfreundlicher Meldung."""


def cli_command() -> list[str] | None:
    """Findet den ausfuehrbaren Befehl fuer die Gemini CLI.

    1. Gebuendelt: APP_DIR/vendor/node/node.exe + APP_DIR/vendor/gemini-cli/.../bundle/gemini.js
    2. Dev-Fallback: shutil.which("gemini")
    3. Globales node + gemini.js falls node und gemini global installiert sind
    """
    # 1. Gebuendelt im App-Verzeichnis (Installer / PyInstaller)
    node_exe = APP_DIR / "vendor" / "node" / "node.exe"
    vendor_cli_pkg = APP_DIR / "vendor" / "gemini-cli" / "node_modules" / "@google" / "gemini-cli"
    if node_exe.is_file():
        # package.json pruefen fuer bin-Eintrag
        pkg_json = vendor_cli_pkg / "package.json"
        bin_rel = "bundle/gemini.js"
        if pkg_json.is_file():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    bin_entry = data.get("bin", {})
                    if isinstance(bin_entry, dict):
                        bin_rel = bin_entry.get("gemini", bin_rel)
                    elif isinstance(bin_entry, str):
                        bin_rel = bin_entry
            except Exception:
                pass
        cli_entry = vendor_cli_pkg / bin_rel
        if cli_entry.is_file():
            return [str(node_exe), str(cli_entry)]

    # 2. Dev-Fallback: gemini im PATH
    cmd = shutil.which("gemini")
    if cmd:
        return [cmd]

    # 3. Fallback: node im PATH + bekanntes globales npm-Modul
    node_cmd = shutil.which("node")
    if node_cmd:
        appdata_npm = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
        if appdata_npm.is_file():
            return [node_cmd, str(appdata_npm)]

    return None


def is_logged_in() -> bool:
    """Prueft, ob CREDS existiert und ein gueltiges JSON mit refresh_token ist."""
    if not CREDS.is_file():
        return False
    try:
        with open(CREDS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("refresh_token"))
    except Exception:
        return False


def get_logged_in_email() -> str | None:
    """Liest die aktive Google-Account-E-Mail aus google_accounts.json, falls vorhanden."""
    if not is_logged_in():
        return None
    if ACCOUNTS.is_file():
        try:
            with open(ACCOUNTS, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("active")
        except Exception:
            pass
    return None


def ensure_workspace() -> None:
    """Legt WORKSPACE/.gemini/settings.json und system.md / GEMINI.md an."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    gemini_cfg_dir = WORKSPACE / ".gemini"
    gemini_cfg_dir.mkdir(parents=True, exist_ok=True)

    # Workspace-Einstellungen: Eingebaute Tools (Shell, Dateien schreiben) deaktivieren!
    ws_settings = {
        "tools": {"core": ["read_many_files"]},
        "telemetry": {"enabled": False},
        "general": {"checkpointing": {"enabled": False}},
    }
    settings_file = gemini_cfg_dir / "settings.json"
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(ws_settings, f, indent=2)
    except OSError:
        pass

    # System-Prompts im Workspace hinterlegen
    system_text = (
        "Du bist Mochi, eine Desktop-Katze. Du hast keine eigenen Tools.\n"
        "Halte dich exakt an das verlangte JSON-Format."
    )
    for fn in ("system.md", "GEMINI.md"):
        try:
            with open(WORKSPACE / fn, "w", encoding="utf-8") as f:
                f.write(system_text)
        except OSError:
            pass


def _configure_user_settings_auth() -> None:
    """Setzt in GEMINI_HOME/settings.json den Auth-Typ auf oauth-personal (mergen, nicht ueberschreiben)."""
    GEMINI_HOME.mkdir(parents=True, exist_ok=True)
    user_settings_file = GEMINI_HOME / "settings.json"
    settings_data: dict = {}
    if user_settings_file.is_file():
        try:
            with open(user_settings_file, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
        except Exception:
            settings_data = {}

    settings_data.setdefault("security", {}).setdefault("auth", {})["selectedType"] = "oauth-personal"
    settings_data["selectedAuthType"] = "oauth-personal"

    try:
        with open(user_settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=2)
    except OSError:
        pass


def start_login() -> subprocess.Popen:
    """Startet den interaktiven Login im Browser ueber die Gemini CLI."""
    cmd = cli_command()
    if not cmd:
        raise LLMError("Gemini CLI ist nicht installiert 😿")

    ensure_workspace()
    _configure_user_settings_auth()

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)

    # Interaktiver Aufruf oeffnet bei Bedarf den Browser
    return subprocess.Popen(
        cmd,
        cwd=str(WORKSPACE),
        creationflags=creationflags,
        env=env,
    )


def logout() -> None:
    """Loescht die gespeicherten Google-Anmeldedaten."""
    for p in (CREDS, ACCOUNTS):
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


def ask(prompt: str, timeout_s: float = 60.0, model: str | None = None) -> str:
    """Fuehrt einen non-interaktiven Prompt per gemini -p aus und gibt die Antwort zurueck."""
    cmd = cli_command()
    if not cmd:
        raise LLMError("Gemini CLI ist nicht installiert 😿")

    ensure_workspace()
    _configure_user_settings_auth()

    args = list(cmd) + ["--skip-trust"]
    use_stdin = len(prompt) > 24000
    if use_stdin:
        args.extend(["-p", "", "--output-format", "json"])
    else:
        args.extend(["-p", prompt, "--output-format", "json"])

    if model and model.strip():
        args.extend(["-m", model.strip()])

    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)
    env.pop("GOOGLE_API_KEY", None)
    env["GEMINI_SYSTEM_MD"] = str(WORKSPACE / "system.md")
    env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    # Bei normalem Prompt geben wir b"n\n" auf stdin mit, falls die CLI ungefragt
    # nach Browser-Login fragen will (so blockiert der non-interaktive Prozess niemals).
    stdin_input = prompt.encode("utf-8") if use_stdin else b"n\n"

    try:
        proc = subprocess.run(
            args,
            cwd=str(WORKSPACE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            input=stdin_input,
            creationflags=creationflags,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        raise LLMError("Die KI antwortet nicht (Zeitueberschreitung) ⌛")
    except OSError as exc:
        raise LLMError(f"Fehler beim Starten der Gemini CLI ({exc})")

    out_text = proc.stdout.decode("utf-8", errors="replace").strip()
    err_text = proc.stderr.decode("utf-8", errors="replace").strip()

    # 1. Versuche JSON zu parsen
    parsed_json = None
    if out_text:
        try:
            parsed_json = json.loads(out_text)
        except ValueError:
            # Manchmal steht vor dem JSON noch eine Zeile (z. B. Banner/Warnung)
            start_brace = out_text.find("{")
            end_brace = out_text.rfind("}")
            if start_brace != -1 and end_brace > start_brace:
                try:
                    parsed_json = json.loads(out_text[start_brace : end_brace + 1])
                except ValueError:
                    pass

    if isinstance(parsed_json, dict):
        if "error" in parsed_json:
            err_info = parsed_json["error"]
            err_msg = str(err_info.get("message") if isinstance(err_info, dict) else err_info)
            err_low = err_msg.lower()
            if any(k in err_low for k in ("auth", "login", "credential", "please set an auth", "consent", "not authenticated")):
                raise LLMError("Bitte zuerst in den Einstellungen mit Google anmelden 🔑")
            if any(k in err_low for k in ("429", "quota", "rate limit", "resourceexhausted")):
                raise LLMError("Mein Gratis-Kontingent ist für heute aufgebraucht 😿")
            raise LLMError(err_msg or "Unbekannter Fehler der Gemini CLI")

        if "response" in parsed_json:
            return str(parsed_json["response"])

    # 2. Wenn JSON nicht geparst werden konnte oder Fehler im Exit-Code:
    combined_err = f"{out_text}\n{err_text}".lower()
    if any(k in combined_err for k in ("auth", "login", "credential", "please set an auth", "consent", "not authenticated", "fatalcancellationerror", "cancelled by user")):
        raise LLMError("Bitte zuerst in den Einstellungen mit Google anmelden 🔑")
    if any(k in combined_err for k in ("429", "quota", "rate limit", "resourceexhausted")):
        raise LLMError("Mein Gratis-Kontingent ist für heute aufgebraucht 😿")

    if proc.returncode != 0:
        msg = err_text or out_text or f"CLI beendet mit Fehlercode {proc.returncode}"
        raise LLMError(f"Gemini CLI Fehler: {msg[:160]}")

    return out_text
