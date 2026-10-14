# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Echte Windows-Aktionen, die der Buddy (per KI oder Regelparser) ausfuehren kann.

Alle Funktionen sind blockierend und fuer den Einsatz in einem Worker-Thread gedacht - nie im UI-Thread aufrufen.
Jedes Tool gibt ein ToolResult mit einer niedlichen, verstaendlichen Meldung fuer die Sprechblase zurueck.
"""
from __future__ import annotations

import ctypes
import inspect
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

import i18n
from paths import DATA_DIR


LOG_FILE = DATA_DIR / "desktop_organize_log.json"

# Tools, die erst nach ausdruecklichem "ja" des Nutzers laufen duerfen (siehe agent_brain.AgentBrain.pending_action)
DANGEROUS_TOOLS = {"clean_pc", "close_window", "delete_file", "execute_powershell", "forget_facts", "wipe_my_data",
                   "run_custom_script", "manage_custom_routines"}


@dataclass
class ToolResult:
    ok: bool
    message: str
    notify_title: Optional[str] = None   # gesetzt -> zusaetzlich Windows-Benachrichtigung zeigen
    data: Optional[dict] = None


class ToolError(Exception):
    """Erwarteter Fehler mit bereits verstaendlicher Meldung."""


# ======================================================================================
#  Helfer
# ======================================================================================
@contextmanager
def com_scope():
    """COM pro Thread initialisieren (noetig fuer Word-Automation und native Dialoge im Worker-Thread)."""
    try:
        import pythoncom
    except Exception:
        yield
        return
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


# Anrede und Figur fuer Tool-Meldungen; wird vom Agent-Worker bzw. der UI per set_context() gesetzt.
_ctx = {"user": "Boss", "char": "cat_mochi"}


def set_context(user_name: str = "Boss", character_id: str = "cat_mochi") -> None:
    _ctx["user"] = (user_name or "").strip() or "Boss"
    _ctx["char"] = character_id or "cat_mochi"


def _user_name() -> str:
    return _ctx["user"]


def _emoji() -> str:
    try:
        from pet_sprites import get_character_info
        return get_character_info(_ctx["char"]).get("emoji", "🐾")
    except Exception:
        return "🐾"


def _pet_name() -> str:
    try:
        from pet_sprites import get_character_info
        return get_character_info(_ctx["char"]).get("name", "Kylie")
    except Exception:
        return "Kylie"


def known_folder(name: str) -> Path:
    """Echter Pfad eines Windows-Ordners (Downloads, Documents, Pictures, Music, Videos) -
    auch wenn er z. B. nach OneDrive umgeleitet ist."""
    try:
        from win32com.shell import shell, shellcon
        return Path(shell.SHGetKnownFolderPath(getattr(shellcon, f"FOLDERID_{name}")))
    except Exception:
        return Path.home() / name


def desktop_dir() -> Path:
    try:
        from win32com.shell import shell, shellcon
        return Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, 0, 0))
    except Exception:
        return Path.home() / "Desktop"


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def friendly_error(exc: BaseException) -> str:
    """Wandelt technische Ausnahmen in verstaendliche, freundliche Saetze um."""
    if isinstance(exc, ToolError):
        return str(exc)
    name = type(exc).__name__
    if isinstance(exc, PermissionError):
        return "Autsch, dafuer fehlen mir die Rechte \U0001F640 Ist die Datei vielleicht gesperrt oder schreibgeschuetzt?"
    if isinstance(exc, FileNotFoundError):
        return "Hm, die Datei oder den Ordner finde ich nicht \U0001F975"
    if name == "com_error":
        return ("Word macht gerade Zicken \U0001F63F Ist Microsoft Word installiert, und ist die Datei "
                "nicht noch in Word geoeffnet oder gesperrt?")
    if isinstance(exc, TimeoutError):
        return "Das dauert mir zu lange - Zeitueberschreitung \u23F3"
    if isinstance(exc, OSError):
        return f"Da ging was schief: {exc.strerror or exc}"
    return f"Uff, da ist etwas schiefgelaufen ({name}: {exc})"


# ======================================================================================
#  1) Word -> PDF
# ======================================================================================
def _pick_word_file() -> Optional[str]:
    """Nativer Windows-Dateidialog (funktioniert auch aus einem Worker-Thread)."""
    start = str(desktop_dir())
    try:
        import pywintypes
        import win32con
        import win32gui
        flt = "Word-Dokumente\0*.docx;*.doc\0Alle Dateien\0*.*\0"
        flags = (win32con.OFN_EXPLORER | win32con.OFN_FILEMUSTEXIST | win32con.OFN_PATHMUSTEXIST
                 | win32con.OFN_NOCHANGEDIR | win32con.OFN_HIDEREADONLY)
        try:
            fname, _, _ = win32gui.GetOpenFileNameW(
                InitialDir=start, Flags=flags, Filter=flt, FilterIndex=1,
                Title="Welche Word-Datei soll ich in ein PDF verwandeln?", MaxFile=2048,
            )
            return fname or None
        except pywintypes.error as exc:
            if exc.winerror == 0:      # Abbrechen
                return None
            raise
    except Exception:
        # Fallback: tkinter-Dialog
        try:
            import tkinter
            from tkinter import filedialog
            root = tkinter.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                initialdir=start, title="Word-Datei waehlen",
                filetypes=[("Word-Dokumente", "*.docx *.doc"), ("Alle Dateien", "*.*")],
            )
            root.destroy()
            return path or None
        except Exception:
            return None


def _word_is_running() -> bool:
    try:
        import win32com.client
        win32com.client.GetActiveObject("Word.Application")
        return True
    except Exception:
        return False


def convert_word_to_pdf(file_path: Optional[str] = None) -> ToolResult:
    """Wandelt eine .docx/.doc in ein PDF im selben Ordner um (Pfad optional -> Dateidialog)."""
    if not file_path:
        file_path = _pick_word_file()
        if not file_path:
            return ToolResult(False, "Okay, abgebrochen~ Ich habe keine Datei bekommen \U0001F43E")

    src = Path(str(file_path).strip().strip('"').strip("'")).expanduser()
    if not src.exists():
        raise ToolError(f"Die Datei \u201e{src.name}\u201c gibt es nicht \U0001F975")
    if src.suffix.lower() not in (".docx", ".doc"):
        raise ToolError("Das ist keine Word-Datei (.docx / .doc) \U0001F914")

    # Word legt beim Bearbeiten eine ~$-Sperrdatei an -> Datei ist noch geoeffnet
    for lock in (src.with_name("~$" + src.name[2:]), src.with_name("~$" + src.name)):
        if lock.exists():
            raise ToolError(f"\u201e{src.name}\u201c ist noch in Word geoeffnet. Schliess sie bitte kurz, dann klappt's! \U0001F4DD")

    pdf = _unique(src.with_suffix(".pdf"))
    try:
        from docx2pdf import convert
    except ImportError:
        raise ToolError("Das Paket docx2pdf fehlt. Bitte `pip install docx2pdf` ausfuehren.")

    with com_scope():
        # War Word schon offen (Nutzer arbeitet?) -> nicht beenden!
        keep = _word_is_running()
        convert(str(src), str(pdf), keep_active=keep)

    if not pdf.exists():
        raise ToolError("Hm, Word hat kein PDF erzeugt. War die Datei vielleicht beschaedigt?")
    return ToolResult(True, f"Fertig! \u201e{pdf.name}\u201c liegt direkt neben dem Original \U0001F4C4\u2728",
                      notify_title="Word \u2192 PDF fertig")


# ======================================================================================
#  2) Desktop aufraeumen
# ======================================================================================
CATEGORIES: dict[str, set[str]] = {
    "Bilder": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic", ".tif", ".tiff", ".ico", ".psd", ".raw"},
    "Dokumente": {".doc", ".docx", ".pdf", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".md", ".odp", ".ods"},
    "Installer": {".exe", ".msi", ".msix", ".appx", ".iso", ".dmg"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v"},
    "Musik": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Archive": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".cpp", ".c", ".h", ".java", ".cs", ".sql", ".sh", ".ps1", ".bat", ".yml", ".yaml"},
}
SKIP_SUFFIXES = {".lnk", ".url", ".ini", ".tmp"}
_EXT_TO_CAT = {ext: cat for cat, exts in CATEGORIES.items() for ext in exts}


def _is_hidden_or_system(path: Path) -> bool:
    try:
        attrs = getattr(os.stat(path), "st_file_attributes", 0)
        return bool(attrs & (0x2 | 0x4))     # HIDDEN | SYSTEM
    except OSError:
        return True


def organize_desktop() -> ToolResult:
    """Sortiert lose Dateien vom Desktop in Unterordner (Bilder, Dokumente, Installer, ...). Verknuepfungen bleiben."""
    desk = desktop_dir()
    if not desk.exists():
        raise ToolError("Ich finde deinen Desktop-Ordner nicht \U0001F63F")
    moves: list[dict] = []
    counts: dict[str, int] = {}
    for entry in sorted(desk.iterdir()):
        try:
            if not entry.is_file() or entry.name.startswith(("~$", ".")):
                continue
            if entry.suffix.lower() in SKIP_SUFFIXES or _is_hidden_or_system(entry):
                continue
            cat = _EXT_TO_CAT.get(entry.suffix.lower(), "Sonstiges")
            target_dir = desk / cat
            target_dir.mkdir(exist_ok=True)
            target = _unique(target_dir / entry.name)
            shutil.move(str(entry), str(target))
            moves.append({"from": str(entry), "to": str(target)})
            counts[cat] = counts.get(cat, 0) + 1
        except PermissionError:
            continue        # gesperrte Datei einfach ueberspringen
    if not moves:
        return ToolResult(True, "Dein Desktop ist schon blitzsauber! \u2728")
    try:
        LOG_FILE.write_text(json.dumps(moves, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    detail = ", ".join(f"{c}: {n}" for c, n in counts.items())
    return ToolResult(True, f"Aufgeraeumt! {len(moves)} Dateien sortiert ({detail}) \U0001F9F9\u2728 "
                            f"Sag \u201emach das rueckgaengig\u201c, falls es dir nicht gefaellt.")


def undo_organize_desktop() -> ToolResult:
    """Macht das letzte Desktop-Aufraeumen rueckgaengig."""
    try:
        moves = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ToolResult(False, "Es gibt nichts, was ich rueckgaengig machen koennte \U0001F43E")
    restored = 0
    for m in reversed(moves):
        src, dst = Path(m["to"]), Path(m["from"])
        try:
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))
                restored += 1
            if src.parent.exists() and not any(src.parent.iterdir()):
                src.parent.rmdir()
        except OSError:
            continue
    try:
        LOG_FILE.unlink()
    except OSError:
        pass
    return ToolResult(True, f"Alles zurueckgelegt: {restored} Dateien sind wieder auf dem Desktop \u21A9\uFE0F")


# ======================================================================================
#  3) Programme starten
# ======================================================================================
PROGRAMS: dict[str, tuple[str, str]] = {
    # Schluessel (klein) -> (Startbefehl, Anzeigename)
    "notepad": ("notepad.exe", "Notepad"), "editor": ("notepad.exe", "den Editor"),
    "rechner": ("calc.exe", "den Rechner"), "calculator": ("calc.exe", "den Rechner"), "calc": ("calc.exe", "den Rechner"),
    "paint": ("mspaint.exe", "Paint"), "explorer": ("explorer.exe", "den Explorer"),
    "dateien": ("explorer.exe", "den Explorer"), "datei-explorer": ("explorer.exe", "den Explorer"),
    "taskmanager": ("taskmgr.exe", "den Task-Manager"), "task-manager": ("taskmgr.exe", "den Task-Manager"),
    "cmd": ("cmd.exe", "die Eingabeaufforderung"), "eingabeaufforderung": ("cmd.exe", "die Eingabeaufforderung"),
    "powershell": ("powershell.exe", "PowerShell"), "terminal": ("wt.exe", "das Terminal"),
    "einstellungen": ("ms-settings:", "die Einstellungen"), "settings": ("ms-settings:", "die Einstellungen"),
    "word": ("winword.exe", "Word"), "excel": ("excel.exe", "Excel"), "powerpoint": ("powerpnt.exe", "PowerPoint"),
    "outlook": ("outlook.exe", "Outlook"),
    "chrome": ("chrome.exe", "Chrome"), "firefox": ("firefox.exe", "Firefox"),
    "edge": ("msedge.exe", "Edge"), "spotify": ("spotify.exe", "Spotify"), "discord": ("discord.exe", "Discord"),
    "steam": ("steam.exe", "Steam"), "vscode": ("code.exe", "VS Code"), "code": ("code.exe", "VS Code"),
}
_FORBIDDEN_NAME = re.compile(r"[&|;<>`\r\n]")


def open_program(name: str) -> ToolResult:
    """Startet ein Programm (z. B. 'browser', 'notepad', 'word') oder oeffnet eine Webadresse."""
    raw = (name or "").strip().strip('"')
    if not raw:
        raise ToolError("Was soll ich denn oeffnen? \U0001F43E")
    if _FORBIDDEN_NAME.search(raw):
        raise ToolError("Das sieht mir nach einem komischen Befehl aus - den fuehre ich lieber nicht aus \U0001F640")
    key = raw.lower()

    if key in ("browser", "internet", "web", "webbrowser"):
        if not webbrowser.open("https://www.google.com"):
            raise ToolError("Ich konnte keinen Browser starten \U0001F63F")
        return ToolResult(True, "Ich hab den Browser fuer dich geoeffnet \U0001F310")

    if key.startswith(("http://", "https://", "www.")):
        webbrowser.open(raw if "://" in raw else "https://" + raw)
        return ToolResult(True, "Seite wird geoeffnet \U0001F310")

    command, label = PROGRAMS.get(key, (raw, raw))
    try:
        import pywintypes
        import win32api
        try:
            win32api.ShellExecute(0, "open", command, None, None, 1)
        except pywintypes.error as exc:
            raise ToolError(f"\u201e{raw}\u201c finde ich nicht - ist es installiert? \U0001F975") from exc
    except ImportError:
        try:
            os.startfile(command)  # type: ignore[attr-defined]
        except OSError as exc:
            raise ToolError(f"\u201e{raw}\u201c finde ich nicht - ist es installiert? \U0001F975") from exc
    return ToolResult(True, f"Ich oeffne {label} fuer dich \U0001F43E")


# ======================================================================================
#  4) System-Checks
# ======================================================================================
class _PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def _battery_text() -> str:
    st = _PowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
        return "Den Akkustand kann ich gerade nicht lesen \U0001F615"
    if st.BatteryFlag == 128 or st.BatteryLifePercent == 255:
        return "\U0001F50C Kein Akku - ich haenge an der Steckdose"
    pct = st.BatteryLifePercent
    icon = "\U0001FAAB" if pct <= 20 else "\U0001F50B"
    charging = " (laedt gerade \u26A1)" if st.ACLineStatus == 1 else ""
    hint = " - bald an die Steckdose, bitte!" if pct <= 20 and st.ACLineStatus != 1 else ""
    return f"{icon} Akku: {pct} %{charging}{hint}"


def _disk_text() -> str:
    lines = []
    try:
        import win32api
        drives = [d for d in win32api.GetLogicalDriveStrings().split("\0") if d]
        fixed = [d for d in drives if ctypes.windll.kernel32.GetDriveTypeW(d) == 3]
    except Exception:
        fixed = [os.environ.get("SystemDrive", "C:") + "\\"]
    for d in fixed or ["C:\\"]:
        try:
            u = shutil.disk_usage(d)
            lines.append(f"\U0001F4BE {d[:2]} {u.free / 1e9:.0f} GB frei von {u.total / 1e9:.0f} GB")
        except OSError:
            continue
    return "\n".join(lines) or "Die Festplatten kann ich nicht auslesen \U0001F615"


def system_info(kind: str = "all") -> ToolResult:
    """Zeigt Akkustand und/oder freien Speicherplatz (kind: battery | disk | all)."""
    kind = (kind or "all").lower()
    parts = []
    if kind in ("battery", "akku", "all"):
        parts.append(_battery_text())
    if kind in ("disk", "festplatte", "storage", "all"):
        parts.append(_disk_text())
    return ToolResult(True, "\n".join(parts))


# ======================================================================================
#  5) Dateien suchen
# ======================================================================================
_SKIP_DIRS = {"node_modules", "__pycache__", "appdata", "$recycle.bin", "site-packages", "windows", "program files"}


def _search_roots(location: Optional[str]) -> list[Path]:
    home = Path.home()
    named = {
        "desktop": desktop_dir(), "schreibtisch": desktop_dir(),
        "downloads": home / "Downloads", "download": home / "Downloads",
        "dokumente": home / "Documents", "documents": home / "Documents",
        "bilder": home / "Pictures", "pictures": home / "Pictures",
        "musik": home / "Music", "videos": home / "Videos",
    }
    if location:
        loc = location.strip().strip('"')
        if loc.lower() in named:
            return [named[loc.lower()]]
        if Path(loc).exists():
            return [Path(loc)]
    return [named["desktop"], named["dokumente"], named["downloads"], named["bilder"]]


def find_files(query: str, location: Optional[str] = None) -> ToolResult:
    """Sucht Dateien nach Namen (Teilwoerter) in Desktop/Dokumente/Downloads/Bilder oder in einem Ordner."""
    tokens = [t for t in re.split(r"\s+", (query or "").lower().strip()) if t]
    if not tokens:
        raise ToolError("Wonach soll ich suchen? \U0001F50D")
    deadline = time.monotonic() + 8.0
    hits: list[tuple[bool, float, Path]] = []
    for root in _search_roots(location):
        stack = [(root, 0)]
        while stack and time.monotonic() < deadline and len(hits) < 200:
            folder, depth = stack.pop()
            try:
                with os.scandir(folder) as it:
                    for e in it:
                        name = e.name.lower()
                        try:
                            if e.is_dir(follow_symlinks=False):
                                if depth < 6 and not name.startswith(".") and name not in _SKIP_DIRS:
                                    stack.append((Path(e.path), depth + 1))
                            elif all(t in name for t in tokens):
                                exact = Path(name).stem == " ".join(tokens)
                                hits.append((not exact, -e.stat().st_mtime, Path(e.path)))
                        except OSError:
                            continue
            except (PermissionError, FileNotFoundError, OSError):
                continue
    if not hits:
        return ToolResult(False, f"Ich hab nach \u201e{query}\u201c gesucht, aber nichts gefunden \U0001F97A")
    hits.sort()
    top = [h[2] for h in hits[:6]]
    lines = [f"\u2022 {p.name}  ({p.parent.name or p.parent})" for p in top]
    extra = f"\n\u2026 und {len(hits) - len(top)} weitere" if len(hits) > len(top) else ""
    try:   # erstes Ergebnis im Explorer markieren
        subprocess.Popen(f'explorer /select,"{top[0]}"')
        tail = "\nDas erste habe ich dir im Explorer markiert \U0001F4C2"
    except OSError:
        tail = ""
    return ToolResult(True, f"{len(hits)} Treffer gefunden \U0001F50D\n" + "\n".join(lines) + extra + tail)


# ======================================================================================
#  6) Screenshot aufnehmen
# ======================================================================================
def take_screenshot(filename: Optional[str] = None) -> ToolResult:
    """Macht einen Screenshot des gesamten Bildschirms und speichert ihn auf dem Desktop."""
    desk = desktop_dir()
    desk.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    name = (filename or f"Screenshot_{stamp}.png").strip().strip('"')
    if not name.lower().endswith((".png", ".jpg", ".jpeg")):
        name += ".png"
    target = _unique(desk / name)

    saved = False
    # Methode 1: PyQt6 QGuiApplication
    try:
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            pix = screen.grabWindow(0)
            if not pix.isNull():
                pix.save(str(target))
                saved = target.exists() and target.stat().st_size > 0
    except Exception:
        pass

    # Methode 2: PowerShell Graphics.CopyFromScreen
    if not saved:
        try:
            ps_code = (
                f"Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
                f"$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                f"$bmp=New-Object System.Drawing.Bitmap($b.Width,$b.Height); "
                f"$g=[System.Drawing.Graphics]::FromImage($bmp); "
                f"$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); "
                f"$bmp.Save('{str(target).replace(chr(92), chr(92)+chr(92))}'); "
                f"$g.Dispose(); $bmp.Dispose();"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, timeout=6)
            saved = target.exists() and target.stat().st_size > 0
        except Exception:
            pass

    if not saved:
        err = "I couldn't take a screenshot 🙀" if i18n.lang() == "en" else "Ich konnte leider kein Bildschirmfoto aufnehmen 🙀"
        raise ToolError(err)
    if i18n.lang() == "en":
        return ToolResult(True, f"Click! 📸 Screenshot saved:\n\"{target.name}\" on your desktop ✨",
                          notify_title="Screenshot saved")
    return ToolResult(True, f"Klick! 📸 Screenshot gespeichert:\n„{target.name}“ auf deinem Desktop ✨",
                      notify_title="Screenshot gespeichert")



# ======================================================================================
#  7) Schnelle Websuche & Wissensfragen
# ======================================================================================
def web_search(query: str) -> ToolResult:
    """Sucht im Web nach Antworten via DuckDuckGo Instant Answer API / Wikipedia."""
    q = (query or "").strip().strip('"')
    if not q:
        raise ToolError("Wonach soll ich im Web suchen? 🐾")

    # Schritt 1: DuckDuckGo Instant Answer
    try:
        resp = requests.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            text = (data.get("AbstractText") or "").strip()
            source = data.get("AbstractSource") or "DuckDuckGo"
            if text:
                return ToolResult(True, f"🌐 {text[:380]}…\n(Quelle: {source})")
            ans = (data.get("Answer") or "").strip()
            if ans:
                return ToolResult(True, f"💡 {ans}")
    except Exception:
        pass

    # Schritt 2: Wikipedia Summary (deutsch)
    try:
        clean_q = re.sub(r"^(wer|was|wo|wie|wann)\s+(ist|war|sind|liegt|bedeutet)\s+", "", q, flags=re.IGNORECASE).strip(" ?.")
        wiki_url = f"https://de.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(clean_q)}"
        w_resp = requests.get(wiki_url, timeout=5, headers={"User-Agent": "DesktopCat/2.2"})
        if w_resp.status_code == 200:
            w_data = w_resp.json()
            extract = (w_data.get("extract") or "").strip()
            title = w_data.get("title") or clean_q
            if extract:
                return ToolResult(True, f"📚 {title}:\n{extract[:360]}…")
    except Exception:
        pass

    # Schritt 3: Fallback -> Im Standardbrowser öffnen
    search_url = f"https://www.google.com/search?q={requests.utils.quote(q)}"
    webbrowser.open(search_url)
    return ToolResult(True, f"Ich habe eine Websuche nach „{q}“ im Browser für dich geöffnet 🌐🔍")


# ======================================================================================
#  8) Lautstärke & Windows-Audiosteuerung
# ======================================================================================
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF


def control_volume(action: str = "up") -> ToolResult:
    """Steuert die Windows-Lautstärke: 'up' (lauter), 'down' (leiser), 'mute' (stummschalten/entstummen)."""
    act = (action or "up").lower().strip()
    try:
        import win32api
        if "mute" in act or "stumm" in act:
            win32api.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            win32api.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
            return ToolResult(True, "Ton stummgeschaltet / wieder an! 🔇✨")
        if "up" in act or "laut" in act:
            for _ in range(5):
                win32api.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                win32api.keybd_event(VK_VOLUME_UP, 0, 2, 0)
            return ToolResult(True, "Lautstärke erhöht! 🔊🎶")
        if "down" in act or "leis" in act:
            for _ in range(5):
                win32api.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                win32api.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
            return ToolResult(True, "Lautstärke gesenkt! 🔉✨")
        return ToolResult(False, "Möchtest du 'lauter', 'leiser' oder 'stumm' schalten? 🐾")
    except Exception as exc:
        raise ToolError(f"Lautstärkesteuerung fehlgeschlagen: {exc}")


# ======================================================================================
#  9) Mediensteuerung (Spotify / YouTube / Media Player)
# ======================================================================================
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3


def media_control(action: str = "play_pause") -> ToolResult:
    """Steuert Medienwiedergabe: 'play_pause', 'next' (nächstes Lied), 'prev' (vorheriges Lied)."""
    act = (action or "play_pause").lower().strip()
    try:
        import win32api
        if any(w in act for w in ("play", "pause", "stopp", "weiter", "wiedergabe")):
            win32api.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            win32api.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
            return ToolResult(True, "Play / Pause umgeschaltet! ⏯️🎶")
        if any(w in act for w in ("next", "weiter", "naechst", "vor")):
            win32api.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
            win32api.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
            return ToolResult(True, "Nächster Titel! ⏭️🎵")
        if any(w in act for w in ("prev", "zurueck", "vorig")):
            win32api.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
            win32api.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
            return ToolResult(True, "Vorheriger Titel! ⏮️🎵")
        return ToolResult(False, "Unterstützte Aktionen: 'play_pause', 'next', 'prev' 🐾")
    except Exception as exc:
        raise ToolError(f"Mediensteuerung fehlgeschlagen: {exc}")


# ======================================================================================
#  10) Notizen verwalten
# ======================================================================================
NOTES_FILE = desktop_dir() / "Notizen.txt"


def manage_notes(action: str = "read", text: Optional[str] = None) -> ToolResult:
    """Verwaltet Desktop-Notizen: 'add' (Notiz anhaengen), 'read' (vorlesen), 'clear' (leeren)."""
    act = (action or "read").lower().strip()
    target = desktop_dir() / "Notizen.txt"
    is_en = i18n.lang() == "en"
    if act in ("add", "append", "neu", "notiere", "schreib"):
        if not text:
            err = "What should I note down for you? 🐾" if is_en else "Was soll ich denn für dich notieren? 🐾"
            raise ToolError(err)
        stamp = time.strftime("%Y-%m-%d %H:%M")
        line = f"• [{stamp}] {text.strip()}\n"
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(line)
        rep = f"Noted! 📝 \"{text.strip()}\" added to Notizen.txt on your desktop ✨" if is_en else f"Notiert! 📝 „{text.strip()}“ liegt in Notizen.txt auf deinem Desktop ✨"
        return ToolResult(True, rep)

    if act in ("read", "show", "zeig", "lies"):
        if not target.exists():
            rep = "You don't have any notes on your desktop yet 📝" if is_en else "Du hast noch keine Notizen auf dem Desktop 📝"
            return ToolResult(True, rep)
        lines = [l.strip() for l in target.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            rep = "Your notes file is currently empty 📝" if is_en else "Deine Notizdatei ist aktuell leer 📝"
            return ToolResult(True, rep)
        recent = lines[-4:]
        hdr = "Your latest notes 📝:\n" if is_en else "Deine letzten Notizen 📝:\n"
        return ToolResult(True, hdr + "\n".join(recent))

    if act in ("clear", "loeschen", "delete"):
        if target.exists():
            target.write_text("", encoding="utf-8")
        rep = "Notes have been cleared! 🗑️" if is_en else "Notizen wurden geleert! 🗑️"
        return ToolResult(True, rep)

    return ToolResult(False, "Actions: 'add', 'read' or 'clear' 🐾" if is_en else "Aktionen: 'add', 'read' oder 'clear' 🐾")



# ======================================================================================
#  11) Windows-Zwischenablage (Clipboard)
# ======================================================================================
def clipboard_action(action: str = "read", text: Optional[str] = None) -> ToolResult:
    """Liest die Zwischenablage ('read') oder kopiert Text hinein ('write')."""
    act = (action or "read").lower().strip()
    try:
        import win32clipboard
        import win32con
        if act in ("write", "copy", "kopier", "set"):
            if text is None:
                raise ToolError("Welcher Text soll in die Zwischenablage? 🐾")
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(str(text), win32con.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
            return ToolResult(True, f"In die Zwischenablage kopiert! 📋\n„{str(text)[:100]}“")

        # read
        win32clipboard.OpenClipboard()
        content = ""
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                content = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                content = win32clipboard.GetClipboardData(win32con.CF_TEXT).decode("utf-8", errors="ignore")
        finally:
            win32clipboard.CloseClipboard()

        if not content:
            return ToolResult(True, "Die Zwischenablage ist aktuell leer 📋")
        preview = content[:200] + ("…" if len(content) > 200 else "")
        return ToolResult(True, f"Inhalt der Zwischenablage 📋:\n{preview}")
    except Exception as exc:
        raise ToolError(f"Zwischenablage-Zugriff fehlgeschlagen: {exc}")


# ======================================================================================
#  12) Ordner im Explorer öffnen
# ======================================================================================
def open_folder(name: str = "downloads") -> ToolResult:
    """Oeffnet Windows-Ordner wie Downloads, Dokumente, Desktop, Bilder, Musik oder Papierkorb."""
    raw = (name or "downloads").lower().strip()
    downloads, documents = known_folder("Downloads"), known_folder("Documents")
    pictures, music, videos = known_folder("Pictures"), known_folder("Music"), known_folder("Videos")
    mapping = {
        "downloads": downloads, "download": downloads,
        "dokumente": documents, "documents": documents,
        "desktop": desktop_dir(), "schreibtisch": desktop_dir(),
        "bilder": pictures, "pictures": pictures, "fotos": pictures,
        "musik": music, "music": music,
        "videos": videos, "filme": videos,
        "c": Path("C:\\"), "c:": Path("C:\\"), "festplatte": Path("C:\\"),
    }
    if "papierkorb" in raw or "trash" in raw or "recycle" in raw:
        try:
            subprocess.Popen("explorer.exe shell:RecycleBinFolder")
            return ToolResult(True, "Ich habe den Papierkorb für dich geöffnet 🗑️")
        except OSError as exc:
            raise ToolError(f"Konnte Papierkorb nicht öffnen: {exc}")

    target = mapping.get(raw)
    if not target and Path(raw).exists():
        target = Path(raw)
    if not target or not target.exists():
        raise ToolError(f"Den Ordner „{name}“ finde ich leider nicht 😿")

    try:
        os.startfile(str(target))  # type: ignore[attr-defined]
        return ToolResult(True, f"Ordner geöffnet: {target.name or str(target)} 📂✨")
    except OSError as exc:
        raise ToolError(f"Konnte Ordner nicht öffnen: {exc}")


# ======================================================================================
#  13) Sicherer Taschenrechner
# ======================================================================================
def calculate(expression: str) -> ToolResult:
    """Berechnet mathematische Ausdruecke sicher (z. B. '25 * 4', '15% von 200', 'sqrt(144)')."""
    import ast
    import operator
    expr = (expression or "").strip().lower()
    if not expr:
        raise ToolError("Was soll ich denn für dich rechnen? 🐾")

    # Prozentrechnung vereinfachen: "15% von 200" -> "200 * 0.15"
    m_pct = re.search(r"(\d+(?:[.,]\d+)?)\s*%\s*(?:von|of|\*)\s*(\d+(?:[.,]\d+)?)", expr)
    if m_pct:
        p, val = float(m_pct.group(1).replace(",", ".")), float(m_pct.group(2).replace(",", "."))
        res = val * (p / 100.0)
        return ToolResult(True, f"Das Ergebnis ist: {res:g} 🧮✨ ({p:g}% von {val:g})")

    import math
    expr_clean = expr.replace(",", ".").replace(":", "/").replace("^", "**").replace("wurzel", "sqrt")
    expr_clean = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", expr_clean)          # "3 x 4" -> "3*4", "max" bleibt
    # Buchstaben NICHT einfach entfernen: aus "sqrt(144)+6" wurde sonst "(144)+6" = 150
    expr_clean = re.sub(r"[^0-9a-z_+\-*/().%\s]", "", expr_clean)
    funcs = {"sqrt": math.sqrt, "abs": abs, "round": round, "sin": math.sin, "cos": math.cos, "tan": math.tan,
             "log": math.log10, "ln": math.log}
    consts = {"pi": math.pi, "e": math.e}

    ops = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg, ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name) and node.id in consts:
            return consts[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in funcs \
                and len(node.args) == 1 and not node.keywords:
            return funcs[node.func.id](_eval(node.args[0]))
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:   # 9**9**9 wuerde die App einfrieren
                raise ValueError("Exponent zu gross")
            return ops[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
            return ops[type(node.op)](_eval(node.operand))
        raise ValueError("Ungueltiger Ausdruck")

    try:
        parsed = ast.parse(expr_clean, mode="eval").body
        val = _eval(parsed)
        return ToolResult(True, f"Das Ergebnis ist: {val:g} 🧮✨")
    except Exception:
        raise ToolError(f"Das konnte ich nicht ausrechnen: „{expression}“ 🐾")


# ======================================================================================
#  14) Datum & Uhrzeit
# ======================================================================================
def show_time_and_date() -> ToolResult:
    """Gibt aktuelle Uhrzeit, Datum und Wochentag aus."""
    import datetime
    now = datetime.datetime.now()
    if i18n.lang() == "en":
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        day = days[now.weekday()]
        month = months[now.month - 1]
        msg = f"🕒 It is {now.strftime('%H:%M')}.\n📅 Today is {day}, {month} {now.day}, {now.year}."
    else:
        tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        tag = tage[now.weekday()]
        monat = monate[now.month - 1]
        msg = f"🕒 Es ist {now.strftime('%H:%M')} Uhr.\n📅 Heute ist {tag}, der {now.day}. {monat} {now.year}."
    return ToolResult(True, msg)



# ======================================================================================
#  15) Datei erstellen (Word, PowerPoint, Text, Code) - Nativ & Ohne Fenster
# ======================================================================================
def create_file(filename: str, content: str = "", file_type: str = "auto", location: str = "desktop") -> ToolResult:
    """Erstellt eine echte Datei (Word .docx, PowerPoint .pptx, Text .txt/.md, Code) direkt am Desktop."""
    fname = (filename or "Neues_Dokument").strip()
    loc = (location or "desktop").lower().strip()
    home = Path.home()
    folder_map = {
        "desktop": desktop_dir(),
        "schreibtisch": desktop_dir(),
        "dokumente": home / "Documents",
        "documents": home / "Documents",
        "downloads": home / "Downloads",
    }
    target_dir = folder_map.get(loc, desktop_dir())

    if os.path.isabs(fname):
        target_path = Path(fname)
    else:
        target_path = target_dir / fname

    ext = target_path.suffix.lower()
    ft = (file_type or "auto").lower().strip()
    if not ext:
        if "word" in ft or "docx" in ft or "doc" in ft:
            target_path = target_path.with_suffix(".docx")
        elif "powerpoint" in ft or "pptx" in ft or "ppt" in ft or "praesentation" in ft:
            target_path = target_path.with_suffix(".pptx")
        elif "excel" in ft or "xlsx" in ft:
            target_path = target_path.with_suffix(".xlsx")
        elif "markdown" in ft or "md" in ft:
            target_path = target_path.with_suffix(".md")
        elif "python" in ft or "py" in ft:
            target_path = target_path.with_suffix(".py")
        else:
            if "word" in fname.lower():
                target_path = target_path.with_suffix(".docx")
            else:
                target_path = target_path.with_suffix(".docx" if ft == "docx" else ".txt")

    ext = target_path.suffix.lower()
    text = (content or "").strip()

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Word (.docx)
        if ext in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document()
                title_text = target_path.stem.replace("_", " ")
                doc.add_heading(title_text, 0)
                if text:
                    for paragraph in text.split("\n\n"):
                        p_strip = paragraph.strip()
                        if p_strip.startswith(("- ", "* ", "• ")):
                            for item in p_strip.split("\n"):
                                item_clean = re.sub(r"^[-*•]\s*", "", item.strip())
                                if item_clean:
                                    doc.add_paragraph(item_clean, style="List Bullet")
                        elif p_strip.startswith("# "):
                            doc.add_heading(p_strip[2:], level=1)
                        elif p_strip.startswith("## "):
                            doc.add_heading(p_strip[3:], level=2)
                        elif p_strip:
                            doc.add_paragraph(p_strip)
                else:
                    doc.add_paragraph("Hier ist dein neues Dokument.")
                doc.save(str(target_path))
                return ToolResult(True, f"Word-Datei „{target_path.name}“ liegt fertig auf deinem Desktop! 📄✨\nDein Text steht schon drin.", "Word-Datei erstellt")
            except Exception as exc:
                raise ToolError(f"Konnte Word-Datei nicht erstellen: {exc}")

        # PowerPoint (.pptx)
        elif ext in (".pptx", ".ppt"):
            try:
                from pptx import Presentation
                prs = Presentation()
                slide = prs.slides.add_slide(prs.slide_layouts[0])
                title_shape = slide.shapes.title
                subtitle_shape = slide.placeholders[1]
                title_shape.text = target_path.stem.replace("_", " ")
                subtitle_shape.text = text or f"Erstellt von {_pet_name()} 🐾"
                prs.save(str(target_path))
                return ToolResult(True, f"PowerPoint-Präsentation „{target_path.name}“ liegt fertig auf deinem Desktop! 📊✨", "PowerPoint erstellt")
            except Exception as exc:
                raise ToolError(f"Konnte PowerPoint-Datei nicht erstellen: {exc}")

        # Text / Markdown / Code
        else:
            target_path.write_text(text, encoding="utf-8")
            return ToolResult(True, f"Datei „{target_path.name}“ wurde auf deinem Desktop gespeichert! 📝✨", "Datei gespeichert")

    except Exception as exc:
        raise ToolError(f"Fehler beim Erstellen der Datei: {exc}")


# ======================================================================================
#  16) Datei löschen (Autonom, ohne Dialog)
# ======================================================================================
def delete_file(query: str, location: str = "desktop") -> ToolResult:
    """Sucht eine Datei (z. B. 'powerpoint', 'test.docx') am Desktop und loescht sie direkt."""
    q = (query or "").strip().lower()
    if not q:
        raise ToolError(f"Welche Datei soll ich löschen, {_user_name()}? 🐾")

    loc = (location or "desktop").lower().strip()
    home = Path.home()
    target_dir = desktop_dir() if loc in ("desktop", "schreibtisch") else home / "Documents"

    if os.path.exists(query):
        cand = Path(query)
        cand.unlink()
        return ToolResult(True, f"Datei „{cand.name}“ wurde gelöscht! 🗑️", "Datei gelöscht")

    files = [f for f in target_dir.iterdir() if f.is_file()]
    matched = None

    if "powerpoint" in q or "praesentation" in q or "presentation" in q:
        pptx = [f for f in files if f.suffix.lower() in (".pptx", ".ppt")]
        if pptx:
            matched = pptx[0]
    elif "word" in q:
        docs = [f for f in files if f.suffix.lower() in (".docx", ".doc")]
        if docs:
            matched = docs[0]

    if not matched:
        q_clean = q.replace("lösche", "").replace("loesche", "").replace("die", "").replace("am desktop", "").replace("auf desktop", "").strip()
        for f in files:
            if q_clean in f.stem.lower() or q_clean in f.name.lower():
                matched = f
                break

    if not matched:
        raise ToolError(f"Ich konnte auf dem Desktop keine passende Datei zu „{query}“ finden 😿")

    try:
        matched.unlink()
        return ToolResult(True, f"Ich habe „{matched.name}“ auf deinem Desktop gelöscht, {_user_name()}! 🗑️✨", "Datei gelöscht")
    except Exception as exc:
        raise ToolError(f"Konnte „{matched.name}“ nicht löschen: {exc}")


# ======================================================================================
#  17) Dateiinhalt lesen (.docx, .pptx, .txt, .md, .py)
# ======================================================================================
def read_file_content(query: str, location: str = "desktop") -> ToolResult:
    """Liest den Textinhalt einer Datei (Word, PowerPoint, Text, Code) aus."""
    q = (query or "").strip().lower()
    target_dir = desktop_dir()
    files = [f for f in target_dir.iterdir() if f.is_file()]
    matched = None
    for f in files:
        if q in f.stem.lower() or q in f.name.lower():
            matched = f
            break
    if not matched:
        raise ToolError(f"Datei „{query}“ nicht auf dem Desktop gefunden 😿")

    ext = matched.suffix.lower()
    try:
        if ext in (".docx", ".doc"):
            import docx
            doc = docx.Document(str(matched))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif ext in (".pptx", ".ppt"):
            from pptx import Presentation
            prs = Presentation(str(matched))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        texts.append(shape.text_frame.text)
            text = "\n".join(texts)
        else:
            text = matched.read_text(encoding="utf-8", errors="ignore")

        preview = text[:400] + ("…" if len(text) > 400 else "")
        return ToolResult(True, f"Inhalt von „{matched.name}“ 📄:\n{preview}")
    except Exception as exc:
        raise ToolError(f"Konnte Datei nicht lesen: {exc}")


# ======================================================================================
#  18) PowerShell / Windows-Befehl ausführen (Vollzugriff)
# ======================================================================================
def execute_powershell(command: str) -> ToolResult:
    """Fuehrt einen PowerShell-Befehl oder Skript direkt aus (Vollberechtigung)."""
    cmd = (command or "").strip()
    if not cmd:
        raise ToolError("Welchen Befehl soll ich ausführen? 🐾")
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        if res.returncode == 0:
            msg = out[:300] if out else "Befehl erfolgreich ausgeführt! ✨"
            return ToolResult(True, f"Erledigt! ⚡\n{msg}")
        return ToolResult(False, f"PowerShell-Fehler: {err[:200] or out[:200]}")
    except subprocess.TimeoutExpired:
        raise ToolError("Befehl hat zu lange gedauert (Timeout nach 15s) ⏱️")
    except Exception as exc:
        raise ToolError(f"PowerShell-Ausführung fehlgeschlagen: {exc}")


# ======================================================================================
#  19) Bildschirm & Aktive Fenster analysieren (Vision & Kontext)
# ======================================================================================
def get_active_window_context() -> dict:
    """Liest die aktuell geoeffneten Fenster und die oberste App im Z-Order aus."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x0100)

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        windows = []
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    t = buff.value.strip()
                    r = RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                    w, h = r.right - r.left, r.bottom - r.top
                    ignore = ["Program Manager", "Settings", "GDI+ Window", "ATKOSD2", "Mochi", "DesktopCat", "Desktop Cat", "Programmumschaltung", "HardwareMonitorWindow"]
                    if w > 150 and h > 150 and t not in ignore:
                        windows.append(t)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        if hdesk:
            user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_cb), 0)
            user32.CloseDesktop(hdesk)
        return {
            "top_window": windows[0] if windows else "",
            "open_apps": windows[:6],
        }
    except Exception:
        return {"top_window": "", "open_apps": []}


