from contextlib import contextmanager
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

from interpretation_runtime import InterpretationKnowledge
from interpretation_validation import validate_context, validate_llm_output, resolve_evidence
from olney_engine import OlneyEngine
from personal_context import reading_intent
from profile_store import ProfileStore
from reading_service import ReadingService


ENGINE = OlneyEngine()
KNOWLEDGE = InterpretationKnowledge.load()
TARGET = "2026-08-31"


def expect_error(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def profile(name, **changes):
    return {"name": name, "birth_date": "1988-10-27", "birth_time": "07:51",
            "birth_place": "Longjumeau, FR", "profile_type": "Humain", **changes}


def event(store, pid, when=TARGET, **changes):
    return store.create_event({"profile_id": pid, "title": "Moment partagé", "date_start": when, **changes})


@contextmanager
def sample():
    with TemporaryDirectory() as directory:
        store = ProfileStore(Path(directory) / "isolated.db")
        alice = store.create_profile(profile("Alice", notes="Contexte libre, pas un vécu daté."))["id"]
        bob = store.create_profile(profile("Bob"))["id"]
        service = ReadingService(store, engine=ENGINE, knowledge=KNOWLEDGE)
        yield store, service, alice, bob


def test_additive_initialization_preserves_legacy_profiles_and_events():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "legacy.db"
        with patch.object(ProfileStore, "_initialize_reading_tables", lambda *args: None):
            legacy = ProfileStore(path)
            person = legacy.create_profile(profile("Historique"))
            old_event = event(legacy, person["id"])
        store = ProfileStore(path)
        assert store.get_profile(person["id"]) == person
        assert store.get_event(old_event["id"]) == old_event
        record = store.add_memory(f"profile:{person['id']}", {"kind": "observation", "text": "Vécu conservé"})
        again = ProfileStore(path)
        assert again.get_memory(record["id"]) == record
        assert len(again.memory_revisions(record["id"])) == 1


def test_reader_and_subject_isolation_even_with_identical_birthdays():
    with sample() as (store, service, alice, bob):
        a = store.add_memory(f"profile:{alice}", {"kind": "observation", "text": "Ma version", "perspective": "self"})
        store.add_memory(f"profile:{alice}", {"kind": "observation", "text": "Autre lecteur"}, reader_key="other")
        store.add_memory(f"profile:{bob}", {"kind": "action", "text": "Action de Bob"})
        ctx = service.profile_context(alice, TARGET)
        validate_context(ctx)
        assert list(ctx["personal"]["records"]) == [a["ref"]]
        assert ctx["personal"]["profile_notes"] == "Contexte libre, pas un vécu daté."
        assert resolve_evidence(ctx, a["ref"])["text"] == "Ma version"
        other = service.profile_context(bob, TARGET)
        assert ctx["cycles"][1]["occurrence_id"] != other["cycles"][1]["occurrence_id"]
        expect_error(lambda: store.get_memory(a["id"], "other"))
        expect_error(lambda: store.add_memory(f"profile:{bob}", {"kind": "hypothesis", "text": "Mélange", "evidence_ids": [a["id"]]}))
        material = store.reading_material(f"profile:{alice}", TARGET)
        material["records"][0]["reader_key"] = "other"
        expect_error(lambda: service.builder.from_dates("1988-10-27", TARGET, reading_material=material))


def test_hypothesis_audit_provenance_and_user_decisions_are_preserved():
    with sample() as (store, service, alice, bob):
        record = store.add_memory(f"profile:{alice}", {"kind": "hypothesis", "text": "Piste à discuter"})
        args = {"status": "confirmed", "expected_revision": 0, "reason": "Retour utilisateur"}
        expect_error(lambda: store.revise_memory(record["id"], {}, actor="model", **args))
        confirmed = store.revise_memory(record["id"], {}, **args)
        assert confirmed["kind"] == "hypothesis" and confirmed["source_type"] == "model_proposed"
        expect_error(lambda: store.revise_memory(record["id"], {}, **args))
        expect_error(lambda: store.revise_memory(record["id"], {"text": "Remplacement"}, status="revised", expected_revision=1, reason="Modèle", actor="model"))
        expect_error(lambda: store.revise_memory(record["id"], {"kind": "observation"}, status="revised", expected_revision=1, reason="Conversion"))
        rejected = store.revise_memory(record["id"], {"text": "Piste écartée après discussion"}, status="rejected", expected_revision=1, reason="Contre-exemple")
        audit = store.memory_revisions(record["id"])
        assert [a["snapshot"]["status"] for a in audit] == ["proposed", "confirmed", "rejected"]
        assert audit[0]["snapshot"]["text"] == "Piste à discuter"
        ctx = service.profile_context(alice, TARGET)
        validate_context(ctx)
        assert rejected["ref"] in ctx["personal"]["excluded_refs"]
        expect_error(lambda: store.revise_memory(record["id"], {}, status="proposed", expected_revision=2, reason="Retour", actor="model"))


def test_invalid_memory_links_dates_and_model_facts_are_rejected():
    with sample() as (store, service, alice, bob):
        key = f"profile:{alice}"
        for data in ({"kind": "observation", "source_type": "model_proposed"},
                     {"kind": "observation", "date_start": TARGET, "date_precision": "undated"},
                     {"kind": "observation", "date_start": TARGET, "date_end": "2020-01-01"},
                     {"kind": "hypothesis", "polarity": "constructive"},
                     {"kind": "observation", "unknown": "field"}):
            expect_error(lambda data=data: store.add_memory(key, {"text": "Test", **data}))
        record = store.add_memory(key, {"kind": "hypothesis", "text": "Hypothèse"})
        expect_error(lambda: store.revise_memory(record["id"], {"evidence_ids": [record["id"]]}, status="revised", expected_revision=0, reason="Boucle"))
        unrelated = event(store, bob)
        expect_error(lambda: store.add_memory(key, {"kind": "observation", "text": "Confusion", "event_ids": [unrelated["id"]]}))


def test_only_exact_self_reports_set_the_target_occurrence_polarity():
    with sample() as (store, service, alice, bob):
        key = f"profile:{alice}"
        current = next(c for c in service.profile_context(alice, TARGET)["cycles"] if c["id"] == "annual")
        data = {"kind": "observation", "text": "J’ai bien vécu cette période", "perspective": "self", "date_start": TARGET,
                "occurrence_id": current["occurrence_id"], "cycle_id": current["id"], "card_id": current["active_card"]["id"], "polarity": "constructive"}
        expect_error(lambda: store.add_memory(key, {**data, "perspective": "observer"}))
        expect_error(lambda: store.add_memory(key, {**data, "date_precision": "approximate"}))
        observation = store.add_memory(key, data)
        ctx = service.profile_context(alice, TARGET)
        validate_context(ctx)
        assert next(c for c in ctx["cycles"] if c["id"] == "annual")["lived_polarity"] == "constructive"
        assert ctx["profile_history"][0]["memory_ref"] == observation["ref"]
        other = service.profile_context(bob, TARGET)
        assert all(c["lived_polarity"] == "unknown" for c in other["cycles"])
        store.revise_memory(observation["id"], {}, status="retracted", expected_revision=0, reason="Je corrige mon retour")
        assert not service.profile_context(alice, TARGET)["profile_history"]


def test_shared_event_keeps_linked_ids_and_each_participants_account():
    with sample() as (store, service, alice, bob):
        moment = event(store, alice, people="Bob, autre Bob")
        assert not store.reading_event(moment["id"])["participants"]  # Never guess identity from a name.
        store.set_event_participants(moment["id"], [{"profile_id": bob, "role": "Co-organisateur"}])
        assert moment["id"] in {item["id"] for item in store.list_events(bob)}
        for pid, text in ((alice, "Enthousiasme"), (bob, "Fatigue")):
            store.add_memory(f"profile:{pid}", {"kind": "observation", "text": text, "event_ids": [moment["id"]], "perspective": "self"})
        result = service.event_context(moment["id"])
        assert len(result["contexts"]) == 2
        for ctx, expected in zip(result["contexts"], ("Enthousiasme", "Fatigue")):
            validate_context(ctx)
            assert [r["text"] for r in ctx["personal"]["records"].values()] == [expected]
            assert ctx["hour_card"] is None
        expect_error(lambda: store.set_event_participants(moment["id"], [{"profile_id": 99999}]))
        assert store.reading_event(moment["id"])["participants"][0]["profile_id"] == bob


def test_event_origin_requires_an_explicit_choice_and_no_invented_hour():
    with sample() as (store, service, alice, bob):
        moment = event(store, alice, "2020-04-02", event_time="12:30")
        expect_error(lambda: service.event_context(moment["id"], mode="origin"))
        store.set_event_reading(moment["id"], origin_label="Lancement public", source="Annonce conservée")
        ctx = service.event_context(moment["id"], mode="origin")
        validate_context(ctx)
        assert ctx["subject"]["key"] == f"event:{moment['id']}"
        assert ctx["subject"]["origin"]["label"] == "Lancement public"
        assert ctx["reading"]["subject_policy"] == "nonhuman_no_intimate_psychology"
        assert ctx["hour_card"] is None and ctx["reading"]["hour_input"]["status"] == "incomplete"
        future = service.event_context(moment["id"], mode="origin", target_date=TARGET)
        validate_context(future)
        assert future["reading"]["hour_input"]["time"] is None
        participants = service.event_context(moment["id"])
        assert participants["contexts"][0]["reading"]["hour_input"]["status"] == "incomplete"


def test_missing_place_does_not_break_cycles_but_invalid_calendar_still_fails():
    with sample() as (store, service, alice, bob):
        ctx = service.profile_context(alice, TARGET, target_time="12:00", target_place="Un endroit introuvable XQZ")
        validate_context(ctx)
        assert ctx["reading"]["hour_input"]["status"] == "unavailable"
        assert len(ctx["cycles"]) == 5 and ctx["hour_card"] is None
        expect_error(lambda: service.profile_context(alice, "2026-99-31"))


def test_subject_type_origin_precision_and_historical_events_are_explicit():
    with sample() as (store, service, alice, bob):
        city = store.create_profile(profile("Cité", profile_type="Ville"))["id"]
        ctx = service.profile_context(city, TARGET)
        assert "origin_basis" in ctx["reading"]["missing_data"]
        store.set_subject_details(city, origin_label="Fondation conventionnelle", date_precision="approximate", source="Archive à vérifier")
        ctx = service.profile_context(city, TARGET)
        validate_context(ctx)
        assert ctx["reading"]["origin_assumption"] == "reference_date_only"
        assert "origin_basis" not in ctx["reading"]["missing_data"]
        ancient = event(store, alice, "1815-06-18")
        comparison = service.event_context(ancient["id"])
        assert comparison["contexts"] == [] and comparison["unavailable"][0]["reason"] == "event_before_subject_origin"


def test_four_reading_angles_are_independent_of_the_cycle_and_optional():
    with sample() as (store, service, alice, bob):
        for angle in ("temporal", "behavioral", "developmental", "existential"):
            ctx = service.profile_context(alice, TARGET, reading_focus="day", options={"angle": angle})
            validate_context(ctx)
            assert ctx["reading"]["focal_cycle_id"] == "week"
            assert ctx["reading"]["intent"]["angle"] == angle
            assert ctx["learning_frame"]["no_maturity_score"]
        store.set_reading_preferences({"existential": "never", "depth": "concise"})
        expect_error(lambda: service.profile_context(alice, TARGET, options={"angle": "existential"}))
        assert service.profile_context(alice, TARGET)["reading"]["intent"]["preferences"]["depth"] == "concise"
        assert store.get_reading_preferences("another")["depth"] == "balanced"
        expect_error(lambda: reading_intent({"angle": "destiny"}))
        expect_error(lambda: store.set_reading_preferences({"maturity": 10}))


def test_retrieval_keeps_corrections_dependencies_and_limits_payload():
    with sample() as (store, service, alice, bob):
        key = f"profile:{alice}"
        counter = store.add_memory(key, {"kind": "observation", "text": "Contre-exemple", "date_start": "2001-01-01"})
        hypothesis = store.add_memory(key, {"kind": "hypothesis", "text": "Ancienne piste", "counterexample_ids": [counter["id"]]})
        store.revise_memory(hypothesis["id"], {}, status="rejected", expected_revision=0, reason="Contredite")
        for i in range(85):
            store.add_memory(key, {"kind": "observation", "text": str(i) + "x" * 4000, "date_start": TARGET})
        material = store.reading_material(key, TARGET, limit=200)
        assert len(material["records"]) <= 100
        assert {counter["id"], hypothesis["id"]} <= {r["id"] for r in material["records"]}
        ctx = service.builder.from_dates("1988-10-27", TARGET, reading_material=material)
        validate_context(ctx)
        assert sum(len(r["text"]) for r in ctx["personal"]["records"].values()) <= 24000
        assert any(r.get("truncated_fields") for r in ctx["personal"]["records"].values())
        assert store.get_memory(counter["id"])["text"] == "Contre-exemple"


def test_factual_repetitions_require_distinct_periods_and_preserve_context():
    with sample() as (store, service, alice, bob):
        seen = {}
        for year in range(1989, 2080):
            when = f"{year}-10-27"
            label = ENGINE.year_table("1988-10-27", when)["year_card"]
            if label in seen:
                first, second = seen[label], when
                break
            seen[label] = when
        event(store, alice, first)
        event(store, alice, (date.fromisoformat(first) + timedelta(days=1)).isoformat())
        baseline = service.profile_context(alice, TARGET, options={"include_patterns": True})
        assert not any(r["cycle_id"] == "seven_year" for r in baseline["personal"]["longitudinal"]["calculated_repetitions"])
        event(store, alice, second)
        ctx = service.profile_context(alice, TARGET, options={"include_patterns": True})
        validate_context(ctx)
        longitudinal = ctx["personal"]["longitudinal"]
        assert any(r["cycle_id"] == "seven_year" for r in longitudinal["calculated_repetitions"])
        assert longitudinal["semantic_inference_performed"] is False
        for state in longitudinal["event_states"]:
            assert all("sequence_planet" in c and "context_planets" in c for c in state["cycles"])


def test_themes_are_recorded_labels_not_automatic_psychological_connections():
    with sample() as (store, service, alice, bob):
        for kind in ("observation", "action"):
            store.add_memory(f"profile:{alice}", {"kind": kind, "text": "Une situation", "themes": ["autonomie"]})
        store.add_memory(f"profile:{alice}", {"kind": "hypothesis", "text": "Supposition", "themes": ["autonomie", "vocation"]})
        moment = event(store, alice)
        store.set_event_reading(moment["id"], date_precision="approximate", event_state="planned")
        ctx = service.profile_context(alice, TARGET, options={"angle": "behavioral"})
        validate_context(ctx)
        themes = ctx["personal"]["longitudinal"]["recorded_themes"]
        assert len(themes) == 1 and len(themes[0]["evidence"]) == 2
        state = ctx["personal"]["longitudinal"]["event_states"][0]
        assert state["status"] == "not_calculated" and state["reason"] == "approximate_event_date"


def test_output_contract_checks_new_blocks_and_hypothesis_provenance():
    with sample() as (store, service, alice, bob):
        record = store.add_memory(f"profile:{alice}", {"kind": "hypothesis", "text": "Piste"})
        ctx = service.profile_context(alice, TARGET, options={"angle": "developmental"})
        output = {"title": "Lecture", "reading_focus": "general", "reading_angle": "developmental", "global_synthesis": "Une dynamique.",
                  "claims": [], "questions": [], "cautions": [], "knowledge_version": ctx["knowledge_version"], "rule_ids_used": ["rule:pedagogy"],
                  "theme_hypotheses": [{"text": "Piste nouvelle", "status": "proposed", "evidence": ["profile.life_path_challenge"], "counterevidence": [], "rule_refs": ["rule:pedagogy"]}],
                  "practice_suggestions": [{"text": "Observer ses réactions", "kind": "observe", "evidence": ["profile.life_path_challenge"]}]}
        validate_llm_output(output, ctx)
        bad = deepcopy(output)
        bad["claims"] = [{"text": "Un vécu certain", "kind": "user_report", "evidence": [record["ref"]], "rule_refs": []}]
        expect_error(lambda: validate_llm_output(bad, ctx))
        bad = deepcopy(output)
        bad["practice_suggestions"][0]["evidence"] = ["memory:9999"]
        expect_error(lambda: validate_llm_output(bad, ctx))
        bad = deepcopy(output)
        bad["reading_angle"] = "existential"
        expect_error(lambda: validate_llm_output(bad, ctx))
        bad_context = deepcopy(ctx)
        bad_context["personal"]["records"][record["ref"]]["subject_key"] = f"profile:{bob}"
        expect_error(lambda: validate_context(bad_context))
        assert json.loads(json.dumps(ctx, ensure_ascii=False)) == ctx


def test_comparisons_have_no_composite_card_or_shared_memory():
    with sample() as (store, service, alice, bob):
        result = service.compare_profiles([alice, bob, alice], TARGET)
        assert len(result["contexts"]) == 2
        assert result["mode"] == "subjects_at_date"
        assert "composite_card" not in result
        for ctx in result["contexts"]:
            validate_context(ctx)
        expect_error(lambda: service.compare_profiles([], TARGET))
