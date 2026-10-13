"""Tests fuer Updater: Versionsvergleich, Whitelist, Hash-Validierung."""
import hashlib
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from updater import DownloadUpdateWorker, is_newer, is_trusted_url, parse_version


def test_version_parsing_and_comparison():
    assert parse_version("2.0.10") > parse_version("2.0.9")
    assert parse_version("v2.1.0") > parse_version("2.0.0")
    assert parse_version("v2.0.0") == parse_version("2.0.0")

    assert is_newer("v2.0.1", "2.0.0") is True
    assert is_newer("2.0.0", "2.0.0") is False
    assert is_newer("v1.9.9", "2.0.0") is False
    assert is_newer("v2.0.0-rc1", "2.0.0") is False


def test_trusted_url_whitelist():
    assert is_trusted_url("https://github.com/Nairolf/Mochi/releases/download/v2.0.1/Mochi-Setup-2.0.1.exe")
    assert is_trusted_url("https://objects.githubusercontent.com/asset-id")
    assert not is_trusted_url("https://evil-site.com/fake-setup.exe")
    assert not is_trusted_url("http://github.com/insecure.exe")
    assert not is_trusted_url("ftp://github.com/setup.exe")


def test_download_worker_hash_mismatch():
    setup_url = "https://github.com/Nairolf/Mochi/releases/download/v2.0.1/Mochi-Setup-2.0.1.exe"
    sha_url = "https://github.com/Nairolf/Mochi/releases/download/v2.0.1/Mochi-Setup-2.0.1.exe.sha256"

    fake_setup_content = b"MZ... fake exe content"
    wrong_expected_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    class FakeResponse:
        def __init__(self, data: bytes):
            self._io = io.BytesIO(data)
            self.headers = {"Content-Length": str(len(data))}

        def read(self, amt=-1):
            return self._io.read(amt)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url == sha_url:
            return FakeResponse(f"{wrong_expected_hash}  Mochi-Setup-2.0.1.exe".encode("utf-8"))
        if url == setup_url:
            return FakeResponse(fake_setup_content)
        raise ValueError("Unknown URL")

    worker = DownloadUpdateWorker(setup_url, sha_url, "2.0.1")

    results = []
    worker.download_completed.connect(lambda ok, msg: results.append((ok, msg)))

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        worker.run()

    assert len(results) == 1
    ok, msg = results[0]
    assert ok is False
    assert "SHA256-Abweichung" in msg
