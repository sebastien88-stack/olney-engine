from pathlib import Path
from tempfile import TemporaryDirectory

from interpretation_runtime import InterpretationKnowledge
from interpretation_validation import validate_relationship_context
from olney_engine import OlneyEngine
from profile_store import ProfileStore
from reading_service import ReadingService
from relationship_runtime import RelationshipEngine, relationship_card_number


ENGINE = OlneyEngine()
RUNTIME = RelationshipEngine(ENGINE, InterpretationKnowledge.load())


def profile(name, birth_date="1988-10-27"):
    return {
        "name": name,
        "last_name": "Test",
        "profile_type": "Humain",
        "birth_date": birth_date,
        "birth_time": "12:00",
        "birth_place": "Paris, FR",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
        "country_code": "FR",
        "notes": "",
    }


def test_relationship_card_uses_solar_values_and_preserves_king_of_spades():
    assert relationship_card_number(26, 33) == 7
    assert ENGINE.card_label(relationship_card_number(26, 33)) == "7♥"
    assert relationship_card_number(52, 52) == 52
    assert ENGINE.card_label(relationship_card_number(52, 52)) == "R♠"
    assert relationship_card_number(8, 25) == 33
    assert ENGINE.card_label(33) == "7♦"


def test_engine_explicit_reference_card_mode_remains_deterministic():
    state = ENGINE.full_state(
        "2010-02-22", "2026-09-01", birth_card_number=4
    )
    assert state["birth"]["card"] == "4♥"
    assert state["birth_card_override"] is True
    assert state["secondary_cards"]["cards"] == []
    assert state["life_path"]["rows"]
    assert state["year"]["year_card"]


def test_morera_associated_cards_are_existing_positional_exchanges():
    number = {label: value for value, label in ENGINE.cards.items()}
    examples = {
        "3♦": {"6♥", "D♦"},
        "9♠": {"R♥", "6♠"},
        "6♦": {"3♠", "9♣"},
    }
    for card, expected in examples.items():
        exchange = ENGINE.positional_exchange(90, 1, number[card])
        assert {exchange["displacement"]["card"], exchange["environment"]["card"]} == expected


def test_relationship_subject_does_not_expand_displaced_cards():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "relations.db")
        saved = store.create_profile(profile("Alice"))
        subject = RUNTIME.subject(saved)
        assert "associated_cards" not in subject
        assert subject["permanent_reference_cards"] == [subject["birth_card"]]


def test_diagonal_links_are_reciprocal_and_horizontal_links_keep_direction():
    def subject(identifier, name, card_number):
        card = {
            "card_number": card_number, "card": ENGINE.card_label(card_number),
            "origin": "carte_de_naissance", "origin_priority": 0,
        }
        return {
            "profile_id": identifier, "name": name,
            "reference_cards": [card], "permanent_reference_cards": [card],
        }

    first_card = ENGINE.card_at(1, 1).card_number
    diagonal_card = ENGINE.card_at(1, 7).card_number
    links = RUNTIME.permanent_links(
        subject(1, "A", first_card), subject(2, "B", diagonal_card)
    )
    diagonal = next(
        link for link in links
        if link.get("table_id") == 1 and link.get("axis") == "diagonale_6"
        and link.get("distance") == 1
    )
    assert diagonal["reciprocal"] is True
    assert diagonal["direction"] == "réciproque"

    number = {label: value for value, label in ENGINE.cards.items()}
    links = RUNTIME.permanent_links(
        subject(1, "Bill", number["7♣"]), subject(2, "Hillary", number["9♥"])
    )
    adjacency = next(
        link for link in links
        if link.get("table_id") == 1 and link.get("axis") == "horizontal"
        and link.get("distance") == 1
    )
    assert adjacency["source_card"]["card"] == "9♥"
    assert adjacency["target_card"]["card"] == "7♣"
    assert adjacency["role"] == "lune_soleil"


def test_permanent_links_only_compare_birth_cards_in_manifested_order():
    number = {label: value for value, label in ENGINE.cards.items()}

    def subject(identifier, name, label):
        card = {
            "card_number": number[label], "card": label,
            "origin": "carte_de_naissance", "origin_priority": 0,
        }
        return {
            "profile_id": identifier, "name": name,
            "reference_cards": [card], "permanent_reference_cards": [card],
        }

    links = RUNTIME.permanent_links(
        subject(1, "Bill", "7♣"), subject(2, "Hillary", "9♥")
    )
    assert links
    assert {link["table"] for link in links} == {"ordre_manifeste"}
    assert all(
        link[side]["origin"] == "carte_de_naissance"
        for link in links for side in ("source_card", "target_card")
    )
    definitions = {
        (
            link["role"], link["reciprocal"],
            link["source_subject_id"], link["target_subject_id"],
        )
        for link in links
    }
    assert len(definitions) == len(links)
    assert all(link["route_count"] == len(link["routes"]) for link in links)


