from datetime import date
from version import APP_VERSION
from olney_engine import OlneyEngine

def test_data_shape():
    e = OlneyEngine()
    assert len(e.series) == 90
    for seq in e.series.values():
        assert len(seq) == 52
        assert set(seq) == set(range(1, 53))

def test_birth_card():
    e = OlneyEngine()
    # 18/05 => 55-(18+10)=27
    assert e.birth_card_number("1965-05-18") == 27
    assert e.card_label(27) == "A♦"

def test_time_state():
    e = OlneyEngine()
    ts = e.time_state("1965-05-18", "2025-02-20")
    assert ts.days_elapsed == (date(2025,2,20)-date(1965,5,18)).days
    assert 1 <= ts.weekday_position <= 7
    assert 1 <= ts.cycle_90_series <= 90

def test_full_state_json_ready():
    e = OlneyEngine()
    state = e.full_state("1965-05-18", "2025-02-20")
    assert state["birth"]["card_number"] == 27
    assert len(state["seven_year"]["rows"]) == 9
    assert len(state["year"]["rows"]) == 9
    assert len(state["week"]["rows"]) == 9
    assert len(state["day"]["rows"]) == 7
    assert len(state["life_path"]["rows"]) == 11


def test_full_state_can_include_the_analyzed_hour_card():
    e = OlneyEngine()
    state = e.full_state(
        "1988-10-27",
        "2026-08-26",
        target_time="17:51",
        target_place="Longjumeau, FR",
    )
    assert state["engine_version"] == APP_VERSION
    assert state["hour_card"]["card"] == "D♥"
    assert state["hour_card"]["solar_time"] == "15:58"


def test_year_card_known_case_1988_10_27():
    e = OlneyEngine()
    state = e.full_state("1988-10-27", "2026-08-26")
    assert state["time"]["age"] == 37
    assert state["time"]["age_seven_year_series"] == 6
    assert state["year"]["year_card"] == "A♥"


def test_full_table_layout_and_names():
    e = OlneyEngine()
    layout = e.full_table_layout(6)
    cells = layout["top"] + [cell for row in layout["grid"] for cell in row]
    assert len(cells) == 52
    assert {cell["position"] for cell in cells} == set(range(1, 53))
    assert e.table_name(1) == "Tableau 0.1"
    assert e.table_name(6) == "Tableau 5"
    assert e.table_name(90) == "Tableau 89"


def test_table_planet_coordinates():
    e = OlneyEngine()
    # In the natural order, 8♥ is position 9: Venus row, Mercury column.
    assert e.find_card_position(90, 8) == 9
    assert e.table_coordinates(9) == {
        "zone": "grille",
        "row_planet": "vénus",
        "column_planet": "mercure",
    }
    assert e.table_coordinates(1) == {
        "zone": "couronne",
        "row_planet": None,
        "column_planet": None,
    }


def test_positional_exchange_uses_natural_order_only_for_life_path():
    e = OlneyEngine()
    birth_number = e.birth_card_number("1988-10-27")

    life_path = e.positional_exchange(90, 1, birth_number)
    assert life_path["card"] == "8♥"
    assert life_path["displacement"]["card"] == "7♠"
    assert life_path["environment"]["card"] == "7♥"

    seven_year = e.positional_exchange(1, 6, birth_number)
    assert seven_year["displacement"]["card"] == "9♦"
    assert seven_year["environment"]["card"] == "9♠"


def test_december_31_is_joker_without_ordinary_cycles():
    e = OlneyEngine()
    state = e.full_state("1988-12-31", "2026-08-26")
    assert state["joker"] is True
    assert state["birth"] == {"card_number": 0, "card": "Joker"}
    assert state["seven_year"] is None
    assert state["year"] is None
    assert state["week"] is None
    assert state["fifty_two_day"] is None
    assert state["day"] is None


