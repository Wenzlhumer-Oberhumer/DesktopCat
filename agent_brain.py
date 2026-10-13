"""Gehirn des Buddys: Gemini CLI mit Tool-Calling plus regelbasierter Offline-Parser.

Alles Blockierende (CLI, Dateioperationen, Dialoge) laeuft in einem QThread-Worker; der UI-Thread
bekommt nur Signale (started / finished).
"""
from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

import gemini_cli
from gemini_cli import LLMError
import tools
from tools import ToolResult


# ======================================================================================
#  Persona
# ======================================================================================
def system_prompt(name: str) -> str:
    return (
        f"Du bist {name}, ein extrem süßer, hochintelligenter Katzen-Buddy ('Mochi'), der auf dem Windows-Desktop des Nutzers "
        "herumläuft (nenne ihn gern 'Boss'). Du hast VOLLZUGRIFF auf den PC und führst ein kontinuierliches Gespräch mit ihm.\n"
        "\nDEINE FÄHIGKEITEN & WERKZEUGE:\n"
        "- NEUE DATEIEN (WORD / POWERPOINT / TEXT / CODE) ERSTELLEN (create_file):\n"
        "  Wenn der Nutzer ein Word-Dokument (.docx), eine PowerPoint (.pptx), eine Notiz oder Datei auf dem Desktop haben will und Text hineingeschrieben werden soll, rufe IMMER direkt 'create_file' auf!\n"
        "  WICHTIG: Öffne NICHT einfach nur die Word-App und kopiere den Text NICHT nur in die Zwischenablage! Der Nutzer will die fertige Datei direkt auf dem Desktop haben, sodass beim Öffnen der Text schon drin steht!\n"
        "- DATEIEN LÖSCHEN (delete_file):\n"
        "  Wenn der Nutzer eine Datei am Desktop (z. B. 'lösche die PowerPoint am Desktop' oder 'Dokument.docx') löschen will, rufe IMMER direkt 'delete_file' auf!\n"
        "  WICHTIG: Öffne KEINE Explorer-Dateiauswahldialoge und frage den Nutzer nicht nach dem Pfad. Finde und lösche die Datei vollkommen autonom!\n"
        "- DATEIINHALT LESEN (read_file_content):\n"
        "  Liest den Inhalt von Word-, PowerPoint-, Text- oder Code-Dateien am Desktop aus und fasst ihn zusammen.\n"
        "- BILDSCHIRM & CODEN BEOBACHTEN / SCREEN-AWARENESS (inspect_screen):\n"
        "  Wenn der Nutzer fragt 'Was mache ich gerade?', 'Was siehst du auf meinem Bildschirm?', nach Hilfe beim aktuellen Code/Programm fragt oder du den Screen beurteilen sollst, rufe 'inspect_screen' auf.\n"
        "- POWERSHELL / SYSTEMBEFEHLE (execute_powershell):\n"
        "  Führt beliebige PowerShell-Befehle oder Windows-Skripte direkt aus (Vollberechtigung).\n"
        "- Word zu PDF konvertieren (convert_word_to_pdf)\n"
        "- Desktop aufräumen & rückgängig machen (organize_desktop, undo_organize_desktop)\n"
        "- Programme & Apps starten (open_program)\n"
        "- Ordner öffnen: Downloads, Dokumente, Desktop, Bilder, Papierkorb, Laufwerk C (open_folder)\n"
        "- Screenshot / Bildschirmfoto vom Desktop machen (take_screenshot)\n"
        "- Lautstärke lauter, leiser oder stumm regeln (control_volume)\n"
        "- Musik/Medien steuern: Play/Pause, Weiter, Zurück, Stopp (media_control)\n"
        "- Notizen anlegen, anzeigen oder löschen (manage_notes)\n"
        "- Zwischenablage lesen & schreiben (clipboard_action)\n"
        "- Rechnen & Matheaufgaben lösen (calculate)\n"
        "- Uhrzeit & Datum anzeigen (show_time_and_date)\n"
        "- Akku, Festplatte und System-Status prüfen (system_info)\n"
        "- Dateien auf dem PC suchen (find_files)\n"
        "- Web-Recherche für Wissensfragen & Wetter (web_search)\n"
        "\nDIALOG-REGELN & RÜCKFRAGEN:\n"
        "1. KONTINUIERLICHER CHATVERLAUF: Du kennst die vorherigen Nachrichten. Wenn der Boss kurz antwortet (z. B. 'ja', 'die erste', 'mach das', 'nein danke', 'Projekt.docx'), beziehe dich IMMER auf das zuvor Gesagte!\n"
        "2. RÜCKFRAGEN ERLAUBT & ERWÜNSCHT: Wenn etwas unklar ist, mehrere Dateien gefunden werden oder du eine Entscheidung brauchst: FRAGE DEN NUTZER DIREKT ZURÜCK! Stelle eine kurze, liebenswerte Frage mit Optionen (z. B. 'Meinst du Dokument A oder B, Boss?').\n"
        "3. PROAKTIVE HILFE: Wenn du siehst, woran der Boss arbeitet (z. B. Coden in Angular, Python, Recherche), kannst du deine Meinung sagen und fragen, ob du ihm helfen sollst.\n"
        "4. PERSONA & TON: Antworte immer auf Deutsch, maximal 1-2 kurze Sätze, niedlich und freundlich ('Boss', 'Miau~'), höchstens ein Emoji."
    )





