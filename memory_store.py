# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Florian Oberhumer und Stefan Wenzlhumer - Desktop Cat (siehe LICENSE)
"""Lokaler Speicher fuer Chats, gemerkte Fakten und Statistiken (SQLite)."""
from __future__ import annotations

import datetime
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from paths import DATA_DIR

STOP_WORDS = {
    "aber", "alle", "allem", "allen", "aller", "alles", "als", "also", "am", "an",
    "ander", "andere", "anderem", "anderen", "anderer", "anderes", "anderm", "andern",
    "anderr", "anders", "auch", "auf", "aus", "bei", "beide", "beiden", "beides",
    "beim", "bereits", "bist", "da", "dabei", "dadurch", "dafür", "daher", "damit",
    "dann", "darüber", "darum", "das", "dass", "dein", "deine", "deinem", "deinen",
    "deiner", "deines", "dem", "demselben", "den", "denn", "denselben", "der", "dere",
    "derem", "deren", "derer", "derselbe", "des", "desselben", "dessen", "dich",
    "die", "dies", "diese", "dieselbe", "dieselben", "diesem", "diesen", "dieser",
    "dieses", "dir", "doch", "dort", "durch", "ein", "eine", "einem", "einen",
    "einer", "eines", "einige", "einigen", "einiges", "einmal", "er", "es", "etwas",
    "euch", "euer", "eure", "eurem", "euren", "eurer", "eures", "für", "ganz",
    "gar", "habe", "haben", "hat", "hatte", "hatten", "hier", "hin", "hinter",
    "ich", "ihm", "ihn", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres",
    "im", "immer", "in", "indem", "ins", "ist", "ja", "jede", "jedem", "jeden",
    "jeder", "jedes", "jetzt", "kann", "kannst", "können", "könnt", "machen",
    "man", "mehr", "mein", "meine", "meinem", "meinen", "meiner", "meines",
    "mich", "mir", "mit", "nach", "nicht", "nichts", "noch", "nun", "nur",
    "oder", "ohne", "sehr", "sein", "seine", "seinem", "seinen", "seiner",
    "seines", "selbst", "sich", "sie", "sind", "so", "solche", "solchem",
    "solchen", "solcher", "solches", "soll", "sollte", "sonst", "über", "um",
    "und", "uns", "unser", "unsere", "unserem", "unseren", "unserer", "unseres",
    "unter", "viel", "vom", "von", "vor", "war", "waren", "warst", "was", "weg",
    "weil", "weiter", "welche", "welchem", "welchen", "welcher", "welches", "wenn",
    "wer", "werde", "werden", "wie", "wieder", "will", "wir", "wird", "wirst",
    "wo", "wollen", "wollte", "würde", "würden", "zu", "zum", "zur", "zwar",
    "zwischen"
}

PLAY_GAMES = frozenset(('ball', 'bubbles', 'yarn', 'bubble', 'cups', 'memory', 'tricks',
                        'story', 'story_picnic', 'story_sock', 'story_stars'))
PLAY_BADGES = frozenset(('first_ball', 'spurnase', 'merkmeister', 'highfive', 'adventurer', 'playmates'))