def test_annual_tables_loop_after_age_89_through_age_180():
    e = OlneyEngine()
    birth = "1900-10-27"
    expected = {
        89: 90,
        90: 1,
        91: 2,
        179: 90,
        180: 1,
    }
    for age, internal_series in expected.items():
        target = e.anniversary_date(birth, age)
        state = e.full_state(birth, target)
        assert state["time"]["age"] == age
        assert state["time"]["age_year_cycle_number"] == age + 1
        assert state["time"]["age_year_series"] == internal_series
        assert state["year"]["series_id"] == internal_series
        assert state["fifty_two_day"]["series_id"] == internal_series
    assert e.table_name(expected[89]) == "Tableau 89"
    assert e.table_name(expected[90]) == "Tableau 0.1"


def test_clock_navigation_keeps_one_coherent_date():
    e = OlneyEngine()
    birth = "1988-10-27"
    target = "2026-08-26"
    assert e.navigate_date(birth, target, "day", 1).isoformat() == "2026-08-27"
    assert e.navigate_date(birth, target, "year", 1).isoformat() == "2026-10-27"
    assert e.navigate_date(birth, target, "year", -1).isoformat() == "2024-10-27"

    next_year = e.full_state(birth, e.navigate_date(birth, target, "year", 1))
    assert next_year["target_date"] == "2026-10-27"
    assert next_year["time"]["age"] == 38

    current_window = e.fifty_two_day_window(birth, target)
    next_cycle = e.navigate_date(birth, target, "fifty_two_day", 1)
    assert next_cycle.isoformat() == current_window["end"]
    assert e.fifty_two_day_window(birth, next_cycle)["start"] == next_cycle.isoformat()


def test_fifty_two_day_boundary_changes_on_september_fifth_not_fourth():
    e = OlneyEngine()
    birth = "1988-10-27"

    september_fourth = e.full_state(birth, "2026-09-04")
    assert september_fourth["fifty_two_day"]["window"]["start"] == "2026-07-15"
    assert september_fourth["fifty_two_day"]["window"]["end"] == "2026-09-05"
    assert september_fourth["fifty_two_day"]["card"] == "A♠"

    september_fifth = e.full_state(birth, "2026-09-05")
    assert september_fifth["fifty_two_day"]["window"]["start"] == "2026-09-05"
    assert september_fifth["fifty_two_day"]["window"]["end"] == "2026-10-27"
    assert september_fifth["fifty_two_day"]["card"] == "R♦"


def test_fifty_two_day_navigation_has_no_duplicate_at_birthday():
    e = OlneyEngine()
    birth = "1988-10-27"

    birthday = e.full_state(birth, "2026-10-27")
    assert birthday["fifty_two_day"]["window"]["start"] == "2026-10-27"
    assert birthday["fifty_two_day"]["window"]["end"] == "2026-12-19"
    assert birthday["fifty_two_day"]["card"] == "3♦"

    next_date = e.navigate_date(birth, "2026-10-27", "fifty_two_day", 1)
    assert next_date.isoformat() == "2026-12-19"
    next_cycle = e.full_state(birth, next_date)
    assert next_cycle["fifty_two_day"]["window"]["start"] == "2026-12-19"
    assert next_cycle["fifty_two_day"]["window"]["end"] == "2027-02-09"
    assert next_cycle["fifty_two_day"]["card"] == "2♣"

    following_date = e.navigate_date(birth, next_date, "fifty_two_day", 1)
    following_cycle = e.full_state(birth, following_date)
    assert following_date.isoformat() == "2027-02-09"
    assert following_cycle["fifty_two_day"]["card"] == "7♠"


def test_annual_period_opens_and_closes_on_exact_anniversaries():
    e = OlneyEngine()
    state = e.full_state("1988-10-27", "2026-10-27")
    dated_rows = [row for row in state["year"]["rows"] if row.get("period_start")]
    assert dated_rows[0]["period_start"] == "2026-10-27"
    assert dated_rows[-1]["period_end"] == "2027-10-27"


def test_complete_reading_has_11_distinct_cards():
    e = OlneyEngine()
    cards = e.relative_cards(6, e.birth_card_number("1988-10-27"))
    assert len(cards) == 11
    assert len({card.card_number for card in cards.values()}) == 11


