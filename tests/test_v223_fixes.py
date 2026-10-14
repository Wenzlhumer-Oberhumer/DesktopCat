# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Regressionstests fuer die Fehler aus dem Review vor v2.2.2 (Update, Ordner, Guide, Onboarding, Wipe)."""
import hashlib
import io
import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import gemini
import memory_store
import tools
from agent_brain import parse_offline
from updater import CheckUpdateWorker, DownloadUpdateWorker

_REPO = Path(__file__).resolve().parent.parent
BASE = "https://github.com/Wenzlhumer-Oberhumer/DesktopCat/releases/download/v9.9.9/"


class _Resp:
    def __init__(self, data: bytes):
        self._io = io.BytesIO(data)
        self.headers = {"Content-Length": str(len(data))}

    def read(self, amt=-1):
        return self._io.read(amt)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _download(sha_bytes: bytes, setup: bytes, with_sha: bool = True):
    urls = {BASE + "DesktopCat-Setup-9.9.9.exe": setup, BASE + "DesktopCat-Setup-9.9.9.exe.sha256": sha_bytes}
    worker = DownloadUpdateWorker(BASE + "DesktopCat-Setup-9.9.9.exe",
                                  BASE + "DesktopCat-Setup-9.9.9.exe.sha256" if with_sha else "", "9.9.9")
    out = []
    worker.download_completed.connect(lambda ok, msg: out.append((ok, msg)))
    with tempfile.TemporaryDirectory() as td, patch("tempfile.gettempdir", return_value=td), \
            patch("urllib.request.urlopen", side_effect=lambda req, **k: _Resp(urls[req.full_url])):
        worker.run()
    return out[0]


def test_update_hash_file_with_bom_is_accepted():
    # Bug: build.ps1 schrieb die .sha256 mit BOM -> Hash hatte 65 Zeichen -> Update scheiterte immer
    setup = b"MZ fake setup"
    sha = "\ufeff" + hashlib.sha256(setup).hexdigest() + "  DesktopCat-Setup-9.9.9.exe\r\n"
    ok, msg = _download(sha.encode("utf-8"), setup)
    assert ok, msg


def test_update_without_hash_is_refused():
    ok, msg = _download(b"", b"MZ fake setup", with_sha=False)
    assert not ok and "SHA256" in msg


def test_update_with_empty_hash_file_is_refused():
    ok, _ = _download(b"   ", b"MZ fake setup")
    assert not ok


def _check(assets):
    release = {"tag_name": "v99.0.0", "body": "", "assets": [{"name": n, "browser_download_url": BASE + n} for n in assets]}
    worker = CheckUpdateWorker(repo="Wenzlhumer-Oberhumer/DesktopCat")
    out = []
    worker.check_completed.connect(out.append)
    with patch("urllib.request.urlopen", return_value=_Resp(json.dumps(release).encode())):
        worker.run()
    return out[0]


def test_update_check_needs_desktopcat_setup_and_matching_hash():
    assert _check(["Mochi-Setup-99.0.0.exe", "Mochi-Setup-99.0.0.exe.sha256"])["status"] == "error"
    assert _check(["DesktopCat-Setup-99.0.0.exe"])["status"] == "error"
    res = _check(["DesktopCat-Setup-99.0.0.exe", "DesktopCat-Setup-99.0.0.exe.sha256"])
    assert res["status"] == "update_available" and res["sha_url"].endswith(".sha256")


def test_build_script_writes_hash_without_bom():
    build = (_REPO / "build.ps1").read_text(encoding="utf-8")
    assert "UTF8Encoding $false" in build and "Set-Content -Path $shaFile" not in build


def test_open_folder_commands_open_the_right_folder():
    # Bug: Parser uebergab 'folder' statt 'name' -> jeder Ordner oeffnete "Downloads"
    fake = {"Downloads": Path("C:/x/Downloads"), "Documents": Path("C:/x/OneDrive/Documents"),
            "Pictures": Path("C:/x/OneDrive/Bilder"), "Music": Path("C:/x/Musik"), "Videos": Path("C:/x/Videos")}
    expected = {"öffne downloads": "Downloads", "öffne dokumente": "Documents", "öffne bilder": "Pictures",
                "öffne musik": "Music", "öffne videos": "Videos"}
    with patch("tools.known_folder", side_effect=lambda n: fake[n]), patch("pathlib.Path.exists", return_value=True), \
            patch("os.startfile") as sf:
        for cmd, folder in expected.items():
            plan = parse_offline(cmd, "Flo", "cat_mochi")
            assert plan.tool == "open_folder" and "name" in plan.args, (cmd, plan.args)
            assert tools.execute(plan.tool, plan.args).ok
            assert Path(sf.call_args.args[0]) == fake[folder], cmd
    with patch("subprocess.Popen") as popen:
        plan = parse_offline("öffne papierkorb", "Flo", "cat_mochi")
        assert tools.execute(plan.tool, plan.args).ok
        assert "RecycleBin" in str(popen.call_args)