def test_natural_order_compares_birth_cards_and_relationship_card_separately():
    first = RUNTIME.subject({"id": 1, **profile("Alice")})
    second = RUNTIME.subject({"id": 2, **profile("Bob", "1990-02-03")})
    relation = RUNTIME._card_fact(
        relationship_card_number(
            first["birth_card"]["card_number"], second["birth_card"]["card_number"]
        ),
        "carte_de_relation",
    )
    links = RUNTIME.natural_order_links(first, second, relation)
    assert links
    assert {link["table_id"] for link in links} == {90}
    assert {link["comparison_pair"] for link in links} == {
        "birth_birth", "first_relationship", "second_relationship",
    }
    assert all(
        link[side]["origin"] in {"carte_de_naissance", "carte_de_relation"}
        for link in links for side in ("source_card", "target_card")
    )
    assert all(
        set(link["role_reading"]) == {"essence", "resource", "tension"}
        for link in links
    )


def test_annual_relationship_roles_are_directional_and_natal_only():
    first_profile = {"id": 1, **profile("Alice")}
    second_profile = {"id": 2, **profile("Bob", "1990-02-03")}
    found = []
    for year in range(2026, 2037):
        package = RUNTIME.build(first_profile, second_profile, f"{year}-09-01")
        found.extend(package["annual_relationship_roles"])
        if found:
            break
    assert found
    assert all(role["type"] == "annual_relationship_role" for role in found)
    assert all(role["host_subject_id"] != role["appearing_subject_id"] for role in found)
    assert all(
        reference["origin"] in {"carte_de_naissance", "carte_secondaire"}
        for role in found for reference in role["matched_references"]
    )
    assert all(
        set(role["role_reading"]) == {"essence", "resource", "tension"}
        for role in found
    )


def test_relationship_storage_is_additive_recent_and_cascades_with_profiles():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "relations.db")
        first = store.create_profile(profile("Alice"))
        second = store.create_profile(profile("Bob", "1990-02-03"))
        created = store.create_relationship({
            "profile_a_id": first["id"], "profile_b_id": second["id"],
            "relationship_type": "Amitié", "title": "Alice et Bob", "notes": "",
        })
        assert store.get_relationship(created["id"])["profile_b_name"] == "Bob"
        store.set_relationship_favorite(created["id"], True)
        assert store.list_relationships()[0]["favorite"] == 1
        store.touch_relationship(created["id"])
        assert store.list_recent_relationships(1)[0]["id"] == created["id"]
        store.delete_profile(first["id"])
        assert store.get_relationship(created["id"]) is None


def test_relationship_service_keeps_two_subjects_and_two_clocks_without_score():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "relations.db")
        first = store.create_profile(profile("Alice"))
        second = store.create_profile(profile("Bob", "1990-02-03"))
        relation = store.create_relationship({
            "profile_a_id": first["id"], "profile_b_id": second["id"],
            "relationship_type": "Amour", "title": "", "notes": "Vécu commun",
        })
        shared = store.create_event({
            "profile_id": first["id"], "title": "Voyage commun",
            "date_start": "2026-05-01", "category": "Voyage",
        })
        store.set_event_participants(shared["id"], [
            {"profile_id": second["id"], "role": "participant"}
        ])
        context = ReadingService(store, engine=ENGINE).relationship_context(
            relation["id"], "2026-09-01", target_time="12:00", target_place="Paris, FR"
        )
        assert context["mode"] == "relationship"
        assert len(context["subjects"]) == 2
        assert len(context["personal_contexts"]) == 2
        assert len(context["current_clocks"]) == 2
        for clock in context["current_clocks"]:
            assert clock["status"] == "calculé"
            assert all(
                clock.get(key)
                for key in ("chemin_de_vie", "année", "52_jours", "jour", "heure")
            )
        assert context["permanent_link_index"]["selected_for_llm"] <= 32
        assert context["schema_version"] == "1.2.0"
        assert context["natural_order_link_index"]["total"] == len(
            context["natural_order_links"]
        )
        assert "annual_relationship_roles" in context
        assert context["llm_policy"]["no_compatibility_score"] is True
        assert "compatibility_score" not in context
        assert context["relationship_card"]["card"] == "4♥"
        relationship_path = context["relationship_life_path"]
        assert [row["slot"] for row in relationship_path["rows"]] == [
            "mercure", "vénus", "mars", "jupiter", "saturne", "uranus",
            "neptune", "défi", "résultat",
        ]
        assert relationship_path["reference_card"] == "4♥"
        relation_reading = context["relationship_card"]["relationship_reading"]
        assert all(
            relation_reading.get(key)
            for key in ("energy", "constructive", "tension", "manifestations")
        )
        assert "Alice Test" in relation_reading["energy"]
        assert "Bob Test" in relation_reading["energy"]
        assert context["common_events"][0]["title"] == "Voyage commun"
        assert "temporal_activations" in context
        assert all(
            activation["type"] == "other_reference_card_active"
            for activation in context["temporal_activations"]
        )
        assert all(
            reference.get("origin") in {
                "carte_de_naissance", "carte_secondaire",
                "chemin_de_vie_manifeste",
            }
            for activation in context["temporal_activations"]
            for reference in activation.get("matched_references", [])
        )
        validate_relationship_context(context)