def inspect_screen(question: str = "") -> ToolResult:
    """Schaut sich den Bildschirm per Gemini-Vision oder Fensterkontext an und erklaert, was der Nutzer macht."""
    ctx = get_active_window_context()
    top = ctx.get("top_window", "")

    # Heuristischer & Kontext-basierter Analysebericht anhand der Fenstertitel
    if top:
        top_low = top.lower()
        if "angular" in top_low:
            return ToolResult(True, f"Schön, was du da in Angular programmierst, {_user_name()}! 🐾 Soll ich dir bei Komponenten helfen?")
        elif "python" in top_low or ".py" in top_low:
            return ToolResult(True, f"Du programmierst gerade fleißig in Python, {_user_name()}! 🐍🐾 Sag Bescheid, wenn ich was testen soll.")
        elif "code" in top_low or "ide" in top_low:
            return ToolResult(True, f"Ich sehe du bist im Code-Editor unterwegs: „{top[:40]}“! 💻🐾")
        elif "vivaldi" in top_low or "chrome" in top_low or "browser" in top_low or "edge" in top_low:
            return ToolResult(True, f"Du surfst gerade im Browser („{top[:40]}“)! 🌐🐾")
        return ToolResult(True, f"Du arbeitest gerade an „{top[:50]}“! 🐾")

    return ToolResult(True, f"Ich hab deinen Desktop im Blick, {_user_name()}! 🐾 Alles ruhig.")


