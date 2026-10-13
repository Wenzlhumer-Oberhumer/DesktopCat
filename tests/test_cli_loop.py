"""Tests fuer die _chat_cli-Schleife mit gemocktem gemini.ask."""
from unittest.mock import patch

from agent_brain import AgentWorker


def test_cli_loop_tool_then_finish():
    worker = AgentWorker("Wie spaet ist es?", {"ai": {"timeout_s": 5}}, [])

    calls = [
        '{"say": "", "tool": {"name": "show_time_and_date", "args": {}}}',
        '{"say": "Es ist jetzt 14:00 Uhr, Boss! 🐾", "tool": null}',
    ]

    def mock_ask(prompt, **kwargs):
        return calls.pop(0)

    with patch("gemini.ask", side_effect=mock_ask):
        result = worker._chat_cli()

    assert "14:00" in result
    assert len(worker.results) == 1
    assert worker.results[0].ok is True


def test_cli_loop_aborts_after_max_steps():
    worker = AgentWorker("Endlosschleife", {"ai": {"timeout_s": 5}}, [])

    # Gibt bei jedem Schritt einen neuen Tool-Aufruf zurueck
    with patch("gemini.ask", return_value='{"say": "", "tool": {"name": "show_time_and_date", "args": {}}}'):
        result = worker._chat_cli()

    # Nach MAX_STEPS (4) bricht die Schleife ab und liefert das letzte Tool-Ergebnis
    assert len(worker.results) == AgentWorker.MAX_STEPS
    assert result != ""
