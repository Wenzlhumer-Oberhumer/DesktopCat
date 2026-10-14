# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Autonome Python-Skript- und Routinen-Engine für Desktop Cat (v2.5.0).

Ermöglicht es dem Desktop-Begleiter (z. B. Kylie) und dem Nutzer,
eigene Python-Skripte autonom zu schreiben, auszuführen, zu verwalten
und als regelmäßige Desktop-Routinen (Startup, täglich, periodisch) einzuplanen.
"""
from __future__ import annotations

import ast
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Optional

from paths import DATA_DIR

SCRIPTS_DIR = DATA_DIR / "scripts"
MANIFEST_FILE = SCRIPTS_DIR / "scripts.json"

DEFAULT_MORGEN_ROUTINE = '''# Morgen-Routine von Kylie 🐾
import platform
import shutil
import sys

def main():
    total, used, free = shutil.disk_usage("C:\\\\")
    free_gb = round(free / (1024**3), 1)
    print(f"Guten Morgen! ☀️ Dein PC ({platform.node()}) läuft super.")
    print(f"💾 Freier Speicher auf C: {free_gb} GB.")
    print("🐾 Kylie wünscht dir einen erfolgreichen, produktiven Tag!")

if __name__ == "__main__":
    main()
'''

DEFAULT_AUGEN_PAUSE = '''# Augen- & Stretch-Pause 🧘
import time

def main():
    print("⏰ Zeit für eine kurze 20-Sekunden-Augenpause!")
    print("👀 Schau kurz aus dem Fenster in die Ferne und kreise deine Schultern.")
    print("✨ Dein Körper und Geist danken es dir!")

if __name__ == "__main__":
    main()
'''

DEFAULT_PC_STATUS = '''# Schneller PC-Status & Helfer ⚡
import os
import platform

def main():
    print(f"💻 System: {platform.system()} {platform.release()}")
    print(f"👤 Benutzer: {os.getlogin()}")
    print("🚀 Alle Systeme bereit für neue Projekte und Aufgaben!")

if __name__ == "__main__":
    main()
'''


def get_scripts_dir() -> Path:
    """Gibt das Skript-Verzeichnis zurück und stellt sicher, dass es existiert."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCRIPTS_DIR


def _load_manifest() -> dict[str, Any]:
    if not MANIFEST_FILE.is_file():
        return {"scripts": {}}
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "scripts" not in data:
                return {"scripts": {}}
            return data
    except Exception:
        return {"scripts": {}}


def _save_manifest(data: dict[str, Any]) -> None:
    get_scripts_dir()
    try:
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"[custom_scripts] Fehler beim Speichern des Manifests: {exc}")


def init_default_scripts() -> None:
    """Legt anfängliche Beispiel-Skripte an, falls noch keine vorhanden sind."""
    get_scripts_dir()
    manifest = _load_manifest()
    scripts = manifest.get("scripts", {})

    if not scripts:
        save_script(
            name="morgen_routine.py",
            code=DEFAULT_MORGEN_ROUTINE,
            title="Morgen-Routine & PC-Check",
            description="Begrüßt den Nutzer morgens, prüft Speicherplatz und System-Status.",
            is_routine=True,
            schedule="daily_09:00",
            enabled=True,
        )
        save_script(
            name="augen_pause.py",
            code=DEFAULT_AUGEN_PAUSE,
            title="Augen- & Entspannungspause",
            description="Erinnert periodisch an Augen-Entspannung und lockeres Schulterkreisen.",
            is_routine=True,
            schedule="interval_60m",
            enabled=True,
        )
        save_script(
            name="quick_pc_status.py",
            code=DEFAULT_PC_STATUS,
            title="Schneller System-Helfer",
            description="Gibt einen kompakten Überblick über System und Benutzer.",
            is_routine=False,
            schedule="manual",
            enabled=True,
        )


def list_scripts() -> list[dict[str, Any]]:
    """Gibt alle registrierten Skripte sortiert nach Namen zurück."""
    init_default_scripts()
    manifest = _load_manifest()
    scripts = manifest.get("scripts", {})
    res = []
    for name, item in sorted(scripts.items()):
        script_file = SCRIPTS_DIR / name
        if not script_file.is_file():
            # Datei neu erstellen falls im Manifest aber nicht auf Festplatte
            if item.get("code"):
                try:
                    script_file.write_text(item["code"], encoding="utf-8")
                except Exception:
                    pass
        res.append(dict(item))
    return res


