"""Additive, local reading memory. All writes are explicit application actions.

reader_key is a local perspective namespace, NOT an authentication boundary.
A future server must supply it from the authenticated session, never the LLM.
"""
from datetime import date
import json


DEFAULT_PREFERENCES = {
    "familiarity": "unspecified", "depth": "balanced", "technical_details": "on_request",
    "existential": "when_relevant_or_requested", "practical_suggestions": "when_useful",
}
PREFERENCE_VALUES = {
    "familiarity": {"unspecified", "new", "familiar", "advanced"},
    "depth": {"concise", "balanced", "deep"},
    "technical_details": {"on_request", "show", "minimal"},
    "existential": {"when_relevant_or_requested", "on_request", "never"},
    "practical_suggestions": {"when_useful", "on_request"},
}
MEMORY_FIELDS = {"kind", "text", "date_start", "date_end", "date_precision", "source_type",
                 "reporter", "perspective", "themes", "event_ids", "evidence_ids", "counterexample_ids",
                 "occurrence_id", "cycle_id", "card_id", "polarity"}
HYPOTHESIS_STATES = {"proposed", "partial", "confirmed", "revised", "rejected", "abandoned"}


def _date(value):
    return date.fromisoformat(value).isoformat() if value else None


def _text(value, limit=6000):
    value = str(value or "").strip()
    if len(value) > limit:
        raise ValueError(f"Texte trop long (maximum {limit} caractères).")
    return value


def _subject_ids(key):
    kind, number = key.split(":", 1)
    number = int(number)
    if kind not in {"profile", "event"} or number < 1:
        raise ValueError("Sujet invalide.")
    return (number, None) if kind == "profile" else (None, number)


