"""SQLite persistence for saved relationships between Olney profiles."""

from __future__ import annotations


RELATIONSHIP_FIELDS = (
    "profile_a_id",
    "profile_b_id",
    "relationship_type",
    "title",
    "notes",
)


class RelationshipStoreMixin:
    """Additive storage mixed into :class:`ProfileStore`."""

    def _initialize_relationship_tables(self, connection):
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_a_id INTEGER NOT NULL,
                profile_b_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL DEFAULT 'Autre',
                title TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT,
                CHECK(profile_a_id <> profile_b_id),
                FOREIGN KEY(profile_a_id) REFERENCES profiles(id) ON DELETE CASCADE,
                FOREIGN KEY(profile_b_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_profiles "
            "ON relationships(profile_a_id, profile_b_id, id)"
        )

    @staticmethod
    def _clean_relationship(data):
        try:
            profile_a_id = int(data.get("profile_a_id"))
            profile_b_id = int(data.get("profile_b_id"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Choisis les deux profils de la relation.") from exc
        if profile_a_id == profile_b_id:
            raise ValueError("Une relation nécessite deux profils différents.")
        relationship_type = str(data.get("relationship_type") or "Autre").strip()
        title = str(data.get("title") or "").strip()
        notes = str(data.get("notes") or "").strip()
        return {
            "profile_a_id": profile_a_id,
            "profile_b_id": profile_b_id,
            "relationship_type": relationship_type,
            "title": title,
            "notes": notes,
        }

    def _relationship_row(self, connection, relationship_id):
        return connection.execute(
            """
            SELECT relationships.*,
                   a.name AS profile_a_name, a.last_name AS profile_a_last_name,
                   b.name AS profile_b_name, b.last_name AS profile_b_last_name
            FROM relationships
            JOIN profiles AS a ON a.id = relationships.profile_a_id
            JOIN profiles AS b ON b.id = relationships.profile_b_id
            WHERE relationships.id = ?
            """,
            (int(relationship_id),),
        ).fetchone()

    def get_relationship(self, relationship_id):
        with self._connect() as connection:
            row = self._relationship_row(connection, relationship_id)
        return self._as_dict(row)

    def list_relationships(self):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT relationships.*,
                       a.name AS profile_a_name, a.last_name AS profile_a_last_name,
                       b.name AS profile_b_name, b.last_name AS profile_b_last_name
                FROM relationships
                JOIN profiles AS a ON a.id = relationships.profile_a_id
                JOIN profiles AS b ON b.id = relationships.profile_b_id
                ORDER BY relationships.favorite DESC,
                         COALESCE(relationships.last_used_at, relationships.created_at) DESC,
                         relationships.id DESC
                """
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def list_recent_relationships(self, limit=5):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT relationships.*,
                       a.name AS profile_a_name, a.last_name AS profile_a_last_name,
                       b.name AS profile_b_name, b.last_name AS profile_b_last_name
                FROM relationships
                JOIN profiles AS a ON a.id = relationships.profile_a_id
                JOIN profiles AS b ON b.id = relationships.profile_b_id
                ORDER BY COALESCE(relationships.last_used_at, relationships.created_at) DESC,
                         relationships.id DESC
                LIMIT ?
                """,
                (max(0, int(limit)),),
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def create_relationship(self, data):
        values = self._clean_relationship(data)
        timestamp = self._now()
        with self._connect() as connection:
            for profile_id in (values["profile_a_id"], values["profile_b_id"]):
                if not connection.execute(
                    "SELECT 1 FROM profiles WHERE id = ?", (profile_id,)
                ).fetchone():
                    raise ValueError("Un des profils de la relation n’existe plus.")
            cursor = connection.execute(
                """
                INSERT INTO relationships (
                    profile_a_id, profile_b_id, relationship_type, title, notes,
                    created_at, updated_at, last_used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(values[field] for field in RELATIONSHIP_FIELDS)
                + (timestamp, timestamp, timestamp),
            )
            relationship_id = cursor.lastrowid
        return self.get_relationship(relationship_id)

    def update_relationship(self, relationship_id, data):
        values = self._clean_relationship(data)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE relationships
                SET profile_a_id = ?, profile_b_id = ?, relationship_type = ?,
                    title = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                tuple(values[field] for field in RELATIONSHIP_FIELDS)
                + (self._now(), int(relationship_id)),
            )
            if cursor.rowcount != 1:
                raise ValueError("Relation introuvable.")
        return self.get_relationship(relationship_id)

    def delete_relationship(self, relationship_id):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM relationships WHERE id = ?", (int(relationship_id),)
            )

    def touch_relationship(self, relationship_id):
        with self._connect() as connection:
            connection.execute(
                "UPDATE relationships SET last_used_at = ? WHERE id = ?",
                (self._now(), int(relationship_id)),
            )

    def set_relationship_favorite(self, relationship_id, favorite):
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE relationships SET favorite = ? WHERE id = ?",
                (1 if favorite else 0, int(relationship_id)),
            )
            if cursor.rowcount != 1:
                raise ValueError("Relation introuvable.")
        return self.get_relationship(relationship_id)
