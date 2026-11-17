from copy import deepcopy
from datetime import date, timedelta

from cycle_reading import CYCLE_FOCUS, CycleCalendarMismatch, present_status
from interpretation_runtime import InterpretationKnowledge, InterpretationContextBuilder
from interpretation_validation import validate_context, validate_llm_output
from olney_engine import OlneyEngine


ENGINE = OlneyEngine()
KNOWLEDGE = InterpretationKnowledge.load()
BUILDER = InterpretationContextBuilder(ENGINE, KNOWLEDGE)
BIRTH = "1988-10-27"
TARGET = "2026-08-26"


def dossier(focus="week", birth=BIRTH, target=TARGET, **kwargs):
    return BUILDER.from_dates(birth, target, reading_focus=focus, reading_mode="cycle", **kwargs)


def must_fail(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("Expected an invalid cycle reading to be rejected")


def test_cycle_reading_is_explicit_and_preserves_current_context():
    normal = BUILDER.from_dates(BIRTH, TARGET)
    assert normal["cycle_reading"] is None
    focused = BUILDER.from_dates(BIRTH, TARGET, reading_focus="week")
    full = dossier()
    validate_context(full)
    assert full["cycles"] == focused["cycles"]
    assert full["profile"] == normal["profile"]
    assert full["synthesis"] == focused["synthesis"]
    assert full["cycle_reading"]["reference_card_id"] == full["profile"]["birth_card"]["id"]
    assert full["cycle_reading"]["result"] != full["cycle_reading"]["steps"][-1]["card"]


def test_all_cycle_views_have_ordered_steps_dates_and_one_current_card():
    for cid, focus in CYCLE_FOCUS.items():
        ctx = dossier(focus)
        validate_context(ctx)
        cycle = next(c for c in ctx["cycles"] if c["id"] == cid)
        reading = ctx["cycle_reading"]
        assert [s["sequence_planet"] for s in reading["steps"]] == ["mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune"]
        assert len(reading["steps"]) == 7 and len(reading["transitions"]) == 6
        current = reading["steps"][reading["current_step_index"]]
        assert current["card"] == cycle["active_card"]
        assert current["position"] == cycle["position"]
        assert current["occurrence_id"] == cycle["occurrence_id"]
        assert reading["moon_card"] == cycle["moon_card"]
        assert reading["challenge"] == cycle["challenge"]
        assert reading["result"] == cycle["result"]
        assert reading["steps"][0]["from_previous"] is None
        assert reading["steps"][-1]["into_next"] is None


def test_seven_stage_exploration_matches_the_engine_for_all_52_birth_cards():
    birthdays = {}
    start = date(2000, 1, 1)
    for offset in range(366):
        birth = start + timedelta(days=offset)
        number = ENGINE.birth_card_number(birth)
        if number:
            birthdays.setdefault(number, birth.isoformat())
    assert len(birthdays) == 52
    keys = {"life_path": ("life_path", "card"), "seven_year": ("year", "year_card"),
            "annual": ("fifty_two_day", "card"), "week": ("day", "card")}
    for birth in birthdays.values():
        for cid, focus in CYCLE_FOCUS.items():
            ctx = dossier(focus, birth=birth)
            validate_context(ctx)
            for step in ctx["cycle_reading"]["steps"]:
                start_date = date.fromisoformat(step["period"]["start"])
                state = ENGINE.full_state(birth, start_date)
                container, key = keys[cid]
                assert state[container][key] == step["card"]["label"], (birth, cid, step["index"], start_date)


def test_cycle_periods_at_birth_leap_day_year_end_and_91_year_restart():
    for birth, target in ((BIRTH, BIRTH), ("2000-02-29", "2025-02-28"),
                          (BIRTH, "2026-12-31"), (BIRTH, "2079-10-27")):
        for focus in CYCLE_FOCUS.values():
            ctx = dossier(focus, birth=birth, target=target)
            validate_context(ctx)
            reading = ctx["cycle_reading"]
            assert reading["period"]["start"] <= target < reading["period"]["end"]
            assert all(s["period"]["start"] >= birth for s in reading["steps"])


def test_existing_30_360_boundary_is_reported_instead_of_reading_the_wrong_card():
    # Preserve the existing engine convention; do not silently change all clocks.
    assert ENGINE.age("2000-01-01", "2012-12-31") == 13
    assert ENGINE.anniversary_date("2000-01-01", 13).isoformat() == "2013-01-01"
    try:
        dossier("life_path", birth="2000-01-01", target="2012-12-31")
    except CycleCalendarMismatch:
        pass
    else:
        raise AssertionError("A calendar/clock mismatch must not become a reading")
    validate_context(dossier("life_path", birth="2000-01-01", target="2013-01-01"))


def test_stage_status_never_infers_a_lived_polarity():
    ctx = dossier("year")
    reading = ctx["cycle_reading"]
    assert any(s["timing"] == "past" for s in reading["steps"])
    assert any(s["timing"] == "upcoming" for s in reading["steps"])
    assert all(s["lived_polarity"] == "unknown" for s in reading["steps"])
    step = reading["steps"][0]
    report = {"source_type": "user_reported", "occurrence_id": step["occurrence_id"],
              "cycle_id": reading["cycle_id"], "card_id": step["card"]["id"], "polarity": "difficult"}
    updated = dossier("year", profile_history=[report])
    validate_context(updated)
    assert updated["cycle_reading"]["steps"][0]["lived_polarity"] == "difficult"
    assert all(s["lived_polarity"] == "unknown" for s in updated["cycle_reading"]["steps"][1:])
    next_year = dossier("year", target=step["period"]["start"], profile_history=[report])
    validate_context(next_year)
    active = next(c for c in next_year["cycles"] if c["id"] == "seven_year")
    assert active["lived_polarity"] == "difficult"


def test_cycle_elements_and_features_are_distinct_from_clock_convergences():
    ctx = dossier()
    reading = ctx["cycle_reading"]
    assert sum(g["count"] for g in reading["elements"]) == 7
    assert ctx["synthesis"]["elements"]["total_active_cards"] == 4
    assert not any(f["kind"] == "active_card_repetition" for f in reading["features"])
    assert any(f["kind"] == "king_spades" for f in reading["features"])
    for step in reading["steps"]:
        position = step["position"]
        if position["zone"] == "couronne":
            assert position["context_planets"] == []
            assert "♛ Couronne" in step["badges"]
        if position["context_amplified"]:
            assert len(set(position["context_planets"])) == 1
        assert step["sequence_planet"]
    assert reading["parent_context"]["at_date"] == TARGET
    assert reading["parent_context"]["scope"] == "at_analysis_date_only"


def test_invalid_cycle_modes_and_joker_are_handled():
    for focus in ("general", "natal", "hour"):
        must_fail(lambda: dossier(focus))
    must_fail(lambda: BUILDER.from_dates(BIRTH, TARGET, reading_mode="invented"))
    for focus in CYCLE_FOCUS.values():
        joker = dossier(focus, birth="2000-12-31")
        validate_context(joker)
        assert joker["cycle_reading"] is None and not joker["cycles"]


def test_cycle_contract_rejects_wrong_order_dates_and_reference_roles():
    for mutate in (
        lambda r: r["steps"].reverse(),
        lambda r: r["steps"][0].update(timing="current"),
        lambda r: r["steps"][0]["period"].update(end="2028-01-01"),
        lambda r: r.update(current_step_index=0),
        lambda r: r.update(result=r["steps"][-1]["card"]),
        lambda r: r["elements"][0].update(count=7),
        lambda r: r["transitions"][0].update(to_index=3),
        lambda r: r["parent_context"].update(at_date="2020-01-01"),
    ):
        broken = dossier()
        mutate(broken["cycle_reading"])
        must_fail(lambda: validate_context(broken))


def test_full_cycle_context_does_not_mutate_engine_data_or_other_readings():
    state = ENGINE.full_state(BIRTH, TARGET)
    before = deepcopy(state)
    first = BUILDER.from_state(state, reading_focus="week", reading_mode="cycle")
    first["cycle_reading"]["steps"][0]["card"]["keywords"].append("test-only")
    second = dossier()
    assert state == before
    assert "test-only" not in second["cycle_reading"]["steps"][0]["card"]["keywords"]
    for step in second["cycle_reading"]["steps"]:
        for card in (step["card"], step["position"]["owner_card"], step["position"]["support_card"]):
            assert card["id"] in second["knowledge_bundle"]["card_profiles"]


def test_future_llm_output_must_follow_the_requested_sequence():
    ctx = dossier()
    reading = ctx["cycle_reading"]
    output = {"title": "Le parcours", "reading_focus": "week", "reading_mode": "cycle", "global_synthesis": "Une lecture de la séquence.",
              "claims": [], "questions": [], "cautions": [], "knowledge_version": ctx["knowledge_version"], "rule_ids_used": ["rule:cycles"],
              "cycle_reading": {"cycle_id": "week", "summary": "Mouvement du cycle", "evidence": ["cycle_reading.steps"],
                                "steps": [{"step_index": s["index"], "card_id": s["card"]["id"], "summary": s["summary"],
                                           "evidence": [f"cycle_reading.steps.{s['index']}.card"]} for s in reading["steps"]]}}
    validate_llm_output(output, ctx)
    broken = deepcopy(output)
    del broken["reading_mode"]
    must_fail(lambda: validate_llm_output(broken, ctx))
    broken = deepcopy(output)
    broken["cycle_reading"]["steps"].reverse()
    must_fail(lambda: validate_llm_output(broken, ctx))
    broken = deepcopy(output)
    del broken["cycle_reading"]
    must_fail(lambda: validate_llm_output(broken, ctx))


def test_present_status_ignores_explored_date_in_all_four_cycles():
    for focus in CYCLE_FOCUS.values():
        reading = dossier(focus)["cycle_reading"]
        today_status = present_status(reading, TARGET)
        index = reading["current_step_index"]
        assert today_status["current_step_index"] == index
        other_index = (index + 1) % 7
        other_date = reading["steps"][other_index]["period"]["start"]
        explored = dossier(focus, target=other_date)["cycle_reading"]
        assert explored["current_step_index"] == other_index
        assert present_status(explored, TARGET) == today_status
        assert present_status(explored, TARGET)["step_timings"][other_index] != "current"


def test_present_status_has_no_current_outside_cycle_and_exact_boundaries():
    for focus in CYCLE_FOCUS.values():
        reading = dossier(focus)["cycle_reading"]
        before = date.fromisoformat(reading["period"]["start"]) - timedelta(days=1)
        after = reading["period"]["end"]
        assert present_status(reading, before)["step_timings"] == ["upcoming"] * 7
        assert present_status(reading, after)["step_timings"] == ["past"] * 7
        assert present_status(reading, before)["current_step_index"] is None
        assert present_status(reading, after)["current_step_index"] is None
        for step in reading["steps"]:
            assert present_status(reading, step["period"]["start"])["current_step_index"] == step["index"]
            last = date.fromisoformat(step["period"]["end"]) - timedelta(days=1)
            assert present_status(reading, last)["current_step_index"] == step["index"]


def test_llm_present_snapshot_is_explicit_and_validated():
    ctx = dossier(target="2040-01-01")
    assert ctx["cycle_reading"]["present"]["date"] == date.today().isoformat()
    validate_context(ctx)
    ctx["cycle_reading"]["present"] = present_status(ctx["cycle_reading"], TARGET)
    validate_context(ctx)
    ctx["cycle_reading"]["present"]["current_step_index"] = 0
    must_fail(lambda: validate_context(ctx))
