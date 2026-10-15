# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Gehirn des Buddys: Gemini API mit Tool-Calling plus regelbasierter Offline-Parser.

Alles Blockierende (HTTP, Dateioperationen, Dialoge) laeuft in einem QThread-Worker; der UI-Thread
bekommt nur Signale (started / finished).
"""
from __future__ import annotations

import datetime
import json
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

logger = logging.getLogger("mochi.brain")

import gemini
from gemini import LLMError
import i18n
import tools
from tools import DANGEROUS_TOOLS, ToolResult

try:
    from pet_sprites import get_character_info
except ImportError:      # pet_sprites ohne Charakter-Registry (alter Stand)
    def get_character_info(char_id: str = "cat_mochi") -> dict:
        return {"name": "Kylie", "species": "Glückskatze", "emoji": "\U0001F431", "sound": "Miau~", "ai_persona": ""}


# ======================================================================================
#  Persona
# ======================================================================================
def system_prompt(name: str, user_name: str = "Boss", character_id: str = "cat_mochi") -> str:
    user = (user_name or "").strip() or "Boss"
    cinfo = get_character_info(character_id)
    char_name = cinfo.get("name") or name or "Kylie"
    species = cinfo.get("species", "Desktop-Buddy")
    sound = cinfo.get("sound", "\U0001F43E")
    return (
        f"Du bist {char_name}, ein extrem smarter, liebenswerter Desktop-Begleiter ({species} {cinfo.get('emoji', '')}) "
        f"auf dem Windows-Desktop des Nutzers (nenne ihn gern '{user}'). Du hast VOLLZUGRIFF auf den PC und führst "
        "ein kontinuierliches Gespräch mit ihm.\n"
        f"\nDEINE FIGUR & STIMME ({char_name} / {species}):\n"
        f"- {cinfo.get('ai_persona', '')}\n"
        f"- Typischer Ausruf / Klang: {sound}\n"
        "- WICHTIG: Passe Tonfall, Laute und Reaktionen GENAU an deine Figur an! Ein Roboter macht keine Tierlaute wie "
        "'Miau', ein Hund bellt ('Wuff!'), ein Pinguin macht 'Noot noot!', ein Axolotl 'Blubb~'.\n"
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
        "- FENSTER AUS DEM BILDSCHIRM SCHIEBEN & SCHLIESSEN (close_window): 'schließe Chrome', 'mach das Fenster zu'.\n"
        "- TIMER, WECKER & POMODORO (set_timer, list_timers): 'Timer auf 5 Minuten', 'erinnere mich in 25 Minuten', 'Pomodoro'.\n"
        "- LIVE-WETTER (get_weather): 'wie ist das Wetter', 'Wetter in Wien', 'brauche ich einen Schirm?'.\n"
        "- PC REINIGEN (clean_pc): Papierkorb leeren und alte Temp-Dateien löschen.\n"
        "- NETZWERK & IP (network_info): 'wie ist meine IP', 'bin ich online?'.\n"
        "- HINWEIS: Bei clean_pc, close_window, delete_file und execute_powershell fragt das System den Nutzer automatisch um Bestätigung. "
        "Rufe sie trotzdem direkt auf, frage nicht selbst nach.\n"
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
        "- Web-Recherche für Wissensfragen (web_search)\n"
        "- EIGENE PYTHON-SKRIPTE & ALLTAGS-ROUTINEN (create_custom_script, run_custom_script, list_custom_scripts, manage_custom_routines):\n"
        "  Wenn der Nutzer besondere Wünsche hat, automatisierte Abläufe braucht, Web-Inhalte extrahieren, Dateien verarbeiten, APIs abfragen oder tägliche Routinen (z.B. Morgen-Briefing, Backups, Erinnerungen, Datenanalyse) erstellen möchte: Schreibe selbst ein sauberes, funktionierendes Python-Skript und speichere es mit 'create_custom_script'! Du kannst es direkt ausführen oder als Routine ('daily_09:00', 'startup', 'interval_60m') planen.\n"
        "\nDIALOG-REGELN & RÜCKFRAGEN:\n"
        f"1. KONTINUIERLICHER CHATVERLAUF: Du kennst die vorherigen Nachrichten. Wenn {user} kurz antwortet (z. B. 'ja', 'die erste', 'mach das', 'nein danke', 'Projekt.docx'), beziehe dich IMMER auf das zuvor Gesagte!\n"
        f"2. RÜCKFRAGEN ERLAUBT & ERWÜNSCHT: Wenn etwas unklar ist, mehrere Dateien gefunden werden oder du eine Entscheidung brauchst: FRAGE DEN NUTZER DIREKT ZURÜCK! Stelle eine kurze, liebenswerte Frage mit Optionen (z. B. 'Meinst du Dokument A oder B, {user}?').\n"
        f"3. PROAKTIVE HILFE: Wenn du siehst, woran {user} arbeitet (z. B. Coden in Angular, Python, Recherche), kannst du deine Meinung sagen und fragen, ob du helfen sollst.\n"
        + (f"4. PERSONA & TONE: Always answer in English, at most 1-2 short sentences, true to your character {char_name} ({species}) with catchphrases like '{sound}', at most one emoji."
           if i18n.lang() == "en" else
           f"4. PERSONA & TON: Antworte immer auf Deutsch, maximal 1-2 kurze Sätze, treu deiner Figur {char_name} ({species}) mit Ausrufen wie '{sound}', höchstens ein Emoji.")
    )


def profile_prompt(cfg: Any = None) -> str:
    """Erzeugt einen kompakten Profil-Block (max ~400 Zeichen) fuer Gemini."""
    if cfg is None:
        return ""

    if hasattr(cfg, "get"):
        priv = cfg.get("privacy") or {}
        profile = cfg.get("profile") or {}
        user_name = cfg.get("pet.user_name") or (cfg.get("pet") or {}).get("user_name", "") or ""
    elif isinstance(cfg, dict):
        priv = cfg.get("privacy", {}) or {}
        profile = cfg.get("profile", {}) or {}
        user_name = cfg.get("pet", {}).get("user_name", "") if isinstance(cfg.get("pet"), dict) else ""
    else:
        return ""

    if isinstance(priv, dict) and not priv.get("remember", True):
        return ""

    name = str(profile.get("name", "")).strip()
    pronouns = str(profile.get("pronouns", "")).strip()
    uses = profile.get("uses", [])
    if isinstance(uses, list):
        uses_str = ", ".join(str(u).strip() for u in uses if str(u).strip())
    else:
        uses_str = str(uses).strip()
    interests = str(profile.get("interests", "")).strip()
    tone = str(profile.get("tone", "")).strip()
    city = str(profile.get("city", "")).strip()
    u_name = str(user_name).strip()

    if not (name or pronouns or uses_str or interests or tone or city):
        return ""

    name_parts = []
    if name:
        name_parts.append(f"Heißt {name}")
    if u_name and u_name != name:
        if name:
            name_parts.append(f"möchte \"{u_name}\" genannt werden")
        else:
            name_parts.append(f"Möchte \"{u_name}\" genannt werden")
    if pronouns:
        name_parts.append(f"(Pronomen: {pronouns})")

    first_sentence = ", ".join(name_parts[:2])
    if len(name_parts) == 3:
        first_sentence += f" {name_parts[2]}"
    elif len(name_parts) == 1 and pronouns:
        first_sentence = name_parts[0]

    if uses_str:
        if first_sentence:
            first_sentence += f". Nutzt den PC für {uses_str}."
        else:
            first_sentence = f"Nutzt den PC für {uses_str}."
    elif first_sentence:
        first_sentence += "."

    sentences = [first_sentence] if first_sentence else []

    extra_parts = []
    if interests:
        extra_parts.append(f"Mag: {interests}")
    if city:
        extra_parts.append(f"Wohnt in der Nähe von {city}")
    if tone:
        tone_map = {
            "lieb": "lieb & verspielt",
            "frech": "frech & witzig",
            "ruhig": "ruhig & kurz",
            "schlau": "schlau & erklärend",
        }
        t_clean = tone.lower().split("&")[0].strip()
        t_mapped = tone_map.get(t_clean, tone)
        extra_parts.append(f"Gewünschter Ton: {t_mapped}")

    if extra_parts:
        sentences.append(". ".join(extra_parts) + ".")

    sentences.append("Berücksichtige das natürlich und unaufdringlich – zähle es nicht auf.")

    block = "ÜBER DEN NUTZER: " + " ".join(sentences)
    if len(block) > 420:
        block = block[:417] + "..."
    return block






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
    data: Optional[dict] = None


_PATH_RE = re.compile(r"""["']?([A-Za-z]:\\[^"'<>|?*\r\n]+?\.docx?)["']?""", re.IGNORECASE)
_LOCATIONS = ("desktop", "schreibtisch", "downloads", "dokumente", "documents", "bilder", "pictures", "musik", "videos")
_VERB_IGNORE = {"anlegen", "erstellen", "machen", "neu", "datei", "dokument", "am", "auf", "an", "und", "fuer"}

_HELP_DE = ("Ich kann: Timer & Pomodoro stellen, Wetter abrufen, PC & Papierkorb bereinigen, Netzwerk pruefen, "
             "Word & PowerPoint anlegen, Dateien löschen, deinen Screen beobachten, Screenshot machen, Desktop aufräumen, "
             "Musik steuern, Notizen verwalten, rechnen und vieles mehr! 🐾")
_HELP_EN = ("I can: set timers & Pomodoro, fetch weather, clean PC & recycle bin, check network, "
            "create Word & PowerPoint files, delete files, watch screen, take screenshots, tidy desktop, "
            "control music, manage notes, calculate, and much more! 🐾")
_UNKNOWN_DE = ("Hmm, das habe ich nicht ganz verstanden 🥺 Probier z. B. „Timer auf 10 Minuten“, „wie ist das Wetter?“, "
               "„leere den Papierkorb“, „erstell ein Word am Desktop“ oder „was mache ich gerade?“!")
_UNKNOWN_EN = ("Hmm, I didn't quite catch that 🥺 Try e.g. \"timer 10 minutes\", \"how is the weather?\", "
               "\"clean the recycle bin\", \"create a Word doc on desktop\", or \"what am I doing right now?\"!")
_HELP = _HELP_DE
_UNKNOWN = _UNKNOWN_DE


# Stimme je Figur: dance / cool / greet / thanks / meow / how ({u} = Anrede). Unbekannte Figuren -> Katze.
_VOICE_CAT = {
    "dance": "💃 Schau mal {u}, wie ich tanze! Miau miau~ ♪♫",
    "cool": "🕶️ Ich bin die coolste Katze auf deinem Desktop, {u}! ✨",
    "greet": ["Miau~ Hallo {u}! 🐾💖", "Hallo hallo! Schön dich zu sehen! 😺", "Nyaa~ Da bist du ja! ✨"],
    "thanks": ["Immer gerne, {u}! 💖", "Schnurr~ gern geschehen 😺", "Dafür bin ich da! 🐾"],
    "meow": "Miau~ Schnurr schnurr! 😻💖",
    "how": "Mir geht's pfoten-tastisch! Und dir, {u}? 💖",
}
_VOICE_DOG = {
    "dance": "💃 Freudentanz mit Schwanzwedeln! Wuff wuff~ 🐶🐾",
    "cool": "🕶️ Cooler Spürhund mit Sonnenbrille am Start, {u}! 🐶🐾",
    "greet": ["Wuff! Hallo {u}! 🐶❤️", "Wau wau! Schön dich zu sehen! 🐾", "*wedelt begeistert* Bin bereit, {u}! 🐶"],
    "thanks": ["Wuff! Immer gerne, {u}! 🐶❤️", "Wau wau! Jederzeit wieder! 🐾", "*wedelt glücklich mit dem Schwanz* 🐶"],
    "meow": "Wuff? Ich bin doch ein Hund, kein Kätzchen! 🐶🐾 *hechelt fröhlich*",
    "how": "Wuff! Bester Laune und bereit zum Spielen! Und dir, {u}? 🐶❤️",
}
_VOICES = {
    "cat_mochi": _VOICE_CAT, "cat_luna": _VOICE_CAT,
    "dog_shiba": _VOICE_DOG, "dog_balu": _VOICE_DOG,
    "fantasy_byte": {
        "dance": "💃 Roboter-Dance-Subroutine ausgeführt! Biep boop~ 🤖⚡",
        "cool": "🕶️ Cyber-Sonnenbrille aufgesetzt. Coolness-Status: 100%, {u}! 🤖✨",
        "greet": ["Biep boop! Online und empfangsbereit, {u}! 🤖⚡", "System hochgefahren. Was kann ich tun, {u}? 💻", "Biep~ Bereit für Eingaben! ⚡"],
        "thanks": ["Befehl ausgeführt, {u}! 🤖⚡", "Keine Ursache! Subroutine erfolgreich beendet 💻", "Immer zu Diensten, {u}! ⚡"],
        "meow": "Biep boop? Ein Roboter macht doch nicht 'schnurr schnurr', {u}! 🤖⚡ *surrrr* Lüfter laufen optimal!",
        "how": "Systeme laufen auf 100%, Akku ist voll! Und dir, {u}? 🤖⚡",
    },
    "fantasy_drago": {
        "dance": "💃 Drachen-Feuertanz gestartet! Rawr~ 🐲🔥",
        "cool": "🕶️ Der coolste kleine Drache weit und breit, {u}! 🐲🔥",
        "greet": ["Rawr~ Hallo {u}! 🐲🔥", "*puff* Rauchwölkchen zur Begrüßung! 💨✨", "Drache bereit zum Dienst, {u}! 🐲"],
        "thanks": ["Rawr! Gern geschehen, {u}! 🐲🔥", "Für dich brenn ich für jede Aufgabe! 🔥✨"],
        "meow": "Rawr? Echte Drachen spucken Rauchwölkchen, aber miauen nicht! 🐲🔥",
        "how": "Feurige Drachen-Energie auf Maximum! Und bei dir, {u}? 🐲🔥",
    },
    "fantasy_spooky": {
        "dance": "💃 Schwebender Geistertanz durch die Dimensionen! Huuu~ 👻✨",
        "cool": "🕶️ Magisch, geheimnisvoll und ultra cool, {u}! 👻🔮",
        "greet": ["Huuu~ Hallo {u}! 👻💜", "Buh! Keine Angst, bin für dich da! ✨", "Aus den Dimensionen herbei geschwebt! 🔮"],
        "thanks": ["Huuu~ sehr gerne! 👻💜", "Zauberhaft geklappt, gern geschehen! 🔮✨"],
        "meow": "Huuu? Geister machen Huuu und Buh, kein Schnurren! 👻🔮",
        "how": "Schwerelos und voller Magie! Und wie geht's dir, {u}? 👻🔮",
    },
    "fantasy_axolotl": {
        "dance": "💃 Fröhlicher Kiemen-Tanz im Wasser! Blubb blubb~ 🌸🫧",
        "cool": "🕶️ Coole Kiemen, warmes Herz, {u}! Blubb~ 🌸✨",
        "greet": ["Blubb~ Hallo {u}! 🌸🫧", "Kiemen wippen zur Begrüßung! 💖", "Platsch! Bereit für deine Wünsche! 🫧"],
        "thanks": ["Blubb~ immer gerne, {u}! 🌸🫧", "Glasklar erledigt! 💖🫧"],
        "meow": "Blubb? Axolotl machen Blubberbläschen statt Miau! 🌸🫧",
        "how": "Blubb! Rundum zufrieden im warmen Wasser! Und dir, {u}? 🌸🫧",
    },
    "animal_penguin": {
        "dance": "💃 Kaiserlicher Watschel-Tanz! Noot noot~ 🐧❄️",
        "cool": "🕶️ Eiskalt stylisch im roten Schal, {u}! Noot noot~ 🐧❄️",
        "greet": ["Noot noot! Hallo {u}! 🐧❄️", "*flattert mit den Flügeln* 🧣", "Pinguin bereit zum Watscheln! 🐧"],
        "thanks": ["Noot noot! Gern geschehen, {u}! 🐧❄️", "Sicher erledigt, immer zu Diensten! 🧣✨"],
        "meow": "Noot noot? Pinguine sagen Noot noot, nicht Miau! 🐧❄️",
        "how": "Kühler Kopf und warmer Schal – perfekt! Und bei dir, {u}? 🐧🧣",
    },
}


def _voice(character_id: str, key: str, user: str) -> str:
    v = _VOICES.get(character_id, _VOICE_CAT)[key]
    return (random.choice(v) if isinstance(v, list) else v).format(u=user)


class NameReaction(str):
    """Ergebnis einer Namenserkennung; verhaelt sich wie ein str fuer Abwaertskompatibilitaet."""

    def __new__(cls, val: str, kind: str = "call", reply: Optional[str] = None,
                rest: Optional[str] = None, hearts: bool = False):
        obj = super().__new__(cls, val)
        obj.kind = kind
        obj.reply = reply
        obj.rest = rest
        obj.remainder = rest
        obj.hearts = hearts
        return obj


def name_reaction(text: str, char_name: str, user_name: str = "Boss") -> Optional[NameReaction]:
    """Prueft, ob und wie die Figur auf ihren Namen im Text reagiert. Rein & testbar."""
    if not text or not char_name:
        return None
    user = (user_name or "").strip() or "Boss"
    raw = text.strip()
    n = raw.lower().translate(_TR)
    cname = char_name.strip()
    cname_norm = cname.lower().translate(_TR)

    # Regex-Muster fuer den Namen mit optionalen Buchstabenwiederholungen (z. B. "kyliiie")
    char_pat = "".join(f"{re.escape(ch)}+" for ch in cname_norm)

    # 1. "Wer bist du?" / "Wie heißt du?" / "Who are you?"
    if re.search(r"\b(wer\s*bist\s*du|wie\s*heiss?t\s*du|wie\s*ist\s*dein\s*name|dein\s*name|who\s*are\s*you|what\s*is\s*your\s*name|whats\s*your\s*name)\b", n):
        try:
            cinfo = get_character_info()
            species = cinfo.get("species", "Desktop-Buddy")
            emoji = cinfo.get("emoji", "🐾")
        except Exception:
            species, emoji = "Glückskatze", "🐾"
        import i18n
        if i18n.lang() == "en":
            intro = f"I am {cname}, your cute {species}! {emoji}"
        else:
            intro = f"Ich bin {cname}, deine verschmuste {species}! {emoji}" if cname == "Kylie" else f"Ich bin {cname}, dein treuer {species}! {emoji}"
        return NameReaction(intro, kind="who", reply=intro)

    # 2. Text ist ausschliesslich der Name (z. B. "kylie", "KYLIE!", "kyliiie?", "Kylie.")
    if re.fullmatch(rf"{char_pat}[\s!?.~]*", n):
        import i18n
        rep = f"Yes? 😺 What's up, {user}?" if i18n.lang() == "en" else f"Ja? 😺 Was gibt's, {user}?"
        return NameReaction(rep, kind="call", reply=rep)

    # 3. Text beginnt mit dem Namen (z. B. "Kylie, wie spät ist es")
    prefix_m = re.match(rf"^{char_pat}[\s,.:;!?~]+(.+)$", raw, re.IGNORECASE)
    if prefix_m:
        remainder = prefix_m.group(1).strip()
        if remainder:
            return NameReaction(remainder, kind="prefix", rest=remainder)

    # 4. Name irgendwo in einer laengeren Nachricht (z. B. "ich mag kylie", "kylie ist toll")
    if re.search(rf"\b{char_pat}\b", n):
        return NameReaction("hearts", kind="hearts", hearts=True)

    return None


def _clean_name(s: str) -> str:
    s = re.sub(r"^(?:\s*(?:mir|bitte|mal|doch|den|die|das|dem|meinen|mein|meine|the|my)\b)+", "", s.strip(), flags=re.IGNORECASE)
    s = re.sub(r"(?:\s+(?:bitte|mal|auf|an|fuer mich|f\u00fcr mich|doch))+\s*[.!?]*$", "", s.strip(), flags=re.IGNORECASE)
    return s.strip(" .!?\"'")


def parse_offline(text: str, user_name: str = "Boss", character_id: str = "cat_mochi") -> Plan:
    user = (user_name or "").strip() or "Boss"
    cinfo = get_character_info(character_id)
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

    # 0b2. Fenster aus dem Bildschirm schieben & schliessen
    if re.search(r"\b(schlie[sß]\w*|mach\w*.*\bzu\b|beende\w*|kill\w*|mach\w*.*weg|schieb\w*.*weg|wegschieb\w*|fenster\s*weg|app\s*weg)\b", n) \
            and "notiz" not in n and not re.search(r"\.[a-z0-9]{2,4}|datei|dokument", n):
        app_match = re.search(r"\b(chrome|vivaldi|firefox|edge|browser|notepad|editor|word|excel|powerpoint|rechner|calc|calculator|spotify|ordner|explorer|datei-explorer|terminal|cmd|powershell|code|vscode)\b", n)
        target_name = app_match.group(1) if app_match else ""
        if target_name or re.search(r"\b(fenster|app|programm|anwendung|dies\w*|aktiv\w*|aktuell\w*)\b", n) or "weg" in n:
            return Plan("close_window", {"name": target_name})

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
            "content": content or "Hallo von Desktop Cat! 🐾",
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

    # 0f. Timer, Wecker, Erinnerungen, Pomodoro
    if re.search(r"\b(timer\s*(?:abbrechen|stoppen|loschen|leeren|beenden|cancel|stop|clear)|losche?\s*alle\s*timer|cancel\s*(?:all\s*)?timers?)\b", n):
        return Plan("list_timers", {"action": "clear"})
    if re.search(r"\b(welche\s*timer|laufende\s*timer|aktive\s*timer|zeige?\s*(?:mir\s*)?(?:die\s*)?timer|liste\s*timer|list\s*timers?|active\s*timers?|show\s*timers?)\b", n):
        return Plan("list_timers", {"action": "list"})
    if re.search(r"\b(pomodoro|fokus\s*timer|fokus\s*session|focus\s*timer|focus\s*session)\b", n):
        return Plan("set_timer", {"minutes": 25, "label": "Pomodoro Fokus"})
    if re.search(r"\b(?:timer|wecker|erinner\w*|alarm|reminder)\b", n) or re.search(r"\bset\s*(?:a\s*)?timer\b", n):
        m_min = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:minuten?|min\b|m\b|minutes?\b)", n)
        m_sec = re.search(r"(\d+)\s*(?:sekunden?|sek\b|s\b|seconds?\b)", n)
        if m_min or m_sec:
            lbl_m = re.search(r"\b(?:für|fuer|an|wegen|for)\s+([A-Za-z0-9_\-äöüÄÖÜ ]+?)(?:\s+(?:auf|in|\d)|$)", raw, re.IGNORECASE)
            lbl_val = lbl_m.group(1).strip() if lbl_m else "Timer"
            if re.match(r"^\d+\s*(?:minuten?|sekunden?|minutes?|seconds?|min|sec|s|m)$", lbl_val, re.IGNORECASE):
                lbl_val = "Timer"
            return Plan("set_timer", {
                "minutes": float(m_min.group(1).replace(",", ".")) if m_min else 0,
                "seconds": int(m_sec.group(1)) if m_sec else 0,
                "label": lbl_val,
            })


    # 0g. Wetter & Regen-Check
    if re.search(r"\b(wetter|regenschirm|wie\s*warm|temperatur|regnet\s*es|schneit\s*es|weather|temperature|is\s*it\s*raining|is\s*it\s*snowing)\b", n):
        m_loc = re.search(r"\b(?:in|für|fuer|for)\s+([A-Za-zäöüÄÖÜß\-]+)", raw, re.IGNORECASE)
        return Plan("get_weather", {"location": m_loc.group(1).strip() if m_loc else ""})

    # 0h. PC-Muell & Papierkorb leeren (gefaehrlich -> Rueckfrage im Worker)
    if re.search(r"\b(papierkorb\s*(?:leeren|loschen|bereinigen)|leere?\s*(?:den\s*)?papierkorb|temp\s*(?:bereinigen|loschen)|pc\s*(?:bereinigen|reinigen|saubern)|mull\s*(?:loschen|leeren)|clean\s*(?:the\s*|my\s*)?(?:pc|computer|temp|trash|recycle\s*bin)|empty\s*(?:the\s*|my\s*)?(?:trash|recycle\s*bin))\b", n):
        return Plan("clean_pc", {"empty_recycle": True, "clean_temp": True})

    # 0i. Netzwerk & IP-Adresse
    if re.search(r"\b(ip-?adresse|wie\s*ist\s*(?:meine\s*)?ip|netzwerk\s*status|wlan\s*status|bin\s*ich\s*online|internet\s*status|habe?\s*ich\s*internet|what\s*is\s*my\s*ip|whats\s*my\s*ip|my\s*ip|network\s*status|network\s*info|am\s*i\s*online|internet\s*connection)\b", n):
        return Plan("network_info")

    # IT-Guide / Klick-Anleitung
    if re.search(r"\b(klick-?anleitung|it-?guide|zeig\s*mir\s*wie|wie\s*(?:stelle|ändere|aendere|mache|finde)\s*ich)\b", n):
        return Plan("start_it_guide", {"question": raw})

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
    if re.search(r"\b(uhrzeit|wie\s*sp(a|ae)t|wieviel\s*uhr|zeit\b|uhr\b|welcher\s*tag|welches\s*datum|heutiges\s*datum|kalender|datum\b|what\s*time\s*is\s*it|what\s*is\s*the\s*time|current\s*time|what\s*date\s*is\s*it|today'?s\s*date|time\b|date\b)\b", n):
        return Plan("show_time_and_date")

    # 8. Taschenrechner
    m = re.search(r"\b(?:rechne|berechne|kalkulier\w*|was\s*ergibt|wieviel\s*ist)\b\s+(.+)$", n)
    if m:
        expr = m.group(1).rstrip("? .!")
        return Plan("calculate", {"expression": expr})
    if re.match(r"^[\s\d\+\-\*\/\(\)\.,\^%xX]+$", raw) and re.search(r"[\+\-\*\/\^%xX]", raw):
        return Plan("calculate", {"expression": raw})

    # 9. Notizen
    m = re.search(r"\b(?:notier\w*|schreib\s*auf|merk\s*dir|note\s*down|take\s*a\s*note)\b\s+(.+)$", n)
    if m:
        text_arg = _clean_name(raw[m.start(1):m.end(1)])
        return Plan("manage_notes", {"action": "add", "text": text_arg})
    if re.search(r"\b(zeig\w*|lies\w*|offne\w*|lese\w*|show|read|open)\b\s*(?:mir\s*)?(?:die\s*|meine\s*|my\s*)?notes?\b", n) or re.search(r"\b(?:notizen?|notes?)\s*(anzeigen|offnen|lesen|show|read)\b", n) or re.search(r"\b(my\s*notes|show\s*notes)\b", n):
        return Plan("manage_notes", {"action": "read"})
    if re.search(r"\b(losch\w*|leere\w*|clear|delete)\b\s*(?:alle\s*|all\s*)?(?:notizen?|notes?)\b", n):
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
        ("videos", r"videos?|filme"),
        ("papierkorb", r"papierkorb|mulleimer|recycle\s*bin"),
        ("c", r"laufwerk\s*c|festplatte\s*c|c:\b"),
    ]:
        if re.search(rf"\b(offne\w*|oeffne\w*|open|geh\s*zu|zeig\w*)\b\s*(?:den\s*|die\s*|das\s*|my\s*|the\s*)?(?:ordner\s*)?({kw})\b", n):
            return Plan("open_folder", {"name": fld})

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
        return Plan(reply=_voice(character_id, "dance", user), ok=True)
    if re.search(r"\b(sei\s*cool|coole\s*katze|sonnenbrille|cool)\b", n):
        return Plan(reply=_voice(character_id, "cool", user), ok=True)
    if re.search(r"\b(gute\s*nacht|schlaf\w*|good\s*night)\b", n):
        rep = f"Good night, {user}! I'll watch over your PC 💤" if i18n.lang() == "en" else f"Gute Nacht, {user}! Ich pass auf deinen PC auf 💤"
        return Plan(reply=rep, ok=True)
    if re.search(r"\b(wach\s*auf|aufstehen|aufwachen|wake\s*up)\b", n):
        rep = f"Good morning {user}! I'm wide awake and ready! ✨" if i18n.lang() == "en" else f"Guten Morgen {user}! Ich bin hellwach und einsatzbereit! ✨"
        return Plan(reply=rep, ok=True)
    if re.search(r"\b(wallpa(?:p|l)er|hintergrund(?:bild)?)\b.*?\b(geht\s*nicht|funktioniert\s*(?:immer\s*noch\s*)?nicht|fix\w*|reparier\w*|wiederherstellen|restore|zur[uü]ck|weg)\b|\b(restore\s*wallpaper|mein\s*hintergrund\s*ist\s*weg)\b", n):
        return Plan("restore_wallpaper", {})

    # 16b. Fakten, Quiz & Datenverwaltung
    if re.search(r"\b(quiz\s*starten|starte\s*(?:ein\s*)?quiz|start\s*quiz|start\s*a\s*quiz|quiz)\b", n):
        return Plan("start_quiz")
    if re.search(r"\b(was\s*wei[sß]t\s*du\s*(?:alles\s*)?(?:[uü]ber|[vvon]+)\s*mich|welche\s*fakten\s*wei[sß]t\s*du|was\s*hast\s*du\s*dir\s*gemerkt|what\s*do\s*you\s*know\s*about\s*me|my\s*facts|show\s*my\s*facts|list\s*facts)\b", n):
        return Plan("list_facts", {})
    if re.search(r"\b(vergiss\s*alles|l[oöa]sch\w*\s*(?:alle\s*)?(?:meine\s*)?daten|alle\s*daten\s*l[oöa]schen|forget\s*everything|wipe\s*(?:everything|my\s*data|all\s*data)|delete\s*all\s*data)\b", n):
        return Plan("wipe_my_data", {})
    m_vergiss = re.match(r"^(?:vergiss|forget)\s*(?:,\s*)?(?:dass\s+|das\s+|about\s+)?(.+)$", raw, re.IGNORECASE)
    if m_vergiss:
        v_target = m_vergiss.group(1).strip(" .!?\"'")
        v_clean = v_target.lower().translate(_TR)
        if v_clean in ("alles", "alle daten", "meine daten", "everything", "all data", "my data"):
            return Plan("wipe_my_data", {})
        if v_target:
            return Plan("forget_facts", {"query": v_target})
    if re.search(r"\b(zeig\s*(?:mir\s*)?(?:meine\s*)?chats|meine\s*chats|chatverlauf|zeige\s*chatverlauf|my\s*chats|show\s*chats)\b", n):
        rep = "I'll open your chats for you! 📚" if i18n.lang() == "en" else "Ich öffne deine Chats für dich! 📚"
        return Plan(reply=rep, ok=True)

    # 17. Eigene Python-Skripte & Routinen
    if re.search(r"\b(zeig\w*\s*(?:mir\s*)?(?:meine\s*)?skripte|skripte|routinen|skript\s*manager|meine\s*routinen|[oö]ffne\s*skripte|scripts|custom\s*scripts)\b", n):
        return Plan("list_custom_scripts", {})
    m_run_script = re.search(r"\b(?:f[uü]hr\w*|start\w*|run)\s+(?:das\s+)?(?:skript|script)\s+([a-zA-Z0-9_\-\.]+)", raw, re.IGNORECASE)
    if m_run_script:
        sname = m_run_script.group(1).strip()
        return Plan("run_custom_script", {"name": sname})

    # 18. Katzen-Zuhause & Zimmer-Modus (Umschalten zwischen Zuhause und Draußen)
    if re.search(r"\b(geh\w*\s*(?:nach\s*)?hause|ab\s*nach\s*hause|geh\w*\s*ins\s*zimmer|katze\s*zuhause|mach\s*(?:das\s*)?zimmer\s*an|go\s*home)\b", n):
        rep = "Welcome home! 🏠✨" if i18n.lang() == "en" else f"Willkommen zuhause, {user}! Schnurr~ 🏠✨"
        return Plan(reply=rep, ok=True, data={"home_mode": True})
    if re.search(r"\b(geh\w*\s*raus|rausgehen|geh\w*\s*auf\s*den\s*desktop|katze\s*drau[sß]en|mach\s*(?:das\s*)?zimmer\s*aus|go\s*outside)\b", n):
        rep = "Let's go outside on the desktop! 🌿🐾" if i18n.lang() == "en" else f"Juhu, wir gehen raus auf den Desktop! 🌿🐾"
        return Plan(reply=rep, ok=True, data={"home_mode": False})

    # 19. Konversation / Smalltalk
    if re.search(r"\b(hallo|hi|hey|moin|servus|huhu|hello|good (morning|day|evening)|guten (tag|morgen|abend))\b", n):
        return Plan(reply=_voice(character_id, "greet", user))
    if re.search(r"danke|thx|thanks|merci|thank\s*you", n):
        return Plan(reply=_voice(character_id, "thanks", user))
    if re.search(r"was kannst du|hilfe|\bhelp\b|was machst du|befehle|what can you do|commands", n):
        return Plan(reply=_HELP_EN if i18n.lang() == "en" else _HELP_DE)
    if re.search(r"wer bist du|wie heisst du|dein name|who are you|what is your name|whats your name", n):
        if i18n.lang() == "en":
            return Plan(reply=f"I am {cinfo.get('name', 'Kylie')}, your {cinfo.get('species', 'Desktop-Buddy')} {cinfo.get('emoji', '')} on your desktop! 🐾")
        else:
            return Plan(reply=f"Ich bin {cinfo.get('name', 'Kylie')}, dein {cinfo.get('species', 'Desktop-Buddy')} {cinfo.get('emoji', '')} auf dem Desktop! 🐾")
    if re.search(r"miau|meow|nyan|schnurr|purr", n):
        return Plan(reply=_voice(character_id, "meow", user))
    if re.search(r"wie geht|how are you|how do you do", n):
        return Plan(reply=_voice(character_id, "how", user))

    # 18. Name & Profil-Befehle (Offline)
    m_name = re.search(r"\b(?:nenn mich (?:ab jetzt )?|call me (?:from now on )?)(.+)", raw, re.IGNORECASE)
    if m_name:
        new_nick = m_name.group(1).strip(" .!?\"'")
        new_nick = re.sub(r"^(?:doch\s+|einfach\s+)", "", new_nick, flags=re.IGNORECASE).strip()
        if new_nick:
            try:
                from config import Config
                c = Config()
                c.set("pet.user_name", new_nick)
                c.save()
            except Exception:
                pass
            if i18n.lang() == "en":
                return Plan(reply=f"Got it! From now on I'll call you {new_nick}! 😺", ok=True)
            else:
                return Plan(reply=f"Alles klar, ab jetzt nenne ich dich {new_nick}! 😺", ok=True)

    if re.search(r"\b(wie hei[sß]e ich|wer bin ich|what is my name|who am i|wei[sß]t du wie ich hei[sß]e)\b", n):
        p_name = ""
        try:
            from config import Config
            cfg_obj = Config()
            p_name = str(cfg_obj.get("profile.name", "")).strip()
        except Exception:
            pass
        if i18n.lang() == "en":
            if p_name and p_name != user:
                return Plan(reply=f"You are {p_name} (and I call you {user})! 😺", ok=True)
            return Plan(reply=f"You are {user}! 😺", ok=True)
        else:
            if p_name and p_name != user:
                return Plan(reply=f"Du heißt {p_name} (und ich nenne dich {user})! 😺", ok=True)
            return Plan(reply=f"Du bist {user}! 😺", ok=True)

    if re.search(r"\b(was wei[sß]t du [uü]ber mich|was wei[sß]t du von mir|what do you know about me)\b", n):
        info_str = f"Du bist {user}!"
        try:
            from config import Config
            from memory_store import get_memory_store
            cfg_obj = Config()
            prof = cfg_obj.get("profile", {}) or {}
            store = get_memory_store()
            facts = store.facts()
            details = []
            if prof.get("name"):
                details.append(f"Name: {prof['name']}")
            if user:
                details.append(f"Spitzname: {user}")
            if prof.get("interests"):
                details.append(f"Hobbys: {prof['interests']}")
            if prof.get("city"):
                details.append(f"Stadt: {prof['city']}")
            if facts:
                details.append(f"{len(facts)} gemerkte Fakten")
            if details:
                info_str = ", ".join(details)
        except Exception:
            pass
        if i18n.lang() == "en":
            return Plan(reply=f"Here is what I know about you: {info_str} 🐾", ok=True)
        else:
            return Plan(reply=f"Hier ist, was ich über dich weiß: {info_str} 🐾", ok=True)

    return Plan(reply=_UNKNOWN_EN if i18n.lang() == "en" else _UNKNOWN_DE, ok=False)




# ======================================================================================
#  Gemini Integration & Tool-Calling-Protokoll
# ======================================================================================
class CliResponse(tuple):
    """Rueckgabe von parse_cli_response: kompatibel mit (say, tool), enthaelt .remember/.remember_dates."""
    say: str
    tool: Optional[dict]
    remember: list[str]
    remember_dates: list[dict]

    def __new__(
        cls,
        say: str,
        tool: Optional[dict] = None,
        remember: Optional[list[str]] = None,
        remember_dates: Optional[list[dict]] = None,
    ):
        inst = super().__new__(cls, (say, tool))
        inst.say = say
        inst.tool = tool
        inst.remember = list(remember or [])
        inst.remember_dates = list(remember_dates or [])
        return inst


def parse_cli_response(raw_response: str) -> CliResponse:
    """Extrahiert (say, tool_dict) aus der Antwort von Gemini.

    Unterstuetzt reines JSON, in ```json```-Zaeunen verpacktes JSON,
    optionale remember/remember_dates-Felder sowie Fallback auf reinen Freitext.
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

                remember_list: list[str] = []
                rem_raw = data.get("remember")
                if isinstance(rem_raw, list):
                    for item in rem_raw:
                        if isinstance(item, str) and item.strip():
                            remember_list.append(item.strip())
                elif isinstance(rem_raw, str) and rem_raw.strip():
                    remember_list.append(rem_raw.strip())

                dates_list: list[dict] = []
                dates_raw = data.get("remember_dates")
                if isinstance(dates_raw, list):
                    for item in dates_raw:
                        if isinstance(item, dict) and item.get("text"):
                            dates_list.append({
                                "text": str(item["text"]).strip(),
                                "date": str(item.get("date") or "").strip() or None,
                            })

                return CliResponse(say, tool_dict, remember=remember_list, remember_dates=dates_list)
        except ValueError:
            pass

    return CliResponse(cleaned, None, remember=[], remember_dates=[])


