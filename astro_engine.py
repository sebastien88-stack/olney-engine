"""Offline birth-place lookup and tropical ascendant calculation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ZODIAC_SIGNS = (
    ("Bélier", "♈"),
    ("Taureau", "♉"),
    ("Gémeaux", "♊"),
    ("Cancer", "♋"),
    ("Lion", "♌"),
    ("Vierge", "♍"),
    ("Balance", "♎"),
    ("Scorpion", "♏"),
    ("Sagittaire", "♐"),
    ("Capricorne", "♑"),
    ("Verseau", "♒"),
    ("Poissons", "♓"),
)

COUNTRY_ALIASES = {
    "france": "FR",
    "belgique": "BE",
    "suisse": "CH",
    "canada": "CA",
    "royaume uni": "GB",
    "etats unis": "US",
    "espagne": "ES",
    "italie": "IT",
    "allemagne": "DE",
    "portugal": "PT",
}


@dataclass(frozen=True)
class Place:
    name: str
    country_code: str
    latitude: float
    longitude: float
    timezone: str
    population: int


def _normalise(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


@lru_cache(maxsize=1)
def _place_rows() -> list[list]:
    source = Path(__file__).with_name("places.json")
    return json.loads(source.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _place_index() -> dict[str, list[list]]:
    index: dict[str, list[list]] = {}
    for row in _place_rows():
        for candidate in {row[0], row[1]}:
            key = _normalise(candidate)
            if key:
                index.setdefault(key, []).append(row)
    return index


@lru_cache(maxsize=1)
def _search_rows() -> list[tuple[str, str, list]]:
    return [(_normalise(row[0]), _normalise(row[1]), row) for row in _place_rows()]


def resolve_place(query: str) -> Place:
    """Resolve `City` or `City, country code` from the bundled GeoNames index."""
    parts = [part.strip() for part in query.split(",") if part.strip()]
    if not parts:
        raise ValueError("Renseigne une ville.")

    candidates = list(_place_index().get(_normalise(parts[0]), ()))
    if len(parts) > 1:
        country_text = _normalise(parts[-1])
        country_code = COUNTRY_ALIASES.get(country_text, parts[-1].strip().upper())
        candidates = [row for row in candidates if row[2] == country_code]

    if not candidates:
        raise ValueError(
            "Ville introuvable dans la base locale. Essaie « Ville, FR » pour préciser le pays."
        )

    row = max(candidates, key=lambda item: item[6])
    return Place(
        name=row[0],
        country_code=row[2],
        latitude=float(row[3]),
        longitude=float(row[4]),
        timezone=row[5],
        population=int(row[6]),
    )


def suggest_places(query: str, limit: int = 8) -> list[str]:
    """Return population-ranked offline city suggestions for an editable field."""
    parts = [part.strip() for part in query.split(",") if part.strip()]
    if not parts or len(_normalise(parts[0])) < 2:
        return []

    name_prefix = _normalise(parts[0])
    country_code = None
    if len(parts) > 1:
        country_text = _normalise(parts[-1])
        country_code = COUNTRY_ALIASES.get(country_text, parts[-1].strip().upper())

    suggestions = []
    for normal_name, normal_ascii, row in _search_rows():
        if country_code and row[2] != country_code:
            continue
        if not normal_name.startswith(name_prefix) and not normal_ascii.startswith(name_prefix):
            continue
        suggestions.append(row)

    suggestions.sort(
        key=lambda item: (
            0 if country_code or item[2] == "FR" else 1,
            -item[6],
            item[0],
            item[2],
        )
    )
    labels = []
    for row in suggestions:
        label = f"{row[0]}, {row[2]}"
        if label not in labels:
            labels.append(label)
        if len(labels) >= max(1, limit):
            break
    return labels


def parse_local_time(value: str) -> time:
    for pattern in ("%H:%M", "%Hh%M", "%H.%M"):
        try:
            return datetime.strptime(value.strip(), pattern).time()
        except ValueError:
            pass
    raise ValueError("Heure invalide. Utilise le format HH:MM, par exemple 07:51.")


def parse_birth_time(value: str) -> time:
    """Backward-compatible name used by the ascendant UI."""
    return parse_local_time(value)


def local_datetime_to_utc(local_date: date, local_time: time, place: Place) -> datetime:
    """Convert a civil local time with the bundled historical timezone rules."""
    try:
        zone = ZoneInfo(place.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Fuseau horaire indisponible : {place.timezone}") from exc

    local_naive = datetime.combine(local_date, local_time)
    local = local_naive.replace(tzinfo=zone)
    utc = local.astimezone(timezone.utc)
    round_trip = utc.astimezone(zone).replace(tzinfo=None)
    if round_trip != local_naive:
        raise ValueError(
            "Cette heure locale n'existait pas lors du changement d'heure. "
            "Vérifie l'heure indiquée."
        )
    return utc


def _local_datetime_to_utc(birth_date: date, birth_time: time, place: Place) -> datetime:
    """Compatibility wrapper for the original ascendant implementation."""
    return local_datetime_to_utc(birth_date, birth_time, place)


def _julian_day(utc_datetime: datetime) -> float:
    return utc_datetime.timestamp() / 86400.0 + 2440587.5


def _mean_obliquity_degrees(julian_day: float) -> float:
    centuries = (julian_day - 2451545.0) / 36525.0
    seconds = (
        21.448
        - 46.8150 * centuries
        - 0.00059 * centuries**2
        + 0.001813 * centuries**3
    )
    return 23.0 + 26.0 / 60.0 + seconds / 3600.0


def _greenwich_sidereal_degrees(julian_day: float) -> float:
    centuries = (julian_day - 2451545.0) / 36525.0
    return (
        280.46061837
        + 360.98564736629 * (julian_day - 2451545.0)
        + 0.000387933 * centuries**2
        - centuries**3 / 38710000.0
    ) % 360.0


def _ascendant_longitude(julian_day: float, latitude: float, longitude: float) -> float:
    sidereal = math.radians((_greenwich_sidereal_degrees(julian_day) + longitude) % 360.0)
    obliquity = math.radians(_mean_obliquity_degrees(julian_day))
    latitude_rad = math.radians(latitude)
    western_intersection = math.degrees(
        math.atan2(
            -math.cos(sidereal),
            math.sin(sidereal) * math.cos(obliquity)
            + math.tan(latitude_rad) * math.sin(obliquity),
        )
    ) % 360.0
    return (western_intersection + 180.0) % 360.0


def calculate_ascendant(birth_date: date, birth_time_text: str, place_text: str) -> dict:
    place = resolve_place(place_text)
    birth_time = parse_birth_time(birth_time_text)
    utc_datetime = _local_datetime_to_utc(birth_date, birth_time, place)
    julian_day = _julian_day(utc_datetime)
    longitude = _ascendant_longitude(julian_day, place.latitude, place.longitude)
    rounded_arcminutes = int(round(longitude * 60.0)) % (360 * 60)
    rounded_longitude = rounded_arcminutes / 60.0
    sign_index = int(rounded_longitude // 30.0) % 12
    sign, symbol = ZODIAC_SIGNS[sign_index]
    sign_arcminutes = rounded_arcminutes % (30 * 60)
    degrees, minutes = divmod(sign_arcminutes, 60)

    return {
        "sign": sign,
        "symbol": symbol,
        "longitude": round(longitude, 6),
        "degree": degrees,
        "minute": minutes,
        "display": f"{symbol} {sign}  {degrees:02d}°{minutes:02d}′",
        "display_sign": f"{symbol} {sign}",
        "birth_time_local": birth_time.strftime("%H:%M"),
        "birth_datetime_utc": utc_datetime.isoformat(),
        "utc_offset_minutes": int(
            datetime.combine(birth_date, birth_time)
            .replace(tzinfo=ZoneInfo(place.timezone))
            .utcoffset()
            .total_seconds()
            // 60
        ),
        "place": asdict(place),
        "julian_day": julian_day,
        "local_sidereal_degrees": round(
            (_greenwich_sidereal_degrees(julian_day) + place.longitude) % 360.0,
            6,
        ),
    }