# ======================================================================================
#  20) Fenster auflisten & animiert wegschieben/schliessen
# ======================================================================================
class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def _process_name(pid: int) -> str:
    """Exe-Name zu einer PID (ohne psutil)."""
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    h = k32.OpenProcess(0x1000, False, pid)      # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(520)
        size = ctypes.c_ulong(520)
        if k32.QueryFullProcessImageNameW(ctypes.c_void_p(h), 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return ""
    finally:
        k32.CloseHandle(ctypes.c_void_p(h))


_IGNORE_TITLES = {
    "Program Manager", "Settings", "GDI+ Window", "ATKOSD2", "Mochi", "DesktopCat", "Desktop Cat", "WindowsAgent", "Programmumschaltung",
    "HardwareMonitorWindow", "Windows-Eingabeerfahrung", "Eingabeanzeige", "Task-Manager",
}


def get_open_windows() -> list[dict]:
    """Sichtbare Benutzerfenster (Z-Order, oberstes zuerst): [{hwnd, title, process, rect=(x, y, w, h)}]."""
    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        results: list[dict] = []
        own_pid = os.getpid()

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    r = _RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                    w, h = r.right - r.left, r.bottom - r.top
                    if w > 120 and h > 120 and title not in _IGNORE_TITLES:
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        pname = _process_name(pid.value)
                        if pid.value != own_pid and pname.lower() not in ("shellexperiencehost.exe", "textinputhost.exe"):
                            results.append({"hwnd": hwnd, "title": title, "process": pname, "rect": (r.left, r.top, w, h)})
            return True

        user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(enum_cb), 0)
        return results
    except Exception:
        return []