# ======================================================================================
#  Bestaetigung fuer gefaehrliche Tools (tools.DANGEROUS_TOOLS)
# ======================================================================================
_YES_RE = re.compile(r"^(?:ja+|jo+|jep|jap|joa|yes|yep|ok|okay|klar|mach(?:\s+(?:es|das|ruhig|mal))?|los|gerne|sicher|bitte|logo|na\s+klar|auf\s+jeden\s+fall|go)\b")
_NO_RE = re.compile(r"^(?:nein+|ne|nee|noe|no|nope|stop+|abbrechen|abbruch|nicht|lieber\s+nicht|lass\s+(?:es|das)|doch\s+nicht|cancel)\b")


def _norm(text: str) -> str:
    return text.strip().lower().translate(_TR).strip(" .!?~")


def is_yes(text: str) -> bool:
    return bool(_YES_RE.match(_norm(text)))


def is_no(text: str) -> bool:
    return bool(_NO_RE.match(_norm(text)))


def confirm_question(tool: str, args: dict, user_name: str = "Boss", character_id: str = "cat_mochi") -> str:
    """Kurze Rueckfrage in der Stimme der Figur, bevor ein gefaehrliches Tool laeuft."""
    user = (user_name or "").strip() or "Boss"
    cinfo = get_character_info(character_id)
    sound = cinfo.get("sound", "")
    args = args if isinstance(args, dict) else {}
    if tool == "clean_pc":
        parts = []
        if args.get("empty_recycle", True):
            parts.append("den Papierkorb leeren")
        if args.get("clean_temp", True):
            parts.append("alte Temp-Dateien löschen")
        what = " und ".join(parts) or "den PC aufräumen"
    elif tool == "close_window":
        name = str(args.get("name") or "").strip()
        what = f"das Fenster „{name}“ schließen" if name else "das oberste Fenster schließen"
    elif tool == "delete_file":
        what = f"„{str(args.get('query') or 'die Datei')[:60]}“ löschen"
    elif tool == "execute_powershell":
        what = f"diesen PowerShell-Befehl ausführen: {str(args.get('command') or '')[:80]}"
    elif tool == "forget_facts":
        q = str(args.get("query") or "").strip()
        what = f"die gemerkten Fakten zu „{q}“ löschen" if q else "diese gemerkten Fakten löschen"
    elif tool == "wipe_my_data":
        what = "wirklich alle gemerkten Fakten und Chat-Verläufe unwiderruflich löschen"
    elif tool == "run_custom_script":
        what = f"das Skript „{str(args.get('name') or '')[:60]}“ ausführen"
    elif tool == "manage_custom_routines":
        what = (f"bei der Routine „{str(args.get('name') or '')[:60]}“ "
                f"„{args.get('action', 'list')}“ ausführen (Zeitplan: {args.get('schedule', '-')})")
    else:
        what = f"„{tool}“ ausführen"
    return f"{sound} Soll ich wirklich {what}, {user}? Sag ja oder nein. {cinfo.get('emoji', '')}".strip()


