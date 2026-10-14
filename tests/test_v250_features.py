# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Unit-Tests für Desktop Cat v2.5.0 Features:
- Autonome Python-Skript- und Routinen-Engine (custom_scripts)
- Syntax-Validierung und sichere Subprozess-Ausführung
- Zeitplan- und Fälligkeits-Prüfung für Routinen (Startup, Täglich, Intervalle)
- KI-Werkzeuge (create_custom_script, run_custom_script, manage_custom_routines)
- Offline-Parser & Umschalten zwischen Katzen-Zuhause und Desktop-Modus
- Scripts-Dialog Instanziierung & Interaktion
"""
import datetime
from pathlib import Path
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

import agent_brain
import custom_scripts
from scripts_dialog import CustomScriptsDialog
import tools
from tools import ToolResult


def test_custom_scripts_lifecycle():
    """Erstellt, führt aus und löscht ein benutzerdefiniertes Skript."""
    code = 'print("Result:", 7 * 6)\n'
    ok, msg, meta = custom_scripts.save_script(
        name="test_math.py",
        code=code,
        title="Mathe Test",
        description="Multipliziert zwei Zahlen",
        schedule="manual",
        enabled=True,
    )
    assert ok is True
    assert meta["name"] == "test_math.py"
    assert meta["title"] == "Mathe Test"

    # In der Liste auffindbar
    scripts = custom_scripts.list_scripts()
    names = [s["name"] for s in scripts]
    assert "test_math.py" in names

    # Ausführen
    res = custom_scripts.run_script("test_math.py")
    assert res["ok"] is True
    assert "Result: 42" in res["stdout"]
    assert res["exit_code"] == 0
    assert res["duration_s"] >= 0.0

    # Letzter Lauf im Skript vermerkt
    updated = custom_scripts.get_script("test_math.py")
    assert updated["last_run"] is not None
    assert updated["last_result"]["ok"] is True

    # Löschen
    deleted = custom_scripts.delete_script("test_math.py")
    assert deleted is True
    assert custom_scripts.get_script("test_math.py") is None


def test_custom_scripts_syntax_error():
    """Fängt ungültigen Python-Code vor dem Speichern ab."""
    broken_code = "def oops( broken code syntax:"
    ok, msg, meta = custom_scripts.save_script(
        name="broken.py",
        code=broken_code,
    )
    assert ok is False
    assert "Syntax-Fehler" in msg
    assert meta is None


def test_custom_scripts_routines_scheduling():
    """Prüft die Fälligkeitslogik für Startup- und Intervall-Routinen."""
    # 1. Startup Routine
    custom_scripts.save_script(
        name="test_startup.py",
        code="print('startup ok')\n",
        schedule="startup",
        enabled=True,
    )
    due_startup = custom_scripts.get_due_routines(is_startup=True)
    assert any(s["name"] == "test_startup.py" for s in due_startup)

    due_normal = custom_scripts.get_due_routines(is_startup=False)
    assert not any(s["name"] == "test_startup.py" for s in due_normal)

    # 2. Intervall Routine (alle 60 Min)
    custom_scripts.save_script(
        name="test_interval.py",
        code="print('interval ok')\n",
        schedule="interval_60m",
        enabled=True,
    )
    now = datetime.datetime.now()
    # Nie gelaufen -> sofort fällig
    due_interval = custom_scripts.get_due_routines(now=now)
    assert any(s["name"] == "test_interval.py" for s in due_interval)

    # Als gelaufen markieren
    custom_scripts.mark_routine_run("test_interval.py", {"ok": True, "stdout": "ok"})
    # 10 Minuten später -> noch nicht fällig
    ten_min_later = now + datetime.timedelta(minutes=10)
    due_later = custom_scripts.get_due_routines(now=ten_min_later)
    assert not any(s["name"] == "test_interval.py" for s in due_later)

    # 65 Minuten später -> wieder fällig!
    sixty_five_later = now + datetime.timedelta(minutes=65)
    due_again = custom_scripts.get_due_routines(now=sixty_five_later)
    assert any(s["name"] == "test_interval.py" for s in due_again)

    # Aufräumen
    custom_scripts.delete_script("test_startup.py")
    custom_scripts.delete_script("test_interval.py")


def test_tools_custom_scripts_execution():
    """Testet die KI-Werkzeuge für Skripte und Routinen."""
    # Skript erstellen
    res_create = tools.execute("create_custom_script", {
        "name": "auto_tool_test.py",
        "code": "print('Automated Tool Execution Success!')\n",
        "title": "Tool Test",
        "schedule": "manual",
    })
    assert isinstance(res_create, ToolResult)
    assert res_create.ok is True
    assert "auto_tool_test.py" in res_create.message

    # Skripte auflisten
    res_list = tools.execute("list_custom_scripts")
    assert res_list.ok is True
    assert "auto_tool_test" in res_list.message

    # Ausführen
    res_run = tools.execute("run_custom_script", {"name": "auto_tool_test.py"})
    assert res_run.ok is True
    assert "Automated Tool Execution Success!" in res_run.message

    # Routine umschalten
    res_toggle = tools.execute("manage_custom_routines", {
        "action": "toggle",
        "name": "auto_tool_test.py",
        "enabled": False,
    })
    assert res_toggle.ok is True
    assert "pausiert" in res_toggle.message

    # Löschen
    res_del = tools.execute("manage_custom_routines", {
        "action": "delete",
        "name": "auto_tool_test.py",
    })
    assert res_del.ok is True
    assert "gelöscht" in res_del.message


def test_offline_parser_scripts_and_home_mode():
    """Prüft die Spracherkennung für Skripte und das Umschalten von Katzen-Zuhause."""
    # Skripte anfordern
    p1 = agent_brain.parse_offline("zeige meine skripte bitte")
    assert p1.tool == "list_custom_scripts"

    p2 = agent_brain.parse_offline("führe skript backup.py aus")
    assert p2.tool == "run_custom_script"
    assert p2.args.get("name") == "backup.py"

    # Nach Hause gehen
    p3 = agent_brain.parse_offline("geh nach hause ins zimmer kylie")
    assert p3.data.get("home_mode") is True
    assert "zuhause" in p3.reply.lower()

    # Raus auf den Desktop gehen
    p4 = agent_brain.parse_offline("geh raus auf den desktop")
    assert p4.data.get("home_mode") is False
    assert "raus" in p4.reply.lower()


def test_scripts_dialog_instantiation():
    """Testet die fehlerfreie Erzeugung des UI-Dialogs für Skripte & Routinen."""
    app = QApplication.instance() or QApplication([])
    dlg = CustomScriptsDialog()
    assert dlg.windowTitle() == "🤖 Eigene Python-Skripte & Routinen"
    assert dlg.list_scripts.count() >= 1
    assert dlg.btn_run.isEnabled() is True
    dlg.close()
