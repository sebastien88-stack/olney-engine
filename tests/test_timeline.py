from datetime import date, datetime, timedelta

from olney_engine import OlneyEngine
from timeline_runtime import TimelineEngine
from timeline_ui import shift_date_for_zoom


def test_timeline_periods_reuse_canonical_boundaries():
    engine = OlneyEngine()
    timeline = TimelineEngine(engine)
    birth = date(1988, 10, 27)
    periods = timeline.get_periods(birth, date(2025, 1, 1), date(2027, 1, 1))

    seven = [p for p in periods if p["level"] == "seven_year"]
    life_path = [p for p in periods if p["level"] == "life_path"]
    annual = [p for p in periods if p["level"] == "annual"]
    short = [p for p in periods if p["level"] == "fifty_two_day"]

    assert any(
        p["start"] == "2023-10-27"
        and p["end_exclusive"] == "2030-10-27"
        and p["label"] == "Tableau 6"
        for p in seven
    )
    active_life_path = next(
        p for p in life_path
        if p["start"] == "2014-10-27" and p["end_exclusive"] == "2027-10-27"
    )
    assert active_life_path["card"] == "D♥"
    assert active_life_path["age_start"] == 26
    assert active_life_path["age_end"] == 38
    current_year = next(p for p in annual if p["start"] == "2025-10-27")
    assert current_year["end_exclusive"] == "2026-10-27"
    assert current_year["card"] == "A♥"
    assert current_year["sequence_planet"] == "mars"
    current_short = next(p for p in short if p["start"] == "2026-07-15")
    assert current_short["end_exclusive"] == "2026-09-05"
    assert current_short["card"] == "A♠"


def test_timeline_occurrences_and_transitions_are_queryable():
    engine = OlneyEngine()
    timeline = TimelineEngine(engine)
    birth = date(1988, 10, 27)
    start = date(2020, 1, 1)
    end = date(2030, 1, 1)

    occurrences = timeline.find_card_occurrences(
        birth, "A♥", start, end, levels=("annual",)
    )
    assert any(item["start"] == "2025-10-27" for item in occurrences)

    transitions = timeline.get_transitions(
        birth, date(2025, 10, 1), date(2027, 1, 1), levels=("annual",)
    )
    assert any(item["date"] == "2025-10-27" for item in transitions)
    assert all(item["type"] == "cycle_change" for item in transitions)


def test_timeline_is_empty_for_joker_birth():
    timeline = TimelineEngine(OlneyEngine())
    assert timeline.get_periods(
        date(2000, 12, 31), date(2000, 12, 31), date(2010, 1, 1)
    ) == []


def test_daily_timeline_uses_the_canonical_day_card_and_week_boundaries():
    engine = OlneyEngine()
    timeline = TimelineEngine(engine)
    birth = date(1988, 10, 27)
    periods = timeline.get_periods(
        birth, date(2026, 8, 24), date(2026, 8, 29), levels=("day",)
    )

    assert len(periods) == 5
    august_26 = next(item for item in periods if item["start"] == "2026-08-26")
    assert august_26["card"] == engine.day_table(birth, date(2026, 8, 26))["card"]
    assert august_26["end_exclusive"] == "2026-08-27"
    assert 1 <= august_26["weekday_position"] <= 7


def test_timeline_navigation_step_follows_zoom_level():
    value = date(2026, 8, 27)
    assert shift_date_for_zoom(value, 0, 1) == date(2033, 8, 27)
    assert shift_date_for_zoom(value, 1, -1) == date(2023, 8, 27)
    assert shift_date_for_zoom(value, 2, 1) == date(2027, 8, 27)
    assert shift_date_for_zoom(value, 3, 1) == date(2027, 2, 27)
    assert shift_date_for_zoom(value, 4, -1) == date(2026, 5, 27)
    assert shift_date_for_zoom(value, 5, 1) == date(2026, 10, 11)
    assert shift_date_for_zoom(value, 6, -1) == date(2026, 8, 20)
    assert shift_date_for_zoom(value, 7, 1) == date(2026, 8, 28)
    moment = datetime(2026, 8, 27, 12, 0)
    assert shift_date_for_zoom(moment, 8, 1) == datetime(2026, 8, 27, 18, 0)
    assert shift_date_for_zoom(moment, 9, -1) == datetime(2026, 8, 27, 11, 0)
    assert shift_date_for_zoom(date(2024, 2, 29), 2, 1) == date(2025, 2, 28)


def test_hour_timeline_is_continuous_and_uses_the_offline_hour_card():
    engine = OlneyEngine()
    timeline = TimelineEngine(engine)
    start = datetime(2026, 8, 26, 15, 0)
    end = datetime(2026, 8, 26, 18, 0)
    periods = timeline.get_hour_periods(start, end, "Longjumeau, FR")

    assert periods[0]["start"] == "2026-08-26T15:00"
    assert periods[-1]["end_exclusive"] == "2026-08-26T18:00"
    assert all(
        previous["end_exclusive"] == current["start"]
        for previous, current in zip(periods, periods[1:])
    )
    moment = datetime(2026, 8, 26, 17, 51)
    active = next(
        item for item in periods
        if datetime.fromisoformat(item["start"]) <= moment
        < datetime.fromisoformat(item["end_exclusive"])
    )
    assert active["card"] == engine.hour_card(
        moment.date(), moment.strftime("%H:%M"), "Longjumeau, FR"
    )["card"]
