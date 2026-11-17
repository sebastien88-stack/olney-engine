"""Deterministic, fully offline calculation of Olney's hour card."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import math

from astro_engine import local_datetime_to_utc, parse_local_time, resolve_place


# The printed HOUR CARDS chart is a 24-card window moving through this
# circular 52-card sequence.  Row N / hour H therefore uses index N - 1 + H.
# Face names use the French labels already used by Olney (V, D, R).
HOUR_CARD_SEQUENCE = (
    "A♥", "7♠", "5♦", "3♣", "2♣", "V♠", "6♠", "4♦", "3♦", "A♣",
    "V♥", "5♠", "4♠", "2♦", "D♠", "10♥", "5♥", "R♦", "D♣", "7♣",
    "6♣", "4♥", "8♦", "9♠", "7♦", "5♣", "3♥", "D♦", "8♠", "6♥",
    "9♦", "8♣", "9♥", "3♠", "A♦", "V♣", "10♠", "6♦", "4♣", "2♥",
    "V♦", "9♣", "8♥", "A♠", "D♥", "7♥", "10♦", "R♣", "R♠", "10♣",
    "R♥", "2♠",
)

SUIT_STARTS = {"♥": 1, "♣": 14, "♦": 27, "♠": 40}
RANK_VALUES = {
    "A": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "V": 11,
    "D": 12,
    "R": 13,
}


def _validate_sequence() -> None:
    if len(HOUR_CARD_SEQUENCE) != 52 or len(set(HOUR_CARD_SEQUENCE)) != 52:
        raise RuntimeError("La séquence HOUR CARDS doit contenir les 52 cartes une fois.")


_validate_sequence()


def card_number(card: str) -> int:
    """Return the card number used by data.json for an Olney card label."""
    suit = card[-1]
    rank = card[:-1]
    return SUIT_STARTS[suit] + RANK_VALUES[rank] - 1


def hour_row_for_date(value: date) -> int:
    """Collapse day 1..366 onto the printed chart's row 1..52."""
    return ((value.timetuple().tm_yday - 1) % 52) + 1


def equation_of_time_minutes(local_datetime: datetime) -> float:
    """NOAA approximation: apparent solar time minus mean solar time."""
    day_of_year = local_datetime.timetuple().tm_yday
    fractional_hour = (
        local_datetime.hour
        + local_datetime.minute / 60.0
        + local_datetime.second / 3600.0
    )
    gamma = 2.0 * math.pi / 365.0 * (
        day_of_year - 1 + (fractional_hour - 12.0) / 24.0
    )
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2.0 * gamma)
        - 0.040849 * math.sin(2.0 * gamma)
    )


def calculate_true_solar_time(
    analyzed_date: date,
    analyzed_time: str,
    analyzed_place: str,
) -> dict:
    """Calculate true solar time from civil time, timezone and longitude."""
    place = resolve_place(analyzed_place)
    local_time = parse_local_time(analyzed_time)
    local_datetime = datetime.combine(analyzed_date, local_time)
    utc_datetime = local_datetime_to_utc(analyzed_date, local_time, place)

    longitude_minutes = place.longitude * 4.0
    equation_minutes = equation_of_time_minutes(local_datetime)
    solar_datetime = utc_datetime.replace(tzinfo=None) + timedelta(
        minutes=longitude_minutes + equation_minutes
    )

    return {
        "analyzed_datetime_local": local_datetime.isoformat(),
        "analyzed_datetime_utc": utc_datetime.isoformat(),
        "place": f"{place.name}, {place.country_code}",
        "timezone": place.timezone,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "longitude_correction_minutes": round(longitude_minutes, 4),
        "equation_of_time_minutes": round(equation_minutes, 4),
        "solar_datetime": solar_datetime.isoformat(),
        "solar_time": solar_datetime.strftime("%H:%M"),
        "solar_hour": solar_datetime.hour,
    }


def get_hour_card(
    analyzed_date: date,
    analyzed_time: str,
    analyzed_place: str,
) -> dict:
    """Return the HOUR CARDS lookup and all deterministic calculation facts."""
    solar = calculate_true_solar_time(
        analyzed_date, analyzed_time, analyzed_place
    )
    day_of_year = analyzed_date.timetuple().tm_yday
    hour_row = hour_row_for_date(analyzed_date)
    sequence_index = (hour_row - 1 + solar["solar_hour"]) % 52
    card = HOUR_CARD_SEQUENCE[sequence_index]

    return {
        **solar,
        "date": analyzed_date.isoformat(),
        "time_local": parse_local_time(analyzed_time).strftime("%H:%M"),
        "day_of_year": day_of_year,
        "hour_row": hour_row,
        "hour_column": solar["solar_hour"],
        "sequence_index": sequence_index,
        "card_number": card_number(card),
        "card": card,
    }
