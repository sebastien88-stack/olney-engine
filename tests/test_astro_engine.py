from datetime import date

from astro_engine import calculate_ascendant, parse_birth_time, resolve_place, suggest_places


def test_offline_place_lookup_finds_longjumeau():
    place = resolve_place("Longjumeau, FR")
    assert place.country_code == "FR"
    assert place.timezone == "Europe/Paris"
    assert abs(place.latitude - 48.69307) < 0.00001
    assert abs(place.longitude - 2.29431) < 0.00001


def test_city_autocomplete_returns_country_qualified_suggestions():
    suggestions = suggest_places("Longj", limit=5)
    assert "Longjumeau, FR" in suggestions


def test_birth_time_accepts_common_french_formats():
    assert parse_birth_time("07:51").strftime("%H:%M") == "07:51"
    assert parse_birth_time("7h51").strftime("%H:%M") == "07:51"


def test_reference_ascendant_uses_historical_paris_timezone():
    result = calculate_ascendant(date(1988, 10, 27), "07:51", "Longjumeau, FR")

    assert result["birth_datetime_utc"] == "1988-10-27T06:51:00+00:00"
    assert result["utc_offset_minutes"] == 60
    assert result["sign"] == "Scorpion"
    assert result["degree"] == 6
    assert result["minute"] == 57
    assert result["display_sign"] == "♏ Scorpion"


def test_timezone_database_applies_summer_time():
    result = calculate_ascendant(date(2026, 8, 26), "17:51", "Longjumeau, FR")
    assert result["birth_datetime_utc"] == "2026-08-26T15:51:00+00:00"
    assert result["utc_offset_minutes"] == 120