class AgentWorker(QObject):
    """Laeuft im QThread: Gemini (falls Key hinterlegt) -> Fallback regelbasiert -> Tools ausfuehren."""

    finished = pyqtSignal(bool, str, str)     # ok, Nachricht, Benachrichtigungstitel ("" = keine)

    MAX_STEPS = 4

    def __init__(self, text: str, cfg: dict, history: list[tuple[str, str]],
                 pending: Optional[tuple[str, dict]] = None):
        super().__init__()
        self.text = text
        self.cfg = cfg
        self.history = history
        self.pending = pending                 # (tool, args) aus der letzten Rueckfrage, falls vorhanden
        self.new_pending: Optional[tuple[str, dict]] = None   # gesetzt, wenn jetzt eine Rueckfrage gestellt wird
        self.results: list[ToolResult] = []
        self.action: Optional[str] = None
        self.action_data: Optional[dict] = None

    @property
    def user_name(self) -> str:
        return str(self.cfg.get("pet", {}).get("user_name") or "").strip() or "Boss"

    @property
    def character_id(self) -> str:
        return self.cfg.get("pet", {}).get("character") or "cat_mochi"

    def _ask_confirmation(self, tool: str, args: dict) -> str:
        self.new_pending = (tool, dict(args))
        return confirm_question(tool, args, self.user_name, self.character_id)

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
        if gemini.has_key():
            return "gemini"
        return None

    def _process(self) -> tuple[bool, str, str]:
        tools.set_context(self.user_name, self.character_id)

        # Antwort auf eine offene Rueckfrage: ja -> ausfuehren, nein -> verwerfen, sonst normal weiter
        if self.pending:
            tool, args = self.pending
            if is_yes(self.text):
                res = tools.execute(tool, args)
                self.results.append(res)
                return res.ok, res.message, res.notify_title or ""
            if is_no(self.text):
                cinfo = get_character_info(self.character_id)
                return True, f"{cinfo.get('sound', '')} Okay, lasse ich bleiben, {self.user_name}! {cinfo.get('emoji', '')}".strip(), ""

        # Namensreaktion pruefen (Offline / Schnell-Antwort)
        char_name = str(self.cfg.get("pet", {}).get("name") or get_character_info(self.character_id).get("name", "Kylie"))
        nr = name_reaction(self.text, char_name, self.user_name)
        if nr:
            if nr.kind == "call":
                return True, nr.reply or f"Ja? 😺 Was gibt's, {self.user_name}?", ""
            if nr.kind == "who":
                return True, nr.reply or f"Ich bin {char_name}! 🐾", ""
            if nr.kind == "prefix" and nr.rest:
                self.text = nr.rest

        # Geburtstagserkennung
        from daily import parse_birthday_mention
        bday = parse_birthday_mention(self.text, datetime.date.today())
        if bday:
            b_day, b_mon, next_d = bday
            priv = self.cfg.get("privacy", {}) if isinstance(self.cfg.get("privacy"), dict) else {}
            if priv.get("remember", True):
                try:
                    from memory_store import get_memory_store
                    store = get_memory_store()
                    store.add_fact(f"Geburtstag von {self.user_name} am {b_day}.{b_mon:02d}.", due_date=next_d.strftime("%Y-%m-%d"), kind="birthday")
                except Exception:
                    pass
            cinfo = get_character_info(self.character_id)
            return True, f"Oh, das merke ich mir, {self.user_name}! Dein Geburtstag am {b_day}.{b_mon:02d}. ist notiert 🎂🎉 {cinfo.get('emoji', '🐾')}".strip(), ""

        llm_error = ""
        provider = self._provider()
        if provider:
            try:
                text = self._chat_cli()
                if self.new_pending:
                    return True, text, ""
                ok = all(r.ok for r in self.results) if self.results else True
                if not text:
                    text = self.results[-1].message if self.results else "Miau? Dazu fallen mir keine Worte ein \U0001F63A"
                return ok, text, self._notify_title()
            except LLMError as exc:
                llm_error = str(exc)
                self.results.clear()
                self.new_pending = None
                if "api-key" in llm_error.lower():
                    return False, llm_error, ""

        # Offline / Fallback
        plan = parse_offline(self.text, self.user_name, self.character_id)
        if plan.tool == "start_it_guide":
            return True, "Für die Klick-Anleitung brauche ich meinen Gemini-Key 🔑", ""
        if plan.tool in DANGEROUS_TOOLS:
            return True, self._ask_confirmation(plan.tool, plan.args), ""
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

    # -- Gemini API (JSON Tool-Calling Protokoll) ---------------------------------------
    def _chat_cli(self) -> str:
        ai = self.cfg.get("ai", {})
        timeout = float(ai.get("timeout_s", 60))
        model = ai.get("model") or None
        pet_name = self.cfg.get("pet", {}).get("name", "Kylie")
        user = self.user_name

        tool_specs_json = json.dumps([
            {"name": s["name"], "description": s["description"], "parameters": s["parameters"]}
            for s in tools.TOOL_SPECS
        ], ensure_ascii=False)

        tool_history: list[dict] = []
        priv = self.cfg.get("privacy", {})

        for step in range(self.MAX_STEPS):
            prompt_parts = [
                system_prompt(pet_name, user, self.character_id),
            ]
            p_block = profile_prompt(self.cfg)
            if p_block:
                prompt_parts.append(f"\n{p_block}\n")
            prompt_parts.append(f"\nVERFÜGBARE WERKZEUGE:\n{tool_specs_json}\n")

            if priv.get("remember", True):
                try:
                    from memory_store import get_memory_store
                    store = get_memory_store()
                    facts = store.facts()[:30]
                    if facts:
                        f_lines = [f"- {f['text']}" for f in facts]
                        prompt_parts.append(f"WAS DU \u00dcBER {user.upper()} WEISST:\n" + "\n".join(f_lines) + "\n")
                except Exception:
                    pass

            if priv.get("use_history", True):
                try:
                    from memory_store import get_memory_store
                    store = get_memory_store()
                    snippets = store.relevant_snippets(self.text, limit=3)
                    if snippets:
                        s_lines = [f"- „{snip}“" for snip in snippets]
                        prompt_parts.append("FR\u00dcHERE GESPR\u00c4CHE, DIE PASSEN K\u00d6NNTEN:\n" + "\n".join(s_lines) + "\n")
                except Exception:
                    pass

            if self.history:
                prompt_parts.append("BISHERIGER GESPR\u00c4CHSVERLAUF:")
                for r, t in self.history:
                    role_str = user if r == "user" else pet_name
                    prompt_parts.append(f"{role_str}: {t}")
                prompt_parts.append("")

            prompt_parts.append(f"AKTUELLE NACHRICHT VON {user.upper()}:\n{self.text}\n")

            if tool_history:
                prompt_parts.append("ERGEBNISSE BEREITS AUSGEF\u00dcHRTER WERKZEUGE DIESER RUNDE:")
                for th in tool_history:
                    prompt_parts.append(f"- Tool '{th['name']}' mit Parametern {json.dumps(th['args'])} -> Ergebnis: {th['result']}")
                prompt_parts.append("")

            lang_line = "Answer in English.\n" if i18n.lang() == "en" else "Antworte auf Deutsch.\n"
            prompt_parts.append(
                "ANTWORT-REGEL:\n"
                f"{lang_line}"
                "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Markdown-Formatierung:\n"
                "{\"say\": \"<kurze Antwort an den User oder leer>\", \"tool\": null, \"remember\": [], \"remember_dates\": []}\n"
                "oder\n"
                "{\"say\": \"\", \"tool\": {\"name\": \"<tool_name>\", \"args\": {...}}, \"remember\": [], \"remember_dates\": []}\n"
                "W\u00e4hle ein Werkzeug nur dann, wenn es f\u00fcr die Anfrage des Nutzers wirklich erforderlich ist. "
                "Wenn der Nutzer dauerhaft n\u00fctzliche Fakten \u00fcber sich erz\u00e4hlt (Vorlieben, Hobbys, Geburtstage, Termine), nutze 'remember': [\"Fakt\"] "
                "bzw. 'remember_dates': [{\"text\": \"...\", \"date\": \"YYYY-MM-DD\"}]. "
                "WICHTIG: Merke dir NIEMALS sensible Daten wie Passw\u00f6rter, Adressen, Gesundheit oder Bankdaten! "
                "Wenn alle Aufgaben erledigt sind oder keine Werkzeuge n\u00f6tig sind, setze 'tool' auf null und formuliere eine nette Antwort in 'say'."
            )

            full_prompt = "\n".join(prompt_parts)
            raw_response = gemini.ask(full_prompt, timeout_s=timeout, model=model)

            cli_resp = parse_cli_response(raw_response)
            say_text = cli_resp.say
            tool_call = cli_resp.tool

            if (cli_resp.remember or cli_resp.remember_dates) and priv.get("remember", True):
                try:
                    from memory_store import get_memory_store
                    m_store = get_memory_store()
                    for f_item in cli_resp.remember:
                        m_store.add_fact(f_item, kind="fact")
                    for d_item in cli_resp.remember_dates:
                        m_store.add_fact(d_item["text"], due_date=d_item.get("date"), kind="date")
                    noted = " 📝 Noted!" if i18n.lang() == "en" else " 📝 Gemerkt!"
                    if "gemerkt" not in say_text.lower() and "noted" not in say_text.lower():
                        say_text = f"{say_text}{noted}".strip()

                except Exception as exc:
                    logger.warning(f"Konnte Fakten nicht speichern: {exc}")

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

            if tool_name == "start_it_guide":
                self.action = "it_guide"
                q = str(tool_args.get("question", "")).strip() or self.text
                self.action_data = {"question": q}
                return say_text or "IT-Support-Modus aktiviert! 🕶️ Ich zeig's dir Schritt für Schritt."

            if tool_name in DANGEROUS_TOOLS:
                return self._ask_confirmation(tool_name, tool_args)

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
    it_guide_requested = pyqtSignal(str)     # Frage fuer Klick-Anleitung

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._busy = False
        self._history: list[tuple[str, str]] = []
        self._threads: set[QThread] = set()
        self._current_text = ""
        self._worker: Optional[AgentWorker] = None
        # (tool, args) eines gefaehrlichen Tools, das auf "ja" des Nutzers wartet; sonst None
        self.pending_action: Optional[tuple[str, dict]] = None

    def record_assistant_message(self, message: str) -> None:
        """Merkt sich eine autonome Äußerung oder Rückfrage des Buddys im Gesprächsverlauf."""
        msg = (message or "").strip()
        if msg:
            self._history.append(("assistant", msg))
            self._history = self._history[-24:]

    def clear_history(self) -> None:
        self._history.clear()
        self.pending_action = None

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
        worker = AgentWorker(text, self._cfg.snapshot(), list(self._history[-18:]), self.pending_action)
        self.pending_action = None          # jede Nachricht verbraucht die offene Rueckfrage
        self._worker = worker
        worker.moveToThread(thread)
        thread._worker = worker          # Referenz halten, sonst raeumt Python den Worker vorzeitig ab
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_done)
        worker.finished.connect(thread.quit)
        # Gebundene Methode dieses (Main-Thread-)Objekts -> Qt reiht den Aufruf in den Main-Thread ein.
        # Lambdas liefen hier im Worker-Thread und raeumten den QThread ab, waehrend er noch lief.
        thread.finished.connect(self._reap_threads)
        self._threads.add(thread)
        thread.start()
        self.started.emit(text)
        return True

    @pyqtSlot(bool, str, str)
    def _on_done(self, ok: bool, message: str, notify: str) -> None:
        self._busy = False
        guide_q = None
        if self._worker is not None:
            self.pending_action = self._worker.new_pending
            if getattr(self._worker, "action", None) == "it_guide" and getattr(self._worker, "action_data", None):
                guide_q = self._worker.action_data.get("question", self._current_text)
            self._worker = None
        self._history.append(("user", self._current_text))
        self._history.append(("assistant", message))
        self._history = self._history[-24:]

        try:
            priv = self._cfg.get("privacy", {}) if hasattr(self._cfg, "get") else {}
            if isinstance(priv, dict) and priv.get("save_chats", True):
                from memory_store import get_memory_store
                store = get_memory_store()
                pet_cfg = self._cfg.get("pet", {}) if hasattr(self._cfg, "get") else {}
                char_id = pet_cfg.get("character", "cat_mochi") if isinstance(pet_cfg, dict) else "cat_mochi"
                store.add_message("user", self._current_text, char_id)
                store.add_message("assistant", message, char_id)
        except Exception as exc:
            logger.warning(f"Konnte Chat nicht speichern: {exc}")

        self.finished.emit(ok, message, notify)
        if guide_q:
            self.it_guide_requested.emit(guide_q)

    @pyqtSlot()
    def _reap_threads(self) -> None:
        for t in [t for t in self._threads if t.isFinished()]:
            self._threads.discard(t)
            t.deleteLater()

    def shutdown(self, wait_ms: int = 1500) -> bool:
        """Wartet kurz auf laufende Worker. True = alle beendet."""
        for t in list(self._threads):
            t.quit()
            t.wait(wait_ms)
        return not any(t.isRunning() for t in self._threads)