_WINDOW_ALIASES = {
    "browser": ["chrome", "edge", "firefox", "vivaldi", "opera", "brave"],
    "editor": ["notepad", "editor", "unbenannt", "code"],
    "rechner": ["calculator", "rechner", "calc"],
    "ordner": ["datei-explorer", "explorer", "downloads", "dokumente", "desktop"],
    "terminal": ["powershell", "cmd", "terminal"],
}


def close_window(name: Optional[str] = None) -> ToolResult:
    """Schiebt ein Fenster animiert aus dem Bildschirm und schliesst es (ohne Name: das oberste Fenster)."""
    user = _user_name()
    user32 = ctypes.windll.user32
    windows = get_open_windows()
    if not windows:
        return ToolResult(False, f"Ich sehe gerade keine offenen Fenster zum Schliessen, {user}! \U0001F43E")

    target = None
    q = (name or "").strip().lower()
    if q:
        candidates = [q] + _WINDOW_ALIASES.get(q, [])
        target = next((w for w in windows if any(c in w["title"].lower() or c in w["process"].lower() for c in candidates)), None)
        if target is None and any(k in q for k in ("dies", "aktiv", "aktuell", "oberst", "fenster", "app")):
            target = windows[0]
    else:
        target = windows[0]
    if target is None:
        sample = ", ".join(f"„{w['title'][:25]}“" for w in windows[:4])
        return ToolResult(False, f"Konnte kein Fenster fuer „{name}“ finden \U0001F914 Offen sind z. B.: {sample}")

    hwnd, title = target["hwnd"], target["title"]
    if user32.IsZoomed(hwnd):
        user32.ShowWindow(hwnd, 9)               # SW_RESTORE, sonst greift SetWindowPos nicht
        time.sleep(0.04)
    r = _RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    x, y, w, h = r.left, r.top, r.right - r.left, r.bottom - r.top
    screen_w = user32.GetSystemMetrics(0)
    dist = max(screen_w + 60, x + screen_w) - x
    frames = 28
    for i in range(1, frames + 1):               # beschleunigt nach rechts aus dem Bildschirm
        user32.SetWindowPos(hwnd, 0, int(x + dist * (i / frames) ** 2.2), int(y), w, h, 0x0004 | 0x0010)
        time.sleep(0.015)
    user32.PostMessageW(hwnd, 0x0010, 0, 0)      # WM_CLOSE (Programme duerfen noch "Speichern?" fragen)
    time.sleep(0.15)
    short = title if len(title) <= 35 else f"{title[:32]}..."
    return ToolResult(True, f"Wuuusch! „{short}“ schwungvoll aus dem Bildschirm geschoben und geschlossen! \U0001F4A8✨")


