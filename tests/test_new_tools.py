# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Tests fuer neue Tools (Timer, Wetter, Netzwerk, Fenster, PC aufraeumen) und den Offline-Parser."""
import threading
from unittest.mock import MagicMock, patch

import requests

import agent_brain
import tools
from tools import ToolResult

NEW_TOOLS = {"set_timer", "list_timers", "get_weather", "clean_pc", "network_info", "close_window"}
DANGEROUS = {"clean_pc", "close_window", "delete_file", "execute_powershell"}


def _spec_names():
    return {spec["name"] for spec in tools.TOOL_SPECS}


def test_new_tools_are_registered():
    assert NEW_TOOLS <= _spec_names()


def test_dangerous_tools_are_marked():
    assert DANGEROUS <= set(tools.DANGEROUS_TOOLS)


def _weather_resp():
    resp = MagicMock(status_code=200, ok=True, reason="OK")
    resp.text = "Wien: +12C"
    resp.json.return_value = {
        "current_condition": [{"temp_C": "12", "FeelsLikeC": "10", "humidity": "70",
                               "weatherDesc": [{"value": "Sunny"}]}],
        "nearest_area": [{"areaName": [{"value": "Vienna"}]}],
    }
    resp.raise_for_status.return_value = None
    return resp


def test_get_weather_with_mocked_http_returns_ok():
    with patch("requests.get", return_value=_weather_resp()) as get:
        res = tools.execute("get_weather", {"location": "Wien"})
    assert isinstance(res, ToolResult) and res.ok
    assert res.message
    assert get.called


def test_get_weather_network_error_is_friendly_not_crash():
    with patch("requests.get", side_effect=requests.ConnectionError("kein Netz")):
        res = tools.execute("get_weather", {"location": "Wien"})
    assert isinstance(res, ToolResult)
    assert res.ok is False
    assert res.message


def test_set_timer_fires_callback_after_one_second():
    fired = threading.Event()
    tools.register_timer_callback(lambda *a, **k: fired.set())
    try:
        res = tools.execute("set_timer", {"seconds": 1})
        assert res.ok
        assert fired.wait(3), "Timer-Callback wurde nicht innerhalb von 3 s aufgerufen"
    finally:
        tools.execute("list_timers", {"action": "clear"})


def _total_seconds(args):
    return args.get("minutes", 0) * 60 + args.get("seconds", 0)


def test_parse_offline_timer():
    plan = agent_brain.parse_offline("stell einen timer auf 5 minuten", "Boss", "cat_mochi")
    assert plan.tool == "set_timer"
    assert _total_seconds(plan.args) == 300


def test_parse_offline_pomodoro_is_25_minutes():
    plan = agent_brain.parse_offline("pomodoro starten", "Boss", "cat_mochi")
    assert plan.tool == "set_timer"
    assert _total_seconds(plan.args) == 25 * 60


def test_parse_offline_weather_location():
    plan = agent_brain.parse_offline("wie ist das wetter in wien", "Boss", "cat_mochi")
    assert plan.tool == "get_weather"
    assert "wien" in str(plan.args.get("location", "")).lower()


def test_parse_offline_network_info():
    plan = agent_brain.parse_offline("wie ist meine ip", "Boss", "cat_mochi")
    assert plan.tool == "network_info"
