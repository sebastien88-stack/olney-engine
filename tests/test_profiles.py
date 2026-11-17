import json
from pathlib import Path
from tempfile import TemporaryDirectory

from profile_store import ProfileStore


def sample_profile(name="Sébastien", last_name="Dupont"):
    return {
        "name": name,
        "last_name": last_name,
        "profile_type": "Humain",
        "birth_date": "1988-10-27",
        "birth_time": "07:51",
        "birth_place": "Longjumeau, FR",
        "latitude": 48.695,
        "longitude": 2.3074,
        "timezone": "Europe/Paris",
        "country_code": "FR",
        "notes": "",
    }


def test_profile_store_crud_and_last_profile():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        created = store.create_profile(sample_profile())
        assert created["name"] == "Sébastien"
        assert created["last_name"] == "Dupont"
        assert created["profile_type"] == "Humain"
        assert store.get_last_profile_id() == created["id"]

        changed = sample_profile("Seb")
        changed["birth_time"] = "08:12"
        updated = store.update_profile(created["id"], changed)
        assert updated["birth_time"] == "08:12"

        copy = store.duplicate_profile(created["id"])
        assert copy["name"] == "Seb — copie"
        assert len(store.list_profiles()) == 2

        store.delete_profile(copy["id"])
        assert store.get_last_profile_id() is None
        assert len(store.list_profiles()) == 1


def test_profile_json_round_trip_uses_a_new_name_on_collision():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        store = ProfileStore(root / "profiles.db")
        created = store.create_profile(sample_profile())
        exported = root / "sebastien.olney.json"
        store.export_profile(created["id"], exported)
        payload = json.loads(exported.read_text(encoding="utf-8"))
        assert payload["format"] == "olney-profile"
        assert "id" not in payload["profile"]

        imported = store.import_profile(exported)
        assert imported["name"] == "Sébastien 2"
        assert imported["last_name"] == "Dupont"
        assert imported["birth_date"] == "1988-10-27"


def test_same_first_name_is_allowed_with_a_different_last_name():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        first = store.create_profile(sample_profile("Sébastien", "Dupont"))
        second = store.create_profile(sample_profile("Sébastien", "Martin"))
        assert first["id"] != second["id"]
        assert len(store.list_profiles()) == 2


def test_recent_profiles_follow_the_last_opened_order():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        profiles = [
            store.create_profile(sample_profile(f"Profil {index}", "Test"))
            for index in range(1, 7)
        ]
        store.set_last_profile_id(profiles[1]["id"])
        recent = store.list_recent_profiles(5)
        assert recent[0]["id"] == profiles[1]["id"]
        assert len(recent) == 5

        store.set_favorite(profiles[0]["id"], True)
        recent = store.list_recent_profiles(5)
        assert recent[0]["id"] == profiles[1]["id"]
        assert store.get_profile(profiles[0]["id"])["favorite"] == 1


def test_legacy_database_is_migrated_without_losing_profiles():
    import sqlite3

    with TemporaryDirectory() as directory:
        database = Path(directory) / "profiles.db"
        connection = sqlite3.connect(database)
        connection.executescript(
            """
            CREATE TABLE profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                birth_date TEXT NOT NULL,
                birth_time TEXT NOT NULL,
                birth_place TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                timezone TEXT,
                country_code TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO profiles VALUES (
                1, 'Ancien profil', '1988-10-27', '07:51', 'Longjumeau, FR',
                48.695, 2.3074, 'Europe/Paris', 'FR', '', 'now', 'now'
            );
            """
        )
        connection.commit()
        connection.close()

        store = ProfileStore(database)
        profile = store.get_profile(1)
        assert profile["name"] == "Ancien profil"
        assert profile["last_name"] == ""
        assert profile["last_used_at"] == "now"
        assert profile["favorite"] == 0
        assert profile["profile_type"] == "Humain"


def test_events_are_profile_bound_and_cascade_on_profile_delete():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        profile = store.create_profile(sample_profile())
        created = store.create_event({
            "profile_id": profile["id"],
            "title": "Création entreprise",
            "category": "Travail",
            "date_start": "2026-08-29",
            "date_end": None,
            "event_time": "14:30",
            "place": "Longjumeau, FR",
            "people": "",
            "tags": "travail, lancement",
            "importance": 5,
            "notes": "Premier jour.",
        })
        assert created["profile_id"] == profile["id"]
        assert store.list_events(profile["id"])[0]["title"] == "Création entreprise"

        changed = dict(created)
        changed["title"] = "Lancement entreprise"
        updated = store.update_event(created["id"], changed)
        assert updated["title"] == "Lancement entreprise"

        store.delete_profile(profile["id"])
        assert store.list_events(profile["id"]) == []


def test_event_rejects_an_end_date_before_its_start():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        profile = store.create_profile(sample_profile())
        try:
            store.create_event({
                "profile_id": profile["id"],
                "title": "Période impossible",
                "category": "Autre",
                "date_start": "2026-08-29",
                "date_end": "2026-08-28",
                "importance": 3,
            })
        except ValueError as exc:
            assert "date de fin" in str(exc)
        else:
            raise AssertionError("Une période inversée aurait dû être refusée.")


def test_events_can_be_listed_across_profiles_and_reassigned():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        first = store.create_profile(sample_profile("Sébastien", "Dupont"))
        second = store.create_profile(sample_profile("Mélanie", "Martin"))
        event = store.create_event({
            "profile_id": first["id"], "title": "Voyage", "category": "Voyage",
            "date_start": "2026-08-29", "date_end": None,
            "event_time": "10:00", "place": "Longjumeau, FR",
            "people": "Mélanie Martin", "tags": "vacances",
            "importance": 4, "notes": "",
        })
        moved = dict(event)
        moved["profile_id"] = second["id"]
        store.update_event(event["id"], moved)

        assert store.list_events(first["id"]) == []
        assert store.list_events(second["id"])[0]["title"] == "Voyage"
        assert store.list_events()[0]["profile_id"] == second["id"]


def test_recent_events_follow_the_last_opened_order():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "profiles.db")
        profile = store.create_profile(sample_profile())
        event_ids = []
        for index in range(3):
            event_ids.append(store.create_event({
                "profile_id": profile["id"], "title": f"Événement {index}",
                "category": "Amour", "date_start": f"2026-08-{20 + index}",
                "importance": 3,
            })["id"])
        store.touch_event(event_ids[0])
        recent = store.list_recent_events(2)
        assert recent[0]["id"] == event_ids[0]
        assert recent[0]["profile_name"] == "Sébastien"