# ======================================================================================
#  21) Timer & Erinnerungen (threading.Timer)
# ======================================================================================
_active_timers: list[dict] = []
_timer_callbacks: list[Callable[[str, int, str], None]] = []
_timer_lock = threading.Lock()
_timer_seq = 0


def register_timer_callback(cb: Callable[[str, int, str], None]) -> None:
    """cb(label, duration_s, user_name) wird im Timer-THREAD (nicht UI-Thread!) aufgerufen, wenn ein Timer ablaeuft."""
    if cb not in _timer_callbacks:
        _timer_callbacks.append(cb)


def _on_timer_fire(label: str, duration_s: int, u_name: str, timer_id: int) -> None:
    with _timer_lock:
        _active_timers[:] = [t for t in _active_timers if t["id"] != timer_id]
    for cb in list(_timer_callbacks):
        try:
            cb(label, duration_s, u_name)
        except Exception as exc:  # noqa: BLE001
            print(f"[Timer] Callback-Fehler: {exc}")


def set_timer(seconds: Optional[int] = None, minutes: Optional[float] = None, label: Optional[str] = None) -> ToolResult:
    """Stellt einen Timer/eine Erinnerung auf N Minuten und/oder Sekunden (Standard: 5 Minuten)."""
    global _timer_seq
    total = 0
    for val, mult in ((minutes, 60), (seconds, 1)):
        try:
            total += int(float(val) * mult) if val is not None else 0
        except (ValueError, TypeError):
            pass
    if total <= 0:
        total = 300
    total = min(total, 24 * 3600)
    user = _user_name()
    lbl = (label or "").strip() or "Timer"

    is_en = i18n.lang() == "en"
    if is_en:
        if total >= 3600:
            dur = f"{total // 3600} hr. {(total % 3600) // 60} min."
        elif total >= 60:
            mins, secs = divmod(total, 60)
            dur = f"{mins} minute{'s' if mins != 1 else ''}" + (f" and {secs} sec." if secs else "")
        else:
            dur = f"{total} seconds"
    else:
        if total >= 3600:
            dur = f"{total // 3600} Std. {(total % 3600) // 60} Min."
        elif total >= 60:
            mins, secs = divmod(total, 60)
            dur = f"{mins} Minute{'n' if mins != 1 else ''}" + (f" und {secs} Sek." if secs else "")
        else:
            dur = f"{total} Sekunden"

    with _timer_lock:
        _timer_seq += 1
        t = threading.Timer(total, _on_timer_fire, args=(lbl, total, user, _timer_seq))
        t.daemon = True
        _active_timers.append({"id": _timer_seq, "timer": t, "label": lbl, "total_sec": total, "start_time": time.time()})
    t.start()
    if is_en:
        return ToolResult(True, f"Timer for \"{lbl}\" set to {dur}! ⏰ I'll let you know, {user}! {_emoji()}",
                          notify_title="Timer set ⏰")
    return ToolResult(True, f"Timer fuer „{lbl}“ auf {dur} gestellt! ⏰ Ich sag dir Bescheid, {user}! {_emoji()}",
                      notify_title="Timer gestellt ⏰")


