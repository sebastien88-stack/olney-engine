from cycle_reading_ui import CycleReadingView
from interpretation_runtime import InterpretationContextBuilder, InterpretationKnowledge
from olney_engine import OlneyEngine


def make_view(focus="year"):
    engine = OlneyEngine()
    knowledge = InterpretationKnowledge.load()
    context = InterpretationContextBuilder(engine, knowledge).from_dates(
        "1988-10-27", "2026-08-26", reading_focus=focus, reading_mode="cycle"
    )
    view = object.__new__(CycleReadingView)
    view.context = context
    view.selected_index = context["cycle_reading"]["current_step_index"]
    view.selected_role = None
    view._render = lambda: None
    view._scroll_to_detail = lambda: None
    return engine, view


def test_every_result_slot_matches_its_cycle_card_without_date_navigation():
    for focus in ("life_path", "year", "fifty_two_days", "week"):
        engine, view = make_view(focus)
        before = view.context
        reading = before["cycle_reading"]
        birth_number = engine.birth_card_number("1988-10-27")
        rows = engine.relative_cards(reading["series_id"], birth_number)
        for slot, card in rows.items():
            assert view.select_slot(slot, expected_card=card.card_label), (focus, slot, card)
            if slot in ("lune", "soleil", "défi", "résultat"):
                assert view.selected_role == slot and view.selected_index is None
            else:
                selected = reading["steps"][view.selected_index]
                assert selected["sequence_planet"] == slot
                assert selected["card"]["label"] == card.card_label
                assert view.selected_role is None
        assert view.context is before


def test_wrong_or_stale_card_link_does_not_change_selection():
    _, view = make_view()
    selected = view.selected_index
    assert not view.select_slot("mars", expected_card="invalid")
    assert not view.select_slot("invalid-slot")
    assert view.selected_index == selected and view.selected_role is None


def test_selecting_sequence_after_support_card_restores_step_mode():
    _, view = make_view()
    assert view.select_slot("résultat")
    view.select_step(0)
    assert view.selected_index == 0 and view.selected_role is None
