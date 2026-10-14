# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer das JSON-Tool-Calling-Protokoll der Gemini CLI."""
from agent_brain import parse_cli_response


def test_pure_json_say():
    raw = '{"say": "Hallo Boss!", "tool": null}'
    say, tool = parse_cli_response(raw)
    assert say == "Hallo Boss!"
    assert tool is None


def test_pure_json_tool():
    raw = '{"say": "Ich schaue nach...", "tool": {"name": "current_time", "args": {}}}'
    say, tool = parse_cli_response(raw)
    assert say == "Ich schaue nach..."
    assert tool == {"name": "current_time", "args": {}}


def test_fenced_json():
    raw = """```json
{
  "say": "Ordner wird geoeffnet",
  "tool": {"name": "open_folder", "args": {"target": "desktop"}}
}
```"""
    say, tool = parse_cli_response(raw)
    assert say == "Ordner wird geoeffnet"
    assert tool == {"name": "open_folder", "args": {"target": "desktop"}}


def test_plain_text_without_json():
    raw = "Miau! Ich bin Mochi und passe auf deinen Desktop auf."
    say, tool = parse_cli_response(raw)
    assert say == "Miau! Ich bin Mochi und passe auf deinen Desktop auf."
    assert tool is None


def test_broken_json():
    raw = '{"say": "Kaputter JSON String, "tool": '
    say, tool = parse_cli_response(raw)
    assert say == raw.strip()
    assert tool is None


def test_nested_text_with_json():
    raw = 'Hier ist die Antwort:\n{"say": "Fertig!", "tool": null}\nIch hoffe das hilft!'
    say, tool = parse_cli_response(raw)
    assert say == "Fertig!"
    assert tool is None