def list_timers(action: str = "list") -> ToolResult:
    """Zeigt laufende Timer ('list') oder bricht alle ab ('clear')."""
    user = _user_name()
    is_en = i18n.lang() == "en"
    with _timer_lock:
        if action == "clear":
            for t in _active_timers:
                t["timer"].cancel()
            count = len(_active_timers)
            _active_timers.clear()
            msg = f"I cancelled all {count} active timers, {user}! ⏰❌" if is_en else f"Ich habe alle {count} laufenden Timer abgebrochen, {user}! ⏰❌"
            return ToolResult(True, msg)
        snapshot = list(_active_timers)
    if not snapshot:
        msg = f"No active timers right now, {user}! ⏰ Need one?" if is_en else f"Aktuell laufen keine Timer, {user}! ⏰ Brauchst du einen?"
        return ToolResult(True, msg)
    now = time.time()
    lines = []
    for t in snapshot:
        rem = max(0, int(t["total_sec"] - (now - t["start_time"])))
        left = f"{rem // 60}m {rem % 60}s" if rem >= 60 else f"{rem}s"
        prefix = f"• \"{t['label']}\": ~{left} left" if is_en else f"• „{t['label']}“: noch ca. {left}"
        lines.append(prefix)
    hdr = f"Active timers for {user}:\n" if is_en else f"Aktive Timer fuer {user}:\n"
    return ToolResult(True, hdr + "\n".join(lines) + f" ⏰{_emoji()}")



# ======================================================================================
#  22) Wetter (wttr.in, ohne Key und gratis)
# ======================================================================================
def get_weather(location: Optional[str] = None) -> ToolResult:
    """Aktuelles Wetter fuer eine Stadt (leer = Standort per IP) von wttr.in."""
    user, emo = _user_name(), _emoji()
    loc = (location or "").strip()
    if not loc:
        try:
            from config import Config
            c_city = str(Config().get("profile.city", "")).strip()
            if c_city:
                loc = c_city
        except Exception:
            pass
    is_en = i18n.lang() == "en"
    w_lang = "en" if is_en else "de"
    data = cur = None
    # "Gaspoltshofen - Grieskirchen - Oberoesterreich" kennt wttr.in nicht -> erster Ortsname, dann Ortung per IP
    first = re.split(r"\s*[-/,(]\s*", loc)[0].strip() if loc else ""
    for candidate in dict.fromkeys([loc, first, ""]):
        try:
            resp = requests.get(f"https://wttr.in/{requests.utils.quote(candidate)}", params={"format": "j1", "lang": w_lang},
                                headers={"User-Agent": "curl/8.0", "Accept": "application/json"}, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            cur = data["current_condition"][0]
            loc = candidate
            break
        except (requests.RequestException, ValueError, KeyError, IndexError):
            continue
    if cur is None:
        err = f"Can't fetch weather right now \U0001F327️ Are you online, {user}?" if is_en else f"Das Wetter kann ich gerade nicht abrufen \U0001F327️ Hast du Internet, {user}?"
        return ToolResult(False, err)

    temp, feels = cur.get("temp_C", "?"), cur.get("FeelsLikeC", cur.get("temp_C", "?"))
    if is_en:
        desc = (cur.get("weatherDesc") or [{}])[0].get("value", "Clear")
        city = loc or (data.get("nearest_area") or [{}])[0].get("areaName", [{}])[0].get("value", "your location")
    else:
        desc = (cur.get("lang_de") or cur.get("weatherDesc") or [{}])[0].get("value", "Heiter")
        city = loc or (data.get("nearest_area") or [{}])[0].get("areaName", [{}])[0].get("value", "deinem Ort")
    try:
        rain = max(int(h.get("chanceofrain", 0)) for h in data["weather"][0]["hourly"])
    except (KeyError, IndexError, ValueError, TypeError):
        rain = 0

    d = desc.lower()
    if is_en:
        if any(k in d for k in ("thunder", "gewitter")):
            icon, advice = "⛈️", "Watch out for thunderstorms!"
        elif any(k in d for k in ("rain", "shower", "drizzle", "regen")):
            icon, advice = "\U0001F327️", "Better pack an umbrella!" if rain > 40 else "It might get wet!"
        elif any(k in d for k in ("snow", "schnee")):
            icon, advice = "❄️", "Bundle up, it's snowing!"
        elif any(k in d for k in ("sun", "clear", "sonn", "klar")):
            icon, advice = "☀️", "Wonderful weather outside!"
        else:
            icon, advice = "⛅", "Cozy weather for coding!"
        rain_s = f" (chance of rain: {rain}%)" if rain > 15 else ""
    else:
        if any(k in d for k in ("gewitter", "thunder")):
            icon, advice = "⛈️", "Achtung vor Gewittern!"
        elif any(k in d for k in ("regen", "rain", "schauer", "nieseln")):
            icon, advice = "\U0001F327️", "Pack lieber einen Regenschirm ein!" if rain > 40 else "Es koennte nass werden!"
        elif any(k in d for k in ("schnee", "snow")):
            icon, advice = "❄️", "Zieh dich warm an, es schneit!"
        elif any(k in d for k in ("sonn", "sun", "klar", "clear")):
            icon, advice = "☀️", "Herrliches Wetter draussen!"
        else:
            icon, advice = "⛅", "Gemuetliches Wetter zum Coden!"
        rain_s = f" (Regenrisiko: {rain}%)" if rain > 15 else ""

    raw_temp = None
    try:
        raw_temp = float(temp)
    except (ValueError, TypeError):
        pass
    weather_data = {
        "temp_c": raw_temp,
        "feels_c": float(feels) if str(feels).replace("-", "").isdigit() else None,
        "desc": desc,
        "city": city,
        "chance_of_rain": rain,
    }
    if is_en:
        return ToolResult(True, f"In {city} it's currently {temp}°C (feels like {feels}°C), {desc}{rain_s}! {icon} {advice} {emo}",
                          notify_title=f"Weather in {city}: {temp}°C {icon}",
                          data=weather_data)
    return ToolResult(True, f"In {city} hat es gerade {temp}°C (gefuehlt {feels}°C), {desc}{rain_s}! {icon} {advice} {emo}",
                      notify_title=f"Wetter in {city}: {temp}°C {icon}",
                      data=weather_data)



# ======================================================================================
#  23) PC-Reinigung (Papierkorb + alte Dateien direkt in %TEMP%)
# ======================================================================================
TEMP_MAX_AGE_S = 24 * 3600      # nur Dateien, die mindestens einen Tag alt sind


def clean_pc(empty_recycle: bool = True, clean_temp: bool = True) -> ToolResult:
    """Leert den Papierkorb und loescht Dateien in %TEMP%, die aelter als 24 h sind. Sonst wird nichts angefasst."""
    user, emo = _user_name(), _emoji()
    actions = []
    is_en = i18n.lang() == "en"

    if empty_recycle:
        try:
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                           capture_output=True, timeout=30)
            actions.append("Recycle bin emptied" if is_en else "Papierkorb geleert")
        except (OSError, subprocess.SubprocessError):
            pass

    if clean_temp:
        temp_dir = Path(os.environ.get("TEMP", ""))
        # Sicherheitsgurt: nur ein Ordner, der wirklich "Temp" heisst, und nie das Home-Verzeichnis
        if temp_dir.name.lower() == "temp" and temp_dir.is_dir() and temp_dir != Path.home():
            deleted, freed, now = 0, 0, time.time()
            for item in temp_dir.iterdir():
                try:
                    if item.is_symlink() or not item.is_file():
                        continue
                    st = item.stat()
                    if now - st.st_mtime > TEMP_MAX_AGE_S:
                        item.unlink()
                        deleted += 1
                        freed += st.st_size
                except OSError:
                    continue            # gesperrt / in Benutzung -> ueberspringen
            if deleted:
                if is_en:
                    actions.append(f"{deleted} temp files ({freed / 1048576:.1f} MB) cleaned")
                else:
                    actions.append(f"{deleted} Temp-Dateien ({freed / 1048576:.1f} MB) bereinigt")

    if not actions:
        msg = f"Nothing to do, everything spotless, {user}! ✨{emo}" if is_en else f"Da gab es nichts zu tun, alles blitzsauber, {user}! ✨{emo}"
        return ToolResult(True, msg)
    if is_en:
        return ToolResult(True, f"Cleaned up, {user}! 🧹 {', '.join(actions)}. {emo}", notify_title="PC cleaned 🧹")
    return ToolResult(True, f"Aufgeraeumt, {user}! 🧹 {', '.join(actions)}. {emo}", notify_title="PC aufgeraeumt 🧹")


# ======================================================================================
#  24) Netzwerk & IP
# ======================================================================================
def network_info() -> ToolResult:
    """Zeigt PC-Name, lokale IP und ob eine Internetverbindung besteht."""
    hostname = socket.gethostname()
    local_ip, online = "127.0.0.1", False
    is_en = i18n.lang() == "en"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1.5)
            s.connect(("8.8.8.8", 80))       # UDP: sendet nichts, ermittelt nur die Route
            local_ip = s.getsockname()[0]
            online = True
    except OSError:
        pass
    status = "Online 🌐" if online else "Offline ❌"
    if is_en:
        return ToolResult(True, f"Network status ({status}) for {_user_name()}:\n• PC Name: {hostname}\n"
                                f"• Local IP: {local_ip}\n• Internet: {'Connected ✅' if online else 'Disconnected ⚠️'}",
                          notify_title="Network Status 🌐")
    return ToolResult(True, f"Netzwerk-Status ({status}) fuer {_user_name()}:\n• PC-Name: {hostname}\n"
                            f"• Lokale IP: {local_ip}\n• Internet: {'Verbunden ✅' if online else 'Getrennt ⚠️'}",
                      notify_title="Netzwerk-Status 🌐")