class ReadingStoreMixin:
    def _initialize_reading_tables(self, connection):
        # No rebuild, deletion, or reinterpretation of existing profiles/events.
        statements = [
            """CREATE TABLE IF NOT EXISTS reading_subjects (
                profile_id INTEGER PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
                origin_label TEXT NOT NULL, date_precision TEXT NOT NULL DEFAULT 'exact',
                source TEXT NOT NULL DEFAULT '', relationship_to_user TEXT NOT NULL DEFAULT 'unspecified')""",
            """CREATE TABLE IF NOT EXISTS event_participants (
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                role TEXT NOT NULL DEFAULT '', PRIMARY KEY(event_id, profile_id))""",
            """CREATE TABLE IF NOT EXISTS event_readings (
                event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
                origin_label TEXT NOT NULL DEFAULT '', date_precision TEXT NOT NULL DEFAULT 'exact',
                source TEXT NOT NULL DEFAULT '', event_state TEXT NOT NULL DEFAULT 'recorded')""",
            """CREATE TABLE IF NOT EXISTS reading_preferences (
                reader_key TEXT PRIMARY KEY, payload TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS reading_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT, reader_key TEXT NOT NULL,
                profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
                event_subject_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                kind TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                CHECK ((profile_id IS NOT NULL) != (event_subject_id IS NOT NULL)))""",
            """CREATE TABLE IF NOT EXISTS reading_memory_revisions (
                memory_id INTEGER NOT NULL REFERENCES reading_memory(id) ON DELETE CASCADE,
                revision INTEGER NOT NULL, snapshot TEXT NOT NULL, reason TEXT NOT NULL,
                actor TEXT NOT NULL, recorded_at TEXT NOT NULL, PRIMARY KEY(memory_id, revision))""",
            "CREATE INDEX IF NOT EXISTS idx_reading_memory_subject ON reading_memory(reader_key, profile_id, event_subject_id, id)",
        ]
        for statement in statements:
            connection.execute(statement)

    def get_reading_preferences(self, reader_key="local_user"):
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM reading_preferences WHERE reader_key=?", (reader_key,)).fetchone()
        return {**DEFAULT_PREFERENCES, **(json.loads(row[0]) if row else {})}

    def set_reading_preferences(self, changes, reader_key="local_user"):
        if set(changes) - set(PREFERENCE_VALUES) or any(value not in PREFERENCE_VALUES[key] for key, value in changes.items()):
            raise ValueError("Préférence de lecture inconnue.")
        preferences = {**self.get_reading_preferences(reader_key), **changes}
        with self._connect() as connection:
            connection.execute("INSERT INTO reading_preferences VALUES (?,?) ON CONFLICT(reader_key) DO UPDATE SET payload=excluded.payload",
                               (reader_key, json.dumps(preferences, ensure_ascii=False)))
        return preferences

    def set_subject_details(self, profile_id, *, origin_label, date_precision="exact", source="", relationship_to_user="unspecified"):
        if not self.get_profile(profile_id) or not _text(origin_label, 200):
            raise ValueError("Profil et libellé de la date d’origine requis.")
        if date_precision not in {"exact", "approximate"} or relationship_to_user not in {"self", "known", "public", "other", "unspecified"}:
            raise ValueError("Précision ou relation au sujet invalide.")
        with self._connect() as connection:
            connection.execute("""INSERT INTO reading_subjects VALUES (?,?,?,?,?)
                ON CONFLICT(profile_id) DO UPDATE SET origin_label=excluded.origin_label,
                date_precision=excluded.date_precision, source=excluded.source, relationship_to_user=excluded.relationship_to_user""",
                (int(profile_id), _text(origin_label, 200), date_precision, _text(source, 1000), relationship_to_user))

    def get_subject(self, profile_id):
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError("Profil introuvable.")
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM reading_subjects WHERE profile_id=?", (profile_id,)).fetchone()
        details = dict(row) if row else {}
        human = profile["profile_type"] == "Humain"
        return {
            "key": f"profile:{profile_id}", "type": profile["profile_type"],
            "name": " ".join(filter(None, (profile["name"], profile["last_name"]))),
            "relationship_to_user": details.get("relationship_to_user", "unspecified"),
            "origin": {"date": profile["birth_date"], "time": profile["birth_time"] or None,
                       "place": profile["birth_place"] or None,
                       "label": details.get("origin_label", "Naissance" if human else "Date de référence enregistrée — choix à préciser"),
                       "precision": details.get("date_precision", "exact"),
                       "source": details.get("source", "Profil saisi dans l’application"),
                       "basis_confirmed": human or bool(details.get("origin_label"))},
        }

    def set_event_reading(self, event_id, *, origin_label="", date_precision="exact", source="", event_state="recorded"):
        if not self.get_event(event_id):
            raise ValueError("Événement introuvable.")
        if date_precision not in {"exact", "approximate"} or event_state not in {"recorded", "occurred", "planned", "cancelled"}:
            raise ValueError("Métadonnées d’événement invalides.")
        with self._connect() as connection:
            connection.execute("""INSERT INTO event_readings VALUES (?,?,?,?,?) ON CONFLICT(event_id) DO UPDATE SET
                origin_label=excluded.origin_label, date_precision=excluded.date_precision, source=excluded.source, event_state=excluded.event_state""",
                (int(event_id), _text(origin_label, 200), date_precision, _text(source, 1000), event_state))

    def set_event_participants(self, event_id, participants):
        if not self.get_event(event_id):
            raise ValueError("Événement introuvable.")
        cleaned = {}
        for item in participants:
            pid = int(item["profile_id"])
            if not self.get_profile(pid) or pid in cleaned:
                raise ValueError("Participant inconnu ou répété.")
            cleaned[pid] = _text(item.get("role"), 200)
        # Only this explicitly selected event's links are replaced, transactionally.
        with self._connect() as connection:
            connection.execute("DELETE FROM event_participants WHERE event_id=?", (event_id,))
            connection.executemany("INSERT INTO event_participants VALUES (?,?,?)", ((event_id, pid, role) for pid, role in cleaned.items()))

    def reading_event(self, event_id):
        event = self.get_event(event_id)
        if not event:
            raise ValueError("Événement introuvable.")
        with self._connect() as connection:
            metadata = connection.execute("SELECT * FROM event_readings WHERE event_id=?", (event_id,)).fetchone()
            participants = connection.execute("""SELECT ep.profile_id, ep.role, p.name, p.last_name, p.profile_type
                FROM event_participants ep JOIN profiles p ON p.id=ep.profile_id WHERE ep.event_id=? ORDER BY ep.profile_id""", (event_id,)).fetchall()
        return {**event, "ref": f"event:{event_id}", "participants": [dict(row) for row in participants],
                "origin_label": metadata["origin_label"] if metadata else "",
                "date_precision": metadata["date_precision"] if metadata else "exact",
                "source": metadata["source"] if metadata else "Événement enregistré par l’utilisateur",
                "event_state": metadata["event_state"] if metadata else "recorded",
                "free_people_text_is_not_identity": True}

    def _check_subject(self, key):
        profile_id, event_id = _subject_ids(key)
        if not (self.get_profile(profile_id) if profile_id else self.get_event(event_id)):
            raise ValueError("Sujet introuvable.")
        return profile_id, event_id

    def _clean_memory(self, subject_key, data, reader_key):
        if set(data) - MEMORY_FIELDS:
            raise ValueError("Champ de mémoire inconnu.")
        result = dict(data)
        if result.get("kind") not in {"observation", "action", "hypothesis"}:
            raise ValueError("Nature de mémoire inconnue.")
        result["text"] = _text(result.get("text"))
        if not result["text"]:
            raise ValueError("Le contenu de la mémoire est vide.")
        result.setdefault("source_type", "model_proposed" if result["kind"] == "hypothesis" else "user_reported")
        if result["source_type"] not in {"user_reported", "third_party_report", "document", "model_proposed"}:
            raise ValueError("Source de mémoire inconnue.")
        if result["kind"] != "hypothesis" and result["source_type"] == "model_proposed":
            raise ValueError("Une proposition du modèle ne peut pas devenir un fait rapporté.")
        result["reporter"] = _text(result.get("reporter", "Utilisateur local"), 200)
        result.setdefault("perspective", "unspecified")
        if result["perspective"] not in {"self", "observer", "document", "unspecified"}:
            raise ValueError("Point de vue invalide.")
        result["date_start"], result["date_end"] = _date(result.get("date_start")), _date(result.get("date_end"))
        result.setdefault("date_precision", "exact" if result["date_start"] else "undated")
        if result["date_precision"] not in {"exact", "approximate", "undated"}:
            raise ValueError("Précision de date invalide.")
        if (result["date_precision"] == "undated") != (result["date_start"] is None):
            raise ValueError("Date et précision incohérentes.")
        if result["date_end"] and (not result["date_start"] or result["date_end"] < result["date_start"]):
            raise ValueError("Période de mémoire invalide.")
        for field in ("themes", "event_ids", "evidence_ids", "counterexample_ids"):
            values = result.get(field, [])
            if not isinstance(values, list) or len(values) > 20:
                raise ValueError("Liste de liens invalide.")
            result[field] = list(dict.fromkeys(_text(v, 120) for v in values)) if field == "themes" else list(dict.fromkeys(int(v) for v in values))
        for eid in result["event_ids"]:
            event = self.reading_event(eid)
            associated = {f"profile:{event['profile_id']}", f"event:{eid}"}
            associated.update(f"profile:{p['profile_id']}" for p in event["participants"])
            if subject_key not in associated:
                raise ValueError("Événement sans lien avec ce sujet.")
        for mid in result["evidence_ids"] + result["counterexample_ids"]:
            record = self.get_memory(mid, reader_key)
            if record["subject_key"] != subject_key:
                raise ValueError("La preuve concerne un autre sujet.")
        if result.get("polarity") is not None:
            if (result["kind"] != "observation" or result["source_type"] != "user_reported" or
                    result["perspective"] != "self" or result["date_precision"] != "exact" or
                    not all(result.get(k) for k in ("occurrence_id", "cycle_id", "card_id")) or
                    result["polarity"] not in {"constructive", "difficult", "mixed"}):
                raise ValueError("Une polarité exige un vécu personnel explicite et une occurrence exacte.")
        return result

    def add_memory(self, subject_key, data, *, reader_key="local_user"):
        profile_id, event_id = self._check_subject(subject_key)
        clean = self._clean_memory(subject_key, data, reader_key)
        status = "proposed" if clean["kind"] == "hypothesis" else "reported"
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute("""INSERT INTO reading_memory
                (reader_key,profile_id,event_subject_id,kind,status,payload,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)""",
                (reader_key, profile_id, event_id, clean["kind"], status, json.dumps(clean, ensure_ascii=False), now, now))
            mid = cursor.lastrowid
            connection.execute("INSERT INTO reading_memory_revisions VALUES (?,?,?,?,?,?)",
                               (mid, 0, json.dumps({**clean, "status": status}, ensure_ascii=False), "Création", clean["source_type"], now))
        return self.get_memory(mid, reader_key)

    def get_memory(self, memory_id, reader_key="local_user"):
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM reading_memory WHERE id=? AND reader_key=?", (memory_id, reader_key)).fetchone()
        if not row:
            raise ValueError("Mémoire introuvable pour ce lecteur.")
        kind, sid = ("profile", row["profile_id"]) if row["profile_id"] else ("event", row["event_subject_id"])
        return {**json.loads(row["payload"]), "id": row["id"], "ref": f"memory:{row['id']}",
                "subject_key": f"{kind}:{sid}", "reader_key": reader_key, "status": row["status"],
                "revision": row["revision"], "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def revise_memory(self, memory_id, changes, *, status, expected_revision, reason, actor="user", reader_key="local_user"):
        old = self.get_memory(memory_id, reader_key)
        allowed = HYPOTHESIS_STATES if old["kind"] == "hypothesis" else {"reported", "retracted"}
        if status not in allowed or actor not in {"user", "model"} or not _text(reason, 1000):
            raise ValueError("Révision invalide.")
        if actor == "model" and (old["kind"] != "hypothesis" or old["source_type"] != "model_proposed"
                or status not in {"proposed", "revised"} or old["status"] not in {"proposed", "revised"}):
            raise ValueError("Le modèle ne peut pas confirmer un vécu ni remplacer une décision humaine sur une hypothèse.")
        if set(changes) & {"kind", "source_type", "reporter", "perspective"}:
            raise ValueError("Une révision conserve la nature et la provenance de l’entrée.")
        if memory_id in changes.get("evidence_ids", []) or memory_id in changes.get("counterexample_ids", []):
            raise ValueError("Une entrée ne constitue pas sa propre preuve.")
        data = self._clean_memory(old["subject_key"], {**{k: old[k] for k in MEMORY_FIELDS if k in old}, **changes}, reader_key)
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute("""UPDATE reading_memory SET payload=?,status=?,revision=revision+1,updated_at=?
                WHERE id=? AND reader_key=? AND revision=?""",
                (json.dumps(data, ensure_ascii=False), status, now, memory_id, reader_key, expected_revision))
            if cursor.rowcount != 1:
                raise ValueError("Cette mémoire a déjà changé ; relire sa dernière révision.")
            connection.execute("INSERT INTO reading_memory_revisions VALUES (?,?,?,?,?,?)",
                (memory_id, expected_revision + 1, json.dumps({**data, "status": status}, ensure_ascii=False), _text(reason, 1000), actor, now))
        return self.get_memory(memory_id, reader_key)

    def memory_revisions(self, memory_id, reader_key="local_user"):
        self.get_memory(memory_id, reader_key)
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM reading_memory_revisions WHERE memory_id=? ORDER BY revision", (memory_id,)).fetchall()
        return [{**dict(row), "snapshot": json.loads(row["snapshot"])} for row in rows]

    def reading_material(self, subject_key, target_date, *, reader_key="local_user", event_ids=(), themes=(), limit=40):
        """Bounded read snapshot for the worker; no database access in Tk workers."""
        profile_id, event_id = self._check_subject(subject_key)
        target = date.fromisoformat(str(target_date))
        limit = max(1, min(80, int(limit)))
        with self._connect() as connection:
            if profile_id:
                candidates = connection.execute("""SELECT DISTINCT e.id,e.date_start FROM events e
                    LEFT JOIN event_participants ep ON ep.event_id=e.id
                    WHERE e.profile_id=? OR ep.profile_id=?
                    ORDER BY ABS(julianday(e.date_start)-julianday(?)),e.id DESC LIMIT ?""",
                    (profile_id, profile_id, target.isoformat(), limit)).fetchall()
            else:
                candidates = connection.execute("SELECT id,date_start FROM events WHERE id=?", (event_id,)).fetchall()
            ids = [r["id"] for r in connection.execute("""SELECT id FROM reading_memory WHERE reader_key=?
                AND profile_id IS ? AND event_subject_id IS ? ORDER BY id DESC LIMIT 400""", (reader_key, profile_id, event_id))]
        # Explicitly requested events are never fetched from unrelated subjects.
        all_eids = list(dict.fromkeys([int(i) for i in event_ids] + [r["id"] for r in candidates]))
        events = []
        for eid in all_eids[:limit]:
            event = self.reading_event(eid)
            related = event["profile_id"] == profile_id or any(p["profile_id"] == profile_id for p in event["participants"]) if profile_id else eid == event_id
            if not related:
                raise ValueError("Événement demandé hors du sujet étudié.")
            events.append(event)
        records = [self.get_memory(mid, reader_key) for mid in ids]
        selected_events = {e["id"] for e in events}
        def relevance(record):
            related = bool(selected_events & set(record["event_ids"])) or bool(set(themes) & set(record["themes"]))
            distance = abs((date.fromisoformat(record["date_start"]) - target).days) if record["date_start"] else 999999
            return (not related, distance, -record["id"])
        # Keep exclusions as well as supporting hypotheses so corrections survive retrieval.
        excluded = [r for r in records if r["status"] in {"rejected", "abandoned", "retracted"}]
        records = sorted(records, key=relevance)[:limit]
        for record in sorted(excluded, key=relevance)[:10]:
            if record not in records:
                records.append(record)
        existing = {r["id"] for r in records}
        for record in list(records):
            for mid in record["evidence_ids"] + record["counterexample_ids"]:
                if mid not in existing and len(records) < 100:
                    dependency = self.get_memory(mid, reader_key)
                    if dependency["subject_key"] == subject_key:
                        records.append(dependency)
                        existing.add(mid)
        if profile_id:
            subject = self.get_subject(profile_id)
            notes = self.get_profile(profile_id)["notes"]
        else:
            event = self.reading_event(event_id)
            subject = {"key": subject_key, "type": "Événement", "name": event["title"], "relationship_to_user": "unspecified",
                       "origin": {"date": event["date_start"], "time": event["event_time"], "place": event["place"],
                                  "label": event["origin_label"], "precision": event["date_precision"],
                                  "source": event["source"], "basis_confirmed": bool(event["origin_label"])}}
            notes = ""
        return {"subject": subject, "preferences": self.get_reading_preferences(reader_key),
                "events": events, "records": records, "profile_notes": notes,
                "reader_key": reader_key, "retrieval": {"limit": limit, "candidate_cap": 400,
                "selected_memory_ids": [r["id"] for r in records], "selected_event_ids": [e["id"] for e in events],
                "selection": "explicit_events_then_near_date_and_explicit_themes", "not_exhaustive": True}}
