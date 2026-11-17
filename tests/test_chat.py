import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from chat_ui import OlneyChatView
from olney_chat import DEFAULT_MODEL, OlneyChatService, OpenAIResponsesClient
from profile_store import ProfileStore


def profile(name="Alice"):
    return {
        "name": name,
        "last_name": "Test",
        "profile_type": "Humain",
        "birth_date": "1988-10-27",
        "birth_time": "12:00",
        "birth_place": "Paris, FR",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
        "country_code": "FR",
        "notes": "",
    }


def test_chat_storage_is_local_additive_and_cascades_messages():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        thread = store.create_chat_thread(
            subject_type="general", subject_label="Sans sujet",
            reading_angle="Automatique", target_date="2026-09-02",
        )
        store.add_chat_message(thread["id"], "user", "Bonjour", context={"x": 1})
        store.add_chat_message(
            thread["id"], "assistant", "Bonjour !", model="gpt-5-mini",
            response_id="resp_test", input_tokens=12, output_tokens=4,
        )
        rows = store.list_chat_messages(thread["id"])
        assert [row["role"] for row in rows] == ["user", "assistant"]
        assert json.loads(rows[0]["context_json"]) == {"x": 1}
        assert rows[1]["response_id"] == "resp_test"
        store.delete_chat_thread(thread["id"])
        assert store.list_chat_messages(thread["id"]) == []


def test_chat_threads_keep_creation_order_after_consultation():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        first = store.create_chat_thread(
            title="Première", target_date="2026-09-02",
        )
        second = store.create_chat_thread(
            title="Deuxième", target_date="2026-09-02",
        )
        store.touch_chat_thread(first["id"])
        assert [row["id"] for row in store.list_chat_threads()] == [
            second["id"], first["id"],
        ]


def test_terra_is_the_default_conversation_model():
    client = OpenAIResponsesClient("secret")
    assert DEFAULT_MODEL == "gpt-5.6-terra"
    assert client.model == "gpt-5.6-terra"
    assert client.reasoning_effort == "medium"


def test_chat_context_is_compact_and_keeps_calculated_facts():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        saved = store.create_profile(profile())
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{saved["id"]}'
        )
        context = service.build_context(subject, "2026-09-02")
        encoded = json.dumps(context, ensure_ascii=False)
        assert context["profile"]["birth_card"]["label"]
        assert context["cycles"]
        assert context["chat_request"]["subject_label"] == "Profil · Alice Test"
        assert "source_refs" not in encoded
        assert len(encoded) < 120000


def test_profile_chat_routes_a_named_event_to_its_historical_clock():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        saved = store.create_profile(profile())
        event = store.create_event({
            "profile_id": saved["id"],
            "title": "Rencontre Mel",
            "category": "Amour",
            "date_start": "2010-02-22",
            "date_end": None,
            "event_time": "19:07",
            "place": "Paris, FR",
            "people": "",
            "tags": "rencontre",
            "importance": 5,
            "notes": "",
        })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{saved["id"]}'
        )
        context = service.build_context(
            subject, "2026-09-02",
            question="Parle-moi de la rencontre avec Mel",
        )
        request = context["chat_request"]
        assert context["mode"] == "event_participants"
        assert context["target_date"] == "2010-02-22"
        assert request["routing"] == "named_event"
        assert request["base_subject"]["type"] == "profile"
        assert request["effective_subject"] == {
            "type": "event", "id": event["id"],
            "label": "Événement · Rencontre Mel · 2010-02-22",
        }
        assert request["requested_at"] == "2010-02-22"


def test_profile_chat_keeps_event_focus_for_followup_then_returns_to_present():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        saved = store.create_profile(profile())
        store.create_event({
            "profile_id": saved["id"], "title": "Permis moto",
            "category": "Réussite", "date_start": "2011-07-25",
            "date_end": None, "event_time": "10:30", "place": "Paris, FR",
            "people": "", "tags": "permis", "importance": 4, "notes": "",
        })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{saved["id"]}'
        )
        first = service.build_context(
            subject, "2026-09-02", question="Parle-moi du permis moto"
        )
        followup = service.build_context(
            subject, "2026-09-02", question="Et qu'est-ce que ça change ?",
            previous_context=first,
        )
        current = service.build_context(
            subject, "2026-09-02", question="Et mes cycles actuels ?",
            previous_context=followup,
        )
        assert followup["chat_request"]["routing"] == "continued_event"
        assert followup["target_date"] == "2011-07-25"
        assert current["chat_request"]["routing"] == "selected_subject"
        assert current["chat_request"]["effective_subject"]["type"] == "profile"
        assert current["target_date"] == "2026-09-02"


def test_chat_resolves_relative_date_before_building_profile_context():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        saved = store.create_profile(profile())
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{saved["id"]}'
        )
        context = service.build_context(
            subject, "2026-09-02", question="Regarde la journée d'hier"
        )
        assert context["target_date"] == "2026-09-01"
        assert context["chat_request"]["routing"] == "relative_date"
        assert context["chat_request"]["requested_at"] == "2026-09-01"