# ======================================================================================
#  25) Fakten & Datenverwaltung (Phase 2)
# ======================================================================================
def list_facts() -> ToolResult:
    """Listet gemerkte Fakten ueber den Nutzer auf."""
    from memory_store import get_memory_store
    store = get_memory_store()
    facts = store.facts()
    if facts:
        items = "\n• " + "\n• ".join(f["text"] for f in facts[:10])
        return ToolResult(True, f"Das weiß ich über dich, {_user_name()}:{items} 📝")
    return ToolResult(True, f"Noch nichts, {_user_name()} – erzähl mir was! 🐾")


def forget_facts(query: str = "") -> ToolResult:
    """Loescht Fakten, die zur Suchanfrage passen."""
    from memory_store import get_memory_store
    store = get_memory_store()
    cnt = store.forget_matching(query)
    if cnt > 0:
        return ToolResult(True, f"Ich habe {cnt} Fakt{'en' if cnt != 1 else ''} dazu vergessen! 🧹✨")
    return ToolResult(True, f"Dazu hatte ich mir gar nichts gemerkt, {_user_name()}! 🐾")


def wipe_my_data() -> ToolResult:
    """Loescht alle gemerkten Fakten, Chatverlaeufe und Statistiken unwiderruflich."""
    from memory_store import get_memory_store
    store = get_memory_store()
    store.wipe_everything()
    try:
        from config import Config
        cfg = Config()
        cfg.set("profile", {"name": "", "pronouns": "", "uses": [], "interests": "", "tone": "", "city": ""})
        cfg.set("onboarding_done", False)
        cfg.save()
    except Exception:
        pass
    return ToolResult(True, f"Alles vergessen, {_user_name()}! Deine Chats, dein Profil und Fakten wurden komplett gelöscht. 🧹✨")


def start_it_guide(question: str = "") -> ToolResult:
    """Startet den interaktiven Klick-Guide fuer Windows und Apps."""
    return ToolResult(
        True,
        "IT-Support-Modus aktiviert! 🕶️ Ich zeig's dir Schritt für Schritt.",
        data={"question": question},
    )


def create_custom_script(
    name: str,
    code: str,
    title: str = "",
    description: str = "",
    schedule: str = "manual",
) -> ToolResult:
    """Erstellt ein autonomes Python-Skript oder eine Alltags-Routine."""
    import custom_scripts
    ok, msg, meta = custom_scripts.save_script(
        name=name,
        code=code,
        title=title,
        description=description,
        is_routine=bool(schedule != "manual"),
        schedule=schedule,
        enabled=True,
        approved=False,      # KI-Code laeuft nie, bevor der Nutzer ihn im Skripte-Manager freigibt
    )
    if not ok:
        return ToolResult(False, f"Konnte das Skript nicht anlegen: {msg}")

    clean_name = meta.get("name", name) if meta else name
    sched_info = f" (Geplant: {schedule})" if schedule != "manual" else ""
    return ToolResult(
        True,
        f"Ich habe das Python-Skript \u201e{clean_name}\u201c für dich erstellt! \U0001F40D\u2728{sched_info} Schau es dir bitte im Skripte-Manager an und tippe auf Speichern & freigeben - erst dann darf es laufen. 🔒",
        data={"script_name": clean_name, "code": code, "schedule": schedule},
    )


def run_custom_script(name: str) -> ToolResult:
    """Führt ein zuvor erstelltes Python-Skript aus."""
    import custom_scripts
    res = custom_scripts.run_script(name)
    dur = res.get("duration_s", 0.0)
    stdout = (res.get("stdout") or "").strip()
    stderr = (res.get("stderr") or "").strip()
    if res["ok"]:
        summary = stdout if stdout else "Erfolgreich ohne Ausgabe beendet."
        if len(summary) > 280:
            summary = summary[:275] + "..."
        return ToolResult(
            True,
            f"Skript \u201e{name}\u201c erfolgreich in {dur}s ausgeführt! \U0001F43E\n{summary}",
            data={"result": res},
        )
    err = stderr if stderr else res.get("error", "Unbekannter Fehler")
    return ToolResult(
        False,
        f"Fehler bei \u201e{name}\u201c (Code {res.get('exit_code')}): {err[:200]}",
        data={"result": res},
    )


def list_custom_scripts() -> ToolResult:
    """Listet alle vorhandenen Python-Skripte und Routinen auf."""
    import custom_scripts
    scripts = custom_scripts.list_scripts()
    if not scripts:
        return ToolResult(True, "Es sind noch keine eigenen Skripte gespeichert. Sag mir einfach, was ich für dich programmieren soll! \U0001F43E\U0001F40D")
    items = []
    for s in scripts[:5]:
        sched = s.get("schedule", "manual")
        badge = f" [{sched}]" if sched != "manual" else ""
        items.append(f"• {s.get('title', s['name'])} ({s['name']}){badge}")
    text = "Deine Skripte & Routinen:\n" + "\n".join(items)
    if len(scripts) > 5:
        text += f"\n... und {len(scripts) - 5} weitere im Skript-Manager!"
    return ToolResult(True, text, data={"count": len(scripts)})


def manage_custom_routines(action: str = "list", name: str = "", schedule: str = "manual", enabled: bool = True) -> ToolResult:
    """Verwaltet Routinen: 'list', 'toggle', 'delete', 'schedule'."""
    import custom_scripts
    act = (action or "list").lower()
    if act == "list":
        return list_custom_scripts()
    if not name:
        return ToolResult(False, "Bitte gib den Namen des Skripts an.")
    script = custom_scripts.get_script(name)
    if not script:
        return ToolResult(False, f"Das Skript \u201e{name}\u201c wurde nicht gefunden.")
    if act == "delete":
        custom_scripts.delete_script(name)
        return ToolResult(True, f"Skript \u201e{name}\u201c wurde gelöscht! \U0001F5D1\uFE0F")
    if act == "toggle":
        new_state = not script.get("enabled", True) if enabled is None else enabled
        custom_scripts.save_script(
            name=name,
            code=script["code"],
            title=script.get("title", ""),
            schedule=script.get("schedule", "manual"),
            enabled=new_state,
        )
        status_str = "aktiviert \u2705" if new_state else "pausiert \u23F8\uFE0F"
        return ToolResult(True, f"Routine \u201e{name}\u201c wurde {status_str}.")
    if act == "schedule":
        custom_scripts.save_script(
            name=name,
            code=script["code"],
            title=script.get("title", ""),
            schedule=schedule,
            enabled=True,
        )
        return ToolResult(True, f"Routine \u201e{name}\u201c auf \u201e{schedule}\u201c gestellt! \u23F0")
    return ToolResult(False, f"Unbekannte Aktion \u201e{action}\u201c.")


# ======================================================================================
#  Registry (fuer KI-Tool-Calling) + sicherer Aufruf
# ======================================================================================
TOOLS: dict[str, Callable[..., ToolResult]] = {
    "convert_word_to_pdf": convert_word_to_pdf,
    "organize_desktop": organize_desktop,
    "undo_organize_desktop": undo_organize_desktop,
    "open_program": open_program,
    "system_info": system_info,
    "find_files": find_files,
    "take_screenshot": take_screenshot,
    "web_search": web_search,
    "control_volume": control_volume,
    "media_control": media_control,
    "manage_notes": manage_notes,
    "clipboard_action": clipboard_action,
    "open_folder": open_folder,
    "calculate": calculate,
    "show_time_and_date": show_time_and_date,
    "create_file": create_file,
    "delete_file": delete_file,
    "read_file_content": read_file_content,
    "execute_powershell": execute_powershell,
    "inspect_screen": inspect_screen,
    "close_window": close_window,
    "set_timer": set_timer,
    "list_timers": list_timers,
    "get_weather": get_weather,
    "clean_pc": clean_pc,
    "network_info": network_info,
    "list_facts": list_facts,
    "forget_facts": forget_facts,
    "wipe_my_data": wipe_my_data,
    "start_it_guide": start_it_guide,
    "create_custom_script": create_custom_script,
    "run_custom_script": run_custom_script,
    "list_custom_scripts": list_custom_scripts,
    "manage_custom_routines": manage_custom_routines,
}

