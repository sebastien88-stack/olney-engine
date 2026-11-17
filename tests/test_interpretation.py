import json
from pathlib import Path

from interpretation_runtime import (
    InterpretationContextBuilder,
    InterpretationKnowledge,
    card_id_from_label,
)
from olney_engine import OlneyEngine


def test_interpretation_knowledge_has_52_complete_polarities():
    knowledge = InterpretationKnowledge.load()
    assert len(knowledge.cards) == 52
    assert set(knowledge.cards) == set(knowledge.polarities)
    assert all(item["constructive"] for item in knowledge.polarities.values())
    assert all(item["difficult"] for item in knowledge.polarities.values())


def test_all_engine_card_labels_have_stable_interpretation_ids():
    engine = OlneyEngine()
    knowledge = InterpretationKnowledge.load()
    descriptions = [knowledge.describe_card(label) for label in engine.cards.values()]
    assert len({item["id"] for item in descriptions}) == 52
    assert card_id_from_label("V♥") == "JH"
    assert card_id_from_label("D♦") == "QD"
    assert card_id_from_label("R♠") == "KS"


def test_density_and_fixed_semantics_are_exposed():
    knowledge = InterpretationKnowledge.load()
    assert knowledge.describe_card("8♥")["density_rank"] == 1
    assert knowledge.describe_card("8♣")["density_rank"] == 2
    assert knowledge.describe_card("8♦")["density_rank"] == 3
    king_spades = knowledge.describe_card("R♠")
    assert king_spades["density_rank"] == 4
    assert "fixed" in king_spades["special"]
    assert "most_powerful_and_dense" in king_spades["special"]
    assert "semi_fixed" in knowledge.describe_card("A♣")["special"]


def test_context_contains_nested_current_cycles_and_life_path_direction():
    engine = OlneyEngine()
    context = InterpretationContextBuilder(engine).from_dates(
        "1988-10-27", "2026-08-26"
    )
    assert [cycle["id"] for cycle in context["cycles"]] == [
        "natal", "life_path", "seven_year", "annual", "week"
    ]
    assert context["profile"]["birth_card"]["label"] == "8♥"
    assert [item["label"] for item in context["profile"]["secondary_cards"]] == [
        "D♥", "A♣"
    ]
    life_path = context["cycles"][1]
    assert life_path["sequence_planet"] == "mars"
    assert context["global_direction"]["result"] == life_path["result"]
    assert all(cycle["lived_polarity"] == "unknown" for cycle in context["cycles"])


def test_profile_history_selects_a_branch_without_removing_both_texts():
    engine = OlneyEngine()
    base = InterpretationContextBuilder(engine).from_dates(
        "1988-10-27", "2026-08-26"
    )
    annual = next(cycle for cycle in base["cycles"] if cycle["id"] == "annual")
    history = [{
        "occurrence_id": annual["occurrence_id"],
        "source_type": "user_reported",
        "cycle_id": "annual",
        "card_id": annual["active_card"]["id"],
        "polarity": "constructive",
        "user_note": "Période bien intégrée",
        "confidence": 0.9,
    }]
    context = InterpretationContextBuilder(engine).from_dates(
        "1988-10-27", "2026-08-26", profile_history=history
    )
    annual = next(cycle for cycle in context["cycles"] if cycle["id"] == "annual")
    assert annual["lived_polarity"] == "constructive"
    assert annual["active_card"]["constructive"]
    assert annual["active_card"]["difficult"]


def test_hour_card_is_enriched_without_inventing_a_table_position():
    engine = OlneyEngine()
    context = InterpretationContextBuilder(engine).from_dates(
        "1988-10-27", "2026-08-26", "17:51", "Longjumeau, FR"
    )
    assert context["hour_card"]["card"]["label"] == "D♥"
    assert "position" not in context["hour_card"]
    assert context["hour_card"]["scope"].startswith("tonalité immédiate")


def test_joker_context_respects_pending_canonical_decision():
    engine = OlneyEngine()
    context = InterpretationContextBuilder(engine).from_dates(
        "2000-12-31", "2026-08-26"
    )
    assert context["joker"] is True
    assert context["cycles"] == []
    assert context["profile"]["birth_card"]["id"] == "JOKER"
    assert "joker_interpretation_choice" in context["pending_rules"]


def test_interpretation_schemas_are_valid_json():
    base = Path(__file__).resolve().parents[1] / "interpretation" / "schemas"
    for path in base.glob("*.json"):
        assert json.loads(path.read_text(encoding="utf-8"))
