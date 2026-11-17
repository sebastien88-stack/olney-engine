"""Additive local persistence for Olney chat conversations."""

from __future__ import annotations

import json


CHAT_SUBJECT_TYPES = {"general", "profile", "relationship", "event"}
CHAT_ROLES = {"user", "assistant"}


class ChatStoreMixin:
    def _initialize_chat_tables(self, connection):
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                subject_type TEXT NOT NULL DEFAULT 'general',
                subject_id INTEGER,
                subject_label TEXT NOT NULL DEFAULT 'Sans sujet',
                reading_angle TEXT NOT NULL DEFAULT 'Automatique',
                target_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_json TEXT,
                model TEXT,
                response_id TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_threads_recent "
            "ON chat_threads(last_used_at DESC, id DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_thread "
            "ON chat_messages(thread_id, id)"
        )

    @staticmethod
    def _clean_chat_subject(subject_type, subject_id):
        kind = str(subject_type or "general").strip().lower()
        if kind not in CHAT_SUBJECT_TYPES:
            raise ValueError("Type de sujet de conversation inconnu.")
        if kind == "general":
            return kind, None
        try:
            return kind, int(subject_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Le sujet de la conversation est incomplet.") from exc

    def create_chat_thread(self, *, subject_type="general", subject_id=None,
                           subject_label="Sans sujet", reading_angle="Automatique",
                           target_date, title=""):
        kind, identifier = self._clean_chat_subject(subject_type, subject_id)
        timestamp = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO chat_threads (
                    title, subject_type, subject_id, subject_label, reading_angle,
                    target_date, created_at, updated_at, last_used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(title or "").strip(), kind, identifier,
                    str(subject_label or "Sans sujet").strip(),
                    str(reading_angle or "Automatique").strip(), str(target_date),
                    timestamp, timestamp, timestamp,
                ),
            )
            thread_id = cursor.lastrowid
        return self.get_chat_thread(thread_id)

    def get_chat_thread(self, thread_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM chat_threads WHERE id = ?", (int(thread_id),)
            ).fetchone()
        return self._as_dict(row)

    def list_chat_threads(self, limit=100):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM chat_threads
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (max(0, int(limit)),),
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def update_chat_thread_title(self, thread_id, title):
        clean = str(title or "").strip()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_threads
                SET title = ?, updated_at = ?, last_used_at = ?
                WHERE id = ?
                """,
                (clean, self._now(), self._now(), int(thread_id)),
            )
            if cursor.rowcount != 1:
                raise ValueError("Conversation introuvable.")
        return self.get_chat_thread(thread_id)

    def touch_chat_thread(self, thread_id):
        with self._connect() as connection:
            connection.execute(
                "UPDATE chat_threads SET last_used_at = ? WHERE id = ?",
                (self._now(), int(thread_id)),
            )

    def delete_chat_thread(self, thread_id):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM chat_threads WHERE id = ?", (int(thread_id),)
            )

    def add_chat_message(self, thread_id, role, content, *, context=None,
                         model=None, response_id=None, input_tokens=None,
                         output_tokens=None):
        role = str(role or "").strip().lower()
        if role not in CHAT_ROLES:
            raise ValueError("Rôle de message inconnu.")
        clean = str(content or "").strip()
        if not clean:
            raise ValueError("Le message est vide.")
        encoded_context = (
            json.dumps(context, ensure_ascii=False, separators=(",", ":"))
            if context is not None else None
        )
        timestamp = self._now()
        with self._connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM chat_threads WHERE id = ?", (int(thread_id),)
            ).fetchone():
                raise ValueError("Conversation introuvable.")
            cursor = connection.execute(
                """
                INSERT INTO chat_messages (
                    thread_id, role, content, context_json, model, response_id,
                    input_tokens, output_tokens, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(thread_id), role, clean, encoded_context,
                    str(model).strip() if model else None,
                    str(response_id).strip() if response_id else None,
                    int(input_tokens) if input_tokens is not None else None,
                    int(output_tokens) if output_tokens is not None else None,
                    timestamp,
                ),
            )
            connection.execute(
                "UPDATE chat_threads SET updated_at = ?, last_used_at = ? WHERE id = ?",
                (timestamp, timestamp, int(thread_id)),
            )
            message_id = cursor.lastrowid
        return self.get_chat_message(message_id)

    def get_chat_message(self, message_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM chat_messages WHERE id = ?", (int(message_id),)
            ).fetchone()
        return self._as_dict(row)

    def list_chat_messages(self, thread_id, limit=None):
        with self._connect() as connection:
            if limit is None:
                rows = connection.execute(
                    "SELECT * FROM chat_messages WHERE thread_id = ? ORDER BY id",
                    (int(thread_id),),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM (
                        SELECT * FROM chat_messages WHERE thread_id = ?
                        ORDER BY id DESC LIMIT ?
                    ) ORDER BY id
                    """,
                    (int(thread_id), max(0, int(limit))),
                ).fetchall()
        return [self._as_dict(row) for row in rows]