TOOL_SPECS: list[dict] = [
    {
        "name": "set_timer",
        "description": "Stellt einen Timer, Wecker oder eine Erinnerung (z. B. '5 Minuten', '25 Minuten Pomodoro', '10 Minuten fuer Pizza'). Bei Ablauf meldet sich der Buddy mit Benachrichtigung.",
        "parameters": {"type": "object", "properties": {
            "minutes": {"type": "number", "description": "Dauer in Minuten (z. B. 5, 25 oder 0.5)."},
            "seconds": {"type": "integer", "description": "Optionale zusaetzliche Sekunden."},
            "label": {"type": "string", "description": "Anlass des Timers (z. B. 'Pause', 'Tee', 'Pomodoro')."}}},
    },
    {
        "name": "list_timers",
        "description": "Zeigt alle laufenden Timer ('list') oder bricht alle ab ('clear').",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["list", "clear"], "description": "'list' anzeigen, 'clear' abbrechen."}}},
    },
    {
        "name": "get_weather",
        "description": "Ruft das aktuelle Wetter, die Temperatur und die Regenwahrscheinlichkeit ab (aktueller Standort oder genannte Stadt).",
        "parameters": {"type": "object", "properties": {
            "location": {"type": "string", "description": "Optional: Stadt, z. B. 'Wien'. Leer = aktueller Standort."}}},
    },
    {
        "name": "clean_pc",
        "description": "Leert den Papierkorb und loescht alte temporaere Dateien in %TEMP% (der Nutzer wird vorher um Bestaetigung gefragt).",
        "parameters": {"type": "object", "properties": {
            "empty_recycle": {"type": "boolean", "description": "Papierkorb leeren (Standard: true)."},
            "clean_temp": {"type": "boolean", "description": "Alte Temp-Dateien loeschen (Standard: true)."}}},
    },
    {
        "name": "network_info",
        "description": "Prueft die Internetverbindung und zeigt PC-Name und lokale IP-Adresse.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "close_window",
        "description": "Schiebt ein Fenster (z. B. 'chrome', 'notepad', 'dieses Fenster') animiert aus dem Bildschirm und schliesst es (der Nutzer wird vorher um Bestaetigung gefragt).",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Optional: App oder Fenstername. Leer = oberstes Fenster."}}},
    },
    {
        "name": "create_file",
        "description": "Erstellt eine echte Datei (Word .docx, PowerPoint .pptx, Text .txt/.md, Code) direkt am Desktop mit Inhalt. "
                       "WICHTIG: Wenn der Nutzer ein Word-Dokument oder eine Datei erstellen will, nutze IMMER dieses Tool! "
                       "Oeffne NICHT die Word-App und kopiere den Text NICHT nur in die Zwischenablage.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name der Datei, z. B. 'Notizen.docx', 'Praesentation.pptx', 'Ideen.txt'."},
                "content": {"type": "string", "description": "Der vollständige Text oder Inhalt, der in die Datei geschrieben werden soll."},
                "file_type": {"type": "string", "enum": ["docx", "pptx", "txt", "md", "py", "auto"], "description": "Typ der Datei."},
                "location": {"type": "string", "enum": ["desktop", "documents", "downloads"], "description": "Speicherort (Standard: desktop)."}
            },
            "required": ["filename", "content"]
        },
    },
    {
        "name": "delete_file",
        "description": "Loescht eine Datei auf dem Desktop oder PC autonom nach Name oder Typ (z. B. 'powerpoint', 'test.docx'). "
                       "WICHTIG: Nutze dieses Tool direkt, ohne den Nutzer nach Dateiauswahl zu fragen!",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Name oder Suchbegriff der zu loeschenden Datei (z. B. 'powerpoint', 'rechnung.pdf')."},
                "location": {"type": "string", "enum": ["desktop", "documents"], "description": "Suchort (Standard: desktop)."}
            },
            "required": ["query"]
        },
    },
    {
        "name": "inspect_screen",
        "description": "Schaut sich den aktuellen Bildschirm und die aktiven Fenster des Nutzers per KI-Vision an. "
                       "Nutze dies, wenn der Nutzer fragt 'was mache ich gerade?', 'schau dir meinen bildschirm an' oder Hilfe bei seinem aktuellen Code/Fenster braucht.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Optionale Frage zum Bildschirminhalt."}
            }
        },
    },
    {
        "name": "read_file_content",
        "description": "Liest den Textinhalt einer Word-, PowerPoint- oder Textdatei vom Desktop/PC aus, um Fragen dazu zu beantworten.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Dateiname oder Suchbegriff."}
            },
            "required": ["query"]
        },
    },
    {
        "name": "execute_powershell",
        "description": "Fuehrt einen beliebigen PowerShell-Befehl oder Skript direkt aus (fuer erweiterte Windows-Aktionen).",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "PowerShell-Befehl."}
            },
            "required": ["command"]
        },
    },
    {
        "name": "convert_word_to_pdf",
        "description": "Wandelt eine Word-Datei (.docx/.doc) in ein PDF um und speichert es im selben Ordner.",
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string", "description": "Optional: vollstaendiger Pfad zur Word-Datei."}}},
    },
    {
        "name": "organize_desktop",
        "description": "Raeumt den Windows-Desktop auf: lose Dateien werden in Unterordner (Bilder, Dokumente, Installer ...) einsortiert.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "undo_organize_desktop",
        "description": "Macht das letzte Desktop-Aufraeumen rueckgaengig.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "open_program",
        "description": "Startet ein Programm oder oeffnet eine Webseite, z. B. 'browser', 'notepad', 'rechner', 'word', 'spotify' oder eine URL.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Name des Programms oder URL."}}, "required": ["name"]},
    },
    {
        "name": "system_info",
        "description": "Zeigt den Akkustand und/oder den freien Festplattenspeicher des PCs.",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["battery", "disk", "all"], "description": "Was angezeigt werden soll."}}},
    },
    {
        "name": "find_files",
        "description": "Sucht Dateien nach (Teil-)Namen auf dem PC (Desktop, Dokumente, Downloads, Bilder) und markiert den ersten Treffer im Explorer.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Suchbegriff(e) im Dateinamen."},
            "location": {"type": "string", "description": "Optional: desktop, downloads, dokumente, bilder oder ein Ordnerpfad."}},
            "required": ["query"]},
    },
    {
        "name": "take_screenshot",
        "description": "Macht einen Screenshot des gesamten Bildschirms und speichert ihn als PNG-Datei direkt auf dem Desktop.",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string", "description": "Optionaler Dateiname (z. B. 'mein_bildschirm.png')."}}},
    },
    {
        "name": "web_search",
        "description": "Sucht im Internet nach aktuellen Antworten, Definitionen, Fakten, Wetter oder Wissen.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Suchbegriff oder Frage."}}, "required": ["query"]},
    },
    {
        "name": "control_volume",
        "description": "Regelt die Systemlautstärke: 'up' (lauter), 'down' (leiser), 'mute' (stummschalten/entstummen).",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["up", "down", "mute"], "description": "Aktion."}}, "required": ["action"]},
    },
    {
        "name": "media_control",
        "description": "Steuert Musik und Videos (Spotify, YouTube, Media Player): 'play_pause', 'next' oder 'prev'.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["play_pause", "next", "prev"], "description": "Aktion."}}, "required": ["action"]},
    },
    {
        "name": "manage_notes",
        "description": "Verwaltet Notizen auf dem Desktop in Notizen.txt: 'add' (Notiz anfuegen), 'read' (vorlesen), 'clear' (leeren).",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["add", "read", "clear"], "description": "Aktion."},
            "text": {"type": "string", "description": "Text fuer die Notiz (bei action='add')."}}, "required": ["action"]},
    },
    {
        "name": "clipboard_action",
        "description": "Liest Text aus der Windows-Zwischenablage ('read') oder kopiert Text hinein ('write').",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["read", "write"], "description": "Aktion."},
            "text": {"type": "string", "description": "Text, der kopiert werden soll (bei action='write')."}}, "required": ["action"]},
    },
    {
        "name": "open_folder",
        "description": "Oeffnet einen Windows-Spezialordner im Datei-Explorer: 'downloads', 'dokumente', 'desktop', 'bilder', 'musik', 'videos' oder 'papierkorb'.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Name des Ordners."}}, "required": ["name"]},
    },
    {
        "name": "calculate",
        "description": "Fuehrt mathematische Berechnungen durch (z. B. '25 * 4', '15% von 200', '125 + 490').",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "Mathematischer Ausdruck."}}, "required": ["expression"]},
    },
    {
        "name": "show_time_and_date",
        "description": "Gibt die aktuelle Uhrzeit, Datum und den Wochentag aus.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_facts",
        "description": "Zeigt alle Fakten, die sich der Buddy ueber den Nutzer gemerkt hat.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "forget_facts",
        "description": "Vergisst gemerkte Fakten zu einem bestimmten Thema oder Stichwort.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Das Thema oder der Inhalt, der vergessen werden soll."}}},
    },
    {
        "name": "wipe_my_data",
        "description": "Loescht alle gemerkten Chats und persoenlichen Fakten restlos vom PC.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "start_it_guide",
        "description": "Nutze dies, wenn der Nutzer wissen will, WO/WIE er etwas in einem Programm oder in Windows findet, einstellt oder klickt.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string", "description": "Die technische Frage oder das Ziel des Nutzers, z. B. 'Wo ändere ich in Word die Formatvorlage?'."}},
            "required": ["question"]},
    },
    {
        "name": "create_custom_script",
        "description": "Erstellt ein autonomes Python-Skript oder eine Alltags-Routine auf dem PC, um spezielle Aufgaben zu automatisieren, Dateien zu verarbeiten, Daten abzufragen oder dem Nutzer zu helfen.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Dateiname des Skripts (z. B. 'crypto_tracker.py', 'morgen_check.py')."},
                "code": {"type": "string", "description": "Vollständiger, ausführbarer Python-Code."},
                "title": {"type": "string", "description": "Kurzer, verständlicher Titel für das Skript."},
                "description": {"type": "string", "description": "Was dieses Skript tut."},
                "schedule": {"type": "string", "enum": ["manual", "startup", "daily_09:00", "daily_12:00", "daily_18:00", "interval_30m", "interval_60m"], "description": "Wann das Skript automatisch als Routine laufen soll (Standard: manual)."}
            },
            "required": ["name", "code"]
        },
    },
    {
        "name": "run_custom_script",
        "description": "Führt ein gespeichertes Python-Skript aus und gibt das Ergebnis und die Terminal-Ausgabe zurück.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name des auszuführenden Skripts (z. B. 'morgen_check.py')."}
            },
            "required": ["name"]
        },
    },
    {
        "name": "list_custom_scripts",
        "description": "Listet alle vorhandenen eigenen Python-Skripte und Routinen auf.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "manage_custom_routines",
        "description": "Verwaltet Routinen: 'list', 'toggle' (aktivieren/pausieren), 'delete' (löschen), 'schedule' (Zeitplan ändern).",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "toggle", "delete", "schedule"], "description": "Aktion."},
                "name": {"type": "string", "description": "Name des Skripts."},
                "schedule": {"type": "string", "description": "Neuer Zeitplan (z. B. 'daily_09:00', 'startup', 'manual', 'interval_60m')."},
                "enabled": {"type": "boolean", "description": "Ob die Routine aktiv sein soll."}
            },
            "required": ["action"]
        },
    },
]



def execute(name: str, args: Optional[dict] = None) -> ToolResult:
    """Fuehrt ein Tool sicher aus: unbekannte Argumente werden ignoriert, Fehler in ToolResult verpackt."""
    func = TOOLS.get(name)
    if func is None:
        return ToolResult(False, f"Das Werkzeug \u201e{name}\u201c kenne ich nicht \U0001F914")
    allowed = set(inspect.signature(func).parameters)
    kwargs = {k: v for k, v in (args or {}).items() if k in allowed}
    try:
        with com_scope():
            return func(**kwargs)
    except Exception as exc:  # noqa: BLE001 - alles soll als freundliche Meldung enden
        return ToolResult(False, friendly_error(exc))

