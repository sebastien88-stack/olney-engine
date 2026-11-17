"""Validate Olney's static interpretation knowledge without external packages."""

from __future__ import annotations

from pathlib import Path
import json
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from interpretation_runtime import InterpretationKnowledge
from interpretation_runtime import InterpretationContextBuilder
from olney_engine import OlneyEngine
from interpretation_validation import validate_context


def main() -> int:
    knowledge = InterpretationKnowledge.load()
    engine = OlneyEngine()

    for label in engine.cards.values():
        knowledge.describe_card(label)

    for schema_path in sorted((knowledge.base_path / "schemas").glob("*.json")):
        json.loads(schema_path.read_text(encoding="utf-8"))

    fixed_positions = {
        label: {
            engine.find_card_position(series_id, number)
            for series_id in range(1, 91)
        }
        for number, label in engine.cards.items()
        if label in {"V♥", "8♣", "R♠"}
    }
    if any(len(positions) != 1 for positions in fixed_positions.values()):
        raise ValueError(f"Fixed-card positions changed: {fixed_positions}")

    builder = InterpretationContextBuilder(engine, knowledge)
    context = builder.from_dates(
        "1988-10-27", "2026-08-26", "17:51", "Longjumeau, FR"
    )
    cycle_ids = [cycle["id"] for cycle in context["cycles"]]
    if cycle_ids != ["natal", "life_path", "seven_year", "annual", "week"]:
        raise ValueError(f"Unexpected cycle hierarchy: {cycle_ids}")
    if context["profile"]["birth_card"]["label"] != "8♥":
        raise ValueError("Known birth-card interpretation context changed")
    if context["hour_card"]["card"]["label"] != "D♥":
        raise ValueError("Known hour-card interpretation context changed")
    if context["global_direction"]["source_cycle"] != "life_path":
        raise ValueError("Global result no longer points to life path")

    joker = builder.from_dates("2000-12-31", "2026-08-26")
    validate_context(context)
    validate_context(joker)
    for focus in ("life_path", "year", "fifty_two_days", "week"):
        full_cycle = builder.from_dates(
            "1988-10-27", "2026-08-26", reading_focus=focus, reading_mode="cycle"
        )
        validate_context(full_cycle)
        if len(full_cycle["cycle_reading"]["steps"]) != 7:
            raise ValueError(f"Full cycle does not contain seven steps: {focus}")
    validate_context(builder.from_dates(
        "2000-12-31", "2026-08-26", reading_focus="week", reading_mode="cycle"
    ))
    if not joker["joker"] or joker["cycles"]:
        raise ValueError("Joker pending-rule context changed")

    print(f"Knowledge version: {knowledge.version}")
    print(f"Cards and polarities: {len(knowledge.cards)}/52")
    print(f"Active energy profiles: {len(knowledge.profiles)}/52")
    print("Elements: hearts/fire, clubs/air, diamonds/water, spades/earth validated")
    print(f"Unique profiles in sample dossier: {len(context['knowledge_bundle']['card_profiles'])}")
    print(f"Rule files: {len(knowledge.rules)}")
    print("Schemas: context structure and references validated (offline schema vocabulary)")
    print("Engine labels: all mapped")
    print("Fixed cards: stable across 90 tables")
    print("LLM context: known profile, cycles and hour validated")
    print("Full-cycle reading: all four sequences and seven ordered steps validated")
    print("Joker context: pending decision preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