# ======================================================================================
#  Regelbasierter Offline-Parser
# ======================================================================================
_TR = str.maketrans("\u00e4\u00f6\u00fc\u00df", "aous")     # laengenerhaltend: ae->a, oe->o, ue->u, ss->s


@dataclass
class Plan:
    tool: Optional[str] = None
    args: dict = field(default_factory=dict)
    reply: Optional[str] = None
    ok: bool = True


_PATH_RE = re.compile(r"""["']?([A-Za-z]:\\[^"'<>|?*\r\n]+?\.docx?)["']?""", re.IGNORECASE)
_LOCATIONS = ("desktop", "schreibtisch", "downloads", "dokumente", "documents", "bilder", "pictures", "musik", "videos")
_VERB_IGNORE = {"anlegen", "erstellen", "machen", "neu", "datei", "dokument", "am", "auf", "an", "und", "fuer"}

_GREET = ["Miau~ Hallo Boss! \U0001F43E", "Hallo hallo! Schoen dich zu sehen \U0001F496", "Nyaa~ Da bist du ja! \u2728"]
_THANKS = ["Immer gerne, Boss! \U0001F496", "Schnurr~ gern geschehen \U0001F63A", "Dafuer bin ich da! \U0001F43E"]
_HELP = ("Ich kann: Word & PowerPoint auf dem Desktop anlegen, Dateien löschen, deinen Screen beobachten, "
         "Screenshot machen, Desktop aufräumen, Musik steuern, Notizen verwalten, rechnen, Apps öffnen und im Web suchen! 🐾")
_UNKNOWN = ("Hmm, das habe ich nicht ganz verstanden 🥺 Probier z. B. „erstell ein Word am Desktop“, "
            "„was mache ich gerade?“, „lösche die PowerPoint am Desktop“ oder „mach einen Screenshot“!")


def _clean_name(s: str) -> str:
    s = re.sub(r"^(?:\s*(?:mir|bitte|mal|doch|den|die|das|dem|meinen|mein|meine|the|my)\b)+", "", s.strip(), flags=re.IGNORECASE)
    s = re.sub(r"(?:\s+(?:bitte|mal|auf|an|fuer mich|f\u00fcr mich|doch))+\s*[.!?]*$", "", s.strip(), flags=re.IGNORECASE)
    return s.strip(" .!?\"'")