def get_script(name: str) -> Optional[dict[str, Any]]:
    """Gibt Metadaten und Code für ein einzelnes Skript zurück."""
    name_clean = name.strip()
    if not name_clean.endswith(".py"):
        name_clean += ".py"
    manifest = _load_manifest()
    item = manifest.get("scripts", {}).get(name_clean)
    if not item:
        script_file = SCRIPTS_DIR / name_clean
        if script_file.is_file():
            code = script_file.read_text(encoding="utf-8", errors="replace")
            return {
                "name": name_clean,
                "title": name_clean[:-3],
                "description": "",
                "code": code,
                "is_routine": False,
                "schedule": "manual",
                "enabled": True,
            }
        return None

    # Frischen Code von Festplatte lesen falls vorhanden
    script_file = SCRIPTS_DIR / name_clean
    if script_file.is_file():
        try:
            item["code"] = script_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return dict(item)


def validate_python_code(code: str) -> tuple[bool, str]:
    """Prüft Python-Code auf Syntaxfehler."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as err:
        return False, f"Syntax-Fehler in Zeile {err.lineno}: {err.msg}"
    except Exception as exc:
        return False, f"Ungültiger Python-Code: {exc}"


def save_script(
    name: str,
    code: str,
    title: str = "",
    description: str = "",
    is_routine: bool = False,
    schedule: str = "manual",
    enabled: bool = True,
) -> tuple[bool, str, Optional[dict[str, Any]]]:
    """Speichert ein Python-Skript und registriert es im Manifest."""
    name_clean = name.strip().replace(" ", "_")
    if not name_clean.endswith(".py"):
        name_clean += ".py"

    # Syntax validieren
    valid, err = validate_python_code(code)
    if not valid:
        return False, err, None

    get_scripts_dir()
    script_path = SCRIPTS_DIR / name_clean
    try:
        script_path.write_text(code, encoding="utf-8")
    except Exception as exc:
        return False, f"Fehler beim Schreiben der Datei: {exc}", None

    manifest = _load_manifest()
    scripts = manifest.setdefault("scripts", {})

    existing = scripts.get(name_clean, {})
    meta = {
        "name": name_clean,
        "title": title or existing.get("title") or name_clean[:-3].replace("_", " ").title(),
        "description": description or existing.get("description", ""),
        "code": code,
        "is_routine": bool(is_routine or schedule != "manual"),
        "schedule": schedule or "manual",
        "enabled": bool(enabled),
        "created_at": existing.get("created_at", datetime.datetime.now().isoformat()),
        "updated_at": datetime.datetime.now().isoformat(),
        "last_run": existing.get("last_run"),
        "last_result": existing.get("last_result"),
    }
    scripts[name_clean] = meta
    _save_manifest(manifest)
    return True, f"Skript '{name_clean}' erfolgreich gespeichert!", meta


def delete_script(name: str) -> bool:
    """Löscht ein Skript und entfernt es aus dem Manifest."""
    name_clean = name.strip()
    if not name_clean.endswith(".py"):
        name_clean += ".py"

    script_path = SCRIPTS_DIR / name_clean
    if script_path.is_file():
        try:
            script_path.unlink()
        except Exception:
            pass

    manifest = _load_manifest()
    if name_clean in manifest.get("scripts", {}):
        del manifest["scripts"][name_clean]
        _save_manifest(manifest)
        return True
    return False


def run_script(
    name_or_code: str,
    is_code: bool = False,
    args: Optional[list[str]] = None,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Führt ein Skript in einem separaten Python-Prozess aus und erfasst Ausgabe und Dauer."""
    t0 = time.monotonic()

    if is_code:
        # Temporäre Datei ausführen
        get_scripts_dir()
        temp_file = SCRIPTS_DIR / "_temp_exec.py"
        valid, err = validate_python_code(name_or_code)
        if not valid:
            return {
                "ok": False,
                "stdout": "",
                "stderr": err,
                "duration_s": 0.0,
                "exit_code": -1,
                "error": err,
            }
        temp_file.write_text(name_or_code, encoding="utf-8")
        target_path = temp_file
        record_name = None
    else:
        name_clean = name_or_code.strip()
        if not name_clean.endswith(".py"):
            name_clean += ".py"
        target_path = SCRIPTS_DIR / name_clean
        if not target_path.is_file():
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"Skriptdatei nicht gefunden: {name_clean}",
                "duration_s": 0.0,
                "exit_code": -1,
                "error": f"Datei {name_clean} existiert nicht",
            }
        record_name = name_clean

    env = os.environ.copy()
    # PYTHONPATH erweitern, damit Skripte Projekt-Module und Helfer importieren können
    root_dir = str(Path(__file__).resolve().parent)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [root_dir, env.get("PYTHONPATH", "")]))

    cmd = [sys.executable, str(target_path.resolve()), *(args or [])]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        duration = round(time.monotonic() - t0, 3)
        res = {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "duration_s": duration,
            "exit_code": proc.returncode,
            "error": proc.stderr.strip() if proc.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        duration = round(time.monotonic() - t0, 3)
        res = {
            "ok": False,
            "stdout": "",
            "stderr": f"Zeitüberschreitung nach {timeout_s}s",
            "duration_s": duration,
            "exit_code": -1,
            "error": f"Timeout nach {timeout_s}s",
        }
    except Exception as exc:
        duration = round(time.monotonic() - t0, 3)
        res = {
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "duration_s": duration,
            "exit_code": -1,
            "error": str(exc),
        }

    # Manifest aktualisieren, wenn ein benanntes Skript gelaufen ist
    if record_name:
        mark_routine_run(record_name, res)

    return res


def mark_routine_run(name: str, result: dict[str, Any]) -> None:
    """Speichert Zeit und Ergebnis des letzten Laufs."""
    manifest = _load_manifest()
    scripts = manifest.get("scripts", {})
    if name in scripts:
        scripts[name]["last_run"] = datetime.datetime.now().isoformat()
        scripts[name]["last_result"] = {
            "ok": result.get("ok", False),
            "summary": (result.get("stdout") or result.get("stderr") or "")[:200],
            "duration_s": result.get("duration_s", 0.0),
        }
        _save_manifest(manifest)


def get_due_routines(
    now: Optional[datetime.datetime] = None,
    is_startup: bool = False,
) -> list[dict[str, Any]]:
    """Ermittelt alle aktiven Routinen, die zum aktuellen Zeitpunkt fällig sind."""
    dt = now or datetime.datetime.now()
    due = []

    for item in list_scripts():
        if not item.get("enabled", True):
            continue
        schedule = item.get("schedule", "manual")
        if schedule == "manual":
            continue

        # 1. Startup
        if is_startup and schedule == "startup":
            due.append(item)
            continue

        # 2. Täglich zu fester Uhrzeit: daily_HH:MM (z. B. daily_09:00)
        if schedule.startswith("daily_"):
            try:
                time_str = schedule.replace("daily_", "").strip()
                sh, sm = map(int, time_str.split(":"))
                if dt.hour == sh and dt.minute == sm:
                    # Prüfen, ob heute in dieser Minute schon ausgeführt
                    last_run_str = item.get("last_run")
                    if last_run_str:
                        last_dt = datetime.datetime.fromisoformat(last_run_str)
                        if (
                            last_dt.year == dt.year
                            and last_dt.month == dt.month
                            and last_dt.day == dt.day
                            and last_dt.hour == dt.hour
                            and last_dt.minute == dt.minute
                        ):
                            continue
                    due.append(item)
            except Exception:
                pass
            continue

        # 3. Periodisches Intervall: interval_Nm (z. B. interval_60m, interval_30m)
        if schedule.startswith("interval_"):
            try:
                val = int(schedule.replace("interval_", "").replace("m", "").strip())
                last_run_str = item.get("last_run")
                if not last_run_str:
                    due.append(item)
                else:
                    last_dt = datetime.datetime.fromisoformat(last_run_str)
                    diff_min = (dt - last_dt).total_seconds() / 60.0
                    if diff_min >= val:
                        due.append(item)
            except Exception:
                pass

    return due
