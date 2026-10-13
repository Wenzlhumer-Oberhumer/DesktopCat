"""Tests fuer den Bestaetigungs-Flow gefaehrlicher Tools (Papierkorb leeren etc.).

Laeuft ueber AgentBrain.submit() mit Worker-Thread, wartet im Test synchron (QEventLoop) auf das
finished-Signal. ALLE gefaehrlichen Tools werden im tools.TOOLS-Dispatch durch Mocks ersetzt -
es wird nie wirklich etwas geleert, geloescht oder geschlossen.
"""
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QEventLoop, QTimer

import agent_brain
from agent_brain import AgentBrain
from tools import DANGEROUS_TOOLS, ToolResult


class _FakeCfg:
    def snapshot(self):
        return {"ai": {"enabled": False}, "pet": {"user_name": "Boss", "character": "cat_mochi"}}

    def get(self, *keys, default=None):
        return default


def _safe_tools():
    """Dispatch-Dict mit Mocks fuer alle gefaehrlichen Tools (patch.dict stellt es danach wieder her)."""
    mocks = {name: MagicMock(return_value=ToolResult(True, f"{name} (Mock)")) for name in DANGEROUS_TOOLS}
    return patch.dict("tools.TOOLS", mocks), mocks


def _send(brain, text):
    """Schickt eine Nachricht durch den Brain und wartet (max. 5 s) auf das Ergebnis."""
    result = {}
    loop = QEventLoop()

    def on_done(ok, msg, notify):
        result["ok"], result["msg"] = ok, msg
        loop.quit()

    brain.finished.connect(on_done)
    try:
        assert brain.submit(text)
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
    finally:
        brain.finished.disconnect(on_done)
    brain.shutdown(3000)  # Worker-Thread sauber beenden, bevor der Test weiterlaeuft
    assert "msg" in result, f"keine Antwort auf {text!r}"
    return result["ok"], result["msg"]


def test_offline_parser_routes_empty_recycle_bin_to_clean_pc():
    plan = agent_brain.parse_offline("leere den papierkorb", "Boss", "cat_mochi")
    assert plan.tool == "clean_pc"


def test_dangerous_tool_asks_instead_of_running():
    dispatch, mocks = _safe_tools()
    with patch("gemini.has_key", return_value=False), dispatch:
        brain = AgentBrain(_FakeCfg())
        ok, msg = _send(brain, "leere den papierkorb")
    mocks["clean_pc"].assert_not_called()
    assert "?" in msg


def test_ja_executes_pending_action():
    dispatch, mocks = _safe_tools()
    with patch("gemini.has_key", return_value=False), dispatch:
        brain = AgentBrain(_FakeCfg())
        _send(brain, "leere den papierkorb")
        mocks["clean_pc"].assert_not_called()
        _send(brain, "ja")
    mocks["clean_pc"].assert_called_once()


def test_nein_clears_pending_action():
    dispatch, mocks = _safe_tools()
    with patch("gemini.has_key", return_value=False), dispatch:
        brain = AgentBrain(_FakeCfg())
        _send(brain, "leere den papierkorb")
        _send(brain, "nein")
        _send(brain, "ja")  # nichts mehr gemerkt -> darf nicht ausfuehren
    mocks["clean_pc"].assert_not_called()