def test_chat_contract_names_emmett_and_forbids_unavailable_actions():
    with TemporaryDirectory() as directory:
        service = OlneyChatService(ProfileStore(Path(directory) / "chat.db"))
        prompt = service.system_prompt()
        assert "Tu es Emmett" in prompt
        assert "Olney Engine" in prompt
        assert "Tu ne peux pas changer le sujet sélectionné" in prompt
        assert "Toutes les cartes de `relationship_life_path` appartiennent au lien" in prompt
        assert "Ne pas proposer spontanément des rituels" in prompt
        assert "ambiguous_relationship" in prompt


def test_enter_sends_and_shift_enter_keeps_a_newline():
    view = object.__new__(OlneyChatView)
    sent = []
    view.send = lambda: sent.append(True)
    event = type("Event", (), {"state": 0})()
    shift_event = type("Event", (), {"state": 0x0001})()
    assert view._send_shortcut(event) == "break"
    assert sent == [True]
    assert view._send_shortcut(shift_event) is None
    assert sent == [True]


def test_event_chat_context_deduplicates_participant_knowledge():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        saved = store.create_profile(profile())
        event = store.create_event({
            "profile_id": saved["id"],
            "title": "Décision importante",
            "category": "Travail",
            "date_start": "2026-09-02",
            "date_end": None,
            "event_time": "12:00",
            "place": "Paris, FR",
            "people": "",
            "tags": "choix",
            "importance": 4,
            "notes": "",
        })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'event:{event["id"]}'
        )
        context = service.build_context(subject, "2030-01-01")
        encoded = json.dumps(context, ensure_ascii=False)
        assert context["mode"] == "event_participants"
        assert context["target_date"] == "2026-09-02"
        assert '"knowledge_bundle"' not in encoded
        assert len(encoded) < 140000


def test_relationship_is_available_as_a_chat_subject():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        first = store.create_profile(profile("Alice"))
        second_data = profile("Bob")
        second_data["birth_date"] = "1990-02-03"
        second = store.create_profile(second_data)
        relation = store.create_relationship({
            "profile_a_id": first["id"],
            "profile_b_id": second["id"],
            "relationship_type": "Amitié",
            "title": "Le duo",
            "notes": "",
        })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'relationship:{relation["id"]}'
        )
        context = service.build_context(subject, "2026-09-02")
        assert context["relationship_card"]
        assert len(context["subjects"]) == 2


def test_profile_chat_routes_a_named_relationship_from_either_participant():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        alice = store.create_profile(profile("Alice"))
        bob_data = profile("Bob")
        bob_data["birth_date"] = "1990-02-03"
        bob = store.create_profile(bob_data)
        relation = store.create_relationship({
            "profile_a_id": alice["id"], "profile_b_id": bob["id"],
            "relationship_type": "Amitié", "title": "Le duo", "notes": "",
        })
        service = OlneyChatService(store)
        subjects = {item["key"]: item for item in service.subject_options()}
        from_alice = service.build_context(
            subjects[f'profile:{alice["id"]}'], "2026-09-02",
            question="Parle-moi de ma relation avec Bob",
        )
        from_bob = service.build_context(
            subjects[f'profile:{bob["id"]}'], "2026-09-02",
            question="Que peux-tu dire de mon lien avec Alice ?",
        )
        for context in (from_alice, from_bob):
            request = context["chat_request"]
            assert context["mode"] == "relationship"
            assert request["routing"] == "named_relationship"
            assert request["effective_subject"]["id"] == relation["id"]


def test_profile_chat_keeps_relationship_focus_and_can_return_to_profile():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        alice = store.create_profile(profile("Alice"))
        bob_data = profile("Bob")
        bob_data["birth_date"] = "1990-02-03"
        bob = store.create_profile(bob_data)
        store.create_relationship({
            "profile_a_id": alice["id"], "profile_b_id": bob["id"],
            "relationship_type": "Amitié", "title": "Le duo", "notes": "",
        })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{alice["id"]}'
        )
        first = service.build_context(
            subject, "2026-09-02", question="Parle-moi de ma relation avec Bob"
        )
        followup = service.build_context(
            subject, "2026-09-02", question="Et son chemin de vie ?",
            previous_context=first,
        )
        current = service.build_context(
            subject, "2026-09-02", question="Reviens à mon profil actuel",
            previous_context=followup,
        )
        assert followup["chat_request"]["routing"] == "continued_relationship"
        assert followup["mode"] == "relationship"
        assert current["chat_request"]["routing"] == "selected_subject"
        assert current["chat_request"]["effective_subject"]["type"] == "profile"