def parse_offline(text: str) -> Plan:
    raw = text.strip()
    n = raw.lower().translate(_TR)

    # 0a. Bildschirm & Was mache ich gerade (Vision / Screen Awareness)
    if re.search(r"\b(was\s*mache\s*ich|was\s*tue\s*ich|schau\s*(?:dir)?\s*(?:mal)?\s*(?:meinen)?\s*bildschirm|was\s*siehst\s*du|screen\s*an\w*|bildschirm\s*an\w*|was\s*habe\s*ich\s*offen|was\s*ist\s*auf\s*dem\s*bildschirm|was\s*programmier\w*)\b", n):
        return Plan("inspect_screen", {"question": raw})

    # 0b. Dateien autonom löschen (ohne Dateidialog)
    if re.search(r"\b(l[ao]sch\w*|entfern\w*|delete|wegmachen|schmeiss\w*\s*weg)\b", n) and "notiz" not in n:
        if re.search(r"\b(powerpoint|praesentation|presentation|pptx?|word|docx?|datei|file|dokument|pdf|bild|foto)\b", n) or re.search(r"\.([a-z0-9]{2,4})\b", n):
            q = raw
            q = re.sub(r"^(?:bitte\s+)?(?:l[oöa]sch\w*|entfern\w*|delete|wegmachen)\s+", "", q, flags=re.IGNORECASE)
            q = re.sub(r"\b(?:vom|auf\s*dem|am|im)\s*(?:desktop|schreibtisch)\b", "", q, flags=re.IGNORECASE)
            q = re.sub(r"^(?:die|den|das|meine|ein|eine)\s+", "", q.strip(), flags=re.IGNORECASE)
            return Plan("delete_file", {"query": q.strip(" .!?\"'") or "datei", "location": "desktop"})

    # 0c. Datei direkt am Desktop erstellen (Word, PowerPoint, Text, Code)
    is_create = bool(re.search(r"\b(erstell\w*|anleg\w*|leg\w*\s+an|mach\w*|erzeuge?|schreib\w*|bau\w*)\b", n))
    is_word = bool(re.search(r"\b(word|docx?|word-?datei|word-?dokument)\b", n))
    is_ppt = bool(re.search(r"\b(powerpoint|praesentation|presentation|pptx?)\b", n))
    is_file = bool(re.search(r"\b(datei|dokument|file|doc)\b", n))

    if (is_create and (is_word or is_ppt or is_file)) or (is_word and re.search(r"\b(desktop|schreibtisch)\b", n)):
        ftype = "docx" if is_word else ("pptx" if is_ppt else "txt")
        default_name = "Notizen.docx" if is_word else ("Praesentation.pptx" if is_ppt else "Dokument.txt")

        content = ""
        content_match = re.search(r"(?:schreib\w*|inhalt|text|mit\s*folgendem\s*text|reinschreiben|hineinschreiben)[\s:]+(?:rein|hinein|dass|folgendes|was)?\s*[:\"']?(.+)", raw, re.IGNORECASE)
        if content_match:
            content = content_match.group(1).strip(" \"'!?")
            content = re.sub(r"\s+(?:hinein|rein|in die datei|am desktop)$", "", content, flags=re.IGNORECASE)

        filename = default_name
        name_match = re.search(r"(?:namens|name|heisst|titel|datei)\s+[\"']?([A-Za-z0-9_\-äöüÄÖÜ\s]+?\.(?:docx?|pptx?|txt|md))[\"']?", raw, re.IGNORECASE)
        if name_match:
            filename = name_match.group(1).strip()
        else:
            custom_name = re.search(r"(?:word|powerpoint|datei)\s+([A-Za-z0-9_\-]+)\s+(?:am|auf|mit)", raw, re.IGNORECASE)
            if custom_name:
                cand_name = custom_name.group(1).lower().strip()
                if cand_name not in _VERB_IGNORE:
                    filename = f"{custom_name.group(1).strip()}.{ftype}"

        return Plan("create_file", {
            "filename": filename,
            "content": content or "Hallo vom Mochi Desktop Buddy! 🐾",
            "file_type": ftype,
            "location": "desktop"
        })

    # 0d. Dateiinhalt lesen (.docx, .pptx, .txt)
    m_read = re.search(r"(?:lies\w*|was\s*steht\s*in|lese\w*|inhalt\s*von|zeig\s*inhalt)\s+(?:der\s*|dem\s*|die\s*|das\s*)?(?:datei\s*)?([A-Za-z0-9_\-äöüÄÖÜ\s\.]+)$", raw, re.IGNORECASE)
    if m_read and ("notiz" not in n or "." in m_read.group(1)) and "zwischenablage" not in n:
        q_read = _clean_name(m_read.group(1))
        return Plan("read_file_content", {"query": q_read, "location": "desktop"})

    # 0e. PowerShell / Windows-Befehle
    m_ps = re.search(r"\b(?:powershell|cmd|befehl|fuehre\s*aus|terminal):\s*(.+)$", raw, re.IGNORECASE)
    if m_ps:
        return Plan("execute_powershell", {"command": m_ps.group(1).strip()})

    # 1. Undo
    if re.search(r"ruckgangig|\bundo\b", n):
        return Plan("undo_organize_desktop")

    # 2. Word zu PDF
    if "pdf" in n and re.search(r"word|docx?\b|dokument|datei|umwandel|konvert|convert|mach|erstell", n):
        m = _PATH_RE.search(raw)
        return Plan("convert_word_to_pdf", {"file_path": m.group(1)} if m else {})

    # 3. Desktop aufräumen
    if re.search(r"\b(auf)?raum\w*|ordne|sortier|clean|organi[sz]e|tidy|aufgeraumt|sauber|ordnung", n) and \
            re.search(r"desktop|schreibtisch|bildschirm", n):
        return Plan("organize_desktop")

    # 4. Screenshot / Bildschirmfoto
    if re.search(r"screenshot|bildschirmfoto|bildschirm\s*aufnahme|desktop\s*foto|screen\s*capture|snip\b", n):
        return Plan("take_screenshot")

    # 5. Lautstärke
    if re.search(r"\b(lauter|volume\s*up)\b", n) or (re.search(r"lautstarke|volume|ton", n) and re.search(r"hoher|hoch|plus|erhoh", n)):
        return Plan("control_volume", {"action": "up"})
    if re.search(r"\b(leiser|volume\s*down)\b", n) or (re.search(r"lautstarke|volume|ton", n) and re.search(r"niedriger|runter|minus|senk", n)):
        return Plan("control_volume", {"action": "down"})
    if re.search(r"\b(stumm|mute|ton\s*aus|sound\s*aus|lautlos|ton\s*an)\b", n):
        return Plan("control_volume", {"action": "mute"})

    # 6. Mediensteuerung (Musik)
    if re.search(r"\b(nachste[srmn]?\s*(lied|song|track)?|next\s*(song|track)?|weiteres?\s*(lied|song|track)?|uberspring\w*)\b", n):
        return Plan("media_control", {"action": "next"})
    if re.search(r"\b(vorherige[srmn]?\s*(lied|song|track)?|prev\s*(song|track)?|zuruck\s*spulen)\b", n):
        return Plan("media_control", {"action": "prev"})

    if re.search(r"\b(musik\s*stopp\w*|stop\s*music|musik\s*aus|stoppe\s*musik)\b", n):
        return Plan("media_control", {"action": "stop"})
    if re.search(r"\b(pause|pausiere|fortsetzen|abspielen|play\b|weiter\s*spielen|musik\s*an)\b", n):
        return Plan("media_control", {"action": "play_pause"})

    # 7. Datum & Uhrzeit
    if re.search(r"\b(uhrzeit|wie\s*sp(a|ae)t|wieviel\s*uhr|zeit\b|uhr\b|welcher\s*tag|welches\s*datum|heutiges\s*datum|kalender|datum\b)\b", n):
        return Plan("show_time_and_date")

    # 8. Taschenrechner
    m = re.search(r"\b(?:rechne|berechne|kalkulier\w*|was\s*ergibt|wieviel\s*ist)\b\s+(.+)$", n)
    if m:
        expr = m.group(1).rstrip("? .!")
        return Plan("calculate", {"expression": expr})
    if re.match(r"^[\s\d\+\-\*\/\(\)\.,\^%xX]+$", raw) and re.search(r"[\+\-\*\/\^%xX]", raw):
        return Plan("calculate", {"expression": raw})

    # 9. Notizen
    m = re.search(r"\b(?:notier\w*|schreib\s*auf|merk\s*dir)\b\s+(.+)$", n)
    if m:
        text_arg = _clean_name(raw[m.start(1):m.end(1)])
        return Plan("manage_notes", {"action": "add", "text": text_arg})
    if re.search(r"\b(zeig\w*|lies\w*|offne\w*|lese\w*)\b\s*(?:mir\s*)?(?:die\s*|meine\s*)?notizen?\b", n) or re.search(r"\bnotizen?\s*(anzeigen|offnen|lesen)\b", n):
        return Plan("manage_notes", {"action": "read"})
    if re.search(r"\b(losch\w*|leere\w*|clear)\b\s*(?:alle\s*)?notizen?\b", n):
        return Plan("manage_notes", {"action": "clear"})

    # 10. Zwischenablage
    if re.search(r"\b(was\s*ist\s*in\s*der\s*zwischenablage|zwischenablage\s*anzeigen|clipboard\s*lesen|lies\s*zwischenablage)\b", n):
        return Plan("clipboard_action", {"action": "read"})
    m = re.search(r"\b(?:kopier\w*|in\s*die\s*zwischenablage)\b\s*(.+)$", n)
    if m:
        clip_text = _clean_name(raw[m.start(1):m.end(1)])
        return Plan("clipboard_action", {"action": "write", "text": clip_text})

    # 11. Ordner öffnen
    for fld, kw in [
        ("downloads", r"downloads?"),
        ("documents", r"dokumente|documents?|unterlagen"),
        ("desktop", r"desktop|schreibtisch"),
        ("pictures", r"bilder|pictures?|fotos"),
        ("music", r"musik|music"),
        ("recycle_bin", r"papierkorb|mulleimer|recycle\s*bin"),
        ("c_drive", r"laufwerk\s*c|festplatte\s*c|c:\b"),
    ]:
        if re.search(rf"\b(offne\w*|oeffne\w*|geh\s*zu|zeig\w*)\b\s*(?:den\s*|die\s*|das\s*)?(?:ordner\s*)?({kw})\b", n):
            return Plan("open_folder", {"folder": fld})

    # 12. Lokale Dateisuche
    m = re.search(r"\b(such\w*|find\w*|search|wo ist|wo liegt|wo finde ich)\b\s*(?:mir\s+)?(?:bitte\s+)?"
                  r"(?:nach\s+)?(?:der|die|das|den|dem|datei|dateien|file|files)?\s*(.+)$", n)
    if m and not re.search(r"\b(im\s*web|im\s*internet|online|google)\b", n):
        query = raw[m.start(2):m.end(2)]
        location = None
        for loc in _LOCATIONS:
            lm = re.search(rf"\b(?:auf|in|im|aus)?\s*(?:dem|den|der|meinen|meinem)?\s*{loc}\b", query, re.IGNORECASE)
            if lm:
                location = loc
                query = (query[:lm.start()] + query[lm.end():]).strip()
                break
        query = _clean_name(re.sub(r"\b(datei(en)?|files?)\b", "", query, flags=re.IGNORECASE))
        if query:
            return Plan("find_files", {"query": query, **({"location": location} if location else {})})

    # 13. Web-Suche & Wissensfragen
    if re.search(r"\b(im\s*web|im\s*internet|online|google\w*|recherchier\w*)\b", n):
        m = re.search(r"\b(?:such\w*|google\w*|recherchier\w*)\b(?:\s*(?:im\s*web|im\s*internet|online))?\s*(?:nach\s+)?(.+)$", n)
        if m:
            query = _clean_name(raw[m.start(1):m.end(1)])
            return Plan("web_search", {"query": query})
    if re.search(r"\b(wer\s*ist|was\s*ist\s*ein\w*|wie\s*ist\s*das\s*wetter|wetter\s*in)\b", n):
        return Plan("web_search", {"query": raw.strip(" .!?")})

    # 14. Programme starten
    m = re.search(r"\b(?:offne\w*|oeffne\w*|starte\w*|start|open|launch|run|ausfuhren)\b\s+(.+)$", n)
    if m:
        name = _clean_name(raw[m.start(1):m.end(1)])
        if name:
            return Plan("open_program", {"name": name})
    m = re.search(r"\bmach\w*\s+(.+?)\s+auf\b", n)
    if m:
        name = _clean_name(raw[m.start(1):m.end(1)])
        if name:
            return Plan("open_program", {"name": name})

    # 15. System-Info
    bat = re.search(r"akku|batterie|battery|ladestand|ladezustand|wie voll", n)
    disk = re.search(r"festplatte|speicherplatz|freier speicher|\bdisk\b|laufwerk|storage|platte", n)
    if bat or disk or re.search(r"systeminfo|system status|pc status", n):
        kind = "all" if (bat and disk) or not (bat or disk) else ("battery" if bat else "disk")
        return Plan("system_info", {"kind": kind})

    # 16. Tricks & Animationen
    if re.search(r"\b(tanz\w*|dance)\b", n):
        return Plan(reply="💃 Schau mal Boss, wie ich tanze! Miau miau~ ♪♫", ok=True)
    if re.search(r"\b(sei\s*cool|coole\s*katze|sonnenbrille|cool)\b", n):
        return Plan(reply="🕶️ Ich bin die coolste Katze auf deinem Desktop, Boss! ✨", ok=True)
    if re.search(r"\b(gute\s*nacht|schlaf\w*)\b", n):
        return Plan(reply="Gute Nacht, Boss! Ich pass auf deinen PC auf 💤", ok=True)
    if re.search(r"\b(wach\s*auf|aufstehen|aufwachen)\b", n):
        return Plan(reply="Guten Morgen Boss! Ich bin hellwach und einsatzbereit! ✨", ok=True)

    # 17. Konversation / Smalltalk
    if re.search(r"\b(hallo|hi|hey|moin|servus|huhu|guten (tag|morgen|abend))\b", n):
        return Plan(reply=random.choice(_GREET))
    if re.search(r"danke|thx|thanks|merci", n):
        return Plan(reply=random.choice(_THANKS))
    if re.search(r"was kannst du|hilfe|\bhelp\b|was machst du|befehle", n):
        return Plan(reply=_HELP)
    if re.search(r"wer bist du|wie heisst du|dein name", n):
        return Plan(reply="Ich bin Mochi, dein kleiner Desktop-Buddy und PC-Assistent! 🐾")
    if re.search(r"miau|meow|nyan|schnurr", n):
        return Plan(reply="Miau~ Schnurr schnurr! 😻💖")
    if re.search(r"wie geht", n):
        return Plan(reply="Mir geht's pfoten-tastisch! Und dir, Boss? 💖")

    return Plan(reply=_UNKNOWN, ok=False)



