from datetime import date

from hour_card import (
    HOUR_CARD_SEQUENCE,
    calculate_true_solar_time,
    get_hour_card,
    hour_row_for_date,
)


def test_hour_card_sequence_is_a_complete_deck():
    assert len(HOUR_CARD_SEQUENCE) == 52
    assert len(set(HOUR_CARD_SEQUENCE)) == 52


def test_day_of_year_wraps_to_the_printed_52_rows():
    assert hour_row_for_date(date(2025, 1, 1)) == 1
    assert hour_row_for_date(date(2026, 8, 26)) == 30
    assert hour_row_for_date(date(1988, 10, 27)) == 41
    assert hour_row_for_date(date(2024, 12, 31)) == 2


def test_reference_1988_longjumeau_returns_king_of_clubs():
    result = get_hour_card(date(1988, 10, 27), "07:51", "Longjumeau, FR")
    assert result["hour_row"] == 41
    assert result["solar_hour"] == 7
    assert result["card"] == "R♣"
    assert result["card_number"] == 26


def test_reference_2026_longjumeau_returns_queen_of_hearts():
    result = get_hour_card(date(2026, 8, 26), "17:51", "Longjumeau, FR")
    assert result["day_of_year"] == 238
    assert result["hour_row"] == 30
    assert result["solar_time"] == "15:58"
    assert result["solar_hour"] == 15
    assert result["card"] == "D♥"


def test_reference_next_solar_hour_returns_seven_of_hearts():
    result = get_hour_card(date(2026, 8, 26), "18:32", "Longjumeau, FR")
    assert result["hour_row"] == 30
    assert result["solar_time"] == "16:39"
    assert result["solar_hour"] == 16
    assert result["card"] == "7♥"


def test_solar_time_uses_historical_timezone_rules():
    winter = calculate_true_solar_time(
        date(1988, 10, 27), "07:51", "Longjumeau, FR"
    )
    summer = calculate_true_solar_time(
        date(2026, 8, 26), "17:51", "Longjumeau, FR"
    )
    assert winter["analyzed_datetime_utc"] == "1988-10-27T06:51:00+00:00"
    assert summer["analyzed_datetime_utc"] == "2026-08-26T15:51:00+00:00"