def test_base_order_tables_are_complete():
    e = OlneyEngine()
    for series_id in (90, 1):
        layout = e.full_table_layout(series_id)
        cells = layout["top"] + [cell for row in layout["grid"] for cell in row]
        assert len(cells) == 52
        assert {cell["card_number"] for cell in cells} == set(range(1, 53))


def test_base_orders_support_moon_to_result_readings():
    e = OlneyEngine()
    birth_number = e.birth_card_number("1988-10-27")
    for series_id in (90, 1):
        reading = e.relative_cards(series_id, birth_number)
        assert len(reading) == 11
        assert list(reading)[0] == "lune"
        assert list(reading)[-1] == "résultat"


def test_fixed_and_semi_fixed_cards_across_all_tables():
    e = OlneyEngine()
    card_numbers = {label: number for number, label in e.cards.items()}

    def positions(label):
        number = card_numbers[label]
        return {e.find_card_position(series_id, number) for series_id in range(1, 91)}

    assert positions("R♠") == {1}
    assert positions("V♥") == {12}
    assert positions("8♣") == {22}
    assert positions("A♣") == positions("2♥") == {3, 15}
    assert positions("7♦") == positions("9♥") == {10, 34}


def test_life_path_uses_seven_thirteen_year_periods():
    e = OlneyEngine()
    state = e.full_state("1988-10-27", "2026-08-26")
    path = state["life_path"]

    assert path["age"] == 37
    assert path["active_slot"] == "mars"
    assert path["active_age_range"] == "26 – 38 ans"
    assert path["card"] == next(
        row["card"] for row in path["rows"] if row["slot"] == "mars"
    )

    planet_rows = [
        row for row in path["rows"]
        if row["slot"] in ("mercure", "vénus", "mars", "jupiter", "saturne", "uranus", "neptune")
    ]
    assert [row["age_range"] for row in planet_rows] == [
        "0 – 12 ans",
        "13 – 25 ans",
        "26 – 38 ans",
        "39 – 51 ans",
        "52 – 64 ans",
        "65 – 77 ans",
        "78 – 90 ans",
    ]


def test_life_path_restarts_after_ninety_years():
    e = OlneyEngine()
    before_restart = e.life_path_table("2000-01-01", "2090-01-01")
    after_restart = e.life_path_table("2000-01-01", "2091-01-01")

    assert before_restart["active_slot"] == "neptune"
    assert after_restart["active_slot"] == "mercure"
    assert before_restart["active_age_range"] == "78 – 90 ans"
    assert after_restart["active_age_range"] == "91 – 103 ans"


def test_life_path_navigation_moves_to_thirteen_year_boundaries():
    e = OlneyEngine()
    birth = "1988-10-27"

    previous_date = e.navigate_date(birth, "2026-08-26", "life_path", -1)
    next_date = e.navigate_date(birth, "2026-08-26", "life_path", 1)

    assert previous_date.isoformat() == "2001-10-27"
    assert next_date.isoformat() == "2027-10-27"
    assert e.full_state(birth, previous_date)["life_path"]["active_slot"] == "vénus"
    assert e.full_state(birth, next_date)["life_path"]["active_slot"] == "jupiter"


def test_scorpio_secondary_cards_use_mars_and_pluto_in_table_zero_one():
    e = OlneyEngine()
    secondary = e.secondary_cards("1988-10-27")

    assert secondary["sign"] == "Scorpion"
    assert [(item["ruler"], item["card"]) for item in secondary["cards"]] == [
        ("mars", "D♥"),
        ("pluton", "A♣"),
    ]


def test_only_scorpio_uses_two_secondary_card_rulers():
    e = OlneyEngine()

    assert [item["ruler"] for item in e.secondary_cards("1990-02-01")["cards"]] == [
        "uranus"
    ]
    assert [item["ruler"] for item in e.secondary_cards("1990-03-01")["cards"]] == [
        "neptune"
    ]
    assert [item["ruler"] for item in e.secondary_cards("1990-04-01")["cards"]] == [
        "mars"
    ]