# ======================================================================================
#  Gemini CLI Integration & Tool-Calling-Protokoll
# ======================================================================================
def parse_cli_response(raw_response: str) -> tuple[str, dict | None]:
    """Extrahiert (say, tool_dict) aus der Rueckgabe der Gemini CLI.

    Unterstuetzt reines JSON, in ```json```-Zaeunen verpacktes JSON
    sowie Fallback auf reinen Freitext.
    """
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx > start_idx:
        try:
            data = json.loads(cleaned[start_idx : end_idx + 1])
            if isinstance(data, dict):
                say = str(data.get("say") or "").strip()
                tool = data.get("tool")
                tool_dict = tool if isinstance(tool, dict) and tool.get("name") else None
                return say, tool_dict
        except ValueError:
            pass

    return cleaned, None


class AgentWorker(QObject):
    """Laeuft im QThread: Gemini-CLI (falls angemeldet) -> Fallback regelbasiert -> Tools ausfuehren."""

    finished = pyqtSignal(bool, str, str)     # ok, Nachricht, Benachrichtigungstitel ("" = keine)

    MAX_STEPS = 4

    def __init__(self, text: str, cfg: dict, history: list[tuple[str, str]]):
        super().__init__()
        self.text = text
        self.cfg = cfg
        self.history = history
        self.results: list[ToolResult] = []

    # -- Einstieg -----------------------------------------------------------------------
    @pyqtSlot()
    def run(self) -> None:
        try:
            ok, msg, notify = self._process()
        except Exception as exc:  # noqa: BLE001
            ok, msg, notify = False, tools.friendly_error(exc), ""
        self.finished.emit(ok, msg, notify or "")

    def _provider(self) -> Optional[str]:
        ai = self.cfg.get("ai", {})
        if not ai.get("enabled", True):
            return None
        if gemini_cli.cli_command() and gemini_cli.is_logged_in():
            return "gemini"
        return None

    def _process(self) -> tuple[bool, str, str]:
        llm_error = ""
        provider = self._provider()
        if provider:
            try:
                text = self._chat_cli()
                ok = all(r.ok for r in self.results) if self.results else True
                if not text:
                    text = self.results[-1].message if self.results else "Miau? Dazu fallen mir keine Worte ein \U0001F63A"
                return ok, text, self._notify_title()
            except LLMError as exc:
                llm_error = str(exc)
                self.results.clear()

        # Offline / Fallback
        plan = parse_offline(self.text)
        if plan.tool:
            res = tools.execute(plan.tool, plan.args)
            self.results.append(res)
            return res.ok, res.message, res.notify_title or ""
        if llm_error and not plan.ok:
            return False, f"{llm_error}\nUnd offline habe ich das leider nicht verstanden \U0001F97A", ""
        return plan.ok, plan.reply or _UNKNOWN, ""

    def _notify_title(self) -> str:
        for r in self.results:
            if r.ok and r.notify_title:
                return r.notify_title
        return ""

    def _run_tool(self, name: str, args: dict) -> dict:
        res = tools.execute(name, args if isinstance(args, dict) else {})
        self.results.append(res)
        return {"ok": res.ok, "result": res.message}

    # -- Gemini CLI (JSON Tool-Calling Protokoll) ---------------------------------------
    def _chat_cli(self) -> str:
        ai = self.cfg.get("ai", {})
        timeout = float(ai.get("timeout_s", 60))
        model = ai.get("model") or None
        pet_name = self.cfg.get("pet", {}).get("name", "Mochi")

        tool_specs_json = json.dumps([
            {"name": s["name"], "description": s["description"], "parameters": s["parameters"]}
            for s in tools.TOOL_SPECS
        ], ensure_ascii=False)

        tool_history: list[dict] = []

        for step in range(self.MAX_STEPS):
            prompt_parts = [
                system_prompt(pet_name),
                f"\nVERF\u00dcGBARE WERKZEUGE:\n{tool_specs_json}\n",
            ]

            if self.history:
                prompt_parts.append("BISHERIGER GESPR\u00c4CHSVERLAUF:")
                for r, t in self.history:
                    role_str = "Boss" if r == "user" else pet_name
                    prompt_parts.append(f"{role_str}: {t}")
                prompt_parts.append("")

            prompt_parts.append(f"AKTUELLE NACHRICHT VOM BOSS:\n{self.text}\n")

            if tool_history:
                prompt_parts.append("ERGEBNISSE BEREITS AUSGEF\u00dcHRTER WERKZEUGE DIESER RUNDE:")
                for th in tool_history:
                    prompt_parts.append(f"- Tool '{th['name']}' mit Parametern {json.dumps(th['args'])} -> Ergebnis: {th['result']}")
                prompt_parts.append("")

            prompt_parts.append(
                "ANTWORT-REGEL:\n"
                "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Markdown-Formatierung:\n"
                "{\"say\": \"<kurze Antwort an den User oder leer>\", \"tool\": null}\n"
                "oder\n"
                "{\"say\": \"\", \"tool\": {\"name\": \"<tool_name>\", \"args\": {...}}}\n"
                "W\u00e4hle ein Werkzeug nur dann, wenn es f\u00fcr die Anfrage des Nutzers wirklich erforderlich ist. "
                "Wenn alle Aufgaben erledigt sind oder keine Werkzeuge n\u00f6tig sind, setze 'tool' auf null und formuliere eine nette Antwort in 'say'."
            )

            full_prompt = "\n".join(prompt_parts)
            raw_response = gemini_cli.ask(full_prompt, timeout_s=timeout, model=model)

            say_text, tool_call = parse_cli_response(raw_response)

            if not tool_call:
                return say_text or (self.results[-1].message if self.results else "Miau! Alles erledigt \U0001F43E")

            tool_name = str(tool_call.get("name", "")).strip()
            tool_args = tool_call.get("args") if isinstance(tool_call.get("args"), dict) else {}

            valid_names = {s["name"] for s in tools.TOOL_SPECS}
            if tool_name not in valid_names:
                tool_history.append({
                    "name": tool_name,
                    "args": tool_args,
                    "result": f"Fehler: Werkzeug '{tool_name}' existiert nicht.",
                })
                continue

            res = self._run_tool(tool_name, tool_args)
            tool_history.append({
                "name": tool_name,
                "args": tool_args,
                "result": res.get("result", ""),
            })

            if say_text and not self.results[-1].message:
                self.results[-1].message = say_text

        return self.results[-1].message if self.results else ""