class MemoryStore:
    """Thread-sicherer lokaler Speicher basierend auf SQLite."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path is None:
            self.path = DATA_DIR / "mochi.db"
        else:
            self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _db(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY, started REAL, character TEXT, title TEXT);")
            db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, conversation_id INTEGER, ts REAL, role TEXT, text TEXT);")
            db.execute("CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY, ts REAL, text TEXT, due_date TEXT NULL, kind TEXT DEFAULT 'fact');")
            db.execute("CREATE TABLE IF NOT EXISTS stats(key TEXT PRIMARY KEY, value TEXT);")
            db.execute("CREATE TABLE IF NOT EXISTS friendship(id INTEGER PRIMARY KEY, points INTEGER, last_update TEXT);")
            db.execute("CREATE TABLE IF NOT EXISTS friendship_daily(date TEXT, kind TEXT, count INTEGER, PRIMARY KEY(date, kind));")
            db.execute("CREATE TABLE IF NOT EXISTS focus(date TEXT, minutes INTEGER, count INTEGER);")
            db.execute("CREATE TABLE IF NOT EXISTS cards(id INTEGER PRIMARY KEY AUTOINCREMENT, deck TEXT, front TEXT, back TEXT, box INTEGER DEFAULT 1, due REAL DEFAULT 0.0);")
            db.execute("CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, color TEXT, x INTEGER, y INTEGER, done INTEGER DEFAULT 0);")
            db.execute("CREATE TABLE IF NOT EXISTS play_sessions(session_id TEXT PRIMARY KEY, game TEXT, mode TEXT, score INTEGER, turns INTEGER, completed INTEGER, awarded INTEGER);")
            db.execute("CREATE TABLE IF NOT EXISTS play_records(game TEXT, mode TEXT, score INTEGER, turns INTEGER, completed INTEGER, rounds INTEGER, completed_rounds INTEGER, PRIMARY KEY(game, mode));")
            db.execute("CREATE TABLE IF NOT EXISTS play_preferences(game TEXT PRIMARY KEY, count INTEGER);")
            db.execute("CREATE TABLE IF NOT EXISTS play_badges(name TEXT PRIMARY KEY);")

    # -- Conversations & Messages ------------------------------------------------------
    def add_message(self, role: str, text: str, character: str = "cat_mochi") -> None:
        """Fuegt eine Nachricht hinzu. Neues Gespraech, wenn das letzte > 30 Min. her ist."""
        clean_text = (text or "").strip()
        if not clean_text:
            return

        now = time.time()
        with self._db() as db:
            cur = db.execute("SELECT id, started FROM conversations ORDER BY started DESC LIMIT 1")
            last_conv = cur.fetchone()

            conv_id: Optional[int] = None
            if last_conv:
                cid = last_conv["id"]
                # Letzte Nachricht in diesem Gespraech pruefen
                cur_msg = db.execute("SELECT ts FROM messages WHERE conversation_id = ? ORDER BY ts DESC LIMIT 1", (cid,))
                last_msg = cur_msg.fetchone()
                last_activity = last_msg["ts"] if last_msg else last_conv["started"]
                if (now - last_activity) < 1800:
                    conv_id = cid

            if conv_id is None:
                title = clean_text[:40] if role == "user" else "Neues Gespräch"
                cur_ins = db.execute(
                    "INSERT INTO conversations(started, character, title) VALUES (?, ?, ?)",
                    (now, character, title),
                )
                conv_id = cur_ins.lastrowid
            else:
                # Falls erstes Gespraech mit Assistant begann und noch Standardtitel hat:
                cur_t = db.execute("SELECT title FROM conversations WHERE id = ?", (conv_id,))
                row_t = cur_t.fetchone()
                if row_t and row_t["title"] == "Neues Gespräch" and role == "user":
                    db.execute("UPDATE conversations SET title = ? WHERE id = ?", (clean_text[:40], conv_id))

            db.execute(
                "INSERT INTO messages(conversation_id, ts, role, text) VALUES (?, ?, ?, ?)",
                (conv_id, now, role, clean_text),
            )

    def conversations(self, search: str = "") -> list[dict]:
        """Gibt alle Gespraeche zurueck, neueste zuerst. Optional gefiltert nach Suchtext."""
        query = search.strip()
        with self._db() as db:
            if query:
                like_pattern = f"%{query}%"
                cur = db.execute(
                    """
                    SELECT c.id, c.started, c.character, c.title, COUNT(m.id) AS msg_count
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    WHERE c.title LIKE ? OR c.id IN (
                        SELECT DISTINCT conversation_id FROM messages WHERE text LIKE ?
                    )
                    GROUP BY c.id
                    ORDER BY c.started DESC
                    """,
                    (like_pattern, like_pattern),
                )
            else:
                cur = db.execute(
                    """
                    SELECT c.id, c.started, c.character, c.title, COUNT(m.id) AS msg_count
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.id
                    GROUP BY c.id
                    ORDER BY c.started DESC
                    """
                )
            return [dict(row) for row in cur.fetchall()]

    def messages(self, conversation_id: int) -> list[dict]:
        """Liefert alle Nachrichten eines Gespraechs chronologisch sortiert."""
        with self._db() as db:
            cur = db.execute(
                "SELECT id, conversation_id, ts, role, text FROM messages WHERE conversation_id = ? ORDER BY ts ASC",
                (conversation_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def delete_conversation(self, conv_id: int) -> None:
        """Loescht ein Gespraech samt aller zugehoerigen Nachrichten."""
        with self._db() as db:
            db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
            db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))

    def delete_all_chats(self) -> None:
        """Loescht alle Gespraeche und Nachrichten."""
        with self._db() as db:
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM conversations")

    # -- Facts -------------------------------------------------------------------------
    def add_fact(self, text: str, due_date: Optional[str] = None, kind: str = "fact") -> int:
        """Speichert einen neuen Fakt."""
        clean = (text or "").strip()
        now = time.time()
        with self._db() as db:
            cur = db.execute(
                "INSERT INTO facts(ts, text, due_date, kind) VALUES (?, ?, ?, ?)",
                (now, clean, due_date, kind),
            )
            return int(cur.lastrowid or 0)

    def facts(self) -> list[dict]:
        """Liefert alle gespeicherten Fakten, neueste zuerst."""
        with self._db() as db:
            cur = db.execute("SELECT id, ts, text, due_date, kind FROM facts ORDER BY ts DESC")
            return [dict(row) for row in cur.fetchall()]

    def delete_fact(self, fact_id: int) -> None:
        """Loescht einen einzelnen Fakt anhand der ID."""
        with self._db() as db:
            db.execute("DELETE FROM facts WHERE id = ?", (fact_id,))

    def forget_matching(self, text: str) -> int:
        """Loescht Fakten, die den Suchtext enthalten (case-insensitive)."""
        pattern = f"%{text.strip().lower()}%"
        with self._db() as db:
            cur = db.execute("DELETE FROM facts WHERE LOWER(text) LIKE ?", (pattern,))
            return cur.rowcount

    def delete_all_facts(self) -> None:
        """Loescht alle Fakten."""
        with self._db() as db:
            db.execute("DELETE FROM facts")

    # -- Relevanzsuche (History Snippets) ----------------------------------------------
    def relevant_snippets(self, query: str, limit: int = 3) -> list[str]:
        """Sucht aehnliche Nachrichten aus frueheren Gespraechen (ohne aktuelles Gespraech)."""
        raw_words = re.findall(r"\b\w{4,}\b", query.lower())
        keywords = [w for w in raw_words if w not in STOP_WORDS]
        if not keywords:
            return []

        now = time.time()
        with self._db() as db:
            # Aktuelles Gespraech ermitteln
            cur_last = db.execute("SELECT id, started FROM conversations ORDER BY started DESC LIMIT 1")
            last_conv = cur_last.fetchone()
            current_cid: Optional[int] = None
            if last_conv:
                cid = last_conv["id"]
                cur_msg = db.execute("SELECT ts FROM messages WHERE conversation_id = ? ORDER BY ts DESC LIMIT 1", (cid,))
                last_msg = cur_msg.fetchone()
                last_activity = last_msg["ts"] if last_msg else last_conv["started"]
                if (now - last_activity) < 1800:
                    current_cid = cid

            if current_cid is not None:
                cur_msgs = db.execute(
                    "SELECT id, text, ts FROM messages WHERE conversation_id != ? ORDER BY ts DESC",
                    (current_cid,),
                )
            else:
                cur_msgs = db.execute("SELECT id, text, ts FROM messages ORDER BY ts DESC")

            rows = cur_msgs.fetchall()

        scored: list[tuple[int, float, str]] = []
        for r in rows:
            msg_text = r["text"]
            msg_low = msg_text.lower()
            matches = sum(1 for kw in keywords if kw in msg_low)
            if matches > 0:
                snippet = msg_text[:200]
                scored.append((matches, float(r["ts"]), snippet))

        # Sortiere nach Trefferanzahl absteigend, dann nach Aktualitaet
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scored[:limit]]

    # -- Stats -------------------------------------------------------------------------
    def get_stat(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._db() as db:
            cur = db.execute("SELECT value FROM stats WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_stat(self, key: str, value: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO stats(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )

    def increment_stat(self, key: str, amount: int = 1) -> int:
        with self._db() as db:
            db.execute('INSERT INTO stats(key, value) VALUES(?, ?) '
                       'ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + excluded.value',
                       (key, str(amount)))
            return int(db.execute('SELECT value FROM stats WHERE key = ?', (key,)).fetchone()['value'])

    # -- Export & Wipe -----------------------------------------------------------------
    def export_text(self, path: Path | str) -> None:
        """Exportiert alle Chats und Fakten als uebersichtliche Textdatei."""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [
            "============================================================",
            " Desktop Cat - Exportierte Daten",
            f" Exportiert am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "============================================================",
            "",
            "--- GEMERKTE FAKTEN ---",
        ]

        all_facts = self.facts()
        if all_facts:
            for f in all_facts:
                dt_str = datetime.datetime.fromtimestamp(f["ts"]).strftime("%Y-%m-%d %H:%M")
                due = f" [Frist/Datum: {f['due_date']}]" if f["due_date"] else ""
                lines.append(f"• [{dt_str}] ({f['kind']}) {f['text']}{due}")
        else:
            lines.append("(Keine gemerkten Fakten vorhanden)")

        lines.extend(["", "--- GESPRÄCHSVERLÄUFE ---"])
        all_convs = self.conversations()
        if all_convs:
            for c in all_convs:
                dt_c = datetime.datetime.fromtimestamp(c["started"]).strftime("%Y-%m-%d %H:%M:%S")
                lines.extend([
                    "",
                    f"=== Gespräch #{c['id']} – „{c['title']}“ ({dt_c}, Figur: {c['character']}) ===",
                ])
                msgs = self.messages(c["id"])
                for m in msgs:
                    m_time = datetime.datetime.fromtimestamp(m["ts"]).strftime("%H:%M:%S")
                    sender = "Du" if m["role"] == "user" else "Buddy"
                    lines.append(f"[{m_time}] {sender}: {m['text']}")
        else:
            lines.append("(Keine gespeicherten Chats vorhanden)")

        out_path.write_text("\n".join(lines), encoding="utf-8")

    # -- Lokale Spielrunden ------------------------------------------------------------
    def finish_play_session(self, session_id: str, game: str, mode: str, score: int,
                            completed: bool = True, remember: bool = False, turns: int = 0) -> dict:
        """Commit one result, record and reward together; retries never pay twice."""
        if (not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 200
                or game not in PLAY_GAMES or not isinstance(mode, str) or not mode.strip()
                or len(mode) > 40 or type(score) is not int or not 0 <= score <= 2**63 - 1
                or type(turns) is not int or not 0 <= turns <= 2**63 - 1
                or type(completed) is not bool or type(remember) is not bool):
            raise ValueError('Invalid play result')
        today = datetime.date.today().isoformat()
        result = dict(duplicate=False, awarded=0, record=False, badges=[])
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM play_sessions WHERE session_id = ?', (session_id,)).fetchone():
                result['duplicate'] = True
                return result
            db.execute('INSERT INTO play_sessions VALUES(?, ?, ?, ?, ?, ?, 0)',
                       (session_id, game, mode, score, turns, int(completed)))
            if not completed:
                return result

            previous = db.execute('SELECT * FROM play_records WHERE game = ? AND mode = ?', (game, mode)).fetchone()
            fewer_turns = game == 'memory' and mode == 'cozy'
            best = previous is None or (turns < previous['turns'] if fewer_turns else score > previous['score'])
            result['record'] = best
            if previous is None:
                db.execute('INSERT INTO play_records VALUES(?, ?, ?, ?, 1, 1, 1)', (game, mode, score, turns))
            else:
                db.execute('UPDATE play_records SET score = ?, turns = ?, rounds = rounds + 1, '
                           'completed_rounds = completed_rounds + 1 WHERE game = ? AND mode = ?',
                           (score if best else previous['score'], turns if best else previous['turns'], game, mode))
            if remember:
                db.execute('INSERT INTO play_preferences VALUES(?, 1) '
                           'ON CONFLICT(game) DO UPDATE SET count = count + 1', (game,))

            if game in ('cups', 'memory', 'story') or game.startswith('story_'):
                allowance = db.execute("SELECT count FROM friendship_daily WHERE date = ? AND kind = 'play'", (today,)).fetchone()
                if allowance is None or allowance['count'] < 10:
                    db.execute("INSERT INTO friendship_daily VALUES(?, 'play', 1) "
                               'ON CONFLICT(date, kind) DO UPDATE SET count = count + 1', (today,))
                    db.execute('INSERT INTO friendship VALUES(1, 3, ?) '
                               'ON CONFLICT(id) DO UPDATE SET points = points + 3, last_update = excluded.last_update', (today,))
                    db.execute('UPDATE play_sessions SET awarded = 3 WHERE session_id = ?', (session_id,))
                    result['awarded'] = 3
            badge = ('adventurer' if game == 'story' or game.startswith('story_') else
                     'spurnase' if game == 'cups' else
                     'merkmeister' if game == 'memory' and score >= 6 else None)
            badges = [badge] if badge else []
            if db.execute('SELECT SUM(completed_rounds) AS count FROM play_records').fetchone()['count'] >= 10:
                badges.append('playmates')
            for name in badges:
                if db.execute('INSERT OR IGNORE INTO play_badges VALUES(?)', (name,)).rowcount:
                    result['badges'].append(name)
        if result.get('awarded'):
            self._notify_friendship_changed()
        return result

    def get_play_records(self) -> list[dict]:
        with self._db() as db:
            return [dict(row) for row in db.execute('SELECT * FROM play_records ORDER BY game, mode')]

    def get_play_preferences(self) -> dict:
        with self._db() as db:
            return {row['game']: row['count'] for row in db.execute('SELECT * FROM play_preferences ORDER BY game')}

    def reset_play_preferences(self) -> None:
        with self._db() as db:
            db.execute('DELETE FROM play_preferences')

    def get_play_badges(self) -> list[str]:
        with self._db() as db:
            return [row['name'] for row in db.execute('SELECT name FROM play_badges ORDER BY name')]

    def unlock_play_badge(self, name: str) -> bool:
        if name not in PLAY_BADGES:
            raise ValueError('Unknown play badge')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            return bool(db.execute('INSERT OR IGNORE INTO play_badges VALUES(?)', (name,)).rowcount)

    # -- Freundschaft & Belohnungen (Phase 6) -------------------------------------------
    def get_friendship_points(self) -> int:
        with self._db() as db:
            cur = db.execute("SELECT points FROM friendship WHERE id = 1")
            row = cur.fetchone()
            return int(row["points"]) if row else 0

    def set_friendship_points(self, points: int) -> None:
        today_str = datetime.date.today().isoformat()
        with self._db() as db:
            db.execute(
                "INSERT INTO friendship(id, points, last_update) VALUES(1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET points = excluded.points, last_update = excluded.last_update",
                (points, today_str),
            )
        self._notify_friendship_changed()

    def add_friendship_points(self, points: int) -> int:
        today_str = datetime.date.today().isoformat()
        with self._db() as db:
            cur = db.execute("SELECT points FROM friendship WHERE id = 1")
            row = cur.fetchone()
            current = int(row["points"]) if row else 0
            new_pts = current + points
            db.execute(
                "INSERT INTO friendship(id, points, last_update) VALUES(1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET points = excluded.points, last_update = excluded.last_update",
                (new_pts, today_str),
            )
        self._notify_friendship_changed()
        return new_pts

    def award_friendship(self, kind: str, date_str: str, limit: int, points: int) -> tuple[int, int]:
        """Keep the daily allowance and point total in one serialized transaction."""
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT points FROM friendship WHERE id = 1').fetchone()
            old = int(row['points']) if row else 0
            row = db.execute('SELECT count FROM friendship_daily WHERE date = ? AND kind = ?',
                             (date_str, kind)).fetchone()
            count = int(row['count']) if row else 0
            if count >= limit:
                return old, old
            new = old + points
            db.execute('INSERT INTO friendship_daily(date, kind, count) VALUES(?, ?, 1) '
                       'ON CONFLICT(date, kind) DO UPDATE SET count = count + 1', (date_str, kind))
            db.execute('INSERT INTO friendship(id, points, last_update) VALUES(1, ?, ?) '
                       'ON CONFLICT(id) DO UPDATE SET points = excluded.points, last_update = excluded.last_update',
                       (new, date_str))
        self._notify_friendship_changed()
        return old, new

    award_friendship_points = award_friendship

    def claim_achievement(self, ach_id: str, stat: str, target: int, reward: int) -> bool:
        """Unlock and pay a trophy once, even when two events arrive together."""
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            key = f'ach_unlocked_{ach_id}'
            row = db.execute('SELECT value FROM stats WHERE key = ?', (key,)).fetchone()
            if row and row['value'] == '1':
                return False
            db.execute('INSERT INTO stats(key, value) VALUES(?, ?) '
                       'ON CONFLICT(key) DO UPDATE SET value = excluded.value', (key, '1'))
            row = db.execute('SELECT value FROM stats WHERE key = ?', (stat,)).fetchone()
            progress = max(int(row['value'] or 0) if row else 0, target)
            db.execute('INSERT INTO stats(key, value) VALUES(?, ?) '
                       'ON CONFLICT(key) DO UPDATE SET value = excluded.value', (stat, str(progress)))
            db.execute('INSERT INTO friendship(id, points, last_update) VALUES(1, ?, ?) '
                       'ON CONFLICT(id) DO UPDATE SET points = points + excluded.points, last_update = excluded.last_update',
                       (reward, datetime.date.today().isoformat()))
        self._notify_friendship_changed()
        return True

    def get_daily_friendship_count(self, kind: str, date_str: str) -> int:
        with self._db() as db:
            cur = db.execute("SELECT count FROM friendship_daily WHERE date = ? AND kind = ?", (date_str, kind))
            row = cur.fetchone()
            return int(row["count"]) if row else 0

    def increment_daily_friendship(self, kind: str, date_str: str) -> int:
        with self._db() as db:
            db.execute(
                "INSERT INTO friendship_daily(date, kind, count) VALUES(?, ?, 1) "
                "ON CONFLICT(date, kind) DO UPDATE SET count = count + 1",
                (date_str, kind),
            )
            cur = db.execute("SELECT count FROM friendship_daily WHERE date = ? AND kind = ?", (date_str, kind))
            row = cur.fetchone()
            return int(row["count"]) if row else 1

    # -- Fokus & Pomodoro (Phase 6) ---------------------------------------------------
    def record_focus(self, date_str: str, minutes: int) -> None:
        with self._db() as db:
            cur = db.execute("SELECT minutes, count FROM focus WHERE date = ?", (date_str,))
            row = cur.fetchone()
            if row:
                db.execute(
                    "UPDATE focus SET minutes = minutes + ?, count = count + 1 WHERE date = ?",
                    (minutes, date_str),
                )
            else:
                db.execute("INSERT INTO focus(date, minutes, count) VALUES(?, ?, 1)", (date_str, minutes))

    def get_focus_data(self) -> list[dict]:
        with self._db() as db:
            cur = db.execute("SELECT date, minutes, count FROM focus ORDER BY date ASC")
            return [{"date": str(r["date"]), "minutes": int(r["minutes"]), "count": int(r["count"])} for r in cur.fetchall()]

    # -- Lernkarten (Phase 6) ---------------------------------------------------------
    def add_card(self, deck: str, front: str, back: str) -> int:
        with self._db() as db:
            cur = db.execute(
                "INSERT INTO cards(deck, front, back, box, due) VALUES(?, ?, ?, 1, 0.0)",
                (deck.strip() or "Allgemein", front.strip(), back.strip()),
            )
            return int(cur.lastrowid)

    def get_cards(self, deck: Optional[str] = None) -> list[dict]:
        with self._db() as db:
            if deck:
                cur = db.execute("SELECT id, deck, front, back, box, due FROM cards WHERE deck = ? ORDER BY id ASC", (deck,))
            else:
                cur = db.execute("SELECT id, deck, front, back, box, due FROM cards ORDER BY deck ASC, id ASC")
            return [
                {
                    "id": int(r["id"]),
                    "deck": str(r["deck"]),
                    "front": str(r["front"]),
                    "back": str(r["back"]),
                    "box": int(r["box"]),
                    "due": float(r["due"]),
                }
                for r in cur.fetchall()
            ]

    def update_card_box(self, card_id: int, box: int) -> None:
        with self._db() as db:
            db.execute("UPDATE cards SET box = ? WHERE id = ?", (box, card_id))

    def delete_card(self, card_id: int) -> None:
        with self._db() as db:
            db.execute("DELETE FROM cards WHERE id = ?", (card_id,))

    def get_decks(self) -> list[str]:
        with self._db() as db:
            cur = db.execute("SELECT DISTINCT deck FROM cards ORDER BY deck ASC")
            return [str(r["deck"]) for r in cur.fetchall()]

    # -- Haftnotizen (Phase 6) --------------------------------------------------------
    def add_note(self, text: str, color: str = "yellow", x: int = 100, y: int = 100) -> int:
        with self._db() as db:
            cur = db.execute(
                "INSERT INTO notes(text, color, x, y, done) VALUES(?, ?, ?, ?, 0)",
                (text.strip(), color, x, y),
            )
            return int(cur.lastrowid)

    def get_notes(self, include_done: bool = False) -> list[dict]:
        with self._db() as db:
            if include_done:
                cur = db.execute("SELECT id, text, color, x, y, done FROM notes ORDER BY id ASC")
            else:
                cur = db.execute("SELECT id, text, color, x, y, done FROM notes WHERE done = 0 ORDER BY id ASC")
            return [
                {
                    "id": int(r["id"]),
                    "text": str(r["text"]),
                    "color": str(r["color"]),
                    "x": int(r["x"]),
                    "y": int(r["y"]),
                    "done": int(r["done"]),
                }
                for r in cur.fetchall()
            ]

    def update_note(
        self,
        note_id: int,
        text: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        done: Optional[int] = None,
    ) -> None:
        with self._db() as db:
            if text is not None:
                db.execute("UPDATE notes SET text = ? WHERE id = ?", (text, note_id))
            if x is not None and y is not None:
                db.execute("UPDATE notes SET x = ?, y = ? WHERE id = ?", (x, y, note_id))
            if done is not None:
                db.execute("UPDATE notes SET done = ? WHERE id = ?", (done, note_id))

    def delete_note(self, note_id: int) -> None:
        with self._db() as db:
            db.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    # Wird nach "Alles vergessen" aufgerufen (z. B. Verlauf im Speicher leeren). Kann aus Worker-Threads kommen.
    on_wipe: list = []
    on_friendship_changed: list = []

    @classmethod
    def _notify_friendship_changed(cls) -> None:
        for cb in list(cls.on_friendship_changed):
            try:
                cb()
            except Exception:
                pass

    def wipe_everything(self) -> None:
        """Loescht alle Tabellen restlos und fuehrt ein VACUUM aus."""
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        try:
            with conn:
                conn.execute("DELETE FROM messages")
                conn.execute("DELETE FROM conversations")
                conn.execute("DELETE FROM facts")
                conn.execute("DELETE FROM stats")
                conn.execute("DELETE FROM friendship")
                conn.execute("DELETE FROM friendship_daily")
                conn.execute("DELETE FROM focus")
                conn.execute("DELETE FROM cards")
                conn.execute("DELETE FROM notes")
                conn.execute("DELETE FROM play_sessions")
                conn.execute("DELETE FROM play_records")
                conn.execute("DELETE FROM play_preferences")
                conn.execute("DELETE FROM play_badges")
            conn.isolation_level = None
            conn.execute("VACUUM")
        finally:
            conn.close()
        for cb in list(MemoryStore.on_wipe):
            try:
                cb()
            except Exception:
                pass
        self._notify_friendship_changed()


_STORE: Optional[MemoryStore] = None


def get_memory_store(db_path: Optional[Path | str] = None) -> MemoryStore:
    """Liefert die MemoryStore-Instanz (Singleton fuer Standardpfad, sonst neue Instanz)."""
    global _STORE
    if db_path is not None:
        return MemoryStore(db_path)
    if _STORE is None:
        _STORE = MemoryStore()
    return _STORE