def test_no_broken_pet_api_calls_in_main():
    # Bug: set_accessory ohne 'on', remove_accessory existiert nicht, fly_to mit einem QPointF
    src = (_REPO / "main.py").read_text(encoding="utf-8")
    assert "remove_accessory(" not in src
    assert not re.search(r"set_accessory\(\"\w+\"\)", src)
    assert not re.search(r"fly_to\(\s*\w+\s*\)", src)
    assert "set_pending_action" not in src


def test_onboarding_key_worker_accepts_valid_key_and_rejects_invalid():
    from onboarding import KeyValidationWorker
    for side_effect, expect in ((None, True), (gemini.LLMError("nope"), False)):
        w = KeyValidationWorker("AIzaTest")
        out = []
        w.validation_done.connect(lambda ok, msg: out.append(ok))
        with patch("gemini.validate_key", side_effect=side_effect), patch("gemini.save_key") as save:
            w.run()
        assert out == [expect]
        assert save.called is expect


def test_wipe_notifies_listeners():
    calls = []
    with tempfile.TemporaryDirectory() as td:
        store = memory_store.MemoryStore(Path(td) / "t.db")
        store.add_fact("Mag Pizza")
        memory_store.MemoryStore.on_wipe.append(lambda: calls.append(1))
        try:
            store.wipe_everything()
        finally:
            memory_store.MemoryStore.on_wipe.pop()
        assert calls == [1] and store.facts() == []


def test_update_check_falls_back_when_api_rate_limited():
    import urllib.error

    class _Head(_Resp):
        def geturl(self):
            return "https://github.com/Wenzlhumer-Oberhumer/DesktopCat/releases/tag/v99.0.0"

    def fake_urlopen(req, **kw):
        if "api.github.com" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 403, "rate limit exceeded", {}, None)
        assert req.get_method() == "HEAD"
        return _Head(b"")

    worker = CheckUpdateWorker(repo="Wenzlhumer-Oberhumer/DesktopCat")
    out = []
    worker.check_completed.connect(out.append)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        worker.run()
    assert out[0]["status"] == "update_available"
    assert out[0]["setup_url"].endswith("/v99.0.0/DesktopCat-Setup-99.0.0.exe")
    assert out[0]["sha_url"].endswith("DesktopCat-Setup-99.0.0.exe.sha256")


def test_calculator_functions_and_safety():
    # Bug: Buchstaben wurden entfernt -> "sqrt(144) + 2*3" ergab 150
    for expr, want in (("sqrt(144) + 2*3", "18"), ("3 x 4", "12"), ("wurzel(81)", "9"), ("2^10", "1024")):
        r = tools.execute("calculate", {"expression": expr})
        assert r.ok and f": {want} " in r.message, (expr, r.message)
    for bad in ("max(3,4)", "9**9**9", "__import__('os')"):
        assert not tools.execute("calculate", {"expression": bad}).ok, bad


def test_weather_falls_back_from_unknown_long_city():
    # Bug: "Gaspoltshofen - Grieskirchen - Oberoester" (aus dem Kennenlernen) kennt wttr.in nicht
    asked = []

    class R:
        def __init__(self, ok):
            self.ok = ok

        def raise_for_status(self):
            if not self.ok:
                raise tools.requests.HTTPError("500 location not found")

        def json(self):
            return {"current_condition": [{"temp_C": "12", "FeelsLikeC": "11", "lang_de": [{"value": "Regen"}],
                                           "weatherDesc": [{"value": "Rain"}]}], "weather": [{"hourly": []}]}

    def fake_get(url, **kw):
        asked.append(url)
        return R(url.endswith("/Gaspoltshofen"))

    with patch("tools.requests.get", side_effect=fake_get):
        r = tools.execute("get_weather", {"location": "Gaspoltshofen - Grieskirchen - Oberoester"})
    assert r.ok and "Gaspoltshofen" in r.message
    assert len(asked) == 2


def test_new_customization_and_focus_features():
    from config import Config
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        c = Config(Path(td) / "cfg.json")
        assert c.get("pet.opacity") == 1.0
        assert c.get("pet.always_on_top") is True
        assert c.get("pet.sound_enabled") is True
        assert c.get("pet.bubble_seconds") == 4.0

