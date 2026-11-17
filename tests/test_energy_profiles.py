from copy import deepcopy
from dataclasses import replace
import re

from interpretation_runtime import InterpretationKnowledge, InterpretationContextBuilder
from interpretation_text import card_essential, card_focus
from interpretation_validation import validate_context, resolve_evidence
from olney_engine import OlneyEngine


KNOWLEDGE = InterpretationKnowledge.load()
ENGINE = OlneyEngine()
BUILDER = InterpretationContextBuilder(ENGINE, KNOWLEDGE)
PILOTS = {"AC", "8H", "9H", "5S", "KS"}
ELEMENTS = {"hearts": "Feu", "clubs": "Air", "diamonds": "Eau", "spades": "Terre"}


def context(**kwargs):
    return BUILDER.from_dates("1988-10-27", "2026-08-26", **kwargs)


def must_fail(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("Expected a validation error")


def test_all_52_energy_profiles_are_complete_and_individual():
    assert set(KNOWLEDGE.profiles) == set(KNOWLEDGE.cards)
    assert len(KNOWLEDGE.profiles) == 52
    assert len({p["energy"] for p in KNOWLEDGE.profiles.values()}) == 52
    assert len({p["title"] for p in KNOWLEDGE.profiles.values()}) == 52
    for profile in KNOWLEDGE.profiles.values():
        assert all(profile.get(field) for field in (
            "title", "movement", "energy", "constructive", "difficult", "manifestations", "cycles", "source_refs"))
        assert len(" ".join(profile[field] for field in ("energy", "constructive", "difficult", "manifestations", "cycles")).split()) >= 150
        assert "Une énergie" in profile["energy"]
        assert all(ref["source_id"] in KNOWLEDGE.provenance["sources"] for ref in profile["source_refs"])
    assert {cid for cid, p in KNOWLEDGE.profiles.items() if p["review_status"] == "user_validated_pilot"} == PILOTS
    assert sum(p["review_status"] == "editorial_extension" for p in KNOWLEDGE.profiles.values()) == 47


def test_approved_pilot_bodies_are_preserved_in_active_profiles():
    text = (KNOWLEDGE.base_path / "drafts" / "FICHES_PILOTES_V0.3.md").read_text(encoding="utf-8")
    ids = {"A♣": "AC", "8♥": "8H", "9♥": "9H", "5♠": "5S", "R♠": "KS"}
    names = {"L’énergie": "energy", "Vécu constructif": "constructive", "Vécu difficile": "difficult", "Dans la vie": "manifestations", "Au fil des cycles": "cycles"}
    for block in text.split("\n## ")[1:]:
        heading, _, body = block.partition("\n")
        label = heading.split(" — ")[0]
        if label not in ids:
            continue
        profile = KNOWLEDGE.profiles[ids[label]]
        body = body.split("\n---")[0].strip()
        for name, value in re.findall(r"\*\*(.+?)\.\*\*\s*([\s\S]*?)(?=\n\*\*|$)", body):
            field = names[name]
            if field == "cycles" and ids[label] in {"AC", "9H", "KS"}:
                value, special = value.strip().split("\n\n", 1)
                assert profile["special_note"] == special
            assert profile[field] == value.strip()


def test_profile_mobility_notes_match_actual_fixed_and_dual_cards():
    fixed = set(KNOWLEDGE.rules["mobility"]["fixed_cards"]["cards"])
    dual = {cid for pair in KNOWLEDGE.rules["mobility"]["semi_fixed_pairs"] for cid in pair["cards"]}
    assert fixed == {"JH", "8C", "KS"}
    for cid, profile in KNOWLEDGE.profiles.items():
        note = profile.get("special_note", "")
        if cid in fixed:
            assert "fixe" in note
        elif cid in dual:
            assert "semi-fixe" in note and "duale" in note
        else:
            assert "fixité" not in profile["cycles"]
            assert "fixe" not in note


def test_elements_are_available_for_every_individual_card():
    for label in ENGINE.cards.values():
        card = KNOWLEDGE.describe_card(label)
        suit = KNOWLEDGE.suits[card["suit"]]
        assert card["element"] == ELEMENTS[card["suit"]]
        assert card["element_ref"] == f"knowledge_bundle.suits.{card['suit']}"
        assert suit["element_reading"]["individual"] in card_essential(card, KNOWLEDGE)
        assert KNOWLEDGE.profiles[card["id"]]["energy"] in card_essential(card, KNOWLEDGE)
        assert card_focus(card) == KNOWLEDGE.profiles[card["id"]]["movement"]


def test_profile_bundle_is_targeted_deduplicated_and_resolvable():
    ctx = context(reading_focus="week")
    validate_context(ctx)
    seen = []

    def walk(value):
        if isinstance(value, dict):
            if "profile_ref" in value:
                seen.append(value["id"])
                assert resolve_evidence(ctx, value["profile_ref"]) == KNOWLEDGE.profiles[value["id"]]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for key in ("profile", "cycles", "hour_card", "global_direction"):
        walk(ctx[key])
    assert set(seen) == set(ctx["knowledge_bundle"]["card_profiles"])
    assert len(seen) > len(set(seen))
    assert len(set(seen)) < 52
    assert ctx["knowledge_bundle"]["pilot_drafts_included"] is False


def test_element_summary_counts_active_occurrences_not_natal_or_palette():
    for kwargs, count in (({}, 4), ({"target_time": "17:51", "target_place": "Longjumeau, FR"}, 5)):
        ctx = context(**kwargs)
        validate_context(ctx)
        summary = ctx["synthesis"]["elements"]
        assert summary["total_active_cards"] == count
        assert sum(g["count"] for g in summary["groups"]) == count
        cycles = [cid for g in summary["groups"] for cid in g["cycle_ids"]]
        assert len(cycles) == len(set(cycles))
        assert "natal" not in cycles
        assert ("hour" in cycles) == (count == 5)
        for group in summary["groups"]:
            assert group["element"] == ELEMENTS[group["suit"]]
            assert group["count"] == len(group["cycle_ids"])
            assert all(resolve_evidence(ctx, ref)["suit"] == group["suit"] for ref in group["evidence"])
        repeats = [o for o in ctx["synthesis"]["observations"] if o["kind"] == "shared_suit"]
        assert len(repeats) == len([g for g in summary["groups"] if g["count"] > 1])
        assert len({o["suit"] for o in repeats}) == len(repeats)


def test_hour_and_joker_keep_their_specific_boundaries():
    ctx = context(target_time="17:51", target_place="Longjumeau, FR", reading_focus="hour")
    validate_context(ctx)
    assert "profile_ref" in ctx["hour_card"]["card"]
    assert not {"sequence_planet", "position", "moon_card", "challenge", "result"} & set(ctx["hour_card"])
    joker = BUILDER.from_dates("2000-12-31", "2026-08-26")
    validate_context(joker)
    assert joker["knowledge_bundle"]["card_profiles"] == {}
    assert joker["synthesis"]["elements"]["groups"] == []
    assert "JOKER" not in KNOWLEDGE.profiles


def test_profile_history_cannot_inject_extra_card_profiles_or_elements():
    normal = context()
    spoof = {"id": "KS", "profile_ref": "knowledge_bundle.card_profiles.KS", "suit": "spades", "element": "Terre"}
    injected = context(profile_history=[spoof])
    validate_context(injected)
    assert injected["knowledge_bundle"]["card_profiles"] == normal["knowledge_bundle"]["card_profiles"]
    assert injected["synthesis"]["elements"] == normal["synthesis"]["elements"]
    injected["knowledge_bundle"]["card_profiles"][next(iter(injected["knowledge_bundle"]["card_profiles"]))]["energy"] = "changed"
    assert KNOWLEDGE.profiles == InterpretationKnowledge.load().profiles


def test_contract_rejects_broken_profiles_and_element_claims():
    ctx = context()
    for field, value in (("profile_ref", "knowledge_bundle.card_profiles.KS"), ("element", "Eau"), ("energy_focus", "Invented")):
        broken = deepcopy(ctx)
        broken["profile"]["birth_card"][field] = value
        must_fail(lambda: validate_context(broken))
    broken = deepcopy(ctx)
    del broken["knowledge_bundle"]["card_profiles"]["8H"]
    must_fail(lambda: validate_context(broken))
    broken = deepcopy(ctx)
    broken["synthesis"]["elements"]["groups"][0]["count"] += 1
    must_fail(lambda: validate_context(broken))
    broken = deepcopy(ctx)
    broken["knowledge_bundle"]["suits"]["hearts"]["element"] = "Eau"
    must_fail(lambda: validate_context(broken))
    broken = deepcopy(ctx)
    broken["knowledge_bundle"]["card_profiles"]["8H"]["energy"] = 42
    must_fail(lambda: validate_context(broken))


def test_static_knowledge_rejects_missing_profiles_and_swapped_elements():
    profiles = deepcopy(KNOWLEDGE.profiles)
    del profiles["AS"]
    must_fail(lambda: replace(KNOWLEDGE, profiles=profiles).validate())
    suits = deepcopy(KNOWLEDGE.suits)
    suits["hearts"]["element"] = "Eau"
    must_fail(lambda: replace(KNOWLEDGE, suits=suits).validate())