def test_relationship_routing_reports_ambiguity_instead_of_guessing():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        alice = store.create_profile(profile("Alice"))
        for index, last_name in enumerate(("Martin", "Durand"), start=1):
            bob_data = profile("Bob")
            bob_data["last_name"] = last_name
            bob_data["birth_date"] = f"1990-02-0{index + 1}"
            bob = store.create_profile(bob_data)
            store.create_relationship({
                "profile_a_id": alice["id"], "profile_b_id": bob["id"],
                "relationship_type": "Amitié", "title": "", "notes": "",
            })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{alice["id"]}'
        )
        context = service.build_context(
            subject, "2026-09-02", question="Parle-moi de ma relation avec Bob"
        )
        request = context["chat_request"]
        assert request["routing"] == "ambiguous_relationship"
        assert request["effective_subject"]["type"] == "profile"
        assert len(request["ambiguous_relationship_candidates"]) == 2


def test_event_wording_does_not_accidentally_route_to_a_one_word_relation_title():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        alice = store.create_profile(profile("Alice"))
        mel_data = profile("Mélanie")
        mel_data["birth_date"] = "1990-02-03"
        mel = store.create_profile(mel_data)
        store.create_relationship({
            "profile_a_id": alice["id"], "profile_b_id": mel["id"],
            "relationship_type": "Amour", "title": "Mélanie", "notes": "",
        })
        event = store.create_event({
            "profile_id": alice["id"], "title": "Rencontre Mélanie",
            "category": "Amour", "date_start": "2010-02-22",
            "date_end": None, "event_time": "19:07", "place": "Paris, FR",
            "people": "", "tags": "rencontre", "importance": 5, "notes": "",
        })
        store.set_event_participants(event["id"], [
            {"profile_id": mel["id"], "role": "Personne concernée"}
        ])
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'profile:{alice["id"]}'
        )
        context = service.build_context(
            subject, "2026-09-02", question="Parle-moi de la rencontre avec Mélanie"
        )
        assert context["chat_request"]["routing"] == "named_event"
        assert context["chat_request"]["effective_subject"]["id"] == event["id"]


def test_relationship_chat_keeps_doctrine_and_hides_internal_path_positions():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "chat.db")
        alice = store.create_profile(profile("Alice"))
        bob_data = profile("Bob")
        bob_data["birth_date"] = "1990-02-03"
        bob = store.create_profile(bob_data)
        relation = store.create_relationship({
            "profile_a_id": alice["id"], "profile_b_id": bob["id"],
            "relationship_type": "Amitié", "title": "Le duo", "notes": "",
        })
        service = OlneyChatService(store)
        subject = next(
            item for item in service.subject_options()
            if item["key"] == f'relationship:{relation["id"]}'
        )
        context = service.build_context(subject, "2026-09-02")
        path = context["relationship_life_path"]
        assert path["belongs_to"] == "relationship"
        assert "series_id" not in path
        assert all("position" not in row for row in path["rows"])
        assert "rule:relationships" in context["knowledge"]["rules"]
        assert context["conversation_evidence_policy"]["free_text_notes"] == (
            "user_context_not_interpretive_proof"
        )


def test_responses_client_uses_stateless_api_and_extracts_text():
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "id": "resp_123", "model": "gpt-5-mini",
                "output": [{
                    "type": "message", "role": "assistant",
                    "content": [{"type": "output_text", "text": "Lecture test"}],
                }],
                "usage": {"input_tokens": 100, "output_tokens": 20},
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    client = OpenAIResponsesClient("secret", model="gpt-5-mini")
    with patch("olney_chat.urlopen", fake_urlopen):
        result = client.respond(
            instructions="Règles", context={"mode": "general"},
            messages=[{"role": "user", "content": "Que vois-tu ?"}],
        )
    assert result["text"] == "Lecture test"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["model"] == "gpt-5-mini"
    assert captured["payload"]["max_output_tokens"] == 3000
    assert captured["payload"]["reasoning"] == {"effort": "medium"}
    assert captured["payload"]["text"] == {"verbosity": "medium"}
    assert captured["payload"]["input"][-1]["content"] == "Que vois-tu ?"


def test_responses_client_retries_an_empty_token_limited_response_once():
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    responses = [
        {
            "id": "resp_short", "model": "gpt-5-mini", "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
            "usage": {"input_tokens": 100, "output_tokens": 3000},
        },
        {
            "id": "resp_retry", "model": "gpt-5-mini", "status": "completed",
            "output_text": "Lecture complète",
            "usage": {"input_tokens": 100, "output_tokens": 40},
        },
    ]

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse(responses[len(calls) - 1])

    client = OpenAIResponsesClient("secret")
    with patch("olney_chat.urlopen", fake_urlopen):
        result = client.respond(
            instructions="Règles", context={"mode": "general"},
            messages=[{"role": "user", "content": "Lis ce moment"}],
        )
    assert result["text"] == "Lecture complète"
    assert result["retry_count"] == 1
    assert result["input_tokens"] == 200
    assert result["output_tokens"] == 3040
    assert [call["max_output_tokens"] for call in calls] == [3000, 6000]
