# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Internationalisierung (i18n) fuer Desktop Cat (Phase 7).

Unterstuetzt Deutsch ('de') und Englisch ('en').
"""
from __future__ import annotations

from typing import Any

_LANG = "de"

STRINGS: dict[str, dict[str, str]] = {
    # -- Kontext- & Tray-Menue ---------------------------------------------------------
    "menu.hide_pet": {
        "de": "🙈  {name} ausblenden (Päuschen)",
        "en": "🙈  Hide {name} (Take a break)",
    },
    "menu.show_pet": {
        "de": "👁️  {name} wieder anzeigen",
        "en": "👁️  Show {name}",
    },
    "menu.focus_mode": {
        "de": "🎯  Fokus-Modus (Katze pausieren)",
        "en": "🎯  Focus Mode (Pause pet)",
    },
    "menu.end_focus_mode": {
        "de": "🎯  Fokus-Modus beenden",
        "en": "🎯  End Focus Mode",
    },
    "menu.feed_pet": {
        "de": "🐟  {name} füttern (Leckerli)",
        "en": "🐟  Feed {name} (Treat)",
    },
    "menu.sub_learn": {
        "de": "💖  Freundschaft & Lernen",
        "en": "💖  Friendship & Learning",
    },
    "menu.sub_tools": {
        "de": "📝  Notizen & Hilfe",
        "en": "📝  Notes & Help",
    },
    "tray.pet_hidden_notify": {
        "de": "{name} macht ein Päuschen! 💤 Klicke auf das Icon in der Taskleiste oder drücke {hotkey}, um sie zurückzuholen.",
        "en": "{name} is taking a break! 💤 Click the taskbar icon or press {hotkey} to bring them back.",
    },
    "menu.enter_key": {
        "de": "🔑  Gemini-Key eintragen",
        "en": "🔑  Enter Gemini Key",
    },
    "menu.input": {
        "de": "💬  Befehl eingeben",
        "en": "💬  Enter Command",
    },
    "menu.friendship": {
        "de": "💖  Freundschaft",
        "en": "💖  Friendship",
    },
    "menu.focus_stats": {
        "de": "📊  Fokus-Statistik",
        "en": "📊  Focus Stats",
    },
    "menu.flashcards": {
        "de": "📚  Lernkarten",
        "en": "📚  Flashcards",
    },
    "menu.photo": {
        "de": "📸  Foto mit {name}",
        "en": "📸  Photo with {name}",
    },
    "menu.new_note": {
        "de": "📝  Neue Haftnotiz",
        "en": "📝  New Sticky Note",
    },
    "menu.error_doctor": {
        "de": "🩺  Was heißt dieser Fehler?",
        "en": "🩺  What does this error mean?",
    },
    "menu.chats": {
        "de": "📚  Meine Chats",
        "en": "📚  My Chats",
    },
    "menu.data": {
        "de": "🔒  Meine Daten",
        "en": "🔒  My Data",
    },
    "menu.onboarding": {
        "de": "✨  Kennenlernen wiederholen",
        "en": "✨  Repeat Onboarding",
    },
    "menu.choose_char": {
        "de": "🎭  Charakter wählen",
        "en": "🎭  Choose Character",
    },
    "menu.tricks": {
        "de": "✨  Tricks & Spaß",
        "en": "✨  Tricks & Fun",
    },
    "menu.dance": {
        "de": "💃  {name}, tanz für mich!",
        "en": "💃  {name}, dance for me!",
    },
    "menu.cool": {
        "de": "🕶️  Coole Pose (Sonnenbrille)",
        "en": "🕶️  Cool Pose (Sunglasses)",
    },
    "menu.push": {
        "de": "💨  Hau-Ruck! Schiebe-Animation",
        "en": "💨  Heave-ho! Push animation",
    },
    "menu.chase": {
        "de": "🐭  Fang die Maus! (15 s)",
        "en": "🐭  Catch the mouse! (15 s)",
    },
    "menu.treat": {
        "de": "🍖  Leckerli geben",
        "en": "🍖  Give a treat",
    },
    "menu.sleep": {
        "de": "💤  Schlafen legen",
        "en": "💤  Go to sleep",
    },
    "menu.wake": {
        "de": "🐾  Aufwecken",
        "en": "🐾  Wake up",
    },
    "menu.quick_tools": {
        "de": "⚡  Schnell-Tools",
        "en": "⚡  Quick Tools",
    },
    "menu.push_windows": {
        "de": "💨  Fenster wegschieben...",
        "en": "💨  Push windows aside...",
    },
    "menu.no_windows": {
        "de": "Keine Fenster gefunden",
        "en": "No windows found",
    },
    "menu.pomodoro_25": {
        "de": "⏱️  25 Min. Pomodoro-Fokus",
        "en": "⏱️  25 min. Pomodoro Focus",
    },
    "menu.pause_5": {
        "de": "⏱️  5 Min. Kurzpause",
        "en": "⏱️  5 min. Short Break",
    },
    "menu.live_weather": {
        "de": "☀️  Live-Wetterbericht",
        "en": "☀️  Live Weather Report",
    },
    "menu.clean_pc": {
        "de": "🧹  Papierkorb & Temp leeren",
        "en": "🧹  Clean Recycle Bin & Temp",
    },
    "menu.network_ip": {
        "de": "🌐  Netzwerk & IP-Info",
        "en": "🌐  Network & IP Info",
    },
    "menu.watch_screen": {
        "de": "👁️  Bildschirm beobachten (Vision)",
        "en": "👁️  Watch Screen (Vision)",
    },
    "menu.create_word": {
        "de": "📄  Word am Desktop erstellen",
        "en": "📄  Create Word Doc on Desktop",
    },
    "menu.create_ppt": {
        "de": "📊  PowerPoint am Desktop erstellen",
        "en": "📊  Create PowerPoint on Desktop",
    },
    "menu.screenshot": {
        "de": "📸  Desktop Screenshot",
        "en": "📸  Desktop Screenshot",
    },
    "menu.tidy_desktop": {
        "de": "🧹  Desktop aufräumen",
        "en": "🧹  Clean up Desktop",
    },
    "menu.datetime": {
        "de": "🕒  Datum & Uhrzeit",
        "en": "🕒  Date & Time",
    },
    "menu.systeminfo": {
        "de": "💻  System-Status",
        "en": "💻  System Status",
    },
    "menu.vol_up": {
        "de": "🔊  Lauter (+10%)",
        "en": "🔊  Volume Up (+10%)",
    },
    "menu.vol_down": {
        "de": "🔉  Leiser (-10%)",
        "en": "🔉  Volume Down (-10%)",
    },
    "menu.mute": {
        "de": "🔇  Stumm / Mute",
        "en": "🔇  Mute",
    },
    "menu.play_pause": {
        "de": "▶️  Musik Play/Pause",
        "en": "▶️  Music Play/Pause",
    },
    "menu.folders": {
        "de": "📂  Ordner öffnen",
        "en": "📂  Open Folders",
    },
    "menu.folder_downloads": {
        "de": "📥  Downloads",
        "en": "📥  Downloads",
    },
    "menu.folder_docs": {
        "de": "📄  Dokumente",
        "en": "📄  Documents",
    },
    "menu.folder_desktop": {
        "de": "🖥️  Desktop",
        "en": "🖥️  Desktop",
    },
    "menu.folder_trash": {
        "de": "🗑️  Papierkorb",
        "en": "🗑️  Recycle Bin",
    },
    "menu.reset_taskbar": {
        "de": "🏠  Zur Taskleiste zurücksetzen",
        "en": "🏠  Reset to Taskbar",
    },
    "menu.settings": {
        "de": "⚙️  Einstellungen",
        "en": "⚙️  Settings",
    },
    "menu.about": {
        "de": "ℹ️  Über Desktop Cat (v{version})",
        "en": "ℹ️  About Desktop Cat (v{version})",
    },
    "menu.quit": {
        "de": "👋  Beenden",
        "en": "👋  Quit",
    },
    "menu.check_updates": {
        "de": "🔄 Nach Updates suchen",
        "en": "🔄 Check for Updates",
    },
    "menu.install_update": {
        "de": "✨ Update auf v{version} installieren",
        "en": "✨ Install update to v{version}",
    },

    # -- Einstellungen -----------------------------------------------------------------
    "settings.title": {
        "de": "Einstellungen – Desktop Cat",
        "en": "Settings – Desktop Cat",
    },
    "settings.language": {
        "de": "Sprache:",
        "en": "Language:",
    },
    "settings.general": {
        "de": "Allgemein",
        "en": "General",
    },
    "settings.ai": {
        "de": "KI & Gehirn",
        "en": "AI & Brain",
    },
    "settings.wellbeing": {
        "de": "Wohlbefinden",
        "en": "Wellbeing",
    },
    "settings.privacy": {
        "de": "Datenschutz",
        "en": "Privacy",
    },
    "settings.autostart": {
        "de": "Mit Windows starten (Autostart)",
        "en": "Start with Windows (Autostart)",
    },
    "settings.wander": {
        "de": "Autonomes Wandern am Bildschirm",
        "en": "Autonomous wandering on screen",
    },
    "settings.pet_name": {
        "de": "Name der Figur:",
        "en": "Pet Name:",
    },
    "settings.user_name": {
        "de": "Wie soll die Figur dich nennen?",
        "en": "What should your pet call you?",
    },
    "settings.save": {
        "de": "Speichern",
        "en": "Save",
    },
    "settings.cancel": {
        "de": "Abbrechen",
        "en": "Cancel",
    },
    "settings.tab_appearance": {
        "de": "🎨  Aussehen & Style",
        "en": "🎨  Appearance & Style",
    },
    "settings.tab_behavior": {
        "de": "🐾  Verhalten & Katze",
        "en": "🐾  Behavior & Pet",
    },
    "settings.tab_ai": {
        "de": "🤖  Gemini-KI & Sprache",
        "en": "🤖  Gemini AI & Language",
    },
    "settings.tab_wellbeing": {
        "de": "🌿  Wohlbefinden & Alltag",
        "en": "🌿  Wellbeing & Daily",
    },
    "settings.tab_system": {
        "de": "⚙️  System & Hotkeys",
        "en": "⚙️  System & Hotkeys",
    },
    "settings.opacity": {
        "de": "Deckkraft / Transparenz:",
        "en": "Opacity / Transparency:",
    },
    "settings.always_on_top": {
        "de": "Immer im Vordergrund (über allen Fenstern)",
        "en": "Always on top (above all windows)",
    },
    "settings.sound_enabled": {
        "de": "Sound-Effekte bei Klicks & Aktionen",
        "en": "Sound effects on clicks & actions",
    },
    "settings.bubble_seconds": {
        "de": "Sprechblasen-Dauer:",
        "en": "Speech bubble duration:",
    },
    "settings.worn_accessory": {
        "de": "Outfit / Accessoire:",
        "en": "Outfit / Accessory:",
    },
    "settings.preview_title": {
        "de": "Charakter-Vorschau",
        "en": "Character Preview",
    },
    "settings.hide_pet_btn": {
        "de": "🙈  Katze jetzt ausblenden (Päuschen)",
        "en": "🙈  Hide pet now (Take a break)",
    },
    "settings.open_cfg": {
        "de": "config.json öffnen",
        "en": "Open config.json",
    },
    "settings.my_data": {
        "de": "🔒  Meine Daten",
        "en": "🔒  My Data",
    },

    # -- Standard-Sprechblasen-Meldungen ------------------------------------------------
    "bubble.working": {
        "de": "Ich bin dran... 🐾",
        "en": "Working on it... 🐾",
    },
    "bubble.busy_wait": {
        "de": "Moment, ich bin noch dran... 🛠️",
        "en": "One moment, still working... 🛠️",
    },
    "bubble.done": {
        "de": "Fertig! ✨  ",
        "en": "Done! ✨  ",
    },
    "bubble.timer_expired": {
        "de": "⏰ {sound}, {user}! Dein Timer für „{label}“ ({time_hint}) ist abgelaufen! {emoji}",
        "en": "⏰ {sound}, {user}! Your timer for \"{label}\" ({time_hint}) is up! {emoji}",
    },
    "bubble.wake_stretch": {
        "de": "Mrrrp… ich bin wach! 😽",
        "en": "Mrrrp… I'm awake! 😽",
    },
    "bubble.treat_thanks": {
        "de": "{sound} Danke, {user}! 🍖 Schon {count} Leckerli bekommen! 💖",
        "en": "{sound} Thanks, {user}! 🍖 Received {count} treats so far! 💖",
    },
    "bubble.battery_warn": {
        "de": "Achtung, Akku fast leer ({percent}%)! 🔌 Steck mich bitte an!",
        "en": "Warning, battery low ({percent}%)! 🔌 Please plug me in!",
    },
    "bubble.water_reminder": {
        "de": "Kleiner Schluck Wasser gefällig, {user}? 💧",
        "en": "Time for a sip of water, {user}? 💧",
    },
    "bubble.break_reminder": {
        "de": "Zeit für eine kurze Bildschirmpause, {user}! 🐾 Kurz strecken?",
        "en": "Time for a quick screen break, {user}! 🐾 Stretch a bit?",
    },
    "bubble.photo_warning": {
        "de": "Achtung, der ganze Bildschirm ist auf dem Foto mit {name} 📸",
        "en": "Notice: the entire screen is on the photo with {name} 📸",
    },
    "bubble.photo_saved": {
        "de": "Klick! 📸 Wunderschön geworden! ✨",
        "en": "Click! 📸 Turned out wonderful! ✨",
    },
    "bubble.note_stuck": {
        "de": "Haftnotiz angeklebt! 📌",
        "en": "Sticky note attached! 📌",
    },
    "bubble.note_done": {
        "de": "Erledigt! Super gemacht! ✨",
        "en": "Done! Great job! ✨",
    },

    # -- Freundschaft & Belohnungen ----------------------------------------------------
    "friendship.title": {
        "de": "💖 Freundschaft mit {name}",
        "en": "💖 Friendship with {name}",
    },
    "friendship.level": {
        "de": "💖 Level {level}: {title}",
        "en": "💖 Level {level}: {title}",
    },
    "friendship.progress_title": {
        "de": "Fortschritt zum nächsten Level",
        "en": "Progress to next level",
    },
    "friendship.points_info": {
        "de": "{pts} / {next_pts} Punkte ({pct}%) • Noch {remain} Punkte bis Level {next_lvl}",
        "en": "{pts} / {next_pts} points ({pct}%) • {remain} points until Level {next_lvl}",
    },
    "friendship.max_level": {
        "de": "{pts} Punkte • Maximales Freundschafts-Level erreicht! 🌟",
        "en": "{pts} points • Maximum friendship level reached! 🌟",
    },
    "friendship.rewards_box": {
        "de": "Freigeschaltete Belohnungen & Accessoires",
        "en": "Unlocked Rewards & Accessories",
    },
    "friendship.equip": {
        "de": "Anziehen",
        "en": "Equip",
    },
    "friendship.unequip": {
        "de": "✔ Ablegen",
        "en": "✔ Unequip",
    },
    "friendship.unlock_at": {
        "de": "ab {pts} Pkt.",
        "en": "from {pts} pts",
    },
    "friendship.close": {
        "de": "Schließen",
        "en": "Close",
    },
    "friendship.levelup_msg": {
        "de": "Level {level}! Wir sind jetzt {title}, {user} 💖{reward}",
        "en": "Level {level}! We are now {title}, {user} 💖{reward}",
    },
    "friendship.reward_unlocked": {
        "de": " Belohnung freigeschaltet: {reward}! 🎁",
        "en": " Reward unlocked: {reward}! 🎁",
    },
    "friendship.header": {
        "de": "<b>{name}</b> & Du",
        "en": "<b>{name}</b> & You",
    },
    "friendship.level_header": {
        "de": "💖 Level {lvl}: <span style='color: #EC4899;'>{title}</span>",
        "en": "💖 Level {lvl}: <span style='color: #EC4899;'>{title}</span>",
    },

    # -- Fokus & Pomodoro --------------------------------------------------------------
    "focus.title": {
        "de": "📊 Fokus-Statistik & Pomodoro",
        "en": "📊 Focus Stats & Pomodoro",
    },
    "focus.today_title": {
        "de": "⏱️ <b>Heute fokussiert</b>",
        "en": "⏱️ <b>Focused Today</b>",
    },
    "focus.minutes_label": {
        "de": "{mins} Min.",
        "en": "{mins} min.",
    },
    "focus.sessions_label": {
        "de": "{count} Pomodoro{suffix}",
        "en": "{count} Pomodoro{suffix}",
    },
    "focus.streak_title": {
        "de": "🔥 <b>Fokus-Serie</b>",
        "en": "🔥 <b>Focus Streak</b>",
    },
    "focus.streak_days": {
        "de": "{days} {unit}",
        "en": "{days} {unit}",
    },
    "focus.day_singular": {
        "de": "Tag",
        "en": "day",
    },
    "focus.days_plural": {
        "de": "Tage",
        "en": "days",
    },
    "focus.streak_sub_active": {
        "de": "In Folge am Ball! 💪",
        "en": "Days in a row! 💪",
    },
    "focus.streak_sub_zero": {
        "de": "Starte heute deine Serie!",
        "en": "Start your streak today!",
    },
    "focus.weekly_box": {
        "de": "Vergangene 7 Tage",
        "en": "Past 7 Days",
    },
    "focus.quote_high": {
        "de": "„Wahnsinn, du bist heute eine echte Fokus-Maschine, Boss! Weiter so!“ {emoji}",
        "en": "\"Awesome, you're a real focus machine today, boss! Keep it up!\" {emoji}",
    },
    "focus.quote_mid": {
        "de": "„Gute Arbeit! Jeder Pomodoro bringt dich deinem Ziel näher.“ {emoji}",
        "en": "\"Great work! Every Pomodoro brings you closer to your goal.\" {emoji}",
    },
    "focus.quote_zero": {
        "de": "„Bereit für etwas Produktivität? Sag mir einfach: 'Pomodoro starten'! ⏱️“ {emoji}",
        "en": "\"Ready for some productivity? Just say: 'Start Pomodoro'! ⏱️\" {emoji}",
    },
    "focus.close": {
        "de": "Fertig",
        "en": "Done",
    },

    # -- Lernkarten --------------------------------------------------------------------
    "cards.title": {
        "de": "📚 Lernkarten & Vokabel-Trainer",
        "en": "📚 Flashcards & Vocabulary Trainer",
    },
    "cards.deck_label": {
        "de": "<b>Aktuelles Deck:</b>",
        "en": "<b>Current Deck:</b>",
    },
    "cards.new_deck": {
        "de": "➕ Neues Deck",
        "en": "➕ New Deck",
    },
    "cards.header_front": {
        "de": "Vorderseite (Frage)",
        "en": "Front (Question)",
    },
    "cards.header_back": {
        "de": "Rückseite (Antwort)",
        "en": "Back (Answer)",
    },
    "cards.header_box": {
        "de": "Box",
        "en": "Box",
    },
    "cards.box_label": {
        "de": "Box {box}",
        "en": "Box {box}",
    },
    "cards.ph_front": {
        "de": "Vorderseite / Wort",
        "en": "Front / Word",
    },
    "cards.ph_back": {
        "de": "Rückseite / Übersetzung",
        "en": "Back / Translation",
    },
    "cards.add": {
        "de": "Hinzufügen",
        "en": "Add",
    },
    "cards.import": {
        "de": "📥 Text-Import",
        "en": "📥 Text Import",
    },
    "cards.import_tooltip": {
        "de": "Format: Zeilenweise 'Wort = Übersetzung'",
        "en": "Format: Line-by-line 'Word = Translation'",
    },
    "cards.ai_cards": {
        "de": "✨ KI-Karten (Gemini)",
        "en": "✨ AI Flashcards (Gemini)",
    },
    "cards.delete": {
        "de": "🗑️ Karte löschen",
        "en": "🗑️ Delete Card",
    },
    "cards.start_quiz": {
        "de": "▶ Quiz starten",
        "en": "▶ Start Quiz",
    },
    "cards.new_deck_title": {
        "de": "Neues Deck",
        "en": "New Deck",
    },
    "cards.new_deck_prompt": {
        "de": "Name des neuen Decks:",
        "en": "Name of the new deck:",
    },
    "cards.import_dlg_title": {
        "de": "Lernkarten aus Text importieren",
        "en": "Import Flashcards from Text",
    },
    "cards.import_dlg_desc": {
        "de": "Füge hier deine Karten ein (eine pro Zeile, z. B. <i>Hund = dog</i>):",
        "en": "Paste your cards here (one per line, e.g. <i>dog = Hund</i>):",
    },
    "cards.import_ph": {
        "de": "Guten Tag = Hello\nKatze = Cat\nApfel = Apple",
        "en": "Hello = Guten Tag\nCat = Katze\nApple = Apfel",
    },
    "cards.btn_import": {
        "de": "Importieren",
        "en": "Import",
    },
    "cards.import_err_title": {
        "de": "Import",
        "en": "Import",
    },
    "cards.import_err_msg": {
        "de": "Keine gültigen Zeilen im Format 'Vorderseite = Rückseite' gefunden.",
        "en": "No valid lines in format 'Front = Back' found.",
    },
    "cards.import_succ_title": {
        "de": "Import erfolgreich",
        "en": "Import Successful",
    },
    "cards.import_succ_msg": {
        "de": "{count} Karten zum Deck '{deck}' hinzugefügt! 🎉",
        "en": "Added {count} cards to deck '{deck}'! 🎉",
    },
    "cards.ai_nokey_title": {
        "de": "Gemini-Key fehlt",
        "en": "Gemini Key Missing",
    },
    "cards.ai_nokey_msg": {
        "de": "Für KI-generierte Lernkarten wird ein kostenloser Gemini-Key benötigt.\nKlicke mit der rechten Maustaste auf {name} -> 'Gemini-Key eintragen'.",
        "en": "A free Gemini key is required for AI flashcards.\nRight-click on {name} -> 'Enter Gemini Key'.",
    },
    "cards.ai_topic_title": {
        "de": "KI-Lernkarten generieren",
        "en": "Generate AI Flashcards",
    },
    "cards.ai_topic_prompt": {
        "de": "Zu welchem Thema möchtest du 10 Lernkarten?\n(z. B. 'Englisch Vokabeln Restaurant' oder 'Photosynthese'):",
        "en": "What topic would you like 10 flashcards for?\n(e.g. 'Restaurant Spanish' or 'Photosynthesis'):",
    },
    "cards.ai_err_title": {
        "de": "KI-Fehler",
        "en": "AI Error",
    },
    "cards.ai_err_msg": {
        "de": "Konnte keine Karten erstellen:\n{err}",
        "en": "Could not generate cards:\n{err}",
    },
    "cards.ai_succ_title": {
        "de": "Lernkarten erstellt",
        "en": "Flashcards Created",
    },
    "cards.ai_succ_msg": {
        "de": "{count} Lernkarten zum Thema '{topic}' hinzugefügt! ✨",
        "en": "Added {count} flashcards on topic '{topic}'! ✨",
    },
    "cards.ai_parse_err": {
        "de": "Konnte keine gültigen Karten aus der KI-Antwort parsen.",
        "en": "Could not parse valid cards from AI response.",
    },
    "cards.no_cards": {
        "de": "Du hast noch keine Lernkarten! 📚 Öffne per Rechtsklick '📚 Lernkarten'!",
        "en": "You don't have any flashcards yet! 📚 Right-click and choose '📚 Flashcards'!",
    },
    "cards.quiz_start_msg": {
        "de": "Quiz-Runde startet! 📚 ({count} Karten)",
        "en": "Quiz starting! 📚 ({count} cards)",
    },
    "cards.quiz_question": {
        "de": "📚 Frage {cur}/{total}:\n„{front}“\n(Tippe deine Antwort)",
        "en": "📚 Question {cur}/{total}:\n\"{front}\"\n(Type your answer)",
    },
    "cards.quiz_correct": {
        "de": "Richtig! 🌟\n„{expected}“",
        "en": "Correct! 🌟\n\"{expected}\"",
    },
    "cards.quiz_close": {
        "de": "Fast perfekt! 🎉\nRichtige Antwort: „{expected}“",
        "en": "Almost perfect! 🎉\nCorrect answer: \"{expected}\"",
    },
    "cards.quiz_wrong": {
        "de": "Leider nicht ganz! 💡\nDie Lösung war: „{expected}“",
        "en": "Not quite! 💡\nThe answer was: \"{expected}\"",
    },
    "cards.quiz_finished": {
        "de": "Quiz abgeschlossen! 🌟 {correct} von {total} richtig! (+3 Freundschaftspunkte 💖)",
        "en": "Quiz finished! 🌟 {correct} of {total} correct! (+3 friendship points 💖)",
    },

    # -- Haftnotizen -------------------------------------------------------------------
    "note.window_title": {
        "de": "Haftnotiz 📌",
        "en": "Sticky Note 📌",
    },
    "note.placeholder": {
        "de": "Notiz schreiben...",
        "en": "Write note...",
    },
    "note.color_tooltip": {
        "de": "Farbe wechseln (Gelb / Rosa / Mint)",
        "en": "Cycle color (Yellow / Pink / Mint)",
    },
    "note.done_tooltip": {
        "de": "Erledigt!",
        "en": "Done!",
    },
    "note.delete_tooltip": {
        "de": "Löschen",
        "en": "Delete",
    },

    # -- IT-Support & Guide ------------------------------------------------------------
    "guide.step_title": {
        "de": "Schritt {step}/{total}",
        "en": "Step {step}/{total}",
    },
    "guide.click_here": {
        "de": "Hier klicken",
        "en": "Click here",
    },
    "guide.done": {
        "de": "Fertig! Du hast alle Schritte geschafft 🎉",
        "en": "Done! You completed all steps 🎉",
    },
    "guide.abort": {
        "de": "Guide abgebrochen. Sag Bescheid, wenn du wieder Hilfe brauchst 🐾",
        "en": "Guide aborted. Let me know if you need help again 🐾",
    },
    "guide.btn_next": {
        "de": "Weiter ▶",
        "en": "Next ▶",
    },
    "guide.btn_abort": {
        "de": "Abbrechen ✖",
        "en": "Cancel ✖",
    },
    "guide.btn_repeat": {
        "de": "Nochmal zeigen 🔁",
        "en": "Show again 🔁",
    },
    "guide.btn_done": {
        "de": "Fertig ✖",
        "en": "Done ✖",
    },

    # -- Error Doctor ------------------------------------------------------------------
    "doctor.btn_show": {
        "de": "Zeig's mir 🕶️",
        "en": "Show me 🕶️",
    },
    "doctor.btn_close": {
        "de": "Schließen ✖",
        "en": "Close ✖",
    },

    # -- Allgemeine UI-Elemente --------------------------------------------------------
    "common.done": {
        "de": "Fertig",
        "en": "Done",
    },
    "common.close": {
        "de": "Schließen",
        "en": "Close",
    },
    "common.cancel": {
        "de": "Abbrechen",
        "en": "Cancel",
    },

    # -- Meine Daten & Datenschutz -----------------------------------------------------
    "data.title": {
        "de": "🔒 Meine Daten – Desktop Cat",
        "en": "🔒 My Data – Desktop Cat",
    },
    "data.section_facts": {
        "de": "Was {name} über dich weiß",
        "en": "What {name} knows about you",
    },
    "data.no_facts": {
        "de": "{name} hat sich noch nichts gemerkt. Erzähl ihr einfach von dir!",
        "en": "{name} hasn't remembered anything yet. Just tell them about yourself!",
    },
    "data.section_privacy": {
        "de": "Datenschutz-Einstellungen",
        "en": "Privacy Settings",
    },
    "data.chk_save_chats": {
        "de": "Chats speichern",
        "en": "Save chats",
    },
    "data.chk_remember": {
        "de": "{name} darf sich Dinge merken",
        "en": "{name} may remember facts",
    },
    "data.chk_use_history": {
        "de": "Frühere Chats nutzen, wenn sie zur Frage passen",
        "en": "Use past chats when relevant",
    },
    "data.privacy_long": {
        "de": "🔒 <b>Deine Daten bleiben auf diesem PC</b> (<code>%APPDATA%\\Mochi\\mochi.db</code>). Die Entwickler von Desktop Cat bekommen nichts.<br><br>🤖 Wenn du {name} etwas fragst, schickt sie deine Frage, deine gemerkten Fakten und höchstens 3 passende Ausschnitte aus früheren Chats an Google Gemini – nur damit die Antwort besser passt.<br><br>⚠️ Beim <b>kostenlosen</b> Gemini-Zugang darf Google gesendete Inhalte laut seinen Nutzungsbedingungen zur Verbesserung seiner Dienste verwenden und von Menschen prüfen lassen. Schreib deshalb keine Passwörter oder sehr privaten Dinge. Ohne Gemini-Key bleibt alles komplett offline.",
        "en": "🔒 <b>Your data stays on this PC</b> (<code>%APPDATA%\\Mochi\\mochi.db</code>). The developers of Desktop Cat receive nothing.<br><br>🤖 When you ask {name} something, it sends your question, remembered facts, and up to 3 relevant snippets from past chats to Google Gemini – solely to improve the answer.<br><br>⚠️ With <b>free</b> Gemini access, Google's Terms of Service allow reviewing and training on submitted content. Therefore, never enter passwords or sensitive personal data. Without a Gemini key, everything remains completely offline.",
    },
    "data.btn_del_chats": {
        "de": "🗑️  Alle Chats löschen",
        "en": "🗑️  Delete All Chats",
    },
    "data.btn_wipe_all": {
        "de": "🧹  Alles vergessen",
        "en": "🧹  Forget Everything",
    },
    "data.btn_export": {
        "de": "📤  Alles exportieren",
        "en": "📤  Export Everything",
    },
    "data.privacy_notice": {
        "de": "Kleiner Hinweis: Ich speichere unsere Chats und Dinge, die du mir erzählst, nur hier auf deinem PC 🔒 Rechtsklick → ‚Meine Daten‘ zeigt alles und löscht es mit einem Klick.",
        "en": "Privacy notice: I only save our chats and facts locally on your PC 🔒 Right-click → 'My Data' shows everything and lets you wipe it with one click.",
    },
    "data.wipe_all": {
        "de": "Alles vergessen & löschen",
        "en": "Forget & Wipe Everything",
    },
    "data.wipe_confirm": {
        "de": "Möchtest du wirklich alle Chats, Notizen, Fakten und Statistiken restlos löschen?",
        "en": "Do you really want to permanently delete all chats, notes, facts, and statistics?",
    },
    "data.wiped_success": {
        "de": "Ich habe alles vergessen! Eine saubere Weste für uns beide ✨",
        "en": "I've forgotten everything! A fresh start for both of us ✨",
    },

    # -- Meine Chats -------------------------------------------------------------------
    "chats.title": {
        "de": "📚 Chat-Verlauf – Desktop Cat",
        "en": "📚 Chat History – Desktop Cat",
    },
    "chats.title_with_name": {
        "de": "📚 Meine Chats mit {name}",
        "en": "📚 My Chats with {name}",
    },
    "chats.search_placeholder": {
        "de": "In Chats suchen...",
        "en": "Search in chats...",
    },
    "chats.empty": {
        "de": "{emoji}\n\nNoch keine Chats – sag {name} einfach Hallo! 👋",
        "en": "{emoji}\n\nNo chats yet – just say hello to {name}! 👋",
    },
    "chats.delete_conv": {
        "de": "🗑️  Gespräch löschen",
        "en": "🗑️  Delete conversation",
    },
    "chats.confirm_delete_conv": {
        "de": "Möchtest du dieses Gespräch wirklich löschen?",
        "en": "Do you really want to delete this conversation?",
    },
    "chats.confirm_delete_all": {
        "de": "Möchtest du wirklich alle Chats löschen? Das kann nicht rückgängig gemacht werden.",
        "en": "Do you really want to delete all chats? This cannot be undone.",
    },
    "chats.export": {
        "de": "Exportieren (.txt)",
        "en": "Export (.txt)",
    },
    "chats.resume": {
        "de": "Unterhaltung fortsetzen",
        "en": "Resume conversation",
    },

    # -- Gemini API --------------------------------------------------------------------
    "gemini.no_internet": {
        "de": "Keine Internetverbindung zu Gemini 📡",
        "en": "No internet connection to Gemini 📡",
    },
    "gemini.invalid_key": {
        "de": "Mein API-Key ist ungültig – bitte in den Einstellungen neu eintragen 🔑",
        "en": "My API key is invalid – please re-enter it in settings 🔑",
    },
    "gemini.quota_exceeded": {
        "de": "Mein Gratis-Kontingent ist gerade aufgebraucht – versuch es gleich nochmal 😿",
        "en": "My free quota is currently exhausted – please try again shortly 😿",
    },
    "gemini.overloaded": {
        "de": "Gemini ist gerade überlastet – versuch es gleich nochmal 😿",
        "en": "Gemini is currently overloaded – please try again shortly 😿",
    },
    "gemini.enter_key_first": {
        "de": "Bitte zuerst in den Einstellungen deinen Gemini-Key eintragen 🔑",
        "en": "Please enter your Gemini key in settings first 🔑",
    },
    "gemini.unreachable": {
        "de": "Gemini ist gerade nicht erreichbar 😿",
        "en": "Gemini is currently unreachable 😿",
    },
    "gemini.timeout": {
        "de": "Die KI antwortet nicht (Zeitüberschreitung) ⌛",
        "en": "The AI is not responding (timeout) ⌛",
    },
    "gemini.blocked": {
        "de": "Die KI wollte darauf nicht antworten",
        "en": "The AI chose not to answer this",
    },
    "gemini.error": {
        "de": "Gemini-Fehler {code}: {msg}",
        "en": "Gemini error {code}: {msg}",
    },

    # -- Tools -------------------------------------------------------------------------
    "tools.current_time": {
        "de": "Es ist {time} Uhr am {date}.",
        "en": "It is {time} on {date}.",
    },
    "tools.timer_started": {
        "de": "Timer für {duration} Sekunden gestellt.",
        "en": "Timer set for {duration} seconds.",
    },
    "tools.recycle_bin_cleaned": {
        "de": "Papierkorb und temporäre Dateien wurden bereinigt.",
        "en": "Recycle bin and temporary files have been cleaned.",
    },

    # -- Onboarding (Phase 10) ---------------------------------------------------------
    "onboarding.q1_welcome": {
        "de": "Hiii! 👋 Ich bin {name}, deine neue Desktop-Katze. Ich würde dich gern kennenlernen – ist das okay?",
        "en": "Hiii! 👋 I am {name}, your new desktop companion. I'd love to get to know you – is that okay?",
    },
    "onboarding.q1_welcome_update": {
        "de": "Ich kenn dich ja schon ein bisschen, {user_name} 😺 – darf ich dir noch ein paar Fragen stellen?",
        "en": "I already know you a little, {user_name} 😺 – may I ask you a few quick questions?",
    },
    "onboarding.q1_chip_yes": {
        "de": "Klar! 😺",
        "en": "Sure! 😺",
    },
    "onboarding.q1_chip_later": {
        "de": "Später",
        "en": "Later",
    },
    "onboarding.q2_language": {
        "de": "Hi! 👋 Welche Sprache magst du?\nWhich language do you prefer?",
        "en": "Hi! 👋 Welche Sprache magst du?\nWhich language do you prefer?",
    },
    "onboarding.q2_chip_de": {
        "de": "Deutsch 🇩🇪",
        "en": "Deutsch 🇩🇪",
    },
    "onboarding.q2_chip_en": {
        "de": "English 🇬🇧",
        "en": "English 🇬🇧",
    },
    "onboarding.q3_name": {
        "de": "Wie heißt du?",
        "en": "What's your name?",
    },
    "onboarding.q3_placeholder": {
        "de": "Dein Name (z. B. Florian)",
        "en": "Your name (e.g. Alex)",
    },
    "onboarding.q4_nickname": {
        "de": "Und wie soll ich dich nennen? Spitzname, Boss, Chef…?",
        "en": "And what should I call you? Nickname, Boss, Chief…?",
    },
    "onboarding.q4_placeholder": {
        "de": "Spitzname oder Anrede",
        "en": "Nickname or salutation",
    },
    "onboarding.q5_pronouns": {
        "de": "Wie soll ich über dich sprechen?",
        "en": "How should I refer to you?",
    },
    "onboarding.q5_chip_he": {
        "de": "er / ihm",
        "en": "he / him",
    },
    "onboarding.q5_chip_she": {
        "de": "sie / ihr",
        "en": "she / her",
    },
    "onboarding.q5_chip_they": {
        "de": "they / them",
        "en": "they / them",
    },
    "onboarding.q5_chip_name_only": {
        "de": "Einfach mein Name",
        "en": "Just use my name",
    },
    "onboarding.q6_uses": {
        "de": "Wofür nutzt du deinen PC am meisten?",
        "en": "What do you use your PC for the most?",
    },
    "onboarding.q6_chip_school": {
        "de": "Schule / Studium",
        "en": "School / Studies",
    },
    "onboarding.q6_chip_work": {
        "de": "Arbeit",
        "en": "Work",
    },
    "onboarding.q6_chip_coding": {
        "de": "Coding",
        "en": "Coding",
    },
    "onboarding.q6_chip_gaming": {
        "de": "Gaming",
        "en": "Gaming",
    },
    "onboarding.q6_chip_creative": {
        "de": "Kreativ",
        "en": "Creative",
    },
    "onboarding.q6_chip_surfing": {
        "de": "Surfen",
        "en": "Web browsing",
    },
    "onboarding.q7_interests": {
        "de": "Was machst du gern? Hobbys, Lieblingsdinge…",
        "en": "What do you like to do? Hobbies, favorite things…",
    },
    "onboarding.q7_placeholder": {
        "de": "z. B. Gitarre, Katzen, Python, Kochen...",
        "en": "e.g. Guitar, cats, Python, cooking...",
    },
    "onboarding.q8_tone": {
        "de": "Wie soll ich so drauf sein?",
        "en": "What personality style should I have?",
    },
    "onboarding.q8_chip_sweet": {
        "de": "🥰 lieb & verspielt",
        "en": "🥰 sweet & playful",
    },
    "onboarding.q8_chip_cheeky": {
        "de": "😎 frech & witzig",
        "en": "😎 cheeky & witty",
    },
    "onboarding.q8_chip_calm": {
        "de": "🧘 ruhig & kurz",
        "en": "🧘 calm & concise",
    },
    "onboarding.q8_chip_smart": {
        "de": "🤓 schlau & erklärend",
        "en": "🤓 smart & explanatory",
    },
    "onboarding.q9_chatter": {
        "de": "Wie oft darf ich mich melden?",
        "en": "How often should I pop up to chat?",
    },
    "onboarding.q9_chip_often": {
        "de": "Oft 📢",
        "en": "Often 📢",
    },
    "onboarding.q9_chip_sometimes": {
        "de": "Ab und zu 💬",
        "en": "Sometimes 💬",
    },
    "onboarding.q9_chip_rare": {
        "de": "Nur wenn du mich rufst 🤫",
        "en": "Only when called 🤫",
    },
    "onboarding.q10_city": {
        "de": "In welcher Stadt bist du ungefähr? Dann kann ich dir morgens das Wetter sagen ☀️",
        "en": "Which city are you in approximately? Then I can tell you the weather in the morning ☀️",
    },
    "onboarding.q10_placeholder": {
        "de": "z. B. Berlin, Wien, Linz...",
        "en": "e.g. Berlin, Vienna, London...",
    },
    "onboarding.q11_key": {
        "de": "Damit ich richtig schlau werde, brauche ich einen Gratis-Schlüssel von Google 🔑",
        "en": "To make me truly smart, I need a free key from Google 🔑",
    },
    "onboarding.q11_get_key": {
        "de": "🌐 Gratis-Key holen (Google AI Studio)",
        "en": "🌐 Get free key (Google AI Studio)",
    },
    "onboarding.q11_placeholder": {
        "de": "Gemini API-Key einfügen (AIzaSy...)",
        "en": "Paste Gemini API key (AIzaSy...)",
    },
    "onboarding.q11_btn_check": {
        "de": "Prüfen & Speichern",
        "en": "Verify & Save",
    },
    "onboarding.q11_skip": {
        "de": "Ohne KI weitermachen",
        "en": "Continue without AI",
    },
    "onboarding.q11_success": {
        "de": "Juhu! Der Schlüssel funktioniert! 🔑✨ Jetzt bin ich richtig schlau.",
        "en": "Yay! The key works! 🔑✨ Now I am super smart.",
    },
    "onboarding.q11_invalid": {
        "de": "Der Schlüssel konnte nicht bestätigt werden 🥺 Bitte prüfe ihn nochmal.",
        "en": "Could not verify this key 🥺 Please check it again.",
    },
    "onboarding.q12_character": {
        "de": "Willst du mich so lassen oder lieber eine andere Figur?",
        "en": "Would you like to keep me as I am, or choose another character?",
    },
    "onboarding.q12_btn_keep": {
        "de": "Mit dieser Figur weitermachen ▶",
        "en": "Continue with this character ▶",
    },
    "onboarding.q13_privacy": {
        "de": "Hier noch deine Datenschutzeinstellungen – alles bleibt auf deinem PC:",
        "en": "Here are your privacy settings – everything stays on your PC:",
    },
    "onboarding.q14_autostart": {
        "de": "Soll ich mit Windows starten?",
        "en": "Should I start automatically with Windows?",
    },
    "onboarding.q14_chip_yes": {
        "de": "Ja, immer dabei! 🚀",
        "en": "Yes, always! 🚀",
    },
    "onboarding.q14_chip_no": {
        "de": "Nein, ich starte dich selbst 💻",
        "en": "No, I'll launch you manually 💻",
    },
    "onboarding.q15_done": {
        "de": "Fertig! 🎉 Schön, dich kennenzulernen, {user_name}! Ich hüpf jetzt auf deine Taskleiste – doppelklick mich, wenn du was brauchst.",
        "en": "All done! 🎉 Nice to meet you, {user_name}! I'll hop onto your taskbar now – double-click me whenever you need something.",
    },
    "onboarding.btn_start": {
        "de": "Los geht's! 🐾",
        "en": "Let's go! 🐾",
    },
    "onboarding.btn_skip": {
        "de": "Überspringen",
        "en": "Skip",
    },
    "onboarding.btn_send": {
        "de": "Senden",
        "en": "Send",
    },
    "onboarding.btn_next": {
        "de": "Weiter ▶",
        "en": "Next ▶",
    },
    "onboarding.typing": {
        "de": "tippt…",
        "en": "typing…",
    },
    "data.section_profile": {
        "de": "👤 Dein Profil",
        "en": "👤 Your Profile",
    },
    "data.profile_name": {
        "de": "Name:",
        "en": "Name:",
    },
    "data.profile_nickname": {
        "de": "Spitzname:",
        "en": "Nickname:",
    },
    "data.profile_pronouns": {
        "de": "Pronomen:",
        "en": "Pronouns:",
    },
    "data.profile_uses": {
        "de": "PC-Nutzung:",
        "en": "PC uses:",
    },
    "data.profile_interests": {
        "de": "Interessen:",
        "en": "Interests:",
    },
    "data.profile_tone": {
        "de": "Tonfall:",
        "en": "Tone:",
    },
    "data.profile_city": {
        "de": "Stadt:",
        "en": "City:",
    },
    "data.btn_onboarding_repeat": {
        "de": "✨ Kennenlernen wiederholen",
        "en": "✨ Repeat Onboarding",
    },
    "data.btn_profile_delete": {
        "de": "Profil löschen",
        "en": "Delete Profile",
    },
    "data.confirm_delete_profile": {
        "de": "Möchtest du dein Profil wirklich zurücksetzen? (Name, Spitzname, Ton und Hobbys werden geleert)",
        "en": "Do you really want to reset your profile? (Name, nickname, tone and hobbies will be cleared)",
    },
    "tray.tooltip": {
        "de": "Desktop Cat - dein Desktop-Buddy",
        "en": "Desktop Cat - your desktop buddy",
    },
    "about.text": {
        "de": "Desktop Cat v{version} \U0001F43E\nDein KI-Desktop-Buddy!\nFreie Software unter der GNU GPL v3",
        "en": "Desktop Cat v{version} \U0001F43E\nYour AI desktop buddy!\nFree software under the GNU GPL v3",
    },
    "say.update_checking": {
        "de": "Suche nach Updates... 🔍",
        "en": "Checking for updates... 🔍",
    },
    "say.update_available": {
        "de": "Es gibt ein Update auf v{ver}! Klick mich zum Installieren ✨",
        "en": "There's an update to v{ver}! Click me to install it ✨",
    },
    "say.update_latest": {
        "de": "Du hast die neueste Version 😺",
        "en": "You have the latest version 😺",
    },
    "say.update_check_failed": {
        "de": "Konnte nicht nach Updates suchen 😿",
        "en": "Couldn't check for updates 😿",
    },
    "say.update_downloading": {
        "de": "Lade Update herunter... ⏳",
        "en": "Downloading update... ⏳",
    },
    "say.update_installing": {
        "de": "Update wird installiert... Bis gleich! 🐾",
        "en": "Installing update... See you in a moment! 🐾",
    },
    "say.update_error": {
        "de": "Update-Fehler: {err} 😿",
        "en": "Update error: {err} 😿",
    },
    "say.still_busy": {
        "de": "Moment, ich bin noch dran... \U0001F6E0\uFE0F",
        "en": "Hang on, I'm still working on it... \U0001F6E0\uFE0F",
    },
    "say.working": {
        "de": "Ich bin dran... \U0001F43E",
        "en": "On it... \U0001F43E",
    },
    "say.i_am": {
        "de": "{sound} Ich bin {name}! {emoji}",
        "en": "{sound} I'm {name}! {emoji}",
    },
    "say.treat_thanks": {
        "de": "{sound} Danke, {name}! \U0001F356 Schon {n} Leckerli bekommen! \U0001F496",
        "en": "{sound} Thanks, {name}! \U0001F356 That's {n} treats already! \U0001F496",
    },
    "say.birthday": {
        "de": "Alles Gute zum Geburtstag, {name}! 🎂🎉✨",
        "en": "Happy birthday, {name}! 🎂🎉✨",
    },
    "say.late_night_1": {
        "de": "Immer noch fleißig, {name}? Schlaf gut und erhol dich schön! 😴💤",
        "en": "Still hard at work, {name}? Sleep well and get some rest! 😴💤",
    },
    "say.late_night_2": {
        "de": "Es ist schon spät, {name} – Zeit fürs Bett? 😴",
        "en": "It's getting late, {name} – time for bed? 😴",
    },
    "say.pc_hot": {
        "de": "Puh, dein PC kocht! \U0001F975 Soll ich nachsehen, was so viel frisst? (Antworte mit Ja oder Nein)",
        "en": "Phew, your PC is boiling! \U0001F975 Want me to check what's eating so much? (Answer yes or no)",
    },
    "say.battery_low": {
        "de": "\U0001F50B Nur noch {pct} % Akku, {name}! Bitte Ladekabel anschlie\u00dfen.",
        "en": "\U0001F50B Only {pct} % battery left, {name}! Please plug in the charger.",
    },
    "say.hotkey_taken": {
        "de": "Dieses Tastenk\u00fcrzel ist schon belegt \U0001F63F Ich behalte das alte.",
        "en": "That shortcut is already taken \U0001F63F I'll keep the old one.",
    },
    "say.saved": {
        "de": "Gespeichert! \U0001F43E",
        "en": "Saved! \U0001F43E",
    },
    "say.nice_to_meet": {
        "de": "Schön dich kennenzulernen, {u}! Ich bin {cname} 🐾",
        "en": "Nice to meet you, {u}! I'm {cname} 🐾",
    },
    "say.no_cards": {
        "de": "Du hast noch keine Lernkarten! 📚 Öffne per Rechtsklick '📚 Lernkarten' oder sag 'Kylie, erstelle mir Lernkarten zu Englisch'!",
        "en": "You don't have any flashcards yet! 📚 Right-click and open '📚 Flashcards' or say 'Kylie, make me flashcards about English'!",
    },
    "say.quiz_start": {
        "de": "Quiz-Runde startet! 📚 ({n} Karten)",
        "en": "Quiz round starting! 📚 ({n} cards)",
    },
    "say.quiz_cancelled": {
        "de": "Quiz abgebrochen. Wir üben ein andermal weiter! 🐾",
        "en": "Quiz cancelled. We'll practice another time! 🐾",
    },
    "say.cards_need_key": {
        "de": "Für automatische KI-Lernkarten trage bitte erst deinen Gemini-Key ein (Rechtsklick → Gemini-Key eintragen) 🔑",
        "en": "For automatic AI flashcards, please enter your Gemini key first (right-click → Enter Gemini key) 🔑",
    },
    "say.cards_creating": {
        "de": "Ich erstelle {count} Lernkarten zu „{topic}“ für dich... 🧠📚",
        "en": "I'm creating {count} flashcards about “{topic}” for you... 🧠📚",
    },
    "say.cards_done": {
        "de": "Fertig! 🎉 {n} Lernkarten im Deck „{deck_name}“ gespeichert. Sag 'quiz starten', um loszulegen! 🐾",
        "en": "Done! 🎉 {n} flashcards saved in the deck “{deck_name}”. Say 'start quiz' to begin! 🐾",
    },
    "say.cards_failed": {
        "de": "Konnte keine Karten erstellen: {err}",
        "en": "Couldn't create any cards: {err}",
    },
    "say.photo_warn": {
        "de": "Achtung, der ganze Bildschirm ist auf dem Foto mit {cname} 📸",
        "en": "Heads up, the whole screen will be in the photo with {cname} 📸",
    },
    "say.countdown_3": {
        "de": "3... 🐾",
        "en": "3... 🐾",
    },
    "say.countdown_2": {
        "de": "2... 📸",
        "en": "2... 📸",
    },
    "say.countdown_1": {
        "de": "1... Smile! ✨",
        "en": "1... Smile! ✨",
    },
    "say.photo_done": {
        "de": "Klick! 📸 Wunderschön geworden! ✨",
        "en": "Click! 📸 It turned out beautifully! ✨",
    },
    "say.photo_done_clip": {
        "de": "Klick! 📸 Wunderschön geworden! Liegt auch in der Zwischenablage ✨",
        "en": "Click! 📸 It turned out beautifully! It's in your clipboard too ✨",
    },
    "photo.caption_prompt": {
        "de": "Schreib eine kurze, süße Bildunterschrift für ein Polaroid-Selfie von {cname} (Desktop-Haustier) mit {user}. Max. 40 Zeichen, höchstens 1 Emoji, nur der Text, keine Anführungszeichen.",
        "en": "Write a short, cute caption for a polaroid selfie of {cname} (desktop pet) with {user}. Max 40 characters, at most 1 emoji, text only, no quotes.",
    },
    "say.photo_failed": {
        "de": "Konnte kein Foto aufnehmen: {exc}",
        "en": "Couldn't take a photo: {exc}",
    },
    "say.note_stuck": {
        "de": "Haftnotiz angeklebt! 📌",
        "en": "Sticky note attached! 📌",
    },
    "say.done_great": {
        "de": "Erledigt! Super gemacht! ✨",
        "en": "Done! Well done! ✨",
    },
    "say.select_first": {
        "de": "Markier erst etwas und drück Strg+C 😺",
        "en": "Select something first and press Ctrl+C 😺",
    },
    "say.explain_need_key": {
        "de": "Für Erklärungen brauche ich meinen Gemini-Key 🔑",
        "en": "I need my Gemini key for explanations 🔑",
    },
    "say.looking": {
        "de": "Ich schau's mir an... 🐾",
        "en": "Let me take a look... 🐾",
    },
    "say.error": {
        "de": "Fehler: {err} 😿",
        "en": "Error: {err} 😿",
    },
    "say.doctor_need_key": {
        "de": "Für den Fehlermeldungs-Doktor brauche ich meinen Gemini-Key 🔑",
        "en": "I need my Gemini key for the error doctor 🔑",
    },
    "say.doctor_scanning": {
        "de": "Ich untersuche den Bildschirm... 🩺",
        "en": "Examining the screen... 🩺",
    },
    "say.doctor_error": {
        "de": "Doktor-Fehler: {err} 😿",
        "en": "Doctor error: {err} 😿",
    },
    "say.guide_need_key": {
        "de": "Für die Klick-Anleitung brauche ich meinen Gemini-Key 🔑",
        "en": "I need my Gemini key for the click guide 🔑",
    },
    "say.guide_start": {
        "de": "IT-Support-Modus aktiviert! 🕶️ Ich zeig's dir Schritt für Schritt.",
        "en": "IT support mode activated! 🕶️ I'll show you step by step.",
    },
    "say.guide_step_failed": {
        "de": "Konnte den nächsten Schritt nicht laden: {err} 😿",
        "en": "Couldn't load the next step: {err} 😿",
    },
    "say.guide_done": {
        "de": "Geschafft! 🎉",
        "en": "Done! 🎉",
    },
    "say.guide_ended": {
        "de": "Klick-Anleitung beendet! 🐾",
        "en": "Click guide finished! 🐾",
    },
    "data.del_chats_title": {
        "de": "Alle Chats löschen",
        "en": "Delete all chats",
    },
    "data.del_chats_text": {
        "de": "Möchtest du wirklich alle gespeicherten Chat-Verläufe löschen?\nGemerkte Fakten bleiben erhalten.",
        "en": "Do you really want to delete all saved chat histories?\nRemembered facts will be kept.",
    },
    "data.deleted_title": {
        "de": "Gelöscht",
        "en": "Deleted",
    },
    "data.deleted_text": {
        "de": "Alle Chat-Verläufe wurden gelöscht. 🗑️",
        "en": "All chat histories have been deleted. 🗑️",
    },
    "data.wipe_title": {
        "de": "Alles vergessen",
        "en": "Forget everything",
    },
    "data.wipe_text": {
        "de": "Wirklich alles vergessen? Das kann nicht rückgängig gemacht werden.\nAlle Chats, gemerkten Fakten und Statistiken werden unwiderruflich gelöscht.",
        "en": "Really forget everything? This cannot be undone.\nAll chats, remembered facts and statistics will be permanently deleted.",
    },
    "data.reset_title": {
        "de": "Zurückgesetzt",
        "en": "Reset",
    },
    "data.reset_text": {
        "de": "Alle Daten wurden vollständig gelöscht. 🧹✨",
        "en": "All data has been completely deleted. 🧹✨",
    },
    "data.export_title": {
        "de": "Alle Daten exportieren",
        "en": "Export all data",
    },
    "common.file_filter_txt": {
        "de": "Textdateien (*.txt);;Alle Dateien (*.*)",
        "en": "Text files (*.txt);;All files (*.*)",
    },
    "common.export_ok_title": {
        "de": "Export erfolgreich",
        "en": "Export successful",
    },
    "common.export_ok_text": {
        "de": "Deine Daten wurden nach:\n{path}\nexportiert! 📄✨",
        "en": "Your data was exported to:\n{path}\n📄✨",
    },
    "common.error_title": {
        "de": "Fehler",
        "en": "Error",
    },
    "data.onboarding_failed": {
        "de": "Konnte Kennenlernen nicht starten: {e}",
        "en": "Couldn't start the onboarding: {e}",
    },
    "data.btn_delete": {
        "de": "Löschen",
        "en": "Delete",
    },
    "data.btn_cancel": {
        "de": "Abbrechen",
        "en": "Cancel",
    },
    "chats.export_title": {
        "de": "Chat-Verlauf exportieren",
        "en": "Export chat history",
    },
    "onboarding.none": {
        "de": "Keine",
        "en": "None",
    },
    "onboarding.privacy_ack": {
        "de": "Datenschutz bestätigt ✓",
        "en": "Privacy confirmed ✓",
    },
    "onboarding.key_entered": {
        "de": "🔑 [API-Key eingegeben]",
        "en": "🔑 [API key entered]",
    },
}



def set_language(language: str) -> None:
    """Setzt die aktive Sprache ('de' oder 'en')."""
    global _LANG
    norm = (language or "").strip().lower()
    _LANG = "en" if norm.startswith("en") else "de"


def lang() -> str:
    """Gibt den aktuellen Sprachcode ('de' oder 'en') zurueck."""
    return _LANG


def tr(key: str, **kwargs: Any) -> str:
    """Uebersetzt einen Schluessel.
    
    Fallback-Reihenfolge:
    1. Gewaehlte Sprache
    2. Deutsch ('de')
    3. Der Schluessel selbst
    """
    entry = STRINGS.get(key)
    if entry is not None:
        text = entry.get(_LANG) or entry.get("de") or key
    else:
        text = key

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
