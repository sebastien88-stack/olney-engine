"""Local SQLite persistence for Olney user profiles."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from reading_store import ReadingStoreMixin
from relationship_store import RelationshipStoreMixin
from chat_store import ChatStoreMixin


PROFILE_FIELDS = (
    "name",
    "last_name",
    "profile_type",
    "birth_date",
    "birth_time",
    "birth_place",
    "latitude",
    "longitude",
    "timezone",
    "country_code",
    "notes",
)

EVENT_FIELDS = (
    "profile_id",
    "title",
    "category",
    "date_start",
    "date_end",
    "event_time",
    "place",
    "people",
    "tags",
    "importance",
    "notes",
)


def default_database_path() -> Path:
    override = os.environ.get("OLNEY_PROFILE_DB")
    if override:
        return Path(override)
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "Olney Engine" / "olney_profiles.db"


class ProfileStore(ReadingStoreMixin, RelationshipStoreMixin, ChatStoreMixin):
    """Small forward-compatible profile database kept outside the app files."""

    def __init__(self, database_path=None):
        self.path = Path(database_path) if database_path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            existing_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(profiles)")
            }
            if existing_columns and "last_name" not in existing_columns:
                connection.execute("ALTER TABLE profiles RENAME TO profiles_legacy")
                self._create_profiles_table(connection)
                connection.execute(
                    """
                    INSERT INTO profiles (
                        id, name, last_name, profile_type, birth_date, birth_time, birth_place,
                        latitude, longitude, timezone, country_code, notes,
                        created_at, updated_at, last_used_at, favorite
                    )
                    SELECT
                        id, name, '', 'Humain', birth_date, birth_time, birth_place,
                        latitude, longitude, timezone, country_code, notes,
                        created_at, updated_at, created_at, 0
                    FROM profiles_legacy
                    """
                )
                connection.execute("DROP TABLE profiles_legacy")
            else:
                self._create_profiles_table(connection)
            current_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(profiles)")
            }
            if "last_used_at" not in current_columns:
                connection.execute("ALTER TABLE profiles ADD COLUMN last_used_at TEXT")
                connection.execute(
                    "UPDATE profiles SET last_used_at = created_at WHERE last_used_at IS NULL"
                )
            if "favorite" not in current_columns:
                connection.execute(
                    "ALTER TABLE profiles ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0"
                )
            if "profile_type" not in current_columns:
                connection.execute(
                    "ALTER TABLE profiles ADD COLUMN profile_type TEXT NOT NULL DEFAULT 'Humain'"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'Autre',
                    date_start TEXT NOT NULL,
                    date_end TEXT,
                    event_time TEXT,
                    place TEXT,
                    people TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    importance INTEGER NOT NULL DEFAULT 3,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_profile_date "
                "ON events(profile_id, date_start, id)"
            )
            event_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(events)")
            }
            if "last_used_at" not in event_columns:
                connection.execute("ALTER TABLE events ADD COLUMN last_used_at TEXT")
                connection.execute(
                    "UPDATE events SET last_used_at = created_at WHERE last_used_at IS NULL"
                )
            self._initialize_reading_tables(connection)
            self._initialize_relationship_tables(connection)
            self._initialize_chat_tables(connection)

    @staticmethod
    def _create_profiles_table(connection):
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE,
                last_name TEXT NOT NULL DEFAULT '' COLLATE NOCASE,
                profile_type TEXT NOT NULL DEFAULT 'Humain',
                birth_date TEXT NOT NULL,
                birth_time TEXT NOT NULL,
                birth_place TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                timezone TEXT,
                country_code TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT,
                favorite INTEGER NOT NULL DEFAULT 0,
                UNIQUE(name, last_name)
            )
            """
        )

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _clean(data):
        cleaned = {field: data.get(field) for field in PROFILE_FIELDS}
        cleaned["name"] = str(cleaned.get("name") or "").strip()
        cleaned["last_name"] = str(cleaned.get("last_name") or "").strip()
        cleaned["profile_type"] = str(cleaned.get("profile_type") or "Humain").strip()
        cleaned["birth_date"] = str(cleaned.get("birth_date") or "").strip()
        cleaned["birth_time"] = str(cleaned.get("birth_time") or "").strip()
        cleaned["birth_place"] = str(cleaned.get("birth_place") or "").strip()
        cleaned["notes"] = str(cleaned.get("notes") or "")
        if not cleaned["name"]:
            raise ValueError("Donne un prénom au profil.")
        if not all(cleaned[key] for key in ("birth_date", "birth_time", "birth_place")):
            raise ValueError("Le profil nécessite une date, une heure et une ville de naissance.")
        return cleaned

    @staticmethod
    def _as_dict(row):
        return dict(row) if row is not None else None

    def list_profiles(self):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM profiles ORDER BY name COLLATE NOCASE, last_name COLLATE NOCASE"
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def list_recent_profiles(self, limit=5):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM profiles
                ORDER BY COALESCE(last_used_at, created_at) DESC, id DESC
                LIMIT ?
                """,
                (max(0, int(limit)),),
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def get_profile(self, profile_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM profiles WHERE id = ?", (int(profile_id),)
            ).fetchone()
        return self._as_dict(row)

    def create_profile(self, data):
        values = self._clean(data)
        timestamp = self._now()
        columns = ", ".join(PROFILE_FIELDS)
        placeholders = ", ".join("?" for _ in PROFILE_FIELDS)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    f"INSERT INTO profiles ({columns}, created_at, updated_at, last_used_at) "
                    f"VALUES ({placeholders}, ?, ?, ?)",
                    tuple(values[field] for field in PROFILE_FIELDS)
                    + (timestamp, timestamp, timestamp),
                )
                profile_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError("Un profil porte déjà ce prénom et ce nom de famille.") from exc
        self.set_last_profile_id(profile_id)
        return self.get_profile(profile_id)

    def update_profile(self, profile_id, data):
        values = self._clean(data)
        assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    f"UPDATE profiles SET {assignments}, updated_at = ? WHERE id = ?",
                    tuple(values[field] for field in PROFILE_FIELDS)
                    + (self._now(), int(profile_id)),
                )
                if cursor.rowcount != 1:
                    raise ValueError("Profil introuvable.")
        except sqlite3.IntegrityError as exc:
            raise ValueError("Un profil porte déjà ce prénom et ce nom de famille.") from exc
        return self.get_profile(profile_id)

    def duplicate_profile(self, profile_id, name=None):
        source = self.get_profile(profile_id)
        if not source:
            raise ValueError("Profil introuvable.")
        data = {field: source.get(field) for field in PROFILE_FIELDS}
        data["name"] = name or self.available_name(f'{source["name"]} — copie')
        return self.create_profile(data)

    def available_name(self, base_name):
        existing = {item["name"].casefold() for item in self.list_profiles()}
        if base_name.casefold() not in existing:
            return base_name
        index = 2
        while f"{base_name} {index}".casefold() in existing:
            index += 1
        return f"{base_name} {index}"

    def delete_profile(self, profile_id):
        profile_id = int(profile_id)
        with self._connect() as connection:
            connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        if self.get_last_profile_id() == profile_id:
            self.set_last_profile_id(None)

    def set_last_profile_id(self, profile_id):
        value = "" if profile_id is None else str(int(profile_id))
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES('last_profile_id', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (value,),
            )
        if profile_id is not None:
            self.touch_profile(profile_id)

    def touch_profile(self, profile_id):
        with self._connect() as connection:
            connection.execute(
                "UPDATE profiles SET last_used_at = ? WHERE id = ?",
                (self._now(), int(profile_id)),
            )

    def set_favorite(self, profile_id, favorite):
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE profiles SET favorite = ? WHERE id = ?",
                (1 if favorite else 0, int(profile_id)),
            )
            if cursor.rowcount != 1:
                raise ValueError("Profil introuvable.")
        return self.get_profile(profile_id)

    @staticmethod
    def _clean_event(data):
        cleaned = {field: data.get(field) for field in EVENT_FIELDS}
        try:
            cleaned["profile_id"] = int(cleaned["profile_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError("L’événement doit être lié à un profil.") from exc
        cleaned["title"] = str(cleaned.get("title") or "").strip()
        cleaned["category"] = str(cleaned.get("category") or "Autre").strip()
        cleaned["date_start"] = str(cleaned.get("date_start") or "").strip()
        cleaned["date_end"] = str(cleaned.get("date_end") or "").strip() or None
        cleaned["event_time"] = str(cleaned.get("event_time") or "").strip() or None
        cleaned["place"] = str(cleaned.get("place") or "").strip() or None
        cleaned["people"] = str(cleaned.get("people") or "").strip()
        cleaned["tags"] = str(cleaned.get("tags") or "").strip()
        cleaned["notes"] = str(cleaned.get("notes") or "").strip()
        try:
            cleaned["importance"] = int(cleaned.get("importance") or 3)
        except (TypeError, ValueError) as exc:
            raise ValueError("L’importance doit être comprise entre 1 et 5.") from exc
        if not cleaned["title"]:
            raise ValueError("Donne un titre à l’événement.")
        try:
            start = datetime.fromisoformat(cleaned["date_start"]).date()
            end = (
                datetime.fromisoformat(cleaned["date_end"]).date()
                if cleaned["date_end"] else None
            )
            if cleaned["event_time"]:
                datetime.strptime(cleaned["event_time"], "%H:%M")
        except ValueError as exc:
            raise ValueError("La date ou l’heure de l’événement est invalide.") from exc
        if end and end < start:
            raise ValueError("La date de fin ne peut pas précéder la date de début.")
        if not 1 <= cleaned["importance"] <= 5:
            raise ValueError("L’importance doit être comprise entre 1 et 5.")
        return cleaned

    def list_events(self, profile_id=None):
        with self._connect() as connection:
            if profile_id is None:
                rows = connection.execute(
                    "SELECT * FROM events "
                    "ORDER BY date_start DESC, COALESCE(event_time, '') DESC, id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT DISTINCT e.* FROM events e "
                    "LEFT JOIN event_participants ep ON ep.event_id = e.id "
                    "WHERE e.profile_id = ? OR ep.profile_id = ? "
                    "ORDER BY e.date_start DESC, COALESCE(e.event_time, '') DESC, e.id DESC",
                    (int(profile_id), int(profile_id)),
                ).fetchall()
        return [self._as_dict(row) for row in rows]

    def get_event(self, event_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE id = ?", (int(event_id),)
            ).fetchone()
        return self._as_dict(row)

    def list_recent_events(self, limit=5):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT events.*, profiles.name AS profile_name,
                       profiles.last_name AS profile_last_name
                FROM events
                JOIN profiles ON profiles.id = events.profile_id
                ORDER BY COALESCE(events.last_used_at, events.created_at) DESC,
                         events.id DESC
                LIMIT ?
                """,
                (max(0, int(limit)),),
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def touch_event(self, event_id):
        with self._connect() as connection:
            connection.execute(
                "UPDATE events SET last_used_at = ? WHERE id = ?",
                (self._now(), int(event_id)),
            )

    def create_event(self, data):
        values = self._clean_event(data)
        timestamp = self._now()
        columns = ", ".join(EVENT_FIELDS)
        placeholders = ", ".join("?" for _ in EVENT_FIELDS)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    f"INSERT INTO events ({columns}, created_at, updated_at) "
                    f"VALUES ({placeholders}, ?, ?)",
                    tuple(values[field] for field in EVENT_FIELDS)
                    + (timestamp, timestamp),
                )
                event_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError("Le profil lié à cet événement n’existe plus.") from exc
        return self.get_event(event_id)

    def update_event(self, event_id, data):
        values = self._clean_event(data)
        assignments = ", ".join(f"{field} = ?" for field in EVENT_FIELDS)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE events SET {assignments}, updated_at = ? WHERE id = ?",
                tuple(values[field] for field in EVENT_FIELDS)
                + (self._now(), int(event_id)),
            )
            if cursor.rowcount != 1:
                raise ValueError("Événement introuvable.")
        return self.get_event(event_id)

    def delete_event(self, event_id):
        with self._connect() as connection:
            connection.execute("DELETE FROM events WHERE id = ?", (int(event_id),))

    def get_last_profile_id(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = 'last_profile_id'"
            ).fetchone()
        if not row or not row["value"]:
            return None
        try:
            return int(row["value"])
        except ValueError:
            return None

    def export_profile(self, profile_id, output_path):
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError("Profil introuvable.")
        payload = {
            "format": "olney-profile",
            "version": 1,
            "profile": {field: profile.get(field) for field in PROFILE_FIELDS},
        }
        Path(output_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def import_profile(self, input_path):
        try:
            payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
            if payload.get("format") != "olney-profile" or payload.get("version") != 1:
                raise ValueError
            data = payload["profile"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("Ce fichier n'est pas un profil Olney valide.") from exc
        data = dict(data)
        data["name"] = self.available_name(str(data.get("name") or "Profil importé"))
        return self.create_profile(data)