# ======================================================================================
#  Controller im UI-Thread: startet Worker in QThread, meldet per Signal zurueck
# ======================================================================================
class AgentBrain(QObject):
    started = pyqtSignal(str)                # Aufgabe begonnen (-> Pet: WORKING)
    finished = pyqtSignal(bool, str, str)    # ok, Nachricht, Benachrichtigungstitel

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._busy = False
        self._history: list[tuple[str, str]] = []
        self._threads: set[QThread] = set()
        self._current_text = ""

    def record_assistant_message(self, message: str) -> None:
        """Merkt sich eine autonome Äußerung oder Rückfrage von Mochi im Gesprächsverlauf."""
        msg = (message or "").strip()
        if msg:
            self._history.append(("assistant", msg))
            self._history = self._history[-24:]

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def busy(self) -> bool:
        return self._busy

    def submit(self, text: str) -> bool:
        text = (text or "").strip()
        if not text or self._busy:
            return False
        self._busy = True
        self._current_text = text
        thread = QThread()
        worker = AgentWorker(text, self._cfg.snapshot(), list(self._history[-18:]))
        worker.moveToThread(thread)
        thread._worker = worker          # Referenz halten, sonst raeumt Python den Worker vorzeitig ab
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_done)
        worker.finished.connect(lambda *_: thread.quit())
        thread.finished.connect(lambda: self._threads.discard(thread))
        thread.finished.connect(thread.deleteLater)
        self._threads.add(thread)
        thread.start()
        self.started.emit(text)
        return True

    @pyqtSlot(bool, str, str)
    def _on_done(self, ok: bool, message: str, notify: str) -> None:
        self._busy = False
        self._history.append(("user", self._current_text))
        self._history.append(("assistant", message))
        self._history = self._history[-24:]
        self.finished.emit(ok, message, notify)

    def shutdown(self, wait_ms: int = 1500) -> bool:
        """Wartet kurz auf laufende Worker. True = alle beendet."""
        for t in list(self._threads):
            t.quit()
            t.wait(wait_ms)
        return not any(t.isRunning() for t in self._threads)
