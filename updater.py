# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Auto-Update-Logik ueber GitHub Releases."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from version import UPDATE_REPO, __version__

logger = logging.getLogger("mochi.updater")

TRUSTED_PREFIXES = (
    "https://github.com/",
    "https://objects.githubusercontent.com/",
)


def parse_version(v: str) -> tuple[int, ...]:
    """Wandelt z. B. 'v2.0.1' oder '2.0.0-rc1' in ein vergleichbares Integer-Tupel um."""
    clean = v.strip().lstrip("vV")
    clean = clean.split("-")[0].split("+")[0]
    parts: list[int] = []
    for piece in clean.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(remote_v: str, current_v: str = __version__) -> bool:
    """Prueft, ob remote_v strikt neuer als current_v ist."""
    return parse_version(remote_v) > parse_version(current_v)


def is_trusted_url(url: str) -> bool:
    """Verhindert Downloads von unbefugten Fremd-Domains."""
    return any(url.startswith(prefix) for prefix in TRUSTED_PREFIXES)


def latest_release_via_redirect(repo: str) -> dict:
    """Neuestes Release ohne GitHub-API (kein Rate-Limit): /releases/latest leitet auf /releases/tag/<tag> weiter.
    Liefert dieselbe Form wie die API-Antwort (tag_name, assets, body)."""
    req = urllib.request.Request(f"https://github.com/{repo}/releases/latest", method="HEAD",
                                 headers={"User-Agent": f"DesktopCat/{__version__}"})
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        final_url = resp.geturl()
    m = re.search(r"/releases/tag/([^/?#]+)", final_url)
    if not m:
        raise ValueError(f"Kein Release gefunden ({final_url})")
    tag = m.group(1)
    setup = f"DesktopCat-Setup-{tag.lstrip('vV')}.exe"
    base = f"https://github.com/{repo}/releases/download/{tag}/"
    return {"tag_name": tag, "body": "",
            "assets": [{"name": n, "browser_download_url": base + n} for n in (setup, setup + ".sha256")]}


class CheckUpdateWorker(QThread):
    """Prueft im Hintergrund, ob ein neues GitHub Release vorliegt."""

    check_completed = pyqtSignal(dict)

    def __init__(self, manual: bool = False, repo: str = UPDATE_REPO):
        super().__init__()
        self.manual = manual
        self.repo = repo

    def run(self) -> None:
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"DesktopCat/{__version__}",
            },
        )
        try:
            try:
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as api_exc:
                # Die API erlaubt ohne Login nur 60 Abfragen/Stunde pro IP (Schule, Firma, ...) -> Webseite fragen
                logger.info("GitHub-API nicht verfuegbar (%s), nutze Release-Weiterleitung", api_exc)
                data = latest_release_via_redirect(self.repo)

            tag = data.get("tag_name", "")
            if not tag:
                self.check_completed.emit({
                    "status": "error",
                    "manual": self.manual,
                    "error": "Kein tag_name im Release gefunden.",
                })
                return

            newer = is_newer(tag, __version__)
            if not newer:
                self.check_completed.emit({
                    "status": "up_to_date",
                    "manual": self.manual,
                    "version": tag,
                })
                return

            # Assets suchen
            setup_url = ""
            sha_url = ""
            assets = {a.get("name", ""): a.get("browser_download_url", "") for a in data.get("assets", [])}
            setup_name = next((n for n in assets if n.startswith("DesktopCat-Setup-") and n.endswith(".exe")), "")
            setup_url = assets.get(setup_name, "")
            sha_url = assets.get(setup_name + ".sha256", "")

            # Ohne Pruefsumme wird nichts installiert (Schutz vor manipulierten/fehlerhaften Downloads)
            if not setup_url or not sha_url:
                self.check_completed.emit({
                    "status": "error",
                    "manual": self.manual,
                    "error": "Im Release fehlt DesktopCat-Setup-*.exe oder die passende .sha256-Datei.",
                })
                return

            self.check_completed.emit({
                "status": "update_available",
                "manual": self.manual,
                "version": tag.lstrip("vV"),
                "notes": data.get("body", ""),
                "setup_url": setup_url,
                "sha_url": sha_url,
            })

        except Exception as exc:
            logger.warning("Update-Check fehlgeschlagen: %s", exc)
            self.check_completed.emit({
                "status": "error",
                "manual": self.manual,
                "error": str(exc),
            })


class DownloadUpdateWorker(QThread):
    """Laedt das Update-Setup streamend herunter und validiert den SHA256-Hash."""

    progress = pyqtSignal(int)
    download_completed = pyqtSignal(bool, str)

    def __init__(self, setup_url: str, sha_url: str, version: str):
        super().__init__()
        self.setup_url = setup_url
        self.sha_url = sha_url
        self.version = version

    def run(self) -> None:
        if not is_trusted_url(self.setup_url):
            self.download_completed.emit(False, "Setup-URL ist nicht vertrauenswuerdig.")
            return

        expected_hash = ""
        if not self.sha_url:
            self.download_completed.emit(False, "Keine SHA256-Pruefsumme vorhanden - Update abgebrochen.")
            return
        if self.sha_url:
            if not is_trusted_url(self.sha_url):
                self.download_completed.emit(False, "SHA256-URL ist nicht vertrauenswuerdig.")
                return
            try:
                req_sha = urllib.request.Request(
                    self.sha_url,
                    headers={"User-Agent": f"DesktopCat/{__version__}"},
                )
                with urllib.request.urlopen(req_sha, timeout=10.0) as resp:
                    sha_content = resp.read().decode("utf-8-sig").strip()
                    parts = sha_content.split()
                    if parts:
                        expected_hash = parts[0].strip().lower()
            except Exception as exc:
                self.download_completed.emit(False, f"Konnte SHA256-Datei nicht laden: {exc}")
                return

        dest_dir = Path(tempfile.gettempdir())
        dest_file = dest_dir / f"DesktopCat-Setup-{self.version}.exe"
        temp_dest = dest_file.with_suffix(".exe.part")

        try:
            req_setup = urllib.request.Request(
                self.setup_url,
                headers={"User-Agent": f"DesktopCat/{__version__}"},
            )
            hasher = hashlib.sha256()

            with urllib.request.urlopen(req_setup, timeout=30.0) as resp, open(temp_dest, "wb") as out:
                total_len = resp.headers.get("Content-Length")
                total_size = int(total_len) if total_len and total_len.isdigit() else 0
                downloaded = 0

                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = int(downloaded * 100 / total_size)
                        self.progress.emit(min(100, pct))

            actual_hash = hasher.hexdigest().lower()
            if not expected_hash or actual_hash != expected_hash:
                try:
                    temp_dest.unlink()
                except OSError:
                    pass
                self.download_completed.emit(
                    False,
                    f"SHA256-Abweichung! Erwartet: {expected_hash}, Erhalten: {actual_hash}",
                )
                return

            if dest_file.exists():
                try:
                    dest_file.unlink()
                except OSError:
                    pass
            temp_dest.rename(dest_file)
            self.download_completed.emit(True, str(dest_file))

        except Exception as exc:
            try:
                if temp_dest.exists():
                    temp_dest.unlink()
            except OSError:
                pass
            self.download_completed.emit(False, f"Download fehlgeschlagen: {exc}")


def launch_installer(setup_exe: str | Path) -> None:
    """Startet das Setup silent und uebergibt Steuerungsflags."""
    cmd = [
        str(setup_exe),
        "/SILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/CLOSEAPPLICATIONS",
    ]
    subprocess.Popen(cmd)
